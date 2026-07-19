#!/usr/bin/env python3
"""Incremental update: fetch only completed points races missing from
races_parsed.pkl, parse them, append, save. Run before predict_next.py
each week. Needs only the pickle, not the full raw-data archive."""
import json, pickle, os, datetime, urllib.request
from parse_lib import parse_race

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r:
        return json.load(r)

races = pickle.load(open('races_parsed.pkl', 'rb'))
known = {r['rid'] for r in races}
this_year = datetime.date.today().year
years = range(max(r['year'] for r in races), this_year + 1)
os.makedirs('data/races', exist_ok=True)

added, failed = [], []
for yr in years:
    rl = fetch(f'https://cf.nascar.com/cacher/{yr}/race_list_basic.json')
    json.dump(rl, open(f'data/race_list_{yr}.json', 'w'))
    for r in rl['series_1']:
        rid = r['race_id']
        if r.get('race_type_id') != 1 or rid in known or not r.get('winner_driver_id'):
            continue
        dt, track = r['race_date'], r['track_name'].strip()
        try:
            lt = fetch(f'https://cf.nascar.com/cacher/{yr}/1/{rid}/lap-times.json')
            wf = fetch(f'https://cf.nascar.com/cacher/{yr}/1/{rid}/weekend-feed.json')
            json.dump(lt, open(f'data/races/{yr}_{rid}_lt.json', 'w'))
            json.dump(wf, open(f'data/races/{yr}_{rid}_wf.json', 'w'))
            parsed, err = parse_race(dt, yr, rid, track, lt, wf)
            if parsed:
                races.append(parsed); added.append((dt[:10], track))
            else:
                failed.append((dt[:10], track, err))
        except Exception as e:
            failed.append((dt[:10], track, repr(e)))

if added:
    races.sort(key=lambda r: r['date'])
    pickle.dump(races, open('races_parsed.pkl', 'wb'))
print(f'{len(races)} races in dataset; added {len(added)}: {added or ""}')
for f in failed: print('  FAILED:', f)
