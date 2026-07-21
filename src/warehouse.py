#!/usr/bin/env python3
"""(Re)build data/nascar.duckdb -- the derived warehouse (specs/medallion_architecture.md, 1.2).

Durable state lives only in bronze files + manifest.jsonl + silver/gold parquet + the committed
repo. This file recreates the duckdb schemas/views from that state; deleting nascar.duckdb must
never lose information. Run standalone (rebuilds bronze.*) or import build_warehouse() from
silver_build.py / gold_build.py in later sessions to extend it.
"""
import glob
import gzip
import json
import os

import duckdb
import pyarrow as pa

from bronze_fetch import ALL_FEEDS, index_year_matches, race_has_run

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(REPO_ROOT, 'data', 'bronze')
MANIFEST_PATH = os.path.join(BRONZE_DIR, 'manifest.jsonl')
DB_PATH = os.path.join(REPO_ROOT, 'data', 'nascar.duckdb')


def load_race_records():
    """Full raw record per (series_id, race_id) -- every field of the race_list_basic index
    entry, unstrimmed. Same disk-latest-snapshot-per-year and 2017-weekend-feed-fallback
    logic as _load_races_index() below, but keeping the whole dict instead of trimming to
    bronze.races_index's 7 columns: silver.races (section 3.2 of the medallion spec) needs
    scheduled_laps/stage_*_laps/winner_driver_id/schedule[]/cautions/lead-changes, all of
    which are already present verbatim on each index entry (and, for fallback years, on the
    equivalent weekend_race[0] object -- verified same field vocabulary, section 8f).
    Returns {(series_id, race_id): {'series_id', 'year', 'record': <raw dict>}}."""
    records = {}
    covered_years = set()
    race_list_root = os.path.join(BRONZE_DIR, 'race_list')
    if os.path.isdir(race_list_root):
        for year_name in sorted(os.listdir(race_list_root)):
            year_dir = os.path.join(race_list_root, year_name)
            if not os.path.isdir(year_dir):
                continue
            try:
                year = int(year_name)
            except ValueError:
                continue
            snapshots = sorted(f for f in os.listdir(year_dir) if f.endswith('.json.gz'))
            if not snapshots:
                continue
            latest = os.path.join(year_dir, snapshots[-1])
            with gzip.open(latest, 'rb') as f:
                idx = json.loads(f.read())
            if not index_year_matches(idx, year):
                # bronze immutability (section 2.5) forbids deleting a mistakenly-stored file
                # (e.g. the 2017 URL's known year-aliasing quirk); skip it here instead.
                continue
            covered_years.add(year)
            for sid in (1, 2, 3):
                for r in (idx.get(f'series_{sid}') or []):
                    rid = r.get('race_id')
                    if rid is None:
                        continue
                    records[(sid, rid)] = {'series_id': sid, 'year': year, 'record': r}
    for key, rec in _load_race_records_from_weekend_feed(covered_years).items():
        records.setdefault(key, rec)
    return records


def _load_race_records_from_weekend_feed(covered_years):
    """Fallback for years with no usable race_list index (2017 -- DATA_DICTIONARY section
    8d/8f: the URL is permanently aliased to another year) but with real weekend-feed data
    recovered by direct race_id probing. Synthesizes the same record shape per (series_id,
    race_id) directly from each race's own weekend-feed payload instead of a year-level
    index snapshot. General on purpose: applies to any year missing race_list coverage,
    not hardcoded to 2017."""
    records = {}
    series_root_names = sorted(
        n for n in os.listdir(BRONZE_DIR) if n.startswith('series_') and os.path.isdir(os.path.join(BRONZE_DIR, n))
    ) if os.path.isdir(BRONZE_DIR) else []
    for series_name in series_root_names:
        try:
            sid = int(series_name.split('_', 1)[1])
        except ValueError:
            continue
        series_dir = os.path.join(BRONZE_DIR, series_name)
        for year_name in sorted(os.listdir(series_dir)):
            year_dir = os.path.join(series_dir, year_name)
            if not os.path.isdir(year_dir):
                continue
            try:
                year = int(year_name)
            except ValueError:
                continue
            if year in covered_years:
                continue
            for race_id_name in sorted(os.listdir(year_dir)):
                race_dir_path = os.path.join(year_dir, race_id_name)
                if not os.path.isdir(race_dir_path):
                    continue
                try:
                    race_id = int(race_id_name)
                except ValueError:
                    continue
                snapshots = sorted(
                    f for f in os.listdir(race_dir_path) if f.startswith('weekend-feed.') and f.endswith('.json.gz')
                )
                if not snapshots:
                    continue
                latest = os.path.join(race_dir_path, snapshots[-1])
                with gzip.open(latest, 'rb') as f:
                    payload = json.loads(f.read())
                wr = (payload.get('weekend_race') or [{}])[0]
                records[(sid, race_id)] = {'series_id': sid, 'year': year, 'record': wr}
    return records


def _load_races_index():
    """One row per (series_id, year, race_id), trimmed to bronze.races_index's columns
    from load_race_records()'s full per-race records."""
    rows = []
    for (sid, rid), info in load_race_records().items():
        r = info['record']
        rows.append({
            'series_id': sid,
            'year': info['year'],
            'race_id': rid,
            'race_type_id': r.get('race_type_id'),
            'race_date': r.get('race_date'),
            'track_name': (r.get('track_name') or '').strip() or None,
            'has_winner': race_has_run(r),
        })
    return rows


def build_warehouse():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = duckdb.connect(DB_PATH)
    con.execute('CREATE SCHEMA IF NOT EXISTS bronze')
    con.execute('CREATE SCHEMA IF NOT EXISTS silver')
    con.execute('CREATE SCHEMA IF NOT EXISTS gold')

    manifest_glob = MANIFEST_PATH.replace('\\', '/')
    if os.path.exists(MANIFEST_PATH) and os.path.getsize(MANIFEST_PATH) > 0:
        con.execute(f"""
            CREATE OR REPLACE VIEW bronze.manifest AS
            SELECT * FROM read_json_auto('{manifest_glob}', format='newline_delimited')
        """)
    else:
        con.execute("""
            CREATE OR REPLACE VIEW bronze.manifest AS
            SELECT NULL::VARCHAR AS run_id, NULL::TIMESTAMP AS fetch_utc, NULL::VARCHAR AS url,
                   NULL::VARCHAR AS feed, NULL::INT AS series_id, NULL::INT AS year, NULL::INT AS race_id,
                   NULL::VARCHAR AS outcome, NULL::INT AS http_status, NULL::VARCHAR AS sha256,
                   NULL::BIGINT AS bytes_raw, NULL::BIGINT AS bytes_gz, NULL::VARCHAR AS path,
                   NULL::INT AS attempts, NULL::VARCHAR AS error
            WHERE FALSE
        """)

    series_glob = os.path.join(BRONZE_DIR, 'series_*', '*', '*', '*.json.gz').replace('\\', '/')
    race_list_glob = os.path.join(BRONZE_DIR, 'race_list', '*', '*.json.gz').replace('\\', '/')
    legacy_glob = os.path.join(BRONZE_DIR, 'legacy_import', '*.json.gz').replace('\\', '/')

    repo_root_prefix = (REPO_ROOT + '/').replace('\\', '/')
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.files AS
        WITH series_files AS (
            SELECT replace(file, '{repo_root_prefix}', '') AS path,
                   regexp_extract(file, 'series_(\\d+)/', 1)::INT AS series_id,
                   regexp_extract(file, 'series_\\d+/(\\d+)/', 1)::INT AS year,
                   regexp_extract(file, 'series_\\d+/\\d+/(\\d+)/', 1)::INT AS race_id,
                   regexp_extract(file, '/([a-z-]+)\\.\\d{{8}}T\\d{{6}}Z\\.json\\.gz$', 1) AS feed,
                   regexp_extract(file, '\\.(\\d{{8}}T\\d{{6}}Z)\\.json\\.gz$', 1) AS fetch_ts
            FROM glob('{series_glob}')
        ),
        race_list_files AS (
            SELECT replace(file, '{repo_root_prefix}', '') AS path,
                   NULL::INT AS series_id,
                   regexp_extract(file, 'race_list/(\\d+)/', 1)::INT AS year,
                   NULL::INT AS race_id,
                   'race_list' AS feed,
                   regexp_extract(file, '\\.(\\d{{8}}T\\d{{6}}Z)\\.json\\.gz$', 1) AS fetch_ts
            FROM glob('{race_list_glob}')
        ),
        legacy_files AS (
            SELECT replace(file, '{repo_root_prefix}', '') AS path,
                   NULL::INT AS series_id, NULL::INT AS year, NULL::INT AS race_id,
                   'legacy_import' AS feed, NULL::VARCHAR AS fetch_ts
            FROM glob('{legacy_glob}')
        ),
        all_files AS (
            SELECT * FROM series_files
            UNION ALL SELECT * FROM race_list_files
            UNION ALL SELECT * FROM legacy_files
        )
        SELECT f.*, m.sha256, m.bytes_raw, m.bytes_gz
        FROM all_files f
        LEFT JOIN (
            SELECT path, sha256, bytes_raw, bytes_gz
            FROM bronze.manifest
            WHERE path IS NOT NULL
            QUALIFY row_number() OVER (PARTITION BY path ORDER BY fetch_utc DESC) = 1
        ) m USING (path)
    """)

    con.execute("""
        CREATE OR REPLACE VIEW bronze.files_latest AS
        SELECT * FROM bronze.files
        QUALIFY row_number() OVER (
            PARTITION BY feed, series_id, year, race_id ORDER BY fetch_ts DESC NULLS LAST
        ) = 1
    """)

    con.execute("""
        CREATE OR REPLACE VIEW bronze.manifest_latest AS
        SELECT feed, series_id, year, race_id, outcome, http_status, error, fetch_utc
        FROM bronze.manifest
        QUALIFY row_number() OVER (
            PARTITION BY feed, series_id, year, race_id ORDER BY fetch_utc DESC
        ) = 1
    """)

    races_index_rows = _load_races_index()
    if races_index_rows:
        tbl = pa.Table.from_pylist(races_index_rows)
        con.register('_races_index_stage', tbl)
        con.execute('CREATE OR REPLACE TABLE bronze.races_index AS SELECT * FROM _races_index_stage')
        con.unregister('_races_index_stage')
    else:
        con.execute("""
            CREATE OR REPLACE TABLE bronze.races_index (
                series_id INT, year INT, race_id INT, race_type_id INT,
                race_date VARCHAR, track_name VARCHAR, has_winner BOOLEAN
            )
        """)

    feeds_list = ', '.join(f"('{f}')" for f in ALL_FEEDS)
    con.execute(f"""
        CREATE OR REPLACE VIEW bronze.coverage AS
        WITH feeds(feed) AS (VALUES {feeds_list})
        SELECT
            ri.series_id, ri.year, ri.race_id, ri.race_type_id, ri.has_winner, f.feed,
            CASE
                WHEN fl.path IS NOT NULL THEN 'stored'
                WHEN ml.outcome = 'absent' THEN 'absent'
                WHEN ml.outcome = 'failed' THEN 'failed'
                WHEN NOT ri.has_winner THEN 'pending'
                ELSE 'pending'
            END AS state
        FROM bronze.races_index ri
        CROSS JOIN feeds f
        LEFT JOIN bronze.files_latest fl
            ON fl.feed = f.feed AND fl.series_id = ri.series_id
           AND fl.year = ri.year AND fl.race_id = ri.race_id
        LEFT JOIN bronze.manifest_latest ml
            ON ml.feed = f.feed AND ml.series_id = ri.series_id
           AND ml.year = ri.year AND ml.race_id = ri.race_id
    """)

    silver_dir = os.path.join(REPO_ROOT, 'data', 'silver')
    silver_races_path = os.path.join(silver_dir, 'races.parquet').replace('\\', '/')
    if os.path.exists(silver_races_path):
        con.execute(f"CREATE OR REPLACE VIEW silver.races AS SELECT * FROM read_parquet('{silver_races_path}')")
    silver_driver_race_path = os.path.join(silver_dir, 'driver_race.parquet').replace('\\', '/')
    if os.path.exists(silver_driver_race_path):
        con.execute(
            f"CREATE OR REPLACE VIEW silver.driver_race AS SELECT * FROM read_parquet('{silver_driver_race_path}')"
        )

    # Section 3.4 breadth tables (C2) + track reference tables (C3, research/track_audit_derivation.md
    # section 2) -- same rebuildable-from-disk view pattern as above.
    for table_name in ('results', 'laps', 'lap_flags', 'flag_events', 'pit_stops',
                        'lap_notes', 'practice_runs', 'live_final',
                        'caution_segments', 'stage_results', 'race_leaders',
                        'track_dim', 'track_xwalk', 'track_priors', 'track_similarity_prior',
                        'rules_era', 'race_track', 'race_track_features'):
        path = os.path.join(silver_dir, f'{table_name}.parquet').replace('\\', '/')
        if os.path.exists(path):
            con.execute(f"CREATE OR REPLACE VIEW silver.{table_name} AS SELECT * FROM read_parquet('{path}')")

    # Gold (D1, section 5) -- same rebuildable-from-disk view pattern.
    gold_dir = os.path.join(REPO_ROOT, 'data', 'gold')
    for table_name in ('track_typology', 'wf_features', 'driver_form', 'driver_type_form',
                       'track_profiles', 'track_profiles_asof',
                       'track_dst', 'track_dst_edges', 'track_pltree', 'track_pltree_splits',
                       'driver_loop_race', 'driver_loop_history',
                       'equip_share_worths', 'equip_share_summary', 'equip_share_connectivity'):
        path = os.path.join(gold_dir, f'{table_name}.parquet').replace('\\', '/')
        if os.path.exists(path):
            con.execute(f"CREATE OR REPLACE VIEW gold.{table_name} AS SELECT * FROM read_parquet('{path}')")

    # Gold read-only conveniences (D2, section 5.5): views over the CSV/JSON artifacts of record.
    # These never write -- predictions/scores_log.csv and the sealed prediction JSONs stay the
    # artifacts of record, exactly as section 5.5 specifies.
    scores_csv_path = os.path.join(REPO_ROOT, 'predictions', 'scores_log.csv').replace('\\', '/')
    if os.path.exists(scores_csv_path):
        con.execute(f"CREATE OR REPLACE VIEW gold.scores AS "
                    f"SELECT * FROM read_csv_auto('{scores_csv_path}', header=true)")

    predictions_glob = os.path.join(REPO_ROOT, 'predictions', 'race_*_prediction.json').replace('\\', '/')
    if glob.glob(predictions_glob):
        con.execute(f"CREATE OR REPLACE VIEW gold.predictions AS "
                    f"SELECT * FROM read_json_auto('{predictions_glob}', union_by_name=true)")

    con.close()


if __name__ == '__main__':
    build_warehouse()
    con = duckdb.connect(DB_PATH, read_only=True)
    print('[warehouse] schemas: bronze, silver, gold')
    print('[warehouse] bronze.files rows:', con.sql('SELECT count(*) FROM bronze.files').fetchone()[0])
    print('[warehouse] bronze.races_index rows:', con.sql('SELECT count(*) FROM bronze.races_index').fetchone()[0])
    con.close()
