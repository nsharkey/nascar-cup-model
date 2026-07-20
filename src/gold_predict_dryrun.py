#!/usr/bin/env python3
"""DRY-RUN ONLY -- specs/medallion_architecture.md section 7.3 step 2 (dual-run identity check).

Generates the weekly prediction payload for a race via the GOLD path -- gold.wf_features for
training (mirrors predict_next.py's single-final-fit training loop, section 5.2), gold.driver_form
/ gold.driver_type_form for current form (section 5.3) -- and returns it in-memory. Writes nothing
to predictions/. predict_next.py is NOT modified and remains the path of record; this file's sole
purpose is proving the gold path reproduces the legacy path's output before section 7.3's owner-
gated cutover happens. At actual cutover, this logic (not this file) is what gets folded into
predict_next.py in place.

Run from src/: `python gold_predict_dryrun.py <race_id>`.
"""
import datetime
import json
import sys
import urllib.request

import duckdb
import numpy as np

import warehouse
from walkforward import wmean, znan, pl_fit

HL, BURN, MIN_HIST, MIN_DRV = 8, 15, 5, 20
FEATS = ['fin', 'pace', 'typed', 'start']


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
        return json.load(r)


def _load_wf_by_race_seq(con):
    cols = ['race_id', 'driver_id', 'race_seq', 'n_hist', 'fin_h', 'pace_h', 'typ_h',
            'start_feat', 'has_pace', 'finish']
    rows = con.sql(f"SELECT {', '.join(cols)} FROM gold.wf_features "
                    f"ORDER BY race_seq, driver_id").fetchall()
    by_seq = {}
    for r in rows:
        rec = dict(zip(cols, r))
        by_seq.setdefault(rec['race_seq'], []).append(rec)
    return by_seq


def fit_weights_from_gold(con):
    """Mirrors predict_next.py's training loop exactly: accumulate every burn/eligibility-
    passing race's (X, order) pair across the full scope-ordered race list (no year windowing),
    single final pl_fit call at the end -- NOT gate_gold.py's incremental walk-forward refit
    (that machinery validates; this is a live final-model fit, matching predict_next.py's own
    single `w = pl_fit(Xs, Os)` call)."""
    by_seq = _load_wf_by_race_seq(con)
    seqs = sorted(by_seq)
    Xs, Os = [], []
    for idx, seq in enumerate(seqs):
        recs = by_seq[seq]
        elig = [r for r in recs if r['n_hist'] >= MIN_HIST and r['has_pace']]
        if idx >= BURN and len(elig) >= MIN_DRV:
            actual = np.array([r['finish'] for r in elig], float)
            start = np.array([r['start_feat'] for r in elig], float)
            fin_h = np.array([r['fin_h'] for r in elig], float)
            pace_h = np.array([r['pace_h'] for r in elig], float)
            typ_h = np.array([r['typ_h'] for r in elig], float)
            bank = dict(fin=znan(fin_h), pace=znan(pace_h), typed=znan(typ_h), start=znan(start))
            X = np.column_stack([bank[k] for k in FEATS])
            Xs.append(-X)
            Os.append(np.argsort(actual))
    w = pl_fit(Xs, Os)
    last_race_id = by_seq[seqs[-1]][0]['race_id']
    trained_through = con.execute(
        "SELECT race_date FROM silver.races WHERE race_id = ? AND series_id = 1",
        [last_race_id]).fetchone()[0]
    return w, len(Xs), str(trained_through)[:10]


def current_form(con, ids, tt):
    """Section 5.3: 'predict_next (post-cutover) computes typ_h from these plus the target
    race's ttype.' Mirrors predict_next.py's hf/hp/ht lookups exactly, sourced from the
    current-form views instead of an in-memory replay dict."""
    fcols = ['driver_id', 'n_hist', 'fin_h', 'pace_h']
    form = {r[0]: dict(zip(fcols, r)) for r in con.sql(
        f"SELECT {', '.join(fcols)} FROM gold.driver_form").fetchall()}
    tcols = ['driver_id', 'm', 'typed_wmean']
    tform = {r[0]: dict(zip(tcols, r)) for r in con.execute(
        "SELECT driver_id, m, typed_wmean FROM gold.driver_type_form WHERE ttype = ?", [tt]
    ).fetchall()}

    hist_n, fin_h, pace_h, typ_h = [], [], [], []
    for d in ids:
        rec = form.get(d)
        if rec is None or not rec['n_hist']:
            hist_n.append(0); fin_h.append(np.nan); pace_h.append(np.nan); typ_h.append(np.nan)
            continue
        hist_n.append(rec['n_hist'])
        fh = rec['fin_h'] if rec['fin_h'] is not None else np.nan
        ph = rec['pace_h'] if rec['pace_h'] is not None else np.nan
        fin_h.append(fh)
        pace_h.append(ph)
        trec = tform.get(d)
        if trec and trec['m']:
            typ_h.append((trec['m'] * trec['typed_wmean'] + 3 * fh) / (trec['m'] + 3))
        else:
            typ_h.append(fh)
    return hist_n, fin_h, pace_h, typ_h


def build_gold_prediction(race_id):
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    w, n_train, trained_through = fit_weights_from_gold(con)

    year = datetime.date.today().year
    rl = fetch(f'https://cf.nascar.com/cacher/{year}/race_list_basic.json')['series_1']
    matches = [r for r in rl if r.get('race_type_id') == 1 and r['race_id'] == race_id]
    if not matches:
        raise SystemExit(f'race {race_id} not found in {year} points races')
    nxt = matches[0]
    track, rdate = nxt['track_name'], nxt['race_date'][:10]

    tt_row = con.execute("SELECT ttype FROM gold.track_typology WHERE track_name = ?", [track]).fetchone()
    tt = tt_row[0] if tt_row else 'UNIQ'

    wf = fetch(f'https://cf.nascar.com/cacher/{year}/1/{race_id}/weekend-feed.json')
    res = (wf.get('weekend_race') or [{}])[0].get('results') or []
    if any(x.get('finishing_position') for x in res):
        raise SystemExit(f'race {race_id} already has results -- refusing a post-hoc prediction')
    entries = [x for x in res if x.get('starting_position')]
    if len(entries) < MIN_DRV:
        raise SystemExit(f'grid not posted yet for {track} {rdate}')

    ids = [e['driver_id'] for e in entries]
    names = {e['driver_id']: e['driver_fullname'] for e in entries}
    start = np.array([e['starting_position'] for e in entries], float)
    hist_n, fin_h, pace_h, typ_h = current_form(con, ids, tt)
    con.close()

    bank = dict(fin=znan(fin_h), pace=znan(pace_h), typed=znan(typ_h), start=znan(start))
    X = np.column_stack([bank[k] for k in FEATS])
    util = -(X @ w)
    order = np.argsort(-util)

    rng = np.random.default_rng(5618)
    NS = 40000
    g = rng.gumbel(size=(NS, len(ids)))
    ranks = np.argsort(-(util[None, :] + g), axis=1)
    pos = np.empty_like(ranks)
    rows_idx = np.arange(NS)[:, None]
    pos[rows_idx, ranks] = np.arange(len(ids))[None, :]
    p_win = (pos == 0).mean(0)
    p_top5 = (pos < 5).mean(0)
    p_top10 = (pos < 10).mean(0)
    h2h = 1.0 / (1.0 + np.exp(-(util[:, None] - util[None, :])))

    return {
        'race_id': race_id, 'track': track, 'track_type': tt, 'race_date': rdate,
        'config': dict(pace='pace_med85', hl=HL, feats=FEATS, typology='MY_TYPE',
                        typed='shrinkage', lam=0.5),
        'trained_through': trained_through, 'n_train_races': n_train,
        'weights': dict(zip(FEATS, [round(float(x), 6) for x in w])),
        'field': [dict(driver_id=int(d), name=names[d], grid=int(start[i]),
                       n_hist=int(hist_n[i]), utility=round(float(util[i]), 4),
                       pred_rank=int(np.where(order == i)[0][0]) + 1,
                       p_win=round(float(p_win[i]), 4), p_top5=round(float(p_top5[i]), 4),
                       p_top10=round(float(p_top10[i]), 4))
                  for i, d in enumerate(ids)],
        'h2h_prob': {str(ids[i]): {str(ids[j]): round(float(h2h[i, j]), 4)
                                   for j in range(len(ids)) if j != i} for i in range(len(ids))},
        'book_prices': {'note': 'fill in matchup/win prices at close, then score', 'entries': []},
        'stand_down': tt == 'SS',
    }


if __name__ == '__main__':
    payload = build_gold_prediction(int(sys.argv[1]))
    print(json.dumps(payload, sort_keys=True, indent=1))
