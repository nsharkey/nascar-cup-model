#!/usr/bin/env python3
"""Capture-assist template -- specs/pricing_layer.md section 7 (FROZEN behavior).

Reads a committed, hash-verified prediction JSON and re-expresses its OWN
sealed numbers (p_win / p_top5 / p_top10 / h2h_prob, all sigma(du) or 40k-
Gumbel-sampled by predict_next.py already) as fair odds, to speed up the
weekly manual book-price capture (HANDOFF.md weekly protocol step 3). Adds NO
new probability to the sealed record -- every number here traces to a field
already in the JSON; this script only converts probability -> fair odds via
pricing_layer.fair_odds() and sorts/labels for fast transcription.

Writes predictions/race_{id}_{date}_capture_template.csv (a working aid; the
sealed JSON is never modified). Run from src/: `python capture_template.py
[race_id]` (defaults to the most recently generated prediction JSON).
"""
import argparse
import glob
import json
import os
import sys

import pricing_layer as pl
import score_race

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
PREDICTIONS_DIR = os.path.join(REPO_ROOT, 'predictions')

LABEL = 'raw-model implied (known underconfident) -- diagnostic, not a betting price'


def _find_prediction_path(race_id):
    if race_id is not None:
        matches = glob.glob(os.path.join(PREDICTIONS_DIR, f'race_{race_id}_*_prediction.json'))
        if not matches:
            print(f'[capture_template] no prediction JSON found for race_id {race_id}', file=sys.stderr)
            sys.exit(1)
        return sorted(matches)[-1]
    matches = sorted(glob.glob(os.path.join(PREDICTIONS_DIR, 'race_*_prediction.json')),
                     key=os.path.getmtime)
    if not matches:
        print('[capture_template] no prediction JSON found in predictions/', file=sys.stderr)
        sys.exit(1)
    return matches[-1]


def _flags(p, stand_down):
    flags = []
    if stand_down:
        flags.append('SS_STAND_DOWN')
    rel = pl.mc_reliability(p)
    if rel['tail_stand_down']:
        flags.append('tail_stand_down')
    return ';'.join(flags)


def build_rows(d):
    stand_down = bool(d['stand_down'])
    field = d['field']
    by_id = {e['driver_id']: e for e in field}
    rows = []

    # per-driver win / top5 / top10 sheet (section 7 point 3)
    for e in sorted(field, key=lambda e: e['grid']):
        for market, pkey in (('win', 'p_win'), ('top5', 'p_top5'), ('top10', 'p_top10')):
            p = e[pkey]
            odds = pl.fair_odds(p)
            rows.append({
                'market': market,
                'driver_a_id': e['driver_id'], 'driver_a_name': e['name'], 'driver_a_grid': e['grid'],
                'driver_b_id': '', 'driver_b_name': '', 'driver_b_grid': '',
                'model_prob': p, 'fair_decimal': round(odds['fair_decimal'], 3),
                'fair_american': odds['fair_american'],
                'flags': _flags(p, stand_down),
            })

    # full-board H2H matchups (section 7 point 2): all unordered pairs, oriented
    # a = lower starting grid, b = higher -- sorted by (a.grid, b.grid) for fast
    # top-down transcription against a book's own grid-ordered board.
    seen = set()
    for i_str, row in d['h2h_prob'].items():
        i = int(i_str)
        for j_str, _ in row.items():
            j = int(j_str)
            pair = frozenset((i, j))
            if pair in seen:
                continue
            seen.add(pair)
            ei, ej = by_id[i], by_id[j]
            a, b = (ei, ej) if ei['grid'] <= ej['grid'] else (ej, ei)
            p = d['h2h_prob'][str(a['driver_id'])][str(b['driver_id'])]
            odds = pl.fair_odds(p)
            rows.append({
                'market': 'h2h',
                'driver_a_id': a['driver_id'], 'driver_a_name': a['name'], 'driver_a_grid': a['grid'],
                'driver_b_id': b['driver_id'], 'driver_b_name': b['name'], 'driver_b_grid': b['grid'],
                'model_prob': p, 'fair_decimal': round(odds['fair_decimal'], 3),
                'fair_american': odds['fair_american'],
                'flags': _flags(p, stand_down),
            })

    h2h_rows = [r for r in rows if r['market'] == 'h2h']
    h2h_rows.sort(key=lambda r: (r['driver_a_grid'], r['driver_b_grid']))
    other_rows = [r for r in rows if r['market'] != 'h2h']
    return other_rows + h2h_rows


def write_csv(d, rows, out_path):
    import csv
    fieldnames = ['market', 'driver_a_id', 'driver_a_name', 'driver_a_grid',
                 'driver_b_id', 'driver_b_name', 'driver_b_grid',
                 'model_prob', 'fair_decimal', 'fair_american', 'flags']
    with open(out_path, 'w', newline='') as f:
        f.write(f"# {LABEL}\n")
        f.write(f"# race_id={d['race_id']} track={d['track']} ({d['track_type']}) "
               f"date={d['race_date']}\n")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser(description='Capture-assist template (specs/pricing_layer.md section 7).')
    ap.add_argument('race_id', nargs='?', type=int, default=None,
                    help='race_id to build the sheet for (default: most recent prediction JSON)')
    args = ap.parse_args()

    pred_path = _find_prediction_path(args.race_id)
    d = json.load(open(pred_path))
    if not score_race.verify_hash(d):
        print(f'[capture_template] {os.path.basename(pred_path)} FAILED hash verification -- '
             f'refusing to build a sheet from a tampered/corrupt sealed record', file=sys.stderr)
        sys.exit(1)

    rows = build_rows(d)
    out_path = os.path.join(PREDICTIONS_DIR, f"race_{d['race_id']}_{d['race_date']}_capture_template.csv")
    write_csv(d, rows, out_path)

    n_h2h = sum(1 for r in rows if r['market'] == 'h2h')
    n_driver = len(rows) - n_h2h
    print(f"[capture_template] {d['track']} ({d['track_type']}) {d['race_date']} -- "
         f"{LABEL}")
    if d['stand_down']:
        print('  SS STAND-DOWN -- not actionable')
    print(f'  {n_driver} driver-market rows (win/top5/top10), {n_h2h} full-board H2H matchups')
    print(f'  -> {out_path}')


if __name__ == '__main__':
    main()
