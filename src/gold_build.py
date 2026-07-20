#!/usr/bin/env python3
"""Gold build -- walk-forward feature bank in SQL (specs/medallion_architecture.md section 5).

Builds gold.track_typology (5.1), gold.wf_features (5.2), and the current-form views
gold.driver_form / gold.driver_type_form (5.3) over silver.driver_race / silver.races.
Transcribes walkforward.run()'s history mechanics exactly, including the pace_h/typ_h
subsequence-indexing detail (the recency exponent ranks WITHIN the filtered subsequence,
not within all prior races -- "the classic transcription bug", section 5.2).

2026-07-19 D1 amendment (spec section 5, `## AMENDMENT` block before 5.3): gold.wf_features's
scope and its own history window are bounded to series_id=1, race_type_id=1, parse_status='ok',
year >= 2022 -- an exact match to what races_parsed.pkl ever contained (src/download.py, retired
at B2, only ever fetched 2022+ Cup data). Building the literal unbounded scope would give 2022
drivers real 2020-2021 history the legacy engine structurally can't have, failing the D-gate's R2
("identical n_hist") for a data-window reason, not a plumbing one. Owner-authorized before any
gold code was written. gold.driver_form / gold.driver_type_form inherit the same bound for
consistency (built from the same scope-filtered driver-race set).

Run from src/.
"""
import os

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

import warehouse

REPO_ROOT = warehouse.REPO_ROOT
GOLD_DIR = os.path.join(REPO_ROOT, 'data', 'gold')
TRACK_TYPOLOGY_PATH = os.path.join(GOLD_DIR, 'track_typology.parquet')
WF_FEATURES_PATH = os.path.join(GOLD_DIR, 'wf_features.parquet')
DRIVER_FORM_PATH = os.path.join(GOLD_DIR, 'driver_form.parquet')
DRIVER_TYPE_FORM_PATH = os.path.join(GOLD_DIR, 'driver_type_form.parquet')

MIN_YEAR = 2022        # 2026-07-19 D1 amendment -- see module docstring
HALF_LIFE = 8.0         # frozen config (HANDOFF.md)
SHRINK_K = 3.0          # frozen shrinkage constant (walkforward.run, typed_mode='shrinkage')

SCOPE_RACES_SQL = f"""
CREATE OR REPLACE TEMP VIEW scope_races AS
SELECT race_id, race_date, track_name,
       row_number() OVER (ORDER BY race_date, race_id) AS race_seq
FROM silver.races
WHERE series_id = 1 AND race_type_id = 1 AND parse_status = 'ok' AND year >= {MIN_YEAR}
"""

DR_VIEW_SQL = """
CREATE OR REPLACE TEMP VIEW dr AS
SELECT d.driver_id, d.race_id, sr.race_seq,
       d.finish, d.start, d.pace_med85,
       COALESCE(tt.ttype, 'UNIQ') AS ttype
FROM silver.driver_race d
JOIN scope_races sr ON sr.race_id = d.race_id
LEFT JOIN gold.track_typology tt ON tt.track_name = sr.track_name
WHERE d.series_id = 1
"""

# Every prior-race-vs-target-race pair for the same driver -- the raw material for n_hist/
# fin_h/pace_h/typ_h. rk (recency rank, 0 = the immediately preceding qualifying race) is
# computed SEPARATELY within each of the three downstream aggregates because pace_h and typ_h
# each rank within their own filtered subsequence, not within all prior races.
WF_FEATURES_SQL = f"""
WITH prior_pairs AS (
    SELECT t.race_id AS race_id, t.driver_id AS driver_id, t.ttype AS target_ttype,
           p.race_seq AS prior_seq, p.finish AS prior_finish, p.pace_med85 AS prior_pace,
           p.ttype AS prior_ttype
    FROM dr t
    JOIN dr p ON p.driver_id = t.driver_id AND p.race_seq < t.race_seq
),
fin_agg AS (
    SELECT race_id, driver_id, count(*) AS n_hist,
           sum(prior_finish * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS fin_h
    FROM (
        SELECT race_id, driver_id, prior_finish,
               row_number() OVER (PARTITION BY race_id, driver_id ORDER BY prior_seq DESC) - 1 AS rk
        FROM prior_pairs
    )
    GROUP BY race_id, driver_id
),
pace_agg AS (
    -- subsequence = prior races with non-null pace_med85 ONLY; rk ranks within that
    -- subsequence (filter first, then rank) -- not within all prior races.
    SELECT race_id, driver_id,
           sum(prior_pace * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS pace_h
    FROM (
        SELECT race_id, driver_id, prior_pace,
               row_number() OVER (PARTITION BY race_id, driver_id ORDER BY prior_seq DESC) - 1 AS rk
        FROM prior_pairs
        WHERE prior_pace IS NOT NULL
    )
    GROUP BY race_id, driver_id
),
typed_agg AS (
    -- subsequence = prior races whose OWN track's ttype equals the target race's ttype;
    -- rk ranks within that subsequence (filter first, then rank).
    SELECT race_id, driver_id, count(*) AS m,
           sum(prior_finish * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS typed_wmean
    FROM (
        SELECT race_id, driver_id, prior_finish,
               row_number() OVER (PARTITION BY race_id, driver_id ORDER BY prior_seq DESC) - 1 AS rk
        FROM prior_pairs
        WHERE prior_ttype = target_ttype
    )
    GROUP BY race_id, driver_id
)
SELECT
    base.race_id::INT AS race_id, base.driver_id::INT AS driver_id, base.race_seq::INT AS race_seq,
    COALESCE(fin_agg.n_hist, 0)::INT AS n_hist,
    fin_agg.fin_h AS fin_h,
    pace_agg.pace_h AS pace_h,
    CASE
        WHEN fin_agg.fin_h IS NULL THEN NULL
        WHEN typed_agg.m IS NULL OR typed_agg.m = 0 THEN fin_agg.fin_h
        ELSE (typed_agg.m * typed_agg.typed_wmean + {SHRINK_K} * fin_agg.fin_h) / (typed_agg.m + {SHRINK_K})
    END AS typ_h,
    (CASE WHEN base.start IS NULL OR base.start = 0 THEN 20 ELSE base.start END)::INT AS start_feat,
    (base.pace_med85 IS NOT NULL) AS has_pace,
    base.finish::INT AS finish
FROM dr base
LEFT JOIN fin_agg ON fin_agg.race_id = base.race_id AND fin_agg.driver_id = base.driver_id
LEFT JOIN pace_agg ON pace_agg.race_id = base.race_id AND pace_agg.driver_id = base.driver_id
LEFT JOIN typed_agg ON typed_agg.race_id = base.race_id AND typed_agg.driver_id = base.driver_id
ORDER BY base.race_seq, base.driver_id
"""

# Current form (section 5.3): "as of the latest parsed race" -- i.e. every scope race counts
# as history, ranked by recency with no target race to exclude.
DRIVER_FORM_SQL = f"""
WITH fin_agg AS (
    SELECT driver_id, count(*) AS n_hist,
           sum(finish * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS fin_h
    FROM (
        SELECT driver_id, finish,
               row_number() OVER (PARTITION BY driver_id ORDER BY race_seq DESC) - 1 AS rk
        FROM dr
    )
    GROUP BY driver_id
),
pace_agg AS (
    SELECT driver_id,
           sum(pace_med85 * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS pace_h
    FROM (
        SELECT driver_id, pace_med85,
               row_number() OVER (PARTITION BY driver_id ORDER BY race_seq DESC) - 1 AS rk
        FROM dr
        WHERE pace_med85 IS NOT NULL
    )
    GROUP BY driver_id
)
SELECT f.driver_id::INT AS driver_id, f.n_hist::INT AS n_hist, f.fin_h AS fin_h, p.pace_h AS pace_h
FROM fin_agg f
LEFT JOIN pace_agg p ON p.driver_id = f.driver_id
ORDER BY f.driver_id
"""

DRIVER_TYPE_FORM_SQL = f"""
SELECT driver_id::INT AS driver_id, ttype, count(*)::INT AS m,
       sum(finish * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS typed_wmean
FROM (
    SELECT driver_id, ttype, finish,
           row_number() OVER (PARTITION BY driver_id, ttype ORDER BY race_seq DESC) - 1 AS rk
    FROM dr
)
GROUP BY driver_id, ttype
ORDER BY driver_id, ttype
"""


def build_gold():
    os.makedirs(GOLD_DIR, exist_ok=True)
    warehouse.build_warehouse()  # ensure silver.* views reflect the current --full parquet state

    # 5.1: MY_TYPE imported (not hand-transcribed) from walkforward.py -- the strongest available
    # guarantee of "verbatim" (spec 5.1), no transcription-typo risk on a 40-entry dict.
    from walkforward import MY_TYPE
    typology_rows = [{'track_name': k, 'ttype': v} for k, v in MY_TYPE.items()]
    typology_schema = pa.schema([('track_name', pa.string()), ('ttype', pa.string())])
    pq.write_table(pa.Table.from_pylist(typology_rows, schema=typology_schema), TRACK_TYPOLOGY_PATH)
    print(f'[gold_build] gold.track_typology: {len(typology_rows)} rows')

    con = duckdb.connect(warehouse.DB_PATH)
    con.execute(f"CREATE OR REPLACE VIEW gold.track_typology AS "
                f"SELECT * FROM read_parquet('{TRACK_TYPOLOGY_PATH}')")
    con.execute(SCOPE_RACES_SQL)
    con.execute(DR_VIEW_SQL)

    wf_table = con.sql(WF_FEATURES_SQL).fetch_arrow_table()
    pq.write_table(wf_table, WF_FEATURES_PATH)
    print(f'[gold_build] gold.wf_features: {wf_table.num_rows} rows '
          f'(scope: series_id=1, race_type_id=1, parse_status=ok, year>={MIN_YEAR})')

    form_table = con.sql(DRIVER_FORM_SQL).fetch_arrow_table()
    pq.write_table(form_table, DRIVER_FORM_PATH)
    print(f'[gold_build] gold.driver_form: {form_table.num_rows} rows')

    type_form_table = con.sql(DRIVER_TYPE_FORM_SQL).fetch_arrow_table()
    pq.write_table(type_form_table, DRIVER_TYPE_FORM_PATH)
    print(f'[gold_build] gold.driver_type_form: {type_form_table.num_rows} rows')

    con.close()
    warehouse.build_warehouse()  # re-register gold.* as durable views over the parquet just written
    print('[gold_build] warehouse rebuilt with gold.* views')


if __name__ == '__main__':
    build_gold()
