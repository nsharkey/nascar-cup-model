#!/usr/bin/env python3
"""Offline validation for live_feed_poller.py (plan session L4). Runs with plain
stdlib asserts (no pytest, no network, no launchd/pmset touched); exits nonzero on
any failure.

Fails on:
  1. is_finished   — correctly reads the checkered-flag signature off a snapshot.
  2. poll()        — writes one gzip-JSONL line per fetch, stamps _captured_at_utc,
                      preserves the original payload, and stops once the finish
                      signature is stable for STABLE_FINISH_SNAPSHOTS in a row.
  3. autodetect    — finds today's Cup race_id from a faked race_list_basic payload,
                      returns None when nothing matches, and never lets a fetch
                      error propagate as an exception.
"""
import gzip
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_feed_poller as lfp  # noqa: E402


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # 1. is_finished
    check(lfp.is_finished({'laps_to_go': 0, 'flag_state': 9}) is True,
          'is_finished: checkered-flag snapshot should read as finished')
    check(lfp.is_finished({'laps_to_go': 5, 'flag_state': 1}) is False,
          'is_finished: green-flag snapshot should not read as finished')
    check(lfp.is_finished({'laps_to_go': 0, 'flag_state': 1}) is False,
          'is_finished: laps_to_go==0 alone (caution at the line) should not count')

    # 2. poll() — feed a scripted sequence of snapshots, no real network/sleep
    snapshots = (
        [{'lap_number': n, 'laps_to_go': 10 - n, 'flag_state': 1} for n in range(1, 6)]
        + [{'lap_number': 10, 'laps_to_go': 0, 'flag_state': 9}] * lfp.STABLE_FINISH_SNAPSHOTS
        + [{'lap_number': 10, 'laps_to_go': 0, 'flag_state': 9}]  # should never be reached
    )
    calls = iter(snapshots)
    tmp_dir = tempfile.mkdtemp(prefix='live_feed_poller_test_')
    try:
        with mock.patch.object(lfp, 'fetch_live_feed', side_effect=lambda *a, **k: next(calls)):
            n_written, n_errors = lfp.poll(
                race_id=9999, interval=0, out_dir=tmp_dir, sleep_fn=lambda s: None)

        expected_n = 5 + lfp.STABLE_FINISH_SNAPSHOTS
        check(n_written == expected_n,
              f'poll: expected {expected_n} snapshots written, got {n_written}')
        check(n_errors == 0, f'poll: expected 0 errors, got {n_errors}')

        out_path = os.path.join(tmp_dir, '9999', 'live-feed.jsonl.gz')
        check(os.path.exists(out_path), f'poll: expected output file at {out_path}')
        with gzip.open(out_path, 'rt', encoding='utf-8') as f:
            lines = [json.loads(line) for line in f]
        check(len(lines) == expected_n,
              f'poll: expected {expected_n} decodable JSONL lines, got {len(lines)}')
        check(all('_captured_at_utc' in rec for rec in lines),
              'poll: every written record must carry _captured_at_utc')
        check(lines[0]['lap_number'] == 1 and lines[-1]['lap_number'] == 10,
              'poll: original payload fields must survive verbatim alongside the stamp')
        check(not any('lap_number' not in rec for rec in lines),
              'poll: original payload fields must survive verbatim')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 3. autodetect_race_id
    fake_index = {
        'series_1': [
            {'race_id': 111, 'race_type_id': 1, 'race_date': '2026-07-26T14:00:00'},
            {'race_id': 222, 'race_type_id': 2, 'race_date': '2026-07-26T14:00:00'},
            {'race_id': 333, 'race_type_id': 1, 'race_date': '2026-08-02T14:00:00'},
        ]
    }
    with mock.patch.object(lfp, '_fetch_json', return_value=fake_index):
        hit = lfp.autodetect_race_id(series_id=1, today='2026-07-26')
        check(hit == 111,
              f'autodetect_race_id: expected the points race (111) on the matching '
              f'date, not the exhibition race (222) or a different date, got {hit}')
        miss = lfp.autodetect_race_id(series_id=1, today='2026-07-27')
        check(miss is None,
              f'autodetect_race_id: expected None for a date with no race, got {miss}')

    def _raise(*a, **k):
        raise lfp.urllib.error.URLError('offline')

    with mock.patch.object(lfp, '_fetch_json', side_effect=_raise):
        err_result = lfp.autodetect_race_id(series_id=1, today='2026-07-26')
        check(err_result is None,
              'autodetect_race_id: a fetch error must return None, not raise')

    if failures:
        print(f'FAIL — {len(failures)} check(s) failed:')
        for msg in failures:
            print(f'  - {msg}')
        sys.exit(1)
    print('PASS — live_feed_poller.py offline checks (is_finished, poll, autodetect_race_id).')


if __name__ == '__main__':
    main()
