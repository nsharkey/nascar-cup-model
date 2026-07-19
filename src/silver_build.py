#!/usr/bin/env python3
"""Silver build -- parity path (specs/medallion_architecture.md, section 3.1-3.3, 3.5).

Builds silver.races (one row per (series_id, race_id), all years/series/race_type_id) and
silver.driver_race (the FROZEN parity table, one row per (series_id, race_id, driver_id) for
every race with parse_status='ok'). driver_race is produced by feeding each race's latest
bronze lap-times + weekend-feed payloads through parse_lib.parse_race() UNMODIFIED -- the
same code path on the same bytes is the only way to guarantee the exact field-for-field
equality section 4's gate demands (section 3.1). Do not rewrite the parser in SQL here.

Modes:
  --full    ignore build state, re-parse every eligible race (section 4's gate always
            requires this)
  (default) incremental: a race's driver rows are only re-parsed if its lap-times/weekend-feed
            shas changed since the last build (section 3.5)

Run from src/.
"""
import argparse, glob, gzip, hashlib, json, os
from collections import Counter

import pyarrow as pa
import pyarrow.parquet as pq

import warehouse
from bronze_fetch import race_dir, latest_stored_path
from parse_lib import parse_race

REPO_ROOT = warehouse.REPO_ROOT
SILVER_DIR = os.path.join(REPO_ROOT, 'data', 'silver')
RACES_PATH = os.path.join(SILVER_DIR, 'races.parquet')
DRIVER_RACE_PATH = os.path.join(SILVER_DIR, 'driver_race.parquet')
BUILD_STATE_PATH = os.path.join(SILVER_DIR, '_build_state.parquet')

PARSER_VERSION = 1          # bump on any parse_lib.parse_race change -- forces a full rebuild
RACE_TYPE_POINTS = 1        # parse_race is attempted only for race_type_id == 1 (section 3.2)

RACES_SCHEMA = pa.schema([
    ('series_id', pa.int32()),
    ('race_id', pa.int32()),
    ('year', pa.int32()),
    ('race_type_id', pa.int32()),
    ('race_date', pa.string()),
    ('race_name', pa.string()),
    ('track_id', pa.int32()),
    ('track_name', pa.string()),
    ('scheduled_laps', pa.int32()),
    ('actual_laps', pa.int32()),
    ('stage_1_laps', pa.int32()),
    ('stage_2_laps', pa.int32()),
    ('stage_3_laps', pa.int32()),
    ('winner_driver_id', pa.int32()),
    ('green_flag_utc', pa.string()),
    ('number_of_cautions', pa.int32()),
    ('number_of_caution_laps', pa.int32()),
    ('number_of_lead_changes', pa.int32()),
    ('parse_status', pa.string()),
    ('n_green', pa.int32()),
    ('n_fe', pa.int32()),
    ('n_prac', pa.int32()),
])

DRIVER_RACE_SCHEMA = pa.schema([
    ('series_id', pa.int32()),
    ('race_id', pa.int32()),
    ('year', pa.int32()),
    ('race_date', pa.string()),
    ('track', pa.string()),
    ('driver_id', pa.int32()),
    ('finish', pa.int32()),
    ('start', pa.int32()),
    ('qspeed', pa.float64()),
    ('status', pa.string()),
    ('team', pa.int32()),
    ('make', pa.string()),
    ('laps_led', pa.int32()),
    ('laps_completed', pa.int32()),
    ('pace_med85', pa.float64()),
    ('pace_mean70', pa.float64()),
    ('pace_p20', pa.float64()),
    ('pace_best', pa.float64()),
    ('nlaps', pa.int32()),
    ('fepace', pa.float64()),
    ('practice', pa.float64()),
])

BUILD_STATE_SCHEMA = pa.schema([
    ('series_id', pa.int32()),
    ('race_id', pa.int32()),
    ('fingerprint', pa.string()),
])


def _sha256_of_gz(path):
    with gzip.open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_json_gz(path):
    with gzip.open(path, 'rb') as f:
        return json.loads(f.read())


def _fingerprint(lt_sha, wf_sha):
    # "that race's feeds" (section 3.5) = the two feeds silver_build.py actually reads for
    # the parity path (section 3.1); race_list/index changes are cheap to re-derive every
    # build regardless (see the races_rows loop below), so they aren't part of this key.
    parts = sorted([f'lap-times:{lt_sha}', f'weekend-feed:{wf_sha}'])
    return hashlib.sha256((f'parser_v{PARSER_VERSION}|' + '|'.join(parts)).encode()).hexdigest()


def _green_flag_utc(schedule):
    for e in (schedule or []):
        if e.get('event_name') == 'Race':
            return e.get('start_time_utc')
    return None


def _load_prior_build_state():
    if not os.path.exists(BUILD_STATE_PATH):
        return {}
    return {(row['series_id'], row['race_id']): row['fingerprint']
            for row in pq.read_table(BUILD_STATE_PATH).to_pylist()}


def _load_prior_rows(path):
    if not os.path.exists(path):
        return []
    return pq.read_table(path).to_pylist()


def build_silver(full=False):
    os.makedirs(SILVER_DIR, exist_ok=True)
    race_records = warehouse.load_race_records()

    prior_state = {} if full else _load_prior_build_state()
    prior_races_by_key = {} if full else {
        (row['series_id'], row['race_id']): row for row in _load_prior_rows(RACES_PATH)
    }
    prior_driver_rows_by_key = {}
    if not full:
        for row in _load_prior_rows(DRIVER_RACE_PATH):
            prior_driver_rows_by_key.setdefault((row['series_id'], row['race_id']), []).append(row)

    races_rows, driver_rows = [], []
    new_build_state = {}
    skip_reason_counts = Counter()
    n_ok = n_reused = n_parsed = n_not_attempted = 0

    for (sid, rid) in sorted(race_records.keys()):
        info = race_records[(sid, rid)]
        year = info['year']
        r = info['record']

        race_type_id = r.get('race_type_id')
        race_date = r.get('race_date')
        track_name = (r.get('track_name') or '').strip()

        dirpath = race_dir(sid, year, rid)
        lt_path = latest_stored_path(dirpath, 'lap-times')
        wf_path = latest_stored_path(dirpath, 'weekend-feed')

        parse_status, n_green, n_fe, n_prac = 'not_attempted', None, None, None

        if race_type_id == RACE_TYPE_POINTS and lt_path and wf_path:
            lt_sha = _sha256_of_gz(lt_path)
            wf_sha = _sha256_of_gz(wf_path)
            fingerprint = _fingerprint(lt_sha, wf_sha)
            new_build_state[(sid, rid)] = fingerprint

            reuse = (not full and prior_state.get((sid, rid)) == fingerprint
                     and (sid, rid) in prior_races_by_key)
            if reuse:
                prior_row = prior_races_by_key[(sid, rid)]
                parse_status = prior_row['parse_status']
                n_green, n_fe, n_prac = prior_row['n_green'], prior_row['n_fe'], prior_row['n_prac']
                if parse_status == 'ok':
                    driver_rows.extend(prior_driver_rows_by_key.get((sid, rid), []))
                n_reused += 1
            else:
                lt = _load_json_gz(lt_path)
                wf = _load_json_gz(wf_path)
                race_dict, err = parse_race(race_date, year, rid, track_name, lt, wf)
                n_parsed += 1
                if race_dict:
                    parse_status = 'ok'
                    n_green, n_fe, n_prac = race_dict['n_green'], race_dict['n_fe'], race_dict['n_prac']
                    for did, d in race_dict['drivers'].items():
                        driver_rows.append({
                            'series_id': sid, 'race_id': rid, 'year': year,
                            'race_date': race_dict['date'], 'track': race_dict['track'],
                            'driver_id': did,
                            'finish': d['finish'], 'start': d.get('start'),
                            'qspeed': d.get('qspeed'), 'status': d.get('status') or '',
                            'team': d.get('team'), 'make': d.get('make'),
                            'laps_led': d.get('laps_led') or 0,
                            'laps_completed': d.get('laps_completed') or 0,
                            'pace_med85': d.get('pace_med85'), 'pace_mean70': d.get('pace_mean70'),
                            'pace_p20': d.get('pace_p20'), 'pace_best': d.get('pace_best'),
                            'nlaps': d.get('nlaps'),
                            'fepace': d.get('fepace'), 'practice': d.get('practice'),
                        })
                else:
                    parse_status = f'skipped: {err}'
                    skip_reason_counts[err] += 1

        if parse_status == 'ok':
            n_ok += 1
        elif parse_status == 'not_attempted':
            n_not_attempted += 1

        races_rows.append({
            'series_id': sid, 'race_id': rid, 'year': year,
            'race_type_id': race_type_id, 'race_date': race_date,
            'race_name': r.get('race_name'), 'track_id': r.get('track_id'),
            'track_name': track_name,
            'scheduled_laps': r.get('scheduled_laps'), 'actual_laps': r.get('actual_laps'),
            'stage_1_laps': r.get('stage_1_laps'), 'stage_2_laps': r.get('stage_2_laps'),
            'stage_3_laps': r.get('stage_3_laps'), 'winner_driver_id': r.get('winner_driver_id'),
            'green_flag_utc': _green_flag_utc(r.get('schedule')),
            'number_of_cautions': r.get('number_of_cautions'),
            'number_of_caution_laps': r.get('number_of_caution_laps'),
            'number_of_lead_changes': r.get('number_of_lead_changes'),
            'parse_status': parse_status, 'n_green': n_green, 'n_fe': n_fe, 'n_prac': n_prac,
        })

    pq.write_table(pa.Table.from_pylist(races_rows, schema=RACES_SCHEMA), RACES_PATH)
    pq.write_table(pa.Table.from_pylist(driver_rows, schema=DRIVER_RACE_SCHEMA), DRIVER_RACE_PATH)
    build_state_rows = [{'series_id': sid, 'race_id': rid, 'fingerprint': fp}
                         for (sid, rid), fp in new_build_state.items()]
    pq.write_table(pa.Table.from_pylist(build_state_rows, schema=BUILD_STATE_SCHEMA), BUILD_STATE_PATH)

    print(f'[silver_build] mode={"full" if full else "incremental"}')
    print(f'[silver_build] {len(races_rows)} races enumerated; {n_ok} ok, '
          f'{n_not_attempted} not_attempted, {len(races_rows) - n_ok - n_not_attempted} skipped')
    print(f'[silver_build] {n_parsed} race(s) parsed fresh, {n_reused} reused from prior build state')
    print(f'[silver_build] {len(driver_rows)} driver_race rows written')
    if skip_reason_counts:
        print('[silver_build] skip reasons:', dict(skip_reason_counts))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--full', action='store_true', help='ignore build state, re-parse everything')
    args = ap.parse_args()
    build_silver(full=args.full)
    warehouse.build_warehouse()
    print('[silver_build] warehouse rebuilt with silver.races / silver.driver_race views')


if __name__ == '__main__':
    main()
