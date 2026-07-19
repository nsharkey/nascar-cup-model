#!/usr/bin/env python3
"""Bronze coverage matrix + terminal-state report (specs/medallion_architecture.md, 2.3/2.9).

Rebuilds the warehouse, then prints per-year x per-series x per-feed terminal-state counts and
overall totals. This is the interim report for B2; B3 owns the full committed
report/BRONZE_COVERAGE.md with the spot-parse and hash-verify checks.
"""
import duckdb

import warehouse

DB_PATH = warehouse.DB_PATH


def main():
    warehouse.build_warehouse()
    con = duckdb.connect(DB_PATH, read_only=True)

    print('=' * 78)
    print('BRONZE COVERAGE -- interim report')
    print('=' * 78)

    total_races = con.sql('SELECT count(*) FROM bronze.races_index').fetchone()[0]
    print(f'\nindex races on disk (latest snapshot per year): {total_races}')

    print('\n-- index snapshot terminal state by year --')
    con.sql("""
        SELECT ri.year,
               count(DISTINCT ri.race_id) AS races,
               sum(CASE WHEN ri.has_winner THEN 1 ELSE 0 END) AS with_winner
        FROM bronze.races_index ri
        GROUP BY ri.year ORDER BY ri.year
    """).show(max_rows=100)

    print('\n-- terminal state counts by feed (all years/series, run races only) --')
    con.sql("""
        SELECT feed, state, count(*) AS n
        FROM bronze.coverage
        WHERE has_winner
        GROUP BY feed, state
        ORDER BY feed, state
    """).show(max_rows=100)

    print('\n-- terminal state counts by series (all years, run races only) --')
    con.sql("""
        SELECT series_id, state, count(*) AS n
        FROM bronze.coverage
        WHERE has_winner
        GROUP BY series_id, state
        ORDER BY series_id, state
    """).show(max_rows=100)

    print('\n-- overall totals --')
    con.sql("""
        SELECT state, count(*) AS n
        FROM bronze.coverage
        WHERE has_winner
        GROUP BY state ORDER BY state
    """).show()

    failed_count = con.sql("""
        SELECT count(*) FROM bronze.coverage WHERE has_winner AND state = 'failed'
    """).fetchone()[0]
    print(f'\nfailed terminal count: {failed_count}')
    if failed_count:
        con.sql("""
            SELECT series_id, year, race_id, feed
            FROM bronze.coverage
            WHERE has_winner AND state = 'failed'
            ORDER BY series_id, year, race_id, feed
            LIMIT 50
        """).show(max_rows=50)
        if failed_count > 50:
            print(f'  ... and {failed_count - 50} more (see bronze.coverage in the warehouse)')

    print('\n-- first-year-with-data per feed per series (discovered floor) --')
    con.sql("""
        SELECT series_id, feed, min(year) AS first_year_stored
        FROM bronze.coverage
        WHERE state = 'stored'
        GROUP BY series_id, feed
        ORDER BY series_id, feed
    """).show(max_rows=100)

    n_files, bytes_raw, bytes_gz = con.sql("""
        SELECT count(*) AS n_files, sum(bytes_raw) AS bytes_raw, sum(bytes_gz) AS bytes_gz
        FROM bronze.files
    """).fetchone()
    bytes_raw = bytes_raw or 0
    bytes_gz = bytes_gz or 0
    print(f'\ntotal stored files: {n_files}  raw: {bytes_raw/1e6:.1f} MB  gzipped: {bytes_gz/1e6:.1f} MB')

    versions = {'duckdb': duckdb.__version__}
    try:
        import pyarrow
        versions['pyarrow'] = pyarrow.__version__
    except Exception:
        pass
    print(f'\nlibrary versions: {versions}')

    con.close()


if __name__ == '__main__':
    main()
