#!/usr/bin/env python3
"""Live-feed poller (plan session L4).

NASCAR's cacher only ever serves the CURRENT state of live-feed.json -- once a race
ends, every earlier lap's live snapshot is gone forever; the archive only keeps the
final frame (confirmed: silver.live_final is built from the "latest stored snapshot
= the post-race final frame", DATA_DICTIONARY.md). The only way to ever recover the
intra-race time series (live running order, flag state, pit activity as it happened)
is to poll while the race is actually green.

This is a plain stdlib script on purpose -- it is meant to run unattended under
launchd with whatever system Python is on PATH, not the project's Anaconda/duckdb
environment. See ops/README.md for how to wire it to launchd + pmset (NOT done by
this script; that is a separate, explicit install step).

Usage:
    python3 live_feed_poller.py --race-id 5619
    python3 live_feed_poller.py                      # auto-detect today's Cup race

Output: newline-delimited JSON, gzip-compressed, one line per snapshot, at
    data/live_capture/{race_id}/live-feed.jsonl.gz
Each line is the raw live-feed.json payload plus one added field, "_captured_at_utc".
Opportunistic / best-effort: gaps in the log are expected whenever the machine is
asleep or off. No roadmap item consumes this data yet -- it is a retention hedge
against an otherwise-permanent loss, nothing more.
"""
import argparse
import datetime
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, 'data', 'live_capture')
BASE_URL = 'https://cf.nascar.com/cacher'
USER_AGENT = 'nascar-cup-model/1.0 (personal research archive)'

DEFAULT_INTERVAL_SECONDS = 7.0
MAX_DURATION_SECONDS = 6 * 3600  # safety cap so a stuck poller can't run forever
STABLE_FINISH_SNAPSHOTS = 3      # consecutive finished-looking snapshots before stopping


def _fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_live_feed(series_id, race_id, timeout=15):
    url = f'{BASE_URL}/live/series_{series_id}/{race_id}/live-feed.json'
    return _fetch_json(url, timeout=timeout)


def is_finished(snapshot):
    """True once the feed itself reports the checkered flag with no laps remaining.
    flag_state==9 / laps_to_go==0 was observed on race 5618's stored final frame."""
    return snapshot.get('laps_to_go') == 0 and snapshot.get('flag_state') == 9


def autodetect_race_id(series_id=1, today=None):
    """Find today's Cup points race_id straight from the live cacher index (no local
    warehouse dependency -- this must work standalone under launchd). Returns None if
    no points race is scheduled today."""
    today = today or datetime.date.today().isoformat()
    year = int(today[:4])
    try:
        rl = _fetch_json(f'{BASE_URL}/{year}/race_list_basic.json')
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    key = f'series_{series_id}'
    for r in rl.get(key, []):
        if r.get('race_type_id') == 1 and str(r.get('race_date', ''))[:10] == today:
            return r.get('race_id')
    return None


def poll(race_id, series_id=1, interval=DEFAULT_INTERVAL_SECONDS,
         max_duration=MAX_DURATION_SECONDS, out_dir=OUT_DIR, sleep_fn=time.sleep):
    race_dir = os.path.join(out_dir, str(race_id))
    os.makedirs(race_dir, exist_ok=True)
    out_path = os.path.join(race_dir, 'live-feed.jsonl.gz')

    start = time.monotonic()
    n_written, n_errors, stable_finish_count = 0, 0, 0
    last_lap = None
    print(f'[poller] race_id={race_id} series_id={series_id} interval={interval}s -> {out_path}')

    with gzip.open(out_path, 'at', encoding='utf-8') as f:
        while True:
            if time.monotonic() - start > max_duration:
                print(f'[poller] max duration ({max_duration}s) reached, stopping')
                break
            try:
                snap = fetch_live_feed(series_id, race_id)
                captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                record = {'_captured_at_utc': captured_at}
                record.update(snap)
                f.write(json.dumps(record) + '\n')
                f.flush()
                n_written += 1
                lap = snap.get('lap_number')
                if lap != last_lap:
                    print(f'[poller] lap {lap} captured ({n_written} snapshots so far)')
                    last_lap = lap
                if is_finished(snap):
                    stable_finish_count += 1
                    if stable_finish_count >= STABLE_FINISH_SNAPSHOTS:
                        print('[poller] race finished (stable), stopping')
                        break
                else:
                    stable_finish_count = 0
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    json.JSONDecodeError, ConnectionError) as e:
                n_errors += 1
                print(f'[poller] fetch error ({n_errors} total): {e!r}')
            sleep_fn(interval)

    print(f'[poller] done: {n_written} snapshots written, {n_errors} errors -> {out_path}')
    return n_written, n_errors


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--race-id', type=int, default=None,
                     help="Cup race_id to poll; default: auto-detect today's race")
    ap.add_argument('--series-id', type=int, default=1)
    ap.add_argument('--interval', type=float, default=DEFAULT_INTERVAL_SECONDS)
    ap.add_argument('--max-duration', type=float, default=MAX_DURATION_SECONDS)
    ap.add_argument('--out-dir', default=OUT_DIR)
    args = ap.parse_args()

    race_id = args.race_id
    if race_id is None:
        race_id = autodetect_race_id(args.series_id)
        if race_id is None:
            print('[poller] no Cup points race scheduled today -- pass --race-id '
                  'explicitly, or there is nothing to do', file=sys.stderr)
            sys.exit(1)
        print(f'[poller] auto-detected race_id={race_id} for today')

    poll(race_id, series_id=args.series_id, interval=args.interval,
         max_duration=args.max_duration, out_dir=args.out_dir)


if __name__ == '__main__':
    main()
