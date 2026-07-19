#!/usr/bin/env python3
"""Full rebuild: parse all raw feeds in data/ -> races_parsed.pkl.
For weekly updates use update_data.py instead (no full re-download needed)."""
import json, pickle
from parse_lib import load, parse_race

races = []
for yr in [2022, 2023, 2024, 2025, 2026]:
    d = json.load(open(f'data/race_list_{yr}.json'))
    for r in d['series_1']:
        if r.get('race_type_id') == 1:
            races.append((r['race_date'], yr, r['race_id'], r['track_name'].strip()))
races.sort()

out, skipped = [], []
for dt, yr, rid, track in races:
    lt = load(f'data/races/{yr}_{rid}_lt.json')
    wf = load(f'data/races/{yr}_{rid}_wf.json')
    r, err = parse_race(dt, yr, rid, track, lt, wf)
    if r: out.append(r)
    else: skipped.append((dt[:10], track, err))

pickle.dump(out, open('races_parsed.pkl', 'wb'))
print(f'parsed {len(out)} races; skipped {len(skipped)}:')
for s in skipped: print('  ', s)
