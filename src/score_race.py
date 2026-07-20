#!/usr/bin/env python3
"""Score a forward prediction against official results (specs/scoring_methodology.md, FROZEN,
implemented verbatim including its amendments). No design judgment calls: every rule below cites
the spec section it implements.

Pipeline (section 8): load prediction JSON -> verify hash (1.3) -> load results (1.2, amended
completeness gate + snapshot freeze) -> common set (2) -> rho (3) -> h2h (4) -> book grading (5,
amended pipeline order) -> upsert scores_log.csv row (6).

Section 5.5 note: this file does not know about bronze. The compatibility shim that populates
src/data/races/{year}_{race_id}_wf.json from the bronze archive is a separate step
(bronze_fetch.py --sync-legacy-cache) that runs BEFORE this script, per the medallion spec.

Run from anywhere (repo root is resolved via __file__, matching the other new medallion modules).
CLI: `score_race.py [race_id] [--prediction-json PATH] [--results-json PATH]` -- no other flags
(section 8; the two path overrides are test-only, no-network affordances).
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone

from scipy.stats import spearmanr

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICTIONS_DIR = os.path.join(REPO_ROOT, 'predictions')
RACES_CACHE_DIR = os.path.join(REPO_ROOT, 'src', 'data', 'races')
SCORES_CSV_PATH = os.path.join(PREDICTIONS_DIR, 'scores_log.csv')
PRISTINE_BOOK_PRICES = {'note': 'fill in matchup/win prices at close, then score', 'entries': []}

FIELDNAMES = ['race_id', 'date', 'track', 'ttype', 'n', 'rho', 'h2h_acc', 'h2h_n',
              'book_n', 'book_agree_n', 'model_beats_book_n', 'notes']


# ---------------------------------------------------------------------------
# 1.3 -- hash verification
# ---------------------------------------------------------------------------
def verify_hash(d):
    payload = {k: v for k, v in d.items() if k != 'sha256_of_payload'}
    payload['book_prices'] = dict(PRISTINE_BOOK_PRICES)
    blob = json.dumps(payload, sort_keys=True).encode()
    sha = hashlib.sha256(blob).hexdigest()
    return sha == d.get('sha256_of_payload')


# ---------------------------------------------------------------------------
# 1.2 (+ amendment) -- results loading
# ---------------------------------------------------------------------------
def _fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _race_list_path(year):
    return os.path.join(REPO_ROOT, 'src', 'data', f'race_list_{year}.json')


def _extract_results(d):
    """Clarification (2026-07-18): missing/empty weekend_race or results -> treated the same as
    'no entry has a truthy finishing_position' -> the section 1.2 refusal exit."""
    wr = d.get('weekend_race') or [{}]
    return (wr[0] or {}).get('results') or []


def check_race_complete(year, race_id):
    """Amendment (results finality, item 1): completeness gate ahead of loading results --
    confirms the race's race_list_basic entry has a truthy winner_driver_id, the same signal
    update_data.py uses. Supplements, does not replace, the finishing_position refusal below."""
    path = _race_list_path(year)
    raw = open(path, 'rb').read() if os.path.exists(path) else _fetch(
        f'https://cf.nascar.com/cacher/{year}/race_list_basic.json')
    idx = json.loads(raw)
    entry = next((r for r in idx.get('series_1', []) if r.get('race_id') == race_id), None)
    if entry is None or not entry.get('winner_driver_id'):
        sys.exit(f'race {race_id} not complete -- refusing to score')


def load_results(year, race_id, path_override=None):
    """Returns (classified_results, raw_bytes, full_dict). classified_results keeps every entry
    with finishing_position >= 1 (section 1.2). Refuses (nonzero exit) if the race hasn't run."""
    if path_override:
        raw = open(path_override, 'rb').read()
        d = json.loads(raw)
        results = _extract_results(d)
        if not any(r.get('finishing_position') for r in results):
            sys.exit(f'race {race_id} not complete -- refusing to score')
        classified = [r for r in results if r.get('finishing_position') and r['finishing_position'] >= 1]
        return classified, raw, d

    check_race_complete(year, race_id)

    scored_path = os.path.join(RACES_CACHE_DIR, f'{year}_{race_id}_wf_scored.json')
    wf_path = os.path.join(RACES_CACHE_DIR, f'{year}_{race_id}_wf.json')
    if os.path.exists(scored_path):
        raw = open(scored_path, 'rb').read()
    elif os.path.exists(wf_path):
        raw = open(wf_path, 'rb').read()
    else:
        raw = _fetch(f'https://cf.nascar.com/cacher/{year}/1/{race_id}/weekend-feed.json')
        os.makedirs(RACES_CACHE_DIR, exist_ok=True)
        open(wf_path, 'wb').write(raw)

    d = json.loads(raw)
    results = _extract_results(d)
    if not any(r.get('finishing_position') for r in results):
        sys.exit(f'race {race_id} not complete -- refusing to score')
    classified = [r for r in results if r.get('finishing_position') and r['finishing_position'] >= 1]

    # Amendment (results finality, item 2) -- snapshot freeze: written once, on first successful
    # scoring, and never overwritten or deleted afterward.
    if not os.path.exists(scored_path):
        os.makedirs(RACES_CACHE_DIR, exist_ok=True)
        open(scored_path, 'wb').write(raw)

    return classified, raw, d


# ---------------------------------------------------------------------------
# 2 -- the scored set
# ---------------------------------------------------------------------------
def common_set(pred, results):
    pred_by_id = {f['driver_id']: f for f in pred['field']}
    res_by_id = {r['driver_id']: r for r in results}
    pred_ids, res_ids = set(pred_by_id), set(res_by_id)
    return {
        'pred_by_id': pred_by_id, 'res_by_id': res_by_id,
        'common_ids': sorted(pred_ids & res_ids),
        'unscored_ids': sorted(pred_ids - res_ids),
        'unpredicted_ids': sorted(res_ids - pred_ids),
    }


# ---------------------------------------------------------------------------
# 3 -- Spearman rho (blank if n < 3, amendment)
# ---------------------------------------------------------------------------
def score_rho(common):
    ids = common['common_ids']
    if len(ids) < 3:
        return None
    pred_ranks = [common['pred_by_id'][d]['pred_rank'] for d in ids]
    finishes = [common['res_by_id'][d]['finishing_position'] for d in ids]
    return round(float(spearmanr(pred_ranks, finishes)[0]), 4)


# ---------------------------------------------------------------------------
# 4 -- head-to-head (blank/zero if n < 3, amendment)
# ---------------------------------------------------------------------------
def score_h2h(pred, common):
    ids = common['common_ids']
    if len(ids) < 3:
        return None, 0, 0
    h2h_prob = pred['h2h_prob']
    res_by_id = common['res_by_id']
    correct = graded = skipped = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            lo, hi = ids[i], ids[j]           # ids sorted ascending -> lo < hi already
            f_lo = res_by_id[lo]['finishing_position']
            f_hi = res_by_id[hi]['finishing_position']
            if f_lo == f_hi:
                skipped += 1                   # finish tie anomaly -> skip pair
                continue
            p = h2h_prob.get(str(lo), {}).get(str(hi))
            if p is None or p == 0.5:
                skipped += 1
                continue
            pick, other = (lo, hi) if p > 0.5 else (hi, lo)
            graded += 1
            if res_by_id[pick]['finishing_position'] < res_by_id[other]['finishing_position']:
                correct += 1
    if graded == 0:
        return None, 0, skipped
    return round(correct / graded, 4), graded, skipped


# ---------------------------------------------------------------------------
# 5 -- book grading, amended pipeline order: malformed -> dedup -> void -> section 5.3 filters
# ---------------------------------------------------------------------------
def _valid_book_entry(e):
    try:
        int(e['driver_id_a']); int(e['driver_id_b'])
        pa, pb = int(e['price_a']), int(e['price_b'])
    except (KeyError, TypeError, ValueError):
        return False
    return pa != 0 and pb != 0


def _dedup_book_entries(valid):
    """valid: list of (index, entry). Prefer closing==true; then latest recorded_utc; then last
    in file order (section 5.2 + amendment). Returns (selected {pair_key: entry}, deduped_count)."""
    groups = {}
    for idx, e in valid:
        key = frozenset((int(e['driver_id_a']), int(e['driver_id_b'])))
        groups.setdefault(key, []).append((idx, e))

    def sort_key(item):
        idx, e = item
        try:
            ts = datetime.fromisoformat(str(e.get('recorded_utc', '')).replace('Z', '+00:00'))
        except ValueError:
            ts = datetime.min.replace(tzinfo=timezone.utc)
        return (bool(e.get('closing')), ts, idx)

    selected, deduped = {}, 0
    for key, group in groups.items():
        if len(group) > 1:
            deduped += len(group) - 1
        selected[key] = max(group, key=sort_key)[1]
    return selected, deduped


def malformed_dedup_void(entries):
    """Steps 1-3 of the amended section 5 pipeline: drop malformed, dedup survivors, drop void
    among the selected. Shared with market_benchmark.py, which imports exactly this mechanism
    (market spec resolved-ambiguity register: 'imports only the entry schema and the
    malformed->dedup->void pipeline' -- NOT section 5.3's strict-book-favorite filter, which stays
    local to grade_books below). Returns (survivors {pair_key: entry}, malformed, deduped, void)."""
    valid = [(i, e) for i, e in enumerate(entries) if _valid_book_entry(e)]
    malformed = len(entries) - len(valid)
    selected, deduped = _dedup_book_entries(valid)
    survivors, void = {}, 0
    for key, e in selected.items():
        if e.get('void'):
            void += 1
        else:
            survivors[key] = e
    return survivors, malformed, deduped, void


def grade_books(pred, common):
    entries = pred['book_prices']['entries']
    if not entries:
        return dict(book_n=0, book_agree_n=0, model_beats_book_n=0,
                    malformed=0, deduped=0, void=0, pickem=0, no_book_prices=True)

    survivors, malformed, deduped, void = malformed_dedup_void(entries)

    res_by_id = common['res_by_id']
    common_ids = set(common['common_ids'])
    h2h_prob = pred['h2h_prob']

    book_n = book_agree = model_beats_book = pickem = 0
    for e in survivors.values():
        a_id, b_id = int(e['driver_id_a']), int(e['driver_id_b'])
        if a_id not in common_ids or b_id not in common_ids:
            continue
        pa, pb = int(e['price_a']), int(e['price_b'])
        p_raw_a = abs(pa) / (abs(pa) + 100) if pa < 0 else 100 / (pa + 100)
        p_raw_b = abs(pb) / (abs(pb) + 100) if pb < 0 else 100 / (pb + 100)
        imp_a = p_raw_a / (p_raw_a + p_raw_b)
        if imp_a == 0.5:
            pickem += 1
            continue
        book_pick = a_id if imp_a > 0.5 else b_id

        lo, hi = min(a_id, b_id), max(a_id, b_id)
        if res_by_id[lo]['finishing_position'] == res_by_id[hi]['finishing_position']:
            continue                            # section 4 tie-skip applies here too
        p = h2h_prob.get(str(lo), {}).get(str(hi))
        if p is None or p == 0.5:
            continue                            # section 4 skip rule, imported verbatim
        model_pick = lo if p > 0.5 else hi

        book_n += 1
        if model_pick == book_pick:
            book_agree += 1
        else:
            other = hi if model_pick == lo else lo
            if res_by_id[model_pick]['finishing_position'] < res_by_id[other]['finishing_position']:
                model_beats_book += 1

    if len(common['common_ids']) < 3:            # amendment: n<3 -> no pairs graded at all
        book_n = book_agree = model_beats_book = 0

    return dict(book_n=book_n, book_agree_n=book_agree, model_beats_book_n=model_beats_book,
                malformed=malformed, deduped=deduped, void=void, pickem=pickem, no_book_prices=False)


# ---------------------------------------------------------------------------
# 5.5-adjacent: post-race price-entry provenance (results-finality provenance amendment).
# Best-effort: any git failure silently yields no note (never blocks scoring). Local committer
# timestamp is the operative signal here -- the same limitation the spec itself names ("the same
# known limitation as the prediction seal itself").
# ---------------------------------------------------------------------------
def _entry_key(e):
    return (e.get('book'), frozenset((int(e['driver_id_a']), int(e['driver_id_b']))), e.get('recorded_utc'))


def _git_first_commit_utc_for_entry(rel_path, entry):
    target = _entry_key(entry)
    log = subprocess.run(['git', 'log', '--follow', '--format=%H %cI', '--reverse', '--', rel_path],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=30, check=True)
    for line in log.stdout.splitlines():
        h, _, ts = line.partition(' ')
        show = subprocess.run(['git', 'show', f'{h}:{rel_path}'], cwd=REPO_ROOT,
                               capture_output=True, text=True, timeout=30, check=True)
        try:
            snap = json.loads(show.stdout)
        except json.JSONDecodeError:
            continue
        for e in (snap.get('book_prices') or {}).get('entries', []):
            try:
                if _entry_key(e) == target:
                    return datetime.fromisoformat(ts)
            except (KeyError, TypeError, ValueError):
                continue
    return None


def _green_flag_utc(year, race_id):
    path = _race_list_path(year)
    raw = open(path, 'rb').read() if os.path.exists(path) else _fetch(
        f'https://cf.nascar.com/cacher/{year}/race_list_basic.json')
    idx = json.loads(raw)
    entry = next((r for r in idx.get('series_1', []) if r.get('race_id') == race_id), None)
    if not entry:
        return None
    for ev in entry.get('schedule', []) or []:
        if ev.get('event_name') == 'Race' and ev.get('start_time_utc'):
            return datetime.fromisoformat(ev['start_time_utc']).replace(tzinfo=timezone.utc)
    return None


def post_race_price_note(pred_path, year, race_id, entries):
    if not entries:
        return False
    try:
        green = _green_flag_utc(year, race_id)
        if green is None:
            return False
        rel_path = os.path.relpath(pred_path, REPO_ROOT)
        for e in entries:
            commit_utc = _git_first_commit_utc_for_entry(rel_path, e)
            if commit_utc is not None and commit_utc > green:
                return True
    except (subprocess.SubprocessError, OSError, ValueError):
        return False
    return False


# ---------------------------------------------------------------------------
# 6 -- compose + upsert the scores_log.csv row
# ---------------------------------------------------------------------------
def compose_row(race_id, date, track, ttype, common, rho, h2h_result, books, stand_down,
                 post_race_price_entry=False):
    h2h_acc, h2h_n, h2h_skipped = h2h_result
    ids = common['common_ids']
    n = len(ids)
    res_by_id = common['res_by_id']

    notes = []
    if stand_down:
        notes.append('SS STAND-DOWN -- not actionable')
    if n < 20:
        notes.append('small common set')
    if common['unscored_ids']:
        notes.append(f"unscored (not in results): {common['unscored_ids']}")
    if common['unpredicted_ids']:
        notes.append(f"unpredicted (in results only): {common['unpredicted_ids']}")
    dq_ids = sorted(d for d in ids if res_by_id[d].get('disqualified'))
    if dq_ids:
        notes.append('DQ: ' + ', '.join(common['pred_by_id'][d]['name'] for d in dq_ids))
    positions = Counter(res_by_id[d]['finishing_position'] for d in ids)
    if any(c > 1 for c in positions.values()):
        notes.append('finish tie anomaly')
    if h2h_skipped:
        notes.append(f'h2h pairs skipped: {h2h_skipped}')
    if books['malformed']:
        notes.append(f"malformed book entries: {books['malformed']}")
    if books['deduped']:
        notes.append(f"book entries deduped: {books['deduped']}")
    if books['void']:
        notes.append(f"book entries void: {books['void']}")
    if books['pickem']:
        notes.append(f"pickem excluded: {books['pickem']}")
    if post_race_price_entry:
        notes.append('post-race price entry')
    if books['no_book_prices']:
        notes.append('no book prices')

    return {
        'race_id': race_id, 'date': date, 'track': track, 'ttype': ttype, 'n': n,
        'rho': '' if rho is None else f'{rho:.4f}',
        'h2h_acc': '' if h2h_acc is None else f'{h2h_acc:.4f}',
        'h2h_n': h2h_n, 'book_n': books['book_n'], 'book_agree_n': books['book_agree_n'],
        'model_beats_book_n': books['model_beats_book_n'], 'notes': '; '.join(notes),
    }


def upsert_row(csv_path, row):
    rows = []
    if os.path.exists(csv_path):
        with open(csv_path, newline='') as f:
            rows = list(csv.DictReader(f))
    rows = [r for r in rows if int(r['race_id']) != int(row['race_id'])]
    rows.append({k: str(row[k]) for k in FIELDNAMES})
    rows.sort(key=lambda r: (r['date'], int(r['race_id'])))
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# 8 -- end-to-end procedure
# ---------------------------------------------------------------------------
def _load_predictions_log():
    path = os.path.join(PREDICTIONS_DIR, 'predictions_log.csv')
    if not os.path.exists(path):
        return []
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def _select_race_id(plog):
    """Clarification (2026-07-18): 'earliest' = minimum (race_date, race_id)."""
    scored = set()
    if os.path.exists(SCORES_CSV_PATH):
        with open(SCORES_CSV_PATH, newline='') as f:
            scored = {int(r['race_id']) for r in csv.DictReader(f)}
    candidates = sorted((r['race_date'], int(r['race_id'])) for r in plog
                        if int(r['race_id']) not in scored)
    if not candidates:
        sys.exit('no unscored predictions in predictions_log.csv')
    return candidates[0][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('race_id', nargs='?', type=int, default=None)
    ap.add_argument('--prediction-json', default=None)
    ap.add_argument('--results-json', default=None)
    args = ap.parse_args()

    if args.prediction_json:
        pred_path = args.prediction_json
        d = json.load(open(pred_path))
        race_id, race_date = d['race_id'], d['race_date']
    else:
        plog = _load_predictions_log()
        race_id = args.race_id if args.race_id is not None else _select_race_id(plog)
        row = next((r for r in plog if int(r['race_id']) == race_id), None)
        if row is None:
            sys.exit(f'race_id {race_id} not found in predictions_log.csv')
        race_date = row['race_date']
        pred_path = os.path.join(PREDICTIONS_DIR, f'race_{race_id}_{race_date}_prediction.json')
        d = json.load(open(pred_path))

    if not verify_hash(d):
        sys.exit(f'[score_race] HASH VERIFICATION FAILED for {pred_path} -- '
                 f'refusing to score, writing nothing.')

    year = int(str(race_date)[:4])
    track, ttype, stand_down = d['track'], d['track_type'], d['stand_down']

    classified, _raw, _wf = load_results(year, race_id, path_override=args.results_json)

    common = common_set(d, classified)
    rho = score_rho(common)
    h2h_result = score_h2h(d, common)
    books = grade_books(d, common)

    post_race = False
    if not args.prediction_json and not args.results_json:
        post_race = post_race_price_note(pred_path, year, race_id, d['book_prices']['entries'])

    row = compose_row(race_id, race_date, track, ttype, common, rho, h2h_result, books,
                       stand_down, post_race)
    upsert_row(SCORES_CSV_PATH, row)

    print('=' * 70)
    print(f"[score_race] {track} ({ttype}) {race_date}  race_id={race_id}")
    print(f"  n={row['n']}  rho={row['rho'] or 'n/a'}  h2h_acc={row['h2h_acc'] or 'n/a'} "
          f"(h2h_n={row['h2h_n']})")
    print(f"  book_n={row['book_n']}  book_agree_n={row['book_agree_n']}  "
          f"model_beats_book_n={row['model_beats_book_n']}")
    if row['notes']:
        print(f"  notes: {row['notes']}")
    print(f'  -> {SCORES_CSV_PATH}')
    print('=' * 70)


if __name__ == '__main__':
    main()
