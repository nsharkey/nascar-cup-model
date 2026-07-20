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

import duckdb
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
    # C4 (section 3.2/10.1 of the medallion spec): sourced from weekend-feed weekend_race[0],
    # not the race_list index (inconsistent stage_4_laps coverage there) -- extracted and
    # patched in by build_silver_breadth() below, carried forward here from the prior build.
    ('stage_4_laps', pa.int32()),
    ('playoff_round', pa.int32()),
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

        # C4: carry forward the prior build's weekend-feed-sourced values (build_silver_breadth()
        # below is the sole writer of these two fields -- see its patch step); empty dict on a
        # --full run, correctly deferring to a fresh extraction there.
        prior_row = prior_races_by_key.get((sid, rid), {})

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
            'stage_4_laps': prior_row.get('stage_4_laps'), 'playoff_round': prior_row.get('playoff_round'),
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


# ---------------------------------------------------------------------------
# Section 3.4 -- new silver tables (no parity obligation), built in DuckDB SQL
# directly over bronze json.gz files (section 3.1). Each race's relevant feed
# is read via a single-file read_json(..., columns={...}) call with an
# EXPLICIT schema -- forces missing keys to NULL instead of erroring, and
# (critically) avoids the cross-file type-drift DuckDB's auto-sampling hits
# when a field's inferred type differs across seasons (e.g. a "0" that reads
# as TIME in one file's sample and a plain int elsewhere). One file, one
# schema, no drift -- proven at scale against the full bronze archive before
# this was adopted as the build strategy.
# ---------------------------------------------------------------------------

BREADTH_VERSION = 2  # bump on any section 3.4 SQL transform change -- forces full rebuild of breadth tables
                     # (v2 = C4: caution_segments/stage_results/race_leaders + silver.races.playoff_round/stage_4_laps)
BREADTH_FEEDS = ['weekend-feed', 'lap-times', 'live-pit-data', 'lap-notes', 'live-flag-data', 'live-feed']

BREADTH_BUILD_STATE_PATH = os.path.join(SILVER_DIR, '_breadth_build_state.parquet')
RESULTS_PATH = os.path.join(SILVER_DIR, 'results.parquet')
LAPS_PATH = os.path.join(SILVER_DIR, 'laps.parquet')
LAP_FLAGS_PATH = os.path.join(SILVER_DIR, 'lap_flags.parquet')
FLAG_EVENTS_PATH = os.path.join(SILVER_DIR, 'flag_events.parquet')
PIT_STOPS_PATH = os.path.join(SILVER_DIR, 'pit_stops.parquet')
LAP_NOTES_PATH = os.path.join(SILVER_DIR, 'lap_notes.parquet')
PRACTICE_RUNS_PATH = os.path.join(SILVER_DIR, 'practice_runs.parquet')
LIVE_FINAL_PATH = os.path.join(SILVER_DIR, 'live_final.parquet')
CAUTION_SEGMENTS_PATH = os.path.join(SILVER_DIR, 'caution_segments.parquet')
STAGE_RESULTS_PATH = os.path.join(SILVER_DIR, 'stage_results.parquet')
RACE_LEADERS_PATH = os.path.join(SILVER_DIR, 'race_leaders.parquet')

RESULTS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('driver_id', pa.int32()), ('driver_fullname', pa.string()),
    ('finishing_position', pa.int32()), ('starting_position', pa.int32()),
    ('finishing_status', pa.string()), ('qualifying_position', pa.int32()),
    ('qualifying_speed', pa.float64()), ('qualifying_order', pa.int32()),
    ('car_number', pa.string()), ('official_car_number', pa.string()),
    ('team_id', pa.int32()), ('team_name', pa.string()),
    ('owner_id', pa.int32()), ('owner_fullname', pa.string()),
    ('crew_chief_id', pa.int32()), ('crew_chief_fullname', pa.string()),
    ('car_make', pa.string()), ('car_model', pa.string()), ('sponsor', pa.string()),
    ('laps_completed', pa.int32()), ('laps_led', pa.int32()), ('times_led', pa.int32()),
    ('points_earned', pa.int32()), ('points_position', pa.int32()), ('points_delta', pa.int32()),
    ('playoff_points_earned', pa.int32()), ('winnings', pa.float64()),
    ('diff_laps', pa.int32()), ('diff_time', pa.float64()), ('disqualified', pa.bool_()),
    ('result_id', pa.int32()),
])

LAPS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('driver_id', pa.int32()), ('lap', pa.int32()), ('lap_time', pa.float64()), ('running_pos', pa.int32()),
])

LAP_FLAGS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('flag_state', pa.int32()), ('laps_completed', pa.int32()),
])

FLAG_EVENTS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('event_seq', pa.int32()),
    ('flag_state', pa.int32()), ('lap_number', pa.int32()), ('elapsed_time', pa.float64()),
    ('time_of_day', pa.float64()), ('time_of_day_os', pa.string()),
    ('comment', pa.string()), ('beneficiary', pa.string()),
])

PIT_STOPS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('stop_seq', pa.int32()),
    ('vehicle_number', pa.string()), ('driver_name', pa.string()), ('driver_id', pa.int32()),
    ('lap_count', pa.int32()), ('leader_lap', pa.int32()),
    ('pit_in_race_time', pa.float64()), ('pit_out_race_time', pa.float64()),
    ('box_stop_race_time', pa.float64()), ('box_leave_race_time', pa.float64()),
    ('pit_stop_duration', pa.float64()), ('total_duration', pa.float64()),
    ('in_travel_duration', pa.float64()), ('out_travel_duration', pa.float64()),
    ('pit_in_flag_status', pa.int32()), ('pit_out_flag_status', pa.int32()),
    ('pit_in_rank', pa.int32()), ('pit_out_rank', pa.int32()),
    ('positions_gained_lost', pa.int32()), ('pit_stop_type', pa.string()),
    ('left_front_tire_changed', pa.bool_()), ('left_rear_tire_changed', pa.bool_()),
    ('right_front_tire_changed', pa.bool_()), ('right_rear_tire_changed', pa.bool_()),
    ('previous_lap_time', pa.float64()), ('next_lap_time', pa.float64()),
    ('vehicle_manufacturer', pa.string()),
])

LAP_NOTES_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('lap_number', pa.int32()), ('note_id', pa.int32()), ('note', pa.string()),
    ('flag_state', pa.int32()), ('driver_ids', pa.list_(pa.int32())),
])

PRACTICE_RUNS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('weekend_run_id', pa.int32()), ('run_type', pa.int32()), ('run_name', pa.string()), ('run_date', pa.string()),
    ('run_id', pa.int32()), ('car_number', pa.string()), ('vehicle_number', pa.string()), ('manufacturer', pa.string()),
    ('driver_id', pa.int32()), ('driver_name', pa.string()), ('finishing_position', pa.int32()),
    ('best_lap_time', pa.float64()), ('best_lap_speed', pa.float64()), ('best_lap_number', pa.int32()),
    ('laps_completed', pa.int32()), ('comment', pa.string()), ('delta_leader', pa.float64()), ('disqualified', pa.bool_()),
])

CAUTION_SEGMENTS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('event_seq', pa.int32()),
    ('start_lap', pa.int32()), ('end_lap', pa.int32()), ('reason', pa.string()),
    ('comment', pa.string()), ('beneficiary_car_number', pa.string()), ('flag_state', pa.int32()),
])

STAGE_RESULTS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('stage_number', pa.int32()),
    ('driver_id', pa.int32()), ('driver_fullname', pa.string()), ('car_number', pa.string()),
    ('finishing_position', pa.int32()), ('stage_points', pa.int32()),
])

RACE_LEADERS_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('leader_seq', pa.int32()),
    ('start_lap', pa.int32()), ('end_lap', pa.int32()), ('car_number', pa.string()),
])

LIVE_FINAL_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()),
    ('lap_number', pa.int32()), ('laps_in_race', pa.int32()), ('flag_state', pa.int32()),
    ('vehicle_number', pa.string()),
    ('driver_id', pa.int32()), ('driver_full_name', pa.string()), ('driver_first_name', pa.string()),
    ('driver_last_name', pa.string()), ('driver_is_in_chase', pa.bool_()),
    ('starting_position', pa.int32()), ('running_position', pa.int32()), ('laps_completed', pa.int32()),
    ('laps_led', pa.list_(pa.struct([('start_lap', pa.int32()), ('end_lap', pa.int32())]))),
    ('best_lap_time', pa.float64()), ('last_lap_time', pa.float64()),
    ('average_running_position', pa.float64()), ('average_speed', pa.float64()),
    ('passes_made', pa.int32()), ('times_passed', pa.int32()), ('quality_passes', pa.int32()),
    ('fastest_laps_run', pa.int32()), ('position_differential_last_10_percent', pa.int32()),
    ('is_on_dvp', pa.bool_()), ('status', pa.int32()),
])

BREADTH_TABLES = {
    'results':        (RESULTS_PATH, RESULTS_SCHEMA),
    'laps':           (LAPS_PATH, LAPS_SCHEMA),
    'lap_flags':      (LAP_FLAGS_PATH, LAP_FLAGS_SCHEMA),
    'flag_events':    (FLAG_EVENTS_PATH, FLAG_EVENTS_SCHEMA),
    'pit_stops':      (PIT_STOPS_PATH, PIT_STOPS_SCHEMA),
    'lap_notes':      (LAP_NOTES_PATH, LAP_NOTES_SCHEMA),
    'practice_runs':  (PRACTICE_RUNS_PATH, PRACTICE_RUNS_SCHEMA),
    'live_final':     (LIVE_FINAL_PATH, LIVE_FINAL_SCHEMA),
    'caution_segments': (CAUTION_SEGMENTS_PATH, CAUTION_SEGMENTS_SCHEMA),
    'stage_results':    (STAGE_RESULTS_PATH, STAGE_RESULTS_SCHEMA),
    'race_leaders':     (RACE_LEADERS_PATH, RACE_LEADERS_SCHEMA),
}

# key map (section 3.4 common rules): NASCARDriverID->driver_id, LapTime->lap_time, Lap->lap,
# RunningPos->running_pos, FlagState->flag_state, LapsCompleted->laps_completed -- applied via
# the `AS` aliases in the extraction queries below.

_RESULTS_STRUCT = """STRUCT(
    driver_id BIGINT, driver_fullname VARCHAR, finishing_position BIGINT, starting_position BIGINT,
    finishing_status VARCHAR, qualifying_position BIGINT, qualifying_speed DOUBLE, qualifying_order BIGINT,
    car_number VARCHAR, official_car_number VARCHAR, team_id BIGINT, team_name VARCHAR, owner_id BIGINT,
    owner_fullname VARCHAR, crew_chief_id BIGINT, crew_chief_fullname VARCHAR, car_make VARCHAR, car_model VARCHAR,
    sponsor VARCHAR, laps_completed BIGINT, laps_led BIGINT, times_led BIGINT, points_earned BIGINT,
    points_position BIGINT, points_delta BIGINT, playoff_points_earned BIGINT, winnings DOUBLE, diff_laps BIGINT,
    diff_time DOUBLE, disqualified BOOLEAN, result_id BIGINT
)[]"""

_RUN_RESULT_STRUCT = """STRUCT(
    run_id BIGINT, car_number VARCHAR, vehicle_number VARCHAR, manufacturer VARCHAR, driver_id BIGINT,
    driver_name VARCHAR, finishing_position BIGINT, best_lap_time DOUBLE, best_lap_speed DOUBLE,
    best_lap_number BIGINT, laps_completed BIGINT, comment VARCHAR, delta_leader DOUBLE, disqualified BOOLEAN
)[]"""

_VEHICLE_STRUCT = """STRUCT(
    vehicle_number VARCHAR,
    driver STRUCT(driver_id BIGINT, full_name VARCHAR, first_name VARCHAR, last_name VARCHAR, is_in_chase BOOLEAN),
    starting_position BIGINT, running_position BIGINT, laps_completed BIGINT,
    laps_led STRUCT(start_lap BIGINT, end_lap BIGINT)[],
    best_lap_time DOUBLE, last_lap_time DOUBLE, average_running_position DOUBLE, average_speed DOUBLE,
    passes_made BIGINT, times_passed BIGINT, quality_passes BIGINT, fastest_laps_run BIGINT,
    position_differential_last_10_percent BIGINT, is_on_dvp BOOLEAN, status BIGINT
)[]"""

_PIT_COLUMNS = {
    'vehicle_number': 'VARCHAR', 'driver_name': 'VARCHAR', 'vehicle_manufacturer': 'VARCHAR',
    'lap_count': 'BIGINT', 'leader_lap': 'BIGINT',
    'pit_in_race_time': 'DOUBLE', 'pit_out_race_time': 'DOUBLE',
    'box_stop_race_time': 'DOUBLE', 'box_leave_race_time': 'DOUBLE',
    'pit_stop_duration': 'DOUBLE', 'total_duration': 'DOUBLE',
    'in_travel_duration': 'DOUBLE', 'out_travel_duration': 'DOUBLE',
    'pit_in_flag_status': 'BIGINT', 'pit_out_flag_status': 'BIGINT',
    'pit_in_rank': 'BIGINT', 'pit_out_rank': 'BIGINT',
    'positions_gained_lost': 'BIGINT', 'pit_stop_type': 'VARCHAR',
    'left_front_tire_changed': 'BOOLEAN', 'left_rear_tire_changed': 'BOOLEAN',
    'right_front_tire_changed': 'BOOLEAN', 'right_rear_tire_changed': 'BOOLEAN',
    'previous_lap_time': 'DOUBLE', 'next_lap_time': 'DOUBLE',
}

_FLAG_EVENT_COLUMNS = {
    'lap_number': 'BIGINT', 'flag_state': 'BIGINT', 'elapsed_time': 'DOUBLE',
    'comment': 'VARCHAR', 'beneficiary': 'VARCHAR', 'time_of_day': 'DOUBLE', 'time_of_day_os': 'VARCHAR',
}


def _extract_results(con, path):
    q = f"""
        SELECT r.result AS result
        FROM read_json($p, columns={{'weekend_race': 'STRUCT(results {_RESULTS_STRUCT})[]'}}) t,
             UNNEST(t.weekend_race) AS _(wr),
             UNNEST(wr.results) AS r(result)
    """
    return [dict(row[0]) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_practice_runs(con, path):
    q = f"""
        SELECT wr.weekend_run_id AS weekend_run_id, wr.run_type AS run_type, wr.run_name AS run_name,
               wr.run_date AS run_date, r.res AS result
        FROM read_json($p, columns={{'weekend_runs':
            'STRUCT(weekend_run_id BIGINT, run_type BIGINT, run_name VARCHAR, run_date VARCHAR,
                     results {_RUN_RESULT_STRUCT})[]'}}) t,
             UNNEST(t.weekend_runs) AS _(wr),
             UNNEST(wr.results) AS r(res)
    """
    rows = []
    for weekend_run_id, run_type, run_name, run_date, result in con.sql(q, params={'p': path}).fetchall():
        row = dict(result)
        row.update(weekend_run_id=weekend_run_id, run_type=run_type, run_name=run_name, run_date=run_date)
        rows.append(row)
    return rows


_CAUTION_SEGMENT_STRUCT = """STRUCT(
    start_lap BIGINT, end_lap BIGINT, reason VARCHAR, comment VARCHAR,
    beneficiary_car_number VARCHAR, flag_state BIGINT
)[]"""

_STAGE_RESULT_STRUCT = """STRUCT(
    driver_fullname VARCHAR, driver_id BIGINT, car_number VARCHAR,
    finishing_position BIGINT, stage_points BIGINT
)[]"""

_RACE_LEADER_STRUCT = """STRUCT(
    start_lap BIGINT, end_lap BIGINT, car_number VARCHAR
)[]"""


def _extract_caution_segments(con, path):
    q = f"""
        SELECT c.seg AS seg
        FROM read_json($p, columns={{'weekend_race': 'STRUCT(caution_segments {_CAUTION_SEGMENT_STRUCT})[]'}}) t,
             UNNEST(t.weekend_race) AS _(wr),
             UNNEST(wr.caution_segments) AS c(seg)
    """
    return [dict(row[0]) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_stage_results(con, path):
    q = f"""
        SELECT s.stage.stage_number AS stage_number, r.res AS result
        FROM read_json($p, columns={{'weekend_race':
            'STRUCT(stage_results STRUCT(stage_number BIGINT, results {_STAGE_RESULT_STRUCT})[])[]'}}) t,
             UNNEST(t.weekend_race) AS _(wr),
             UNNEST(wr.stage_results) AS s(stage),
             UNNEST(s.stage.results) AS r(res)
    """
    rows = []
    for stage_number, result in con.sql(q, params={'p': path}).fetchall():
        row = dict(result)
        row['stage_number'] = stage_number
        rows.append(row)
    return rows


def _extract_race_leaders(con, path):
    q = f"""
        SELECT l.seg AS seg
        FROM read_json($p, columns={{'weekend_race': 'STRUCT(race_leaders {_RACE_LEADER_STRUCT})[]'}}) t,
             UNNEST(t.weekend_race) AS _(wr),
             UNNEST(wr.race_leaders) AS l(seg)
    """
    return [dict(row[0]) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_race_meta(con, path):
    """C4: playoff_round + stage_4_laps, scalar per race, sourced from weekend-feed
    weekend_race[0] (not the race_list index -- inconsistent stage_4_laps coverage there)."""
    q = """
        SELECT wr.playoff_round AS playoff_round, wr.stage_4_laps AS stage_4_laps
        FROM read_json($p, columns={'weekend_race': 'STRUCT(playoff_round BIGINT, stage_4_laps BIGINT)[]'}) t,
             UNNEST(t.weekend_race) AS _(wr)
        LIMIT 1
    """
    row = con.sql(q, params={'p': path}).fetchone()
    return (None, None) if row is None else (row[0], row[1])


def _extract_laps(con, path):
    q = """
        SELECT d.driver.NASCARDriverID AS driver_id, l.lap.Lap AS lap,
               l.lap.LapTime AS lap_time, l.lap.RunningPos AS running_pos
        FROM read_json($p, columns={'laps':
            'STRUCT(NASCARDriverID BIGINT, Laps STRUCT(Lap BIGINT, LapTime DOUBLE, RunningPos BIGINT)[])[]'}) t,
             UNNEST(t.laps) AS d(driver),
             UNNEST(d.driver.Laps) AS l(lap)
    """
    cols = ['driver_id', 'lap', 'lap_time', 'running_pos']
    return [dict(zip(cols, row)) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_lap_flags(con, path):
    q = """
        SELECT f.flag.FlagState AS flag_state, f.flag.LapsCompleted AS laps_completed
        FROM read_json($p, columns={'flags': 'STRUCT(FlagState BIGINT, LapsCompleted BIGINT)[]'}) t,
             UNNEST(t.flags) AS f(flag)
    """
    cols = ['flag_state', 'laps_completed']
    return [dict(zip(cols, row)) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_flag_events(con, path):
    cols = list(_FLAG_EVENT_COLUMNS)
    col_spec = ', '.join(f"'{k}':'{v}'" for k, v in _FLAG_EVENT_COLUMNS.items())
    q = f"SELECT {', '.join(cols)} FROM read_json($p, columns={{{col_spec}}})"
    return [dict(zip(cols, row)) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_pit_stops(con, path):
    cols = list(_PIT_COLUMNS)
    col_spec = ', '.join(f"'{k}':'{v}'" for k, v in _PIT_COLUMNS.items())
    q = f"SELECT {', '.join(cols)} FROM read_json($p, columns={{{col_spec}}})"
    return [dict(zip(cols, row)) for row in con.sql(q, params={'p': path}).fetchall()]


def _extract_lap_notes(con, path):
    q = """
        SELECT m.key AS lap_key, n.note.NoteID AS note_id, n.note.Note AS note,
               n.note.FlagState AS flag_state, n.note.DriverIDs AS driver_ids
        FROM read_json($p, columns={'laps':
            'MAP(VARCHAR, STRUCT(FlagState BIGINT, Note VARCHAR, NoteID BIGINT, DriverIDs BIGINT[])[])'}) t,
             UNNEST(map_entries(t.laps)) AS _(m),
             UNNEST(m.value) AS n(note)
    """
    rows = []
    for lap_key, note_id, note, flag_state, driver_ids in con.sql(q, params={'p': path}).fetchall():
        rows.append({
            'lap_number': int(lap_key), 'note_id': note_id, 'note': note,
            'flag_state': flag_state, 'driver_ids': driver_ids,
        })
    return rows


def _extract_live_final(con, path):
    q = f"""
        SELECT lap_number, laps_in_race, flag_state, v.veh AS vehicle
        FROM read_json($p, columns={{'lap_number':'BIGINT','laps_in_race':'BIGINT','flag_state':'BIGINT',
            'vehicles':'{_VEHICLE_STRUCT}'}}) t,
             UNNEST(t.vehicles) AS v(veh)
    """
    rows = []
    for lap_number, laps_in_race, flag_state, vehicle in con.sql(q, params={'p': path}).fetchall():
        vehicle = dict(vehicle)
        driver = vehicle.pop('driver') or {}
        row = dict(vehicle)
        row.update(
            driver_id=driver.get('driver_id'), driver_full_name=driver.get('full_name'),
            driver_first_name=driver.get('first_name'), driver_last_name=driver.get('last_name'),
            driver_is_in_chase=driver.get('is_in_chase'),
            lap_number=lap_number, laps_in_race=laps_in_race, flag_state=flag_state,
        )
        rows.append(row)
    return rows


def _row_sig(row):
    """Hashable signature of a row's values (order-independent) for exact-duplicate detection."""
    def conv(v):
        if isinstance(v, list):
            return tuple(conv(x) for x in v)
        if isinstance(v, dict):
            return tuple(sorted((k, conv(v2)) for k, v2 in v.items()))
        return v
    return tuple((k, conv(row[k])) for k in sorted(row))


def _dedupe(rows, key_fields):
    """Section 3.4 dedupe rule: drop exact-duplicate rows silently, keep-first + count
    same-key-different-value conflicts. `key_fields` is the natural grain of the table; for the
    ordered "event" tables (flag_events, pit_stops) the key is every raw source field, since an
    event/stop has no smaller natural business key -- under that key, "conflict" is structurally
    impossible (a differing row is a different key by construction) and dedupe reduces to
    exact-row-content matching, which is the intended behavior."""
    out = []
    first_row = {}
    sigs_seen = {}
    dup_dropped = 0
    conflicts = 0
    for row in rows:
        key = tuple(row.get(f) for f in key_fields)
        sig = _row_sig(row)
        if key not in first_row:
            first_row[key] = row
            sigs_seen[key] = {sig}
            out.append(row)
        elif sig in sigs_seen[key]:
            dup_dropped += 1
        else:
            sigs_seen[key].add(sig)
            conflicts += 1
    return out, dup_dropped, conflicts


def _resolve_pit_driver_ids(pit_rows, results_rows):
    """Section 3.4 pit_stops.driver_id resolution: join vehicle_number to silver.results.car_number
    (trimmed strings, within race); else exact driver_name==driver_fullname; else NULL."""
    car_to_drivers, name_to_drivers = {}, {}
    for r in results_rows:
        cn = (r.get('car_number') or '').strip()
        if cn:
            car_to_drivers.setdefault(cn, set()).add(r['driver_id'])
        fn = r.get('driver_fullname')
        if fn:
            name_to_drivers.setdefault(fn, set()).add(r['driver_id'])
    by_car = by_name = unresolved = 0
    for row in pit_rows:
        vn = (row.get('vehicle_number') or '').strip()
        cands = car_to_drivers.get(vn, set())
        if len(cands) == 1:
            row['driver_id'] = next(iter(cands))
            by_car += 1
            continue
        dn = row.get('driver_name')
        cands2 = name_to_drivers.get(dn, set()) if dn else set()
        if len(cands2) == 1:
            row['driver_id'] = next(iter(cands2))
            by_name += 1
            continue
        row['driver_id'] = None
        unresolved += 1
    return by_car, by_name, unresolved


def _breadth_fingerprint(feed_shas):
    parts = sorted(f'{feed}:{feed_shas.get(feed) or "absent"}' for feed in BREADTH_FEEDS)
    return hashlib.sha256((f'breadth_v{BREADTH_VERSION}|' + '|'.join(parts)).encode()).hexdigest()


def _load_prior_breadth_state():
    if not os.path.exists(BREADTH_BUILD_STATE_PATH):
        return {}
    return {(row['series_id'], row['race_id']): row['fingerprint']
            for row in pq.read_table(BREADTH_BUILD_STATE_PATH).to_pylist()}


def _load_prior_breadth_rows(table_name):
    path, _ = BREADTH_TABLES[table_name]
    by_key = {}
    if os.path.exists(path):
        for row in pq.read_table(path).to_pylist():
            by_key.setdefault((row['series_id'], row['race_id']), []).append(row)
    return by_key


def build_silver_breadth(race_records, full=False):
    con = duckdb.connect()
    prior_state = {} if full else _load_prior_breadth_state()
    prior_rows = {name: ({} if full else _load_prior_breadth_rows(name)) for name in BREADTH_TABLES}

    table_rows = {name: [] for name in BREADTH_TABLES}
    dedupe_stats = {name: Counter() for name in BREADTH_TABLES}
    pit_resolution = Counter()
    new_state = {}
    n_reused = n_fresh = n_no_feeds = 0
    race_meta = {}  # C4: {(sid, rid): (playoff_round, stage_4_laps)}, fresh races only --
                     # patched onto races.parquet after the loop; reused races keep whatever
                     # build_silver() already carried forward from the prior races.parquet.

    for (sid, rid) in sorted(race_records.keys()):
        year = race_records[(sid, rid)]['year']
        dirpath = race_dir(sid, year, rid)
        feed_paths = {feed: latest_stored_path(dirpath, feed) for feed in BREADTH_FEEDS}
        if not any(feed_paths.values()):
            n_no_feeds += 1
            continue

        feed_shas = {feed: _sha256_of_gz(p) for feed, p in feed_paths.items() if p}
        fingerprint = _breadth_fingerprint(feed_shas)
        new_state[(sid, rid)] = fingerprint
        reuse = not full and prior_state.get((sid, rid)) == fingerprint

        if reuse:
            for name in BREADTH_TABLES:
                table_rows[name].extend(prior_rows[name].get((sid, rid), []))
            n_reused += 1
            continue

        n_fresh += 1
        race_results = []

        if feed_paths['weekend-feed']:
            raw = _extract_results(con, feed_paths['weekend-feed'])
            for r in raw:
                r['series_id'], r['race_id'] = sid, rid
            deduped, dd, cf = _dedupe(raw, ['series_id', 'race_id', 'driver_id'])
            dedupe_stats['results']['dropped'] += dd
            dedupe_stats['results']['conflicts'] += cf
            table_rows['results'].extend(deduped)
            race_results = deduped

            raw_pr = _extract_practice_runs(con, feed_paths['weekend-feed'])
            for r in raw_pr:
                r['series_id'], r['race_id'] = sid, rid
            deduped_pr, dd, cf = _dedupe(raw_pr, ['series_id', 'race_id', 'weekend_run_id', 'driver_id'])
            dedupe_stats['practice_runs']['dropped'] += dd
            dedupe_stats['practice_runs']['conflicts'] += cf
            table_rows['practice_runs'].extend(deduped_pr)

            raw_cs = _extract_caution_segments(con, feed_paths['weekend-feed'])
            for r in raw_cs:
                r['series_id'], r['race_id'] = sid, rid
            deduped_cs, dd, cf = _dedupe(
                raw_cs, ['series_id', 'race_id', 'start_lap', 'end_lap', 'reason',
                         'comment', 'beneficiary_car_number', 'flag_state']
            )
            dedupe_stats['caution_segments']['dropped'] += dd
            dedupe_stats['caution_segments']['conflicts'] += cf
            for seq, r in enumerate(deduped_cs):
                r['event_seq'] = seq
            table_rows['caution_segments'].extend(deduped_cs)

            raw_sr = _extract_stage_results(con, feed_paths['weekend-feed'])
            for r in raw_sr:
                r['series_id'], r['race_id'] = sid, rid
            deduped_sr, dd, cf = _dedupe(raw_sr, ['series_id', 'race_id', 'stage_number', 'driver_id'])
            dedupe_stats['stage_results']['dropped'] += dd
            dedupe_stats['stage_results']['conflicts'] += cf
            table_rows['stage_results'].extend(deduped_sr)

            raw_rl = _extract_race_leaders(con, feed_paths['weekend-feed'])
            for r in raw_rl:
                r['series_id'], r['race_id'] = sid, rid
            deduped_rl, dd, cf = _dedupe(
                raw_rl, ['series_id', 'race_id', 'start_lap', 'end_lap', 'car_number']
            )
            dedupe_stats['race_leaders']['dropped'] += dd
            dedupe_stats['race_leaders']['conflicts'] += cf
            for seq, r in enumerate(deduped_rl):
                r['leader_seq'] = seq
            table_rows['race_leaders'].extend(deduped_rl)

            race_meta[(sid, rid)] = _extract_race_meta(con, feed_paths['weekend-feed'])

        if feed_paths['lap-times']:
            raw_laps = _extract_laps(con, feed_paths['lap-times'])
            for r in raw_laps:
                r['series_id'], r['race_id'] = sid, rid
            deduped_laps, dd, cf = _dedupe(raw_laps, ['series_id', 'race_id', 'driver_id', 'lap'])
            dedupe_stats['laps']['dropped'] += dd
            dedupe_stats['laps']['conflicts'] += cf
            table_rows['laps'].extend(deduped_laps)

            raw_flags = _extract_lap_flags(con, feed_paths['lap-times'])
            for r in raw_flags:
                r['series_id'], r['race_id'] = sid, rid
            deduped_flags, dd, cf = _dedupe(raw_flags, ['series_id', 'race_id', 'laps_completed'])
            dedupe_stats['lap_flags']['dropped'] += dd
            dedupe_stats['lap_flags']['conflicts'] += cf
            table_rows['lap_flags'].extend(deduped_flags)

        if feed_paths['live-pit-data']:
            raw_pit = _extract_pit_stops(con, feed_paths['live-pit-data'])
            for r in raw_pit:
                r['series_id'], r['race_id'] = sid, rid
            deduped_pit, dd, cf = _dedupe(
                raw_pit, ['series_id', 'race_id'] + list(_PIT_COLUMNS)
            )
            dedupe_stats['pit_stops']['dropped'] += dd
            dedupe_stats['pit_stops']['conflicts'] += cf
            by_car, by_name, unresolved = _resolve_pit_driver_ids(deduped_pit, race_results)
            pit_resolution['by_car'] += by_car
            pit_resolution['by_name'] += by_name
            pit_resolution['unresolved'] += unresolved
            for seq, r in enumerate(deduped_pit):
                r['stop_seq'] = seq
            table_rows['pit_stops'].extend(deduped_pit)

        if feed_paths['lap-notes']:
            raw_notes = _extract_lap_notes(con, feed_paths['lap-notes'])
            for r in raw_notes:
                r['series_id'], r['race_id'] = sid, rid
            deduped_notes, dd, cf = _dedupe(raw_notes, ['series_id', 'race_id', 'note_id'])
            dedupe_stats['lap_notes']['dropped'] += dd
            dedupe_stats['lap_notes']['conflicts'] += cf
            table_rows['lap_notes'].extend(deduped_notes)

        if feed_paths['live-flag-data']:
            raw_events = _extract_flag_events(con, feed_paths['live-flag-data'])
            for r in raw_events:
                r['series_id'], r['race_id'] = sid, rid
            deduped_events, dd, cf = _dedupe(
                raw_events, ['series_id', 'race_id'] + list(_FLAG_EVENT_COLUMNS)
            )
            dedupe_stats['flag_events']['dropped'] += dd
            dedupe_stats['flag_events']['conflicts'] += cf
            for seq, r in enumerate(deduped_events):
                r['event_seq'] = seq
            table_rows['flag_events'].extend(deduped_events)

        if feed_paths['live-feed']:
            raw_live = _extract_live_final(con, feed_paths['live-feed'])
            for r in raw_live:
                r['series_id'], r['race_id'] = sid, rid
            deduped_live, dd, cf = _dedupe(raw_live, ['series_id', 'race_id', 'driver_id'])
            dedupe_stats['live_final']['dropped'] += dd
            dedupe_stats['live_final']['conflicts'] += cf
            table_rows['live_final'].extend(deduped_live)

    con.close()

    for name, (path, schema) in BREADTH_TABLES.items():
        pq.write_table(pa.Table.from_pylist(table_rows[name], schema=schema), path)
    build_state_rows = [{'series_id': sid, 'race_id': rid, 'fingerprint': fp}
                         for (sid, rid), fp in new_state.items()]
    pq.write_table(pa.Table.from_pylist(build_state_rows, schema=BUILD_STATE_SCHEMA), BREADTH_BUILD_STATE_PATH)

    # C4: patch playoff_round/stage_4_laps onto the races.parquet build_silver() already wrote --
    # only for races freshly (re-)extracted this run; reused races keep the value build_silver()
    # already carried forward from the prior races.parquet (see its prior_row.get(...) above).
    n_meta_patched = 0
    if os.path.exists(RACES_PATH):
        races_rows_out = pq.read_table(RACES_PATH).to_pylist()
        for row in races_rows_out:
            key = (row['series_id'], row['race_id'])
            if key in race_meta:
                row['playoff_round'], row['stage_4_laps'] = race_meta[key]
                n_meta_patched += 1
        pq.write_table(pa.Table.from_pylist(races_rows_out, schema=RACES_SCHEMA), RACES_PATH)

    report = {
        'mode': 'full' if full else 'incremental',
        'n_races_fresh': n_fresh, 'n_races_reused': n_reused, 'n_races_no_feeds': n_no_feeds,
        'row_counts': {name: len(rows) for name, rows in table_rows.items()},
        'dedupe': {name: dict(counts) for name, counts in dedupe_stats.items()},
        'pit_resolution': dict(pit_resolution),
        'n_races_meta_patched': n_meta_patched,
    }
    return report


def print_breadth_report(report):
    print(f"[silver_build] breadth mode={report['mode']}")
    print(f"[silver_build] races: {report['n_races_fresh']} fresh, {report['n_races_reused']} reused, "
          f"{report['n_races_no_feeds']} with no relevant feed stored")
    for name, n in report['row_counts'].items():
        d = report['dedupe'][name]
        print(f"[silver_build] silver.{name}: {n} rows "
              f"(dedup dropped={d.get('dropped', 0)}, conflicts={d.get('conflicts', 0)})")
    print(f"[silver_build] silver.races.playoff_round/stage_4_laps: "
          f"{report['n_races_meta_patched']} races patched from weekend-feed")
    pr = report['pit_resolution']
    print(f"[silver_build] pit_stops.driver_id resolution: by_car={pr.get('by_car', 0)}, "
          f"by_name={pr.get('by_name', 0)}, unresolved={pr.get('unresolved', 0)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--full', action='store_true', help='ignore build state, re-parse everything')
    args = ap.parse_args()
    race_records = warehouse.load_race_records()
    build_silver(full=args.full)
    breadth_report = build_silver_breadth(race_records, full=args.full)
    warehouse.build_warehouse()
    print('[silver_build] warehouse rebuilt with silver.races / silver.driver_race views')
    print_breadth_report(breadth_report)


if __name__ == '__main__':
    main()
