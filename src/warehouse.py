#!/usr/bin/env python3
"""(Re)build data/nascar.duckdb -- the derived warehouse (specs/medallion_architecture.md, 1.2).

Durable state lives only in bronze files + manifest.jsonl + silver/gold parquet + the committed
repo. This file recreates the duckdb schemas/views from that state; deleting nascar.duckdb must
never lose information. Run standalone (rebuilds bronze.*) or import build_warehouse() from
silver_build.py / gold_build.py in later sessions to extend it.
"""
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


def _load_races_index():
    """One row per (series_id, year, race_id) from the latest on-disk race_list snapshot per year.
    Python, not SQL: the index JSON nests races under series_1/2/3 keys, and only the *latest*
    version per year is wanted (disk-latest = lexicographic max filename, per section 1.1)."""
    rows = []
    race_list_root = os.path.join(BRONZE_DIR, 'race_list')
    if not os.path.isdir(race_list_root):
        return rows
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
        for sid in (1, 2, 3):
            for r in (idx.get(f'series_{sid}') or []):
                rows.append({
                    'series_id': sid,
                    'year': year,
                    'race_id': r.get('race_id'),
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

    con.close()


if __name__ == '__main__':
    build_warehouse()
    con = duckdb.connect(DB_PATH, read_only=True)
    print('[warehouse] schemas: bronze, silver, gold')
    print('[warehouse] bronze.files rows:', con.sql('SELECT count(*) FROM bronze.files').fetchone()[0])
    print('[warehouse] bronze.races_index rows:', con.sql('SELECT count(*) FROM bronze.races_index').fetchone()[0])
    con.close()
