#!/usr/bin/env python3
"""B4 follow-up: fetch the remaining 5 feeds (lap-times, live-pit-data, lap-notes,
live-flag-data, live-feed) for the 2017 races bronze_probe_2017.py already confirmed
real (DATA_DICTIONARY.md section 8f). Targeted at the exact (series_id, race_id)
pairs weekend-feed recovered -- no need to re-probe a wide id range since
weekend-feed already pinned down which race_ids are genuine 2017 races per series.

Run from src/.
"""
import json
import threading

import bronze_fetch as bf

YEAR = 2017
REMAINING_FEEDS = ['lap-times', 'live-pit-data', 'lap-notes', 'live-flag-data', 'live-feed']


def _known_2017_races():
    pairs = set()
    with open(bf.MANIFEST_PATH) as f:
        for line in f:
            e = json.loads(line)
            if e.get('feed') == 'weekend-feed' and e.get('year') == YEAR and e.get('outcome') == 'stored':
                pairs.add((e['series_id'], e['race_id']))
    return sorted(pairs)


def main():
    bf.ensure_dirs()
    bf.clean_tmp()
    run_id = bf.utc_ts()
    races = _known_2017_races()
    print(f'[bronze_probe_2017_remaining] run_id={run_id} {len(races)} known 2017 races '
          f'x {len(REMAINING_FEEDS)} feeds')

    manifest_state = bf.load_manifest_state()
    manifest_lock = threading.Lock()
    throttle = bf.Throttle(bf.DEFAULT_WORKERS)

    tasks = [(feed, sid, YEAR, race_id, False)
             for sid, race_id in races
             for feed in REMAINING_FEEDS]
    print(f'[bronze_probe_2017_remaining] {len(tasks)} tasks queued')

    tentative_absents = []
    bf.run_tasks(tasks, throttle, manifest_lock, manifest_state, tentative_absents, run_id, bf.DEFAULT_WORKERS)
    print(f'[bronze_probe_2017_remaining] sweeping {len(tentative_absents)} tentative-absent URLs')
    bf.sweep_tentative(tentative_absents, manifest_lock, manifest_state, run_id)

    for feed in REMAINING_FEEDS:
        stored = sum(1 for k, v in manifest_state.items() if k[0] == feed and k[2] == YEAR and v == 'stored')
        print(f'[bronze_probe_2017_remaining] {feed}: {stored}/{len(races)} stored')

    bf.print_run_summary(manifest_state)


if __name__ == '__main__':
    main()
