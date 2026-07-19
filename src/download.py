#!/usr/bin/env python3
"""Download lap-times + weekend-feed for every Cup points race 2022-2026, cached to disk."""
import json, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

os.makedirs('data/races', exist_ok=True)

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'audit/1.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                return {'__error__': str(e)}
            time.sleep(1.5 * (i + 1))

races = []
for yr in [2022, 2023, 2024, 2025, 2026]:
    d = json.load(open(f'data/race_list_{yr}.json'))
    for r in d['series_1']:
        if r.get('race_type_id') == 1:
            races.append((r['race_date'], yr, r['race_id'], r['track_name']))
races.sort()
print(f'{len(races)} scheduled points races 2022-2026')

def job(item):
    dt, yr, rid, track = item
    out = {}
    for name, url in [
        ('lt', f'https://cf.nascar.com/cacher/{yr}/1/{rid}/lap-times.json'),
        ('wf', f'https://cf.nascar.com/cacher/{yr}/1/{rid}/weekend-feed.json'),
    ]:
        path = f'data/races/{yr}_{rid}_{name}.json'
        if os.path.exists(path):
            out[name] = 'cached'
            continue
        d = fetch(url)
        if d and '__error__' not in d:
            json.dump(d, open(path, 'w'))
            out[name] = 'ok'
        else:
            out[name] = f"FAIL {d.get('__error__','empty') if d else 'none'}"
    return (dt, yr, rid, track, out)

fails = []
done = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(job, it) for it in races]
    for f in as_completed(futs):
        dt, yr, rid, track, out = f.result()
        done += 1
        if any(v.startswith('FAIL') for v in out.values()):
            fails.append((dt[:10], yr, rid, track, out))
        if done % 30 == 0:
            print(f'  {done}/{len(races)} done')

print(f'\nCompleted. {len(fails)} races with missing feeds:')
for x in sorted(fails):
    print('  ', x[0], x[3], {k: v for k, v in x[4].items() if v.startswith("FAIL")})
