#!/usr/bin/env python3
"""Forward-test harness. Generates a timestamped, tamper-evident prediction log
for the next scheduled Cup points race, using the audit-validated PL config:
  pace_med85, half-life 8, corrected typology (MY_TYPE), shrinkage typed history,
  features [fin, pace, typed, start], burn=15, min_hist=5, min_drv=20, lam=0.5.
Run after qualifying posts. Re-running before the race overwrites cleanly;
running after the race refuses (results already known -> not a forward pick).
"""
import json, hashlib, datetime, urllib.request, os, sys
import numpy as np
from walkforward import RACES, MY_TYPE, wmean, znan, pl_fit

HL, BURN, MIN_HIST, MIN_DRV = 8, 15, 5, 20
PACE_KEY = 'pace_med85'
FEATS = ['fin', 'pace', 'typed', 'start']
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'predictions')
os.makedirs(OUT_DIR, exist_ok=True)

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
        return json.load(r)

# ---- 1. replay history + build PL training set (mirrors walkforward.run) ----
hf, hp, ht = {}, {}, {}
Xs, Os = [], []
completed_ids = set()
for idx, race in enumerate(RACES):
    tt = MY_TYPE.get(race['track'], 'UNIQ')
    drivers = race['drivers']
    completed_ids.add(race['rid'])
    if idx >= BURN:
        elig = [d for d in drivers
                if d in hf and len(hf[d]) >= MIN_HIST and drivers[d].get(PACE_KEY) is not None]
        if len(elig) >= MIN_DRV:
            actual = np.array([drivers[d]['finish'] for d in elig], float)
            start = np.array([drivers[d]['start'] if drivers[d]['start'] else 20 for d in elig], float)
            fin_h = np.array([wmean(hf[d], HL) for d in elig])
            pace_h = np.array([wmean(hp[d], HL) for d in elig])
            typ_h = []
            for d in elig:
                th = ht.get((d, tt), [])
                base = wmean(hf[d], HL)
                typ_h.append((len(th) * wmean(th, HL) + 3 * base) / (len(th) + 3) if th else base)
            typ_h = np.array(typ_h)
            bank = dict(fin=znan(fin_h), pace=znan(pace_h), typed=znan(typ_h), start=znan(start))
            X = np.column_stack([bank[k] for k in FEATS])
            Xs.append(-X)                       # negate: higher utility = better
            Os.append(np.argsort(actual))       # best finisher first
    for d, v in drivers.items():
        hf.setdefault(d, []).append(v['finish'])
        if v.get(PACE_KEY) is not None:
            hp.setdefault(d, []).append(v[PACE_KEY])
        ht.setdefault((d, tt), []).append(v['finish'])

w = pl_fit(Xs, Os)
last_done = max(RACES, key=lambda r: r['date'])
print(f"trained on {len(Xs)} races through {last_done['date'][:10]} ({last_done['track']})")
print("fitted weights:", dict(zip(FEATS, np.round(w, 4))))

# ---- 2. find next race + live grid -----------------------------------------
year = datetime.date.today().year
rl = fetch(f'https://cf.nascar.com/cacher/{year}/race_list_basic.json')['series_1']
pts = [r for r in rl if r.get('race_type_id') == 1]
upcoming = sorted((r for r in pts if not r.get('winner_driver_id')
                   and r['race_id'] not in completed_ids), key=lambda r: r['race_date'])
if not upcoming:
    sys.exit('no upcoming race found')
nxt = upcoming[0]
rid, track, rdate = nxt['race_id'], nxt['track_name'], nxt['race_date'][:10]
tt = MY_TYPE.get(track, 'UNIQ')
wf = fetch(f'https://cf.nascar.com/cacher/{year}/1/{rid}/weekend-feed.json')
res = (wf.get('weekend_race') or [{}])[0].get('results') or []
if any(x.get('finishing_position') for x in res):
    sys.exit(f'race {rid} already has results -- refusing to log a post-hoc "prediction"')
entries = [x for x in res if x.get('starting_position')]
if len(entries) < MIN_DRV:
    sys.exit(f'grid not posted yet for {track} {rdate} ({len(entries)} starters set)')
print(f"\nnext race: {track} ({tt}) {rdate}, race_id {rid}, {len(entries)} starters, grid posted")

# ---- 3. features for the field ---------------------------------------------
ids = [e['driver_id'] for e in entries]
names = {e['driver_id']: e['driver_fullname'] for e in entries}
start = np.array([e['starting_position'] for e in entries], float)
fin_h, pace_h, typ_h, hist_n = [], [], [], []
for d in ids:
    fh, ph, th = hf.get(d, []), hp.get(d, []), ht.get((d, tt), [])
    hist_n.append(len(fh))
    fin_h.append(wmean(fh, HL) if fh else np.nan)
    pace_h.append(wmean(ph, HL) if ph else np.nan)
    if fh:
        base = wmean(fh, HL)
        typ_h.append((len(th) * wmean(th, HL) + 3 * base) / (len(th) + 3) if th else base)
    else:
        typ_h.append(np.nan)
bank = dict(fin=znan(fin_h), pace=znan(pace_h), typed=znan(typ_h), start=znan(start))
X = np.column_stack([bank[k] for k in FEATS])
util = -(X @ w)                                 # higher = better
order = np.argsort(-util)

# ---- 4. probabilities: P(win/top5/top10) by PL sampling, full H2H matrix ---
rng = np.random.default_rng(5618)
NS = 40000
g = rng.gumbel(size=(NS, len(ids)))
ranks = np.argsort(-(util[None, :] + g), axis=1)   # sampled finishing orders
pos = np.empty_like(ranks)
rows_idx = np.arange(NS)[:, None]
pos[rows_idx, ranks] = np.arange(len(ids))[None, :]
p_win = (pos == 0).mean(0)
p_top5 = (pos < 5).mean(0)
p_top10 = (pos < 10).mean(0)
h2h = 1.0 / (1.0 + np.exp(-(util[:, None] - util[None, :])))

# ---- 5. write tamper-evident log -------------------------------------------
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
payload = {
    'generated_utc': now, 'race_id': rid, 'track': track, 'track_type': tt,
    'race_date': rdate, 'config': dict(pace=PACE_KEY, hl=HL, feats=FEATS,
                                       typology='MY_TYPE', typed='shrinkage', lam=0.5),
    'trained_through': last_done['date'][:10], 'n_train_races': len(Xs),
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
blob = json.dumps(payload, sort_keys=True).encode()
sha = hashlib.sha256(blob).hexdigest()
jpath = f'{OUT_DIR}/race_{rid}_{rdate}_prediction.json'
json.dump({'sha256_of_payload': sha, **payload}, open(jpath, 'w'), indent=1)

lines = [f"# Forward prediction -- {track} ({tt}), {rdate}",
         f"generated {now} | race_id {rid} | trained on {len(Xs)} races "
         f"through {last_done['date'][:10]} | payload sha256 {sha[:16]}...",
         f"weights: " + ", ".join(f"{k}={v:+.3f}" for k, v in zip(FEATS, w)),
         "STAND-DOWN: superspeedway -- do not act on this output." if tt == 'SS' else
         "actionable per doctrine (non-superspeedway)", "",
         f"{'rk':>2} {'driver':<24} {'grid':>4} {'hist':>4} {'util':>7} "
         f"{'P(win)':>7} {'P(top5)':>7} {'P(top10)':>8}"]
for r_, i in enumerate(order):
    fl = ' *' if hist_n[i] < MIN_HIST else ''
    lines.append(f"{r_+1:>2} {names[ids[i]]:<24} {int(start[i]):>4} {hist_n[i]:>4} "
                 f"{util[i]:>7.3f} {p_win[i]:>7.1%} {p_top5[i]:>7.1%} {p_top10[i]:>8.1%}{fl}")
lines.append("\n* fewer than 5 career races in dataset -- feature fallback, treat with caution")
mpath = f'{OUT_DIR}/race_{rid}_{rdate}_prediction.md'
open(mpath, 'w').write("\n".join(lines) + "\n")

lg = f'{OUT_DIR}/predictions_log.csv'
new = not os.path.exists(lg)
with open(lg, 'a') as f:
    if new:
        f.write('generated_utc,race_id,race_date,track,track_type,sha256,stand_down\n')
    f.write(f'{now},{rid},{rdate},{track},{tt},{sha},{tt=="SS"}\n')
print(f"\nwrote {jpath}\n      {mpath}\nlogged to {lg}")
print("\n".join(lines[5:20]))
