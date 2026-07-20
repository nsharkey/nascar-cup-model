#!/usr/bin/env python3
"""F13 -- driver loop-metric histories, in-house loop data (specs/loop_metric_histories.md).

Builds gold.driver_loop_race (raw, same-race, audit-only -- spec section 4.1) and
gold.driver_loop_history (AS-OF, strictly-prior, the deliverable -- spec section 4.2) from
silver.laps / silver.lap_flags (C2). Six components: ARP (green-flag-only, pinned per spec
section 2.1), green-flag pass differential, quality passes, fastest-lap share, laps-in-top-15,
closers (positions gained in the final 10% of green-flag laps). Green-flag-lap and pass are
imported verbatim from track_profiles_build (F3) per the spec's own overlap guard -- not
re-implemented here (spec section 1).

Build-graph isolation (spec section 5, enforced by gate_loop_metrics.py): neither
driver_loop_race nor driver_loop_history may ever be read by gold_build.py / walkforward.py /
predict_next.py.

Run from src/.
"""
import os
from collections import defaultdict

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import warehouse
from track_profiles_build import _green_stretches, _green_laps_by_driver

REPO_ROOT = warehouse.REPO_ROOT
GOLD_DIR = os.path.join(REPO_ROOT, 'data', 'gold')
DRIVER_LOOP_RACE_PATH = os.path.join(GOLD_DIR, 'driver_loop_race.parquet')
DRIVER_LOOP_HISTORY_PATH = os.path.join(GOLD_DIR, 'driver_loop_history.parquet')

HALF_LIFE = 8.0             # reuse of the frozen production half-life (HANDOFF.md / gold_build.py)
CLOSER_WINDOW_FRAC = 0.10   # spec section 2.6

DRIVER_LOOP_RACE_SCHEMA = pa.schema([
    ('driver_id', pa.int32()), ('race_id', pa.int32()), ('race_seq', pa.int32()),
    ('n_green_race', pa.int32()), ('green_flag_laps', pa.int32()), ('arp', pa.float64()),
    ('passes_made', pa.int32()), ('times_passed', pa.int32()), ('pass_diff', pa.int32()),
    ('quality_passes', pa.int32()), ('quality_pass_rate', pa.float64()),
    ('fastest_laps', pa.int32()), ('fastest_lap_share', pa.float64()),
    ('laps_top15', pa.int32()), ('laps_top15_rate', pa.float64()),
    ('closers', pa.float64()),
])

DRIVER_LOOP_HISTORY_SCHEMA = pa.schema([
    ('driver_id', pa.int32()), ('race_id', pa.int32()), ('race_seq', pa.int32()),
    ('n_hist', pa.int32()), ('arp_h', pa.float64()), ('pass_diff_h', pa.float64()),
    ('quality_pass_rate_h', pa.float64()), ('fastest_lap_share_h', pa.float64()),
    ('laps_top15_rate_h', pa.float64()), ('n_hist_closers', pa.int32()),
    ('closers_h', pa.float64()), ('composite_h', pa.float64()),
])

# spec section 3.1: sign-flip ARP (lower is better), everything else higher-is-better.
COMPOSITE_FIELDS = {
    'arp_h': -1.0, 'pass_diff_h': 1.0, 'quality_pass_rate_h': 1.0,
    'fastest_lap_share_h': 1.0, 'laps_top15_rate_h': 1.0, 'closers_h': 1.0,
}


# ---------------------------------------------------------------------------
# Section 3 -- scope (Cup points races with >=1 green-flag lap; global race_seq)
# ---------------------------------------------------------------------------
def load_scope_races(con):
    """race_id -> race_seq (global ordinal, spec section 3)."""
    rows = con.sql("""
        SELECT r.race_id, r.race_date
        FROM silver.races r
        WHERE r.series_id = 1 AND r.race_type_id = 1
          AND EXISTS (
              SELECT 1 FROM silver.lap_flags lf
              WHERE lf.series_id = 1 AND lf.race_id = r.race_id AND lf.flag_state = 1
          )
        ORDER BY r.race_date, r.race_id
    """).fetchall()
    return {rid: i + 1 for i, (rid, _date) in enumerate(rows)}


# ---------------------------------------------------------------------------
# Section 2 -- raw per-(driver_id, race_id) extraction
# ---------------------------------------------------------------------------
def _position_rows_by_driver(con):
    """(race_id, driver_id) -> sorted [(lap, running_pos), ...] for green-flag laps, Cup only
    (spec section 1's imported green-flag-lap join)."""
    recs = con.sql("""
        SELECT la.race_id, la.driver_id, la.lap, la.running_pos
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.running_pos IS NOT NULL
        ORDER BY la.race_id, la.driver_id, la.lap
    """).fetchall()
    by_driver = defaultdict(list)
    for rid, did, lap, pos in recs:
        by_driver[(rid, did)].append((lap, pos))
    return by_driver


def _race_green_lap_values(con):
    """race_id -> sorted distinct [laps_completed, ...] where flag_state=1 -- spec section 2.6's G,
    and the source of n_green_race, the shared rate denominator (spec section 2)."""
    recs = con.sql("""
        SELECT DISTINCT race_id, laps_completed FROM silver.lap_flags
        WHERE series_id = 1 AND flag_state = 1
        ORDER BY race_id, laps_completed
    """).fetchall()
    by_race = defaultdict(list)
    for rid, lap in recs:
        by_race[rid].append(lap)
    return by_race


def _fastest_lap_counts(con):
    """(race_id, driver_id) -> count of green-flag laps where that driver held the field's
    minimum lap_time for that lap (spec section 2.4; ties credited to every tied driver).
    Sourced from track_profiles_build._green_laps_by_driver -- imported, not re-queried."""
    by_driver = _green_laps_by_driver(con)
    by_race_lap = defaultdict(list)
    for (rid, did), seq in by_driver.items():
        for lap, lt in seq:
            by_race_lap[(rid, lap)].append((did, lt))
    counts = defaultdict(int)
    for (rid, _lap), entries in by_race_lap.items():
        min_lt = min(lt for _, lt in entries)
        for did, lt in entries:
            if lt == min_lt:
                counts[(rid, did)] += 1
    return counts


def _passes_and_quality(seq):
    """seq: sorted [(lap, pos), ...] green laps for one driver-race. Returns
    (passes_made, times_passed, quality_passes) using the imported section-1 pass definition,
    applied within each contiguous green-flag stretch (track_profiles_build._green_stretches,
    imported -- spec section 2.3)."""
    passes_made = times_passed = quality_passes = 0
    for stretch in _green_stretches(seq):
        positions = [p for _, p in stretch]
        for i in range(len(positions) - 1):
            if positions[i + 1] < positions[i]:
                passes_made += 1
                if positions[i + 1] <= 15:
                    quality_passes += 1
            elif positions[i + 1] > positions[i]:
                times_passed += 1
    return passes_made, times_passed, quality_passes


def closer_window_start(g):
    """g: sorted distinct green-flag lap values for a race. Returns l_start (spec section 2.6)."""
    return g[int(np.floor((1.0 - CLOSER_WINDOW_FRAC) * len(g)))]


def closers_value(seq, l_start):
    """seq: sorted [(lap, pos), ...] green laps for one driver-race (non-empty). Spec section 2.6.
    NULL (None) iff the driver has no green-flag lap at or after l_start."""
    at_or_after_start = [pos for lap, pos in seq if lap >= l_start]
    if not at_or_after_start:
        return None
    pos_start = at_or_after_start[0]
    pos_end = seq[-1][1]
    return float(pos_start - pos_end)


def build_driver_loop_race_rows(con):
    """spec section 2 + section 4.1 -- one row per (driver_id, race_id) in scope."""
    scope = load_scope_races(con)
    pos_by_driver = _position_rows_by_driver(con)
    green_lap_values = _race_green_lap_values(con)
    fastest_counts = _fastest_lap_counts(con)
    n_green_race = {rid: len(laps) for rid, laps in green_lap_values.items()}

    rows = []
    for (rid, did), seq in pos_by_driver.items():
        if rid not in scope:
            continue
        n_green = n_green_race.get(rid)
        if not n_green:
            continue

        arp = float(np.mean([p for _, p in seq]))
        passes_made, times_passed, quality_passes = _passes_and_quality(seq)
        laps_top15 = sum(1 for _, p in seq if p <= 15)
        fastest_laps = fastest_counts.get((rid, did), 0)

        l_start = closer_window_start(green_lap_values[rid])
        closers = closers_value(seq, l_start)

        rows.append(dict(
            driver_id=did, race_id=rid, race_seq=scope[rid],
            n_green_race=n_green, green_flag_laps=len(seq), arp=arp,
            passes_made=passes_made, times_passed=times_passed,
            pass_diff=passes_made - times_passed,
            quality_passes=quality_passes, quality_pass_rate=quality_passes / n_green,
            fastest_laps=fastest_laps, fastest_lap_share=fastest_laps / n_green,
            laps_top15=laps_top15, laps_top15_rate=laps_top15 / n_green,
            closers=closers,
        ))
    return rows


# ---------------------------------------------------------------------------
# Section 3 -- AS-OF history (strictly-prior, half-life weighted)
# ---------------------------------------------------------------------------
def build_driver_loop_history_rows(con, raw_rows):
    """spec section 3 -- mirrors gold_build.py's WF_FEATURES_SQL prior_pairs shape exactly:
    same p.race_seq < t.race_seq self-join, same "rank within the filtered subsequence" discipline
    (the fastest_lap_share_h/arp_h/etc share one subsequence since they are non-NULL together in
    the raw table by construction; closers_h has its own subsequence since closers can be NULL
    on its own, spec section 2.6)."""
    raw_table = pa.Table.from_pylist(raw_rows, schema=DRIVER_LOOP_RACE_SCHEMA)
    con.register('dlr_tmp', raw_table)
    con.execute('CREATE OR REPLACE TEMP VIEW dlr AS SELECT * FROM dlr_tmp')

    sql = f"""
    WITH prior_pairs AS (
        SELECT t.race_id AS race_id, t.driver_id AS driver_id, t.race_seq AS race_seq,
               p.race_seq AS prior_seq, p.arp AS prior_arp, p.pass_diff AS prior_pass_diff,
               p.quality_pass_rate AS prior_qpr, p.fastest_lap_share AS prior_fls,
               p.laps_top15_rate AS prior_ltr, p.closers AS prior_closers
        FROM dlr t
        JOIN dlr p ON p.driver_id = t.driver_id AND p.race_seq < t.race_seq
    ),
    main_agg AS (
        SELECT race_id, driver_id, count(*) AS n_hist,
               sum(prior_arp * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE})) AS arp_h,
               sum(prior_pass_diff * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE}))
                   AS pass_diff_h,
               sum(prior_qpr * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE}))
                   AS quality_pass_rate_h,
               sum(prior_fls * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE}))
                   AS fastest_lap_share_h,
               sum(prior_ltr * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE}))
                   AS laps_top15_rate_h
        FROM (
            SELECT race_id, driver_id, prior_arp, prior_pass_diff, prior_qpr, prior_fls, prior_ltr,
                   row_number() OVER (PARTITION BY race_id, driver_id ORDER BY prior_seq DESC) - 1
                       AS rk
            FROM prior_pairs
        )
        GROUP BY race_id, driver_id
    ),
    closer_agg AS (
        SELECT race_id, driver_id, count(*) AS n_hist_closers,
               sum(prior_closers * pow(0.5, rk / {HALF_LIFE})) / sum(pow(0.5, rk / {HALF_LIFE}))
                   AS closers_h
        FROM (
            SELECT race_id, driver_id, prior_closers,
                   row_number() OVER (PARTITION BY race_id, driver_id ORDER BY prior_seq DESC) - 1
                       AS rk
            FROM prior_pairs
            WHERE prior_closers IS NOT NULL
        )
        GROUP BY race_id, driver_id
    )
    SELECT d.race_id::INT AS race_id, d.driver_id::INT AS driver_id, d.race_seq::INT AS race_seq,
           COALESCE(m.n_hist, 0)::INT AS n_hist,
           m.arp_h AS arp_h, m.pass_diff_h AS pass_diff_h,
           m.quality_pass_rate_h AS quality_pass_rate_h,
           m.fastest_lap_share_h AS fastest_lap_share_h, m.laps_top15_rate_h AS laps_top15_rate_h,
           COALESCE(c.n_hist_closers, 0)::INT AS n_hist_closers, c.closers_h AS closers_h
    FROM dlr d
    LEFT JOIN main_agg m ON m.race_id = d.race_id AND m.driver_id = d.driver_id
    LEFT JOIN closer_agg c ON c.race_id = d.race_id AND c.driver_id = d.driver_id
    ORDER BY d.race_seq, d.driver_id
    """
    cols = ['race_id', 'driver_id', 'race_seq', 'n_hist', 'arp_h', 'pass_diff_h',
            'quality_pass_rate_h', 'fastest_lap_share_h', 'laps_top15_rate_h',
            'n_hist_closers', 'closers_h']
    rows = [dict(zip(cols, row)) for row in con.sql(sql).fetchall()]
    con.unregister('dlr_tmp')
    return rows


# ---------------------------------------------------------------------------
# Section 3.1 -- self-built composite (replaces NASCAR's Driver Rating)
# ---------------------------------------------------------------------------
def add_composite(hist_rows):
    """Mutates hist_rows in place, adding composite_h (spec section 3.1). Cross-sectional
    z-score of each of the six _h columns within that race_id, sign-flipping arp_h; requires
    ALL SIX non-NULL (no invented partial-count threshold) and >=2 drivers + nonzero stddev per
    component per race for that component's z to be defined at all."""
    by_race = defaultdict(list)
    for r in hist_rows:
        by_race[r['race_id']].append(r)

    for _rid, rows in by_race.items():
        stats = {}
        for f, sign in COMPOSITE_FIELDS.items():
            vals = [sign * r[f] for r in rows if r[f] is not None]
            if len(vals) >= 2 and np.std(vals, ddof=1) > 0:
                stats[f] = (float(np.mean(vals)), float(np.std(vals, ddof=1)))
            else:
                stats[f] = None
        for r in rows:
            zs = []
            ok = True
            for f, sign in COMPOSITE_FIELDS.items():
                if r[f] is None or stats[f] is None:
                    ok = False
                    break
                mu, sd = stats[f]
                zs.append((sign * r[f] - mu) / sd)
            r['composite_h'] = float(np.mean(zs)) if ok else None
    return hist_rows


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------
def build_loop_metrics():
    os.makedirs(GOLD_DIR, exist_ok=True)
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH)

    print('[loop_metrics_build] extracting section-2 raw per-(driver,race) values...')
    raw_rows = build_driver_loop_race_rows(con)
    print(f'[loop_metrics_build] gold.driver_loop_race: {len(raw_rows)} rows')
    pq.write_table(pa.Table.from_pylist(raw_rows, schema=DRIVER_LOOP_RACE_SCHEMA),
                   DRIVER_LOOP_RACE_PATH)

    print('[loop_metrics_build] building section-3 AS-OF histories...')
    hist_rows = build_driver_loop_history_rows(con, raw_rows)
    add_composite(hist_rows)
    n_composite = sum(1 for r in hist_rows if r['composite_h'] is not None)
    print(f'[loop_metrics_build] gold.driver_loop_history: {len(hist_rows)} rows '
          f'({n_composite} with a defined composite_h)')
    pq.write_table(pa.Table.from_pylist(hist_rows, schema=DRIVER_LOOP_HISTORY_SCHEMA),
                    DRIVER_LOOP_HISTORY_PATH)

    con.close()
    warehouse.build_warehouse()  # re-register so gold.driver_loop_race/driver_loop_history exist
    return raw_rows, hist_rows


if __name__ == '__main__':
    build_loop_metrics()
