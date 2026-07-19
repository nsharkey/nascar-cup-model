#!/usr/bin/env python3
"""B4: one-time probe recovering 2017 index/schedule metadata via direct race_id
enumeration (DATA_DICTIONARY.md section 8d/8e; plan/schedule.yml B4).

2017's race_list_basic.json is permanently aliased to 2018 (index_year_matches()
rejects it), so bronze has never enumerated 2017 race_ids and never attempted
2017 detailed feeds -- distinct from 2015-2016's confirmed-absent case. This
probes weekend-feed directly for the race_id range each series occupied in the
2016->2018 gap (derived from bronze.races_index: each series' max 2016 race_id
to its min 2018 race_id), reusing bronze_fetch's exact fetch/retry/circuit-
breaker/manifest machinery so results are indistinguishable from a normal pull.

Not part of the recurring --update/--full modes -- run once, ad hoc, from src/.
"""
import threading

import bronze_fetch as bf

YEAR = 2017
FEED = 'weekend-feed'
WORKERS = bf.DEFAULT_WORKERS

# 2026-07-19: derived from bronze.races_index -- each series' max race_id in its
# 2016 races through its min race_id in its 2018 races (see DATA_DICTIONARY.md 8d).
SERIES_RANGES = {
    1: (4519, 4672),   # Cup
    2: (4552, 4713),   # Xfinity
    3: (4575, 4746),   # Trucks
}


def main():
    bf.ensure_dirs()
    bf.clean_tmp()
    run_id = bf.utc_ts()
    print(f'[bronze_probe_2017] run_id={run_id} feed={FEED} year={YEAR}')

    manifest_state = bf.load_manifest_state()
    manifest_lock = threading.Lock()
    throttle = bf.Throttle(WORKERS)

    tasks = [(FEED, sid, YEAR, race_id, False)
             for sid, (lo, hi) in SERIES_RANGES.items()
             for race_id in range(lo, hi + 1)]

    counts = ', '.join(f'series_{sid}: {hi - lo + 1}' for sid, (lo, hi) in SERIES_RANGES.items())
    print(f'[bronze_probe_2017] {len(tasks)} candidate race_ids queued ({counts})')

    tentative_absents = []
    bf.run_tasks(tasks, throttle, manifest_lock, manifest_state, tentative_absents, run_id, WORKERS)
    print(f'[bronze_probe_2017] sweeping {len(tentative_absents)} tentative-absent URLs')
    bf.sweep_tentative(tentative_absents, manifest_lock, manifest_state, run_id)

    stored = sorted(
        (k for k, v in manifest_state.items() if k[0] == FEED and k[2] == YEAR and v == 'stored'),
        key=lambda k: (k[1], k[3]),
    )
    print(f'[bronze_probe_2017] result: {len(stored)} race(s) recovered (stored), '
          f'{len(tasks) - len(stored)} confirmed absent/failed')
    for feed, sid, year, race_id in stored:
        print(f'  RECOVERED series_{sid} race_id={race_id}')

    bf.print_run_summary(manifest_state)


if __name__ == '__main__':
    main()
