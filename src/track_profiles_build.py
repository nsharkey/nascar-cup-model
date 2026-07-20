#!/usr/bin/env python3
"""F3 -- track-audit prior calibration: empirical track profiles (specs/track_profiles.md).

Builds gold.track_profiles (full-sample, analytics/DFS/betting reference ONLY) and
gold.track_profiles_asof (walk-forward, the only variant that could ever be feature-eligible,
and only via its own later gated A/B). Ten metrics per research/track_audit_derivation.md
section 3 (TDS/TPP/PDI/ARS/RVS/PIS/QIS/SFS/DCI/FVS) plus the F16 additions (caution-cause
taxonomy, K7 make-clustering, H5 contender-exclusion sensitivity). specs/track_profiles.md
is the execution contract -- read that first; this module implements it mechanically.

Build-graph isolation (spec section 1.8, enforced by gate_track_profiles.py): this module reads
gold.wf_features (for QIS/FVS-model) but nothing in gold_build.py/walkforward.py/predict_next.py
may ever read from gold.track_profiles* -- one-directional.

Run from src/.
"""
import os
from collections import defaultdict

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import theilslopes

import warehouse
import walkforward
from walkforward import MY_TYPE, pl_fit, wmean, znan
import gate_gold

REPO_ROOT = warehouse.REPO_ROOT
GOLD_DIR = os.path.join(REPO_ROOT, 'data', 'gold')
TRACK_PROFILES_PATH = os.path.join(GOLD_DIR, 'track_profiles.parquet')
TRACK_PROFILES_ASOF_PATH = os.path.join(GOLD_DIR, 'track_profiles_asof.parquet')

SHRINK_K = 5.0            # fixed a priori, spec section 1.5
MIN_RACES_DEFAULT = 5     # fixed a priori, spec section 1.4

# metric -> (min_races, min_events) -- spec section 1.4 table
FLOORS = {
    'tds_core':                    (5, 15),
    'tds_dispersion':               (5, 15),
    'tpp':                          (5, 10),
    'pdi':                          (5, 300),
    'pdi_v1':                       (5, 300),
    'ars_a_crash_dnf_rate':         (5, 100),
    'ars_a_mech_dnf_rate':          (5, 100),
    'ars_b_common_cause_mean_cars': (5, 8),
    'ars_c_major_loss_tail_p':      (5, 150),
    'ars_caution_accident_share':   (5, 10),
    'ars_lucky_dog_rate':           (5, 10),
    'ars_b_make_clustering_index':  (5, 500),
    'rvs':                          (5, 20),
    'pis':                          (5, 40),
    'pit_stop_duration':            (5, 40),
    'penalty_rate':                 (5, 40),
    'qis':                          (5, 60),
    'sfs':                          (5, 40),
    'sfs_nonmodal_top5_share':      (5, 40),
    'dci_laps_led_hhi':             (5, 5),
    'dci_fastest_laps_hhi':         (5, 5),
    'fvs_simple_sd':                (5, 5),
    'fvs_simple_top10_deep_start':  (5, 5),
    'fvs_model':                    (5, 5),
}

PRIOR_NAME_OF = {
    'tds_core': 'tire_degradation_prior', 'tpp': 'track_position_premium_prior',
    'pdi': 'passing_difficulty_prior', 'ars_a_crash_dnf_rate': 'attrition_risk_prior',
    'rvs': 'restart_volatility_prior', 'pis': 'pit_road_importance_prior',
    'qis': 'qualifying_importance_prior', 'sfs': 'strategy_flexibility_prior',
    'dci_combined': 'dfs_dominator_concentration_prior', 'fvs_model': 'finish_variance_prior',
}


# ---------------------------------------------------------------------------
# Shared reference loaders
# ---------------------------------------------------------------------------
def load_track_family(con):
    """track_id -> primary_family, from silver.track_dim (C3)."""
    rows = con.sql("SELECT track_id, primary_family FROM silver.track_dim").fetchall()
    return {r[0]: r[1] for r in rows}


def load_race_track_era(con):
    """(series_id=1) race_id -> (track_id, era_key), from silver.race_track_features (C3)."""
    rows = con.sql("""
        SELECT race_id, track_id, era_key FROM silver.race_track_features WHERE series_id = 1
    """).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def load_race_dates(con):
    """race_id -> race_date (text), from silver.races, Cup points races only."""
    rows = con.sql("""
        SELECT race_id, race_date FROM silver.races WHERE series_id = 1 AND race_type_id = 1
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def load_race_years(con):
    rows = con.sql("""
        SELECT race_id, year FROM silver.races WHERE series_id = 1 AND race_type_id = 1
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def restrict_and_reseq(rows, year_of, min_year, dates):
    """Post-filter a metric's own eligible universe to year >= min_year (spec section 2's
    per-metric depth annotations, honored verbatim even where the raw feed technically extends
    further -- e.g. TDS/TPP/PDI/RVS/PIS/SFS/ARS-b/ARS-c/DCI-fastest are all pinned '>=2022' by
    their own derivation-doc subsection), then reassign race_seq over the narrowed universe."""
    kept = [r for r in rows if year_of.get(r['race_id'], 0) >= min_year]
    seq = assign_race_seq([r['race_id'] for r in kept], dates)
    for r in kept:
        r['race_seq'] = seq[r['race_id']]
    return kept


def assign_race_seq(race_ids, race_dates):
    """Metric-scope-relative race_seq (spec section 1.6): 1-based rank of race_id within the
    given set, ordered by (race_date, race_id) ascending."""
    ordered = sorted(set(race_ids), key=lambda rid: (race_dates[rid], rid))
    return {rid: i + 1 for i, rid in enumerate(ordered)}


# ---------------------------------------------------------------------------
# Shared aggregation: per-race raw values -> full-sample + as-of track/family blends
# (spec sections 1.3-1.5)
# ---------------------------------------------------------------------------
def blend_values(track_raw, family_raw, n_races, n_events, min_races, min_events, k=SHRINK_K):
    """The spec section 1.5 shrinkage-and-floor rule, as a standalone scalar operation so
    non-mean metrics (ARS-a's beta-binomial, QIS's regression coefficient) can call it directly
    instead of going through compute_profiles' per-race-list aggregation."""
    below_floor = not (n_races >= min_races and n_events >= min_events)
    if below_floor or track_raw is None:
        value = family_raw
    elif family_raw is None:
        value = track_raw
    else:
        w = n_races / (n_races + k)
        value = w * track_raw + (1 - w) * family_raw
    return dict(value=value, track_raw=track_raw, family_raw=family_raw,
                n_races=n_races, n_events=n_events, below_floor=bool(below_floor))


def compute_profiles(rows, family_of, min_races, min_events, agg_fn=None, k=SHRINK_K):
    """rows: list of dict(track_id, era_key, race_id, race_seq, v, e, ...) with v the per-race
    raw value (spec 1.3, None rows dropped) and e the per-race event count (spec 1.4). Extra
    per-row fields are preserved and visible to agg_fn for metrics that aggregate something
    other than a plain mean of v (e.g. ARS-a's beta-binomial success/trial sums).
    agg_fn: list[row-dict] -> float, default mean of r['v'] (TDS_core passes a median agg_fn).
    Returns (full_sample, asof):
      full_sample: dict (track_id, era_key) -> result dict
      asof:        dict (track_id, era_key, race_id) -> result dict (adds race_id, race_seq)
    """
    agg_fn = agg_fn or (lambda rs: float(np.mean([r['v'] for r in rs])))
    rows = [r for r in rows if r['v'] is not None]

    by_track_era = defaultdict(list)
    by_fam_era = defaultdict(list)
    for r in rows:
        fam = family_of[r['track_id']]
        by_track_era[(r['track_id'], r['era_key'])].append(r)
        by_fam_era[(fam, r['era_key'])].append(r)
    for lst in by_track_era.values():
        lst.sort(key=lambda r: r['race_seq'])
    for lst in by_fam_era.values():
        lst.sort(key=lambda r: r['race_seq'])

    def blend(track_sub, fam_sub):
        n_races = len(track_sub)
        n_events = sum(r['e'] for r in track_sub)
        track_raw = agg_fn(track_sub) if track_sub else None
        family_raw = agg_fn(fam_sub) if fam_sub else None
        return blend_values(track_raw, family_raw, n_races, n_events, min_races, min_events, k)

    full_sample = {}
    for key, sub in by_track_era.items():
        fam = family_of[key[0]]
        fam_sub = by_fam_era[(fam, key[1])]
        full_sample[key] = blend(sub, fam_sub)

    asof = {}
    for key, sub in by_track_era.items():
        fam = family_of[key[0]]
        fam_sub_all = by_fam_era[(fam, key[1])]
        for i, r in enumerate(sub):
            prior_track = sub[:i]
            prior_fam = [x for x in fam_sub_all if x['race_seq'] < r['race_seq']]
            res = blend(prior_track, prior_fam)
            res['race_id'] = r['race_id']
            res['race_seq'] = r['race_seq']
            asof[(key[0], key[1], r['race_id'])] = res

    return full_sample, asof


def _mkrows(con, sql, rte, dates, extra_fields=()):
    """Common shape: sql yields (race_id, v, e, *extra), joined to (track_id, era_key) via rte
    and race_seq via dates (assigned over exactly the races sql returns). Rows whose race_id
    isn't in rte (not a Cup race_track_features race) are dropped."""
    out = con.sql(sql).fetchall()
    race_ids = [r[0] for r in out if r[0] in rte]
    seq = assign_race_seq(race_ids, dates)
    rows = []
    for rec in out:
        rid = rec[0]
        if rid not in rte or rid not in seq:
            continue
        track_id, era_key = rte[rid]
        row = dict(track_id=track_id, era_key=era_key, race_id=rid, race_seq=seq[rid],
                   v=rec[1], e=rec[2])
        for name, val in zip(extra_fields, rec[3:]):
            row[name] = val
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 2.9 DCI -- laps_led component (results-grade, 2017+)
# ---------------------------------------------------------------------------
def extract_dci_laps_led(con, rte, dates):
    sql = """
        WITH ll AS (
            SELECT race_id, driver_id, laps_led::DOUBLE AS laps_led
            FROM silver.results WHERE series_id = 1 AND laps_led > 0
        ), tot AS (
            SELECT race_id, sum(laps_led) AS total FROM ll GROUP BY race_id
        )
        SELECT ll.race_id, sum(power(ll.laps_led / tot.total, 2)) AS hhi, 1 AS e
        FROM ll JOIN tot USING (race_id)
        GROUP BY ll.race_id
    """
    return _mkrows(con, sql, rte, dates)


# ---------------------------------------------------------------------------
# 2.9 DCI -- fastest-laps component (>=2022, lap-times floor; prefers live_final)
# ---------------------------------------------------------------------------
def extract_dci_fastest_laps(con, rte, dates):
    sql_live = """
        WITH f AS (
            SELECT race_id, driver_id, fastest_laps_run::DOUBLE AS n
            FROM silver.live_final WHERE series_id = 1 AND fastest_laps_run > 0
        ), tot AS (SELECT race_id, sum(n) AS total FROM f GROUP BY race_id)
        SELECT f.race_id, sum(power(f.n / tot.total, 2)) AS hhi, 1 AS e
        FROM f JOIN tot USING (race_id) GROUP BY f.race_id
    """
    live_rows = _mkrows(con, sql_live, rte, dates)
    have_live = {r['race_id'] for r in live_rows}

    # fallback: per green lap, the min lap_time driver gets one fastest-lap credit
    sql_laps = """
        WITH green AS (
            SELECT la.race_id, la.driver_id, la.lap, la.lap_time
            FROM silver.laps la
            JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
                AND lf.laps_completed = la.lap AND lf.flag_state = 1
            WHERE la.series_id = 1 AND la.lap_time IS NOT NULL AND la.lap_time > 0
        ), winner AS (
            SELECT race_id, lap, driver_id,
                   row_number() OVER (PARTITION BY race_id, lap ORDER BY lap_time ASC) AS rk
            FROM green
        ), counts AS (
            SELECT race_id, driver_id, count(*)::DOUBLE AS n
            FROM winner WHERE rk = 1 GROUP BY race_id, driver_id
        ), tot AS (SELECT race_id, sum(n) AS total FROM counts GROUP BY race_id)
        SELECT counts.race_id, sum(power(counts.n / tot.total, 2)) AS hhi, 1 AS e
        FROM counts JOIN tot USING (race_id) GROUP BY counts.race_id
    """
    laps_rows = [r for r in _mkrows(con, sql_laps, rte, dates) if r['race_id'] not in have_live]
    all_rows = live_rows + laps_rows
    # re-derive race_seq over the UNION of both sources (a metric's own eligible universe)
    seq = assign_race_seq([r['race_id'] for r in all_rows], dates)
    for r in all_rows:
        r['race_seq'] = seq[r['race_id']]
    return all_rows


# ---------------------------------------------------------------------------
# 2.10 FVS-simple (results-grade, 2017+)
# ---------------------------------------------------------------------------
def extract_fvs_simple(con, rte, dates):
    sql_sd = """
        SELECT race_id, stddev_samp((finishing_position - starting_position)::DOUBLE) AS v,
               count(*) AS e
        FROM silver.results
        WHERE series_id = 1 AND finishing_position IS NOT NULL AND starting_position IS NOT NULL
        GROUP BY race_id HAVING count(*) >= 2
    """
    sql_deep = """
        SELECT race_id,
               avg(CASE WHEN finishing_position <= 10 AND starting_position > 15
                        THEN 1.0 ELSE 0.0 END) AS v,
               count(*) AS e
        FROM silver.results
        WHERE series_id = 1 AND finishing_position IS NOT NULL AND starting_position IS NOT NULL
        GROUP BY race_id
    """
    return _mkrows(con, sql_sd, rte, dates), _mkrows(con, sql_deep, rte, dates)


# ---------------------------------------------------------------------------
# 2.4 ARS-a -- DNF rate, beta-binomial (results-grade, 2017+)
# ---------------------------------------------------------------------------
CRASH_STATUSES = {'accident', 'dvp'}
BETA_ALPHA, BETA_BETA = 2.0, 18.0   # fixed a priori, spec section 2.4


def extract_ars_a_rows(con, rte, dates):
    """One row per race with crash/mech DNF counts and total driver-race count -- the raw
    material for the beta-binomial aggregator below (not a plain mean, so this returns counts
    rather than a single v)."""
    sql = """
        SELECT race_id, lower(trim(coalesce(finishing_status, ''))) AS status
        FROM silver.results WHERE series_id = 1
    """
    recs = con.sql(sql).fetchall()
    by_race = defaultdict(lambda: [0, 0, 0])  # crash, mech, total
    for rid, status in recs:
        by_race[rid][2] += 1
        if status != 'running':
            if status in CRASH_STATUSES:
                by_race[rid][0] += 1
            else:
                by_race[rid][1] += 1
    race_ids = [rid for rid in by_race if rid in rte]
    seq = assign_race_seq(race_ids, dates)
    rows = []
    for rid in race_ids:
        if rid not in seq:
            continue
        crash, mech, total = by_race[rid]
        track_id, era_key = rte[rid]
        rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid, race_seq=seq[rid],
                          v=1.0, e=total, crash=crash, mech=mech, n=total))
    return rows


def _beta_binomial_agg(field):
    def agg(rows):
        s = sum(r[field] for r in rows)
        n = sum(r['n'] for r in rows)
        return (BETA_ALPHA + s) / (BETA_ALPHA + BETA_BETA + n)
    return agg


# ---------------------------------------------------------------------------
# 3.1 F16 -- caution-cause taxonomy + lucky-dog beneficiary (2017+, via C4)
# ---------------------------------------------------------------------------
def extract_ars_caution_taxonomy(con, rte, dates):
    sql_accident = """
        SELECT race_id,
               avg(CASE WHEN reason IN ('Accident', 'Spin') THEN 1.0 ELSE 0.0 END) AS v,
               count(*) AS e
        FROM silver.caution_segments WHERE series_id = 1
        GROUP BY race_id
    """
    sql_lucky_dog = """
        SELECT race_id,
               avg(CASE WHEN beneficiary_car_number IS NOT NULL THEN 1.0 ELSE 0.0 END) AS v,
               count(*) AS e
        FROM silver.caution_segments WHERE series_id = 1
        GROUP BY race_id
    """
    return _mkrows(con, sql_accident, rte, dates), _mkrows(con, sql_lucky_dog, rte, dates)


# ---------------------------------------------------------------------------
# 2.1 TDS -- Tire Degradation Score (>=2022 per derivation doc, live-data)
# ---------------------------------------------------------------------------
def _green_laps_by_driver(con):
    """(race_id, driver_id) -> sorted [(lap, lap_time), ...] for green-flag laps (flag_state=1,
    spec section 1.7), Cup only."""
    recs = con.sql("""
        SELECT la.race_id, la.driver_id, la.lap, la.lap_time
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.lap_time IS NOT NULL AND la.lap_time > 0
        ORDER BY la.race_id, la.driver_id, la.lap
    """).fetchall()
    by_driver = defaultdict(list)
    for rid, did, lap, lt in recs:
        by_driver[(rid, did)].append((lap, lt))
    return by_driver


def _pit_laps_by_driver(con):
    recs = con.sql("""
        SELECT race_id, driver_id, lap_count FROM silver.pit_stops
        WHERE series_id = 1 AND driver_id IS NOT NULL AND lap_count IS NOT NULL
    """).fetchall()
    out = defaultdict(set)
    for rid, did, lap in recs:
        out[(rid, did)].add(lap)
    return out


def _tds_runs(seq, pit_lap_set):
    """seq: sorted [(lap, lap_time), ...] green laps for one driver-race. Drop pit-stop laps
    (contaminated in/out laps), then split into maximal consecutive-lap (gap=1) runs -- this
    creates a boundary at every removed pit lap and at every caution gap automatically. Returns
    list of run lap_time arrays with length >= 8 (spec section 2.1)."""
    clean = [(lap, lt) for lap, lt in seq if lap not in pit_lap_set]
    if not clean:
        return []
    runs, cur = [], [clean[0]]
    for lap, lt in clean[1:]:
        if lap == cur[-1][0] + 1:
            cur.append((lap, lt))
        else:
            runs.append(cur)
            cur = [(lap, lt)]
    runs.append(cur)
    return [np.array([lt for _, lt in r], dtype=float) for r in runs if len(r) >= 8]


def extract_tds(con, rte, dates):
    """Returns (core_rows, dispersion_rows). core v = median run-slope pooled across the race's
    runs (section 1.3's named exception -- median, not mean); dispersion v = cross-driver IQR of
    per-driver median run-slope within the race."""
    by_driver = _green_laps_by_driver(con)
    pit_laps = _pit_laps_by_driver(con)

    race_slopes = defaultdict(list)          # race_id -> [run slope, ...]
    race_driver_median = defaultdict(list)   # race_id -> [per-driver median slope, ...]
    for (rid, did), seq in by_driver.items():
        runs = _tds_runs(seq, pit_laps.get((rid, did), set()))
        slopes = []
        for run_y in runs:
            x = np.arange(len(run_y), dtype=float)
            slope = theilslopes(run_y, x)[0]
            slopes.append(float(slope))
        if slopes:
            race_slopes[rid].extend(slopes)
            race_driver_median[rid].append(float(np.median(slopes)))

    core_recs = [(rid, float(np.median(vs)), len(vs)) for rid, vs in race_slopes.items()]
    disp_recs = [(rid, float(np.subtract(*np.percentile(vs, [75, 25]))), len(race_slopes[rid]))
                 for rid, vs in race_driver_median.items() if len(vs) >= 2]

    def to_rows(recs):
        race_ids = [r[0] for r in recs if r[0] in rte]
        seq_map = assign_race_seq(race_ids, dates)
        rows = []
        for rid, v, e in recs:
            if rid not in rte or rid not in seq_map:
                continue
            track_id, era_key = rte[rid]
            rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid,
                              race_seq=seq_map[rid], v=v, e=e))
        return rows

    return to_rows(core_recs), to_rows(disp_recs)


# ---------------------------------------------------------------------------
# 2.3 PDI -- Passing Difficulty Index (>=2022, live-data)
# ---------------------------------------------------------------------------
def _green_car_laps(con):
    """race_id -> green_laps * distinct_drivers (spec section 2.3's shared denominator)."""
    green_laps = dict(con.sql("""
        SELECT race_id, count(*) FROM silver.lap_flags
        WHERE series_id = 1 AND flag_state = 1 GROUP BY race_id
    """).fetchall())
    n_drivers = dict(con.sql("""
        SELECT race_id, count(DISTINCT driver_id) FROM silver.laps
        WHERE series_id = 1 GROUP BY race_id
    """).fetchall())
    return {rid: green_laps[rid] * n_drivers[rid] for rid in green_laps if rid in n_drivers}


def _durable_passes_by_driver(seq, window=5):
    """seq: sorted [(lap, running_pos), ...] GREEN laps only for one driver-race (may have gaps
    at cautions -- a gap breaks the 'consecutive green laps' window, per section 1.7). Returns
    count of durable passes (a position gain at L->L+1 held for every available green lap in
    L+1..min(L+5, end of this contiguous green stretch))."""
    # split into contiguous (gap=1) stretches first -- a pass and its persistence window must
    # stay within one uninterrupted green stretch (a caution/pit gap ends the window early).
    stretches, cur = [], [seq[0]]
    for lap, pos in seq[1:]:
        if lap == cur[-1][0] + 1:
            cur.append((lap, pos))
        else:
            stretches.append(cur)
            cur = [(lap, pos)]
    stretches.append(cur)

    durable = 0
    for stretch in stretches:
        positions = [p for _, p in stretch]
        n = len(positions)
        for i in range(n - 1):
            if positions[i + 1] < positions[i]:  # a pass at i -> i+1
                end = min(i + 1 + window, n - 1)
                if all(positions[k] < positions[i] for k in range(i + 1, end + 1)):
                    durable += 1
    return durable


def extract_pdi(con, rte, dates):
    """Returns (v2_durable_rows, v1_quality_pass_rows) -- v2 is primary (section 2.3)."""
    green_car_laps = _green_car_laps(con)
    pos_recs = con.sql("""
        SELECT la.race_id, la.driver_id, la.lap, la.running_pos
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.running_pos IS NOT NULL
        ORDER BY la.race_id, la.driver_id, la.lap
    """).fetchall()
    by_driver = defaultdict(list)
    for rid, did, lap, pos in pos_recs:
        by_driver[(rid, did)].append((lap, pos))

    race_durable = defaultdict(int)
    for (rid, did), seq in by_driver.items():
        race_durable[rid] += _durable_passes_by_driver(seq)

    v2_recs = [(rid, -1.0 * cnt / green_car_laps[rid], green_car_laps[rid])
               for rid, cnt in race_durable.items() if rid in green_car_laps]

    qp = con.sql("""
        SELECT race_id, sum(coalesce(quality_passes, passes_made))
        FROM silver.live_final WHERE series_id = 1
            AND coalesce(quality_passes, passes_made) IS NOT NULL
        GROUP BY race_id
    """).fetchall()
    v1_recs = [(rid, -1.0 * float(total) / green_car_laps[rid], green_car_laps[rid])
               for rid, total in qp if rid in green_car_laps]

    def to_rows(recs):
        race_ids = [r[0] for r in recs if r[0] in rte]
        seq_map = assign_race_seq(race_ids, dates)
        rows = []
        for rid, v, e in recs:
            if rid not in rte or rid not in seq_map:
                continue
            track_id, era_key = rte[rid]
            rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid,
                              race_seq=seq_map[rid], v=v, e=e))
        return rows

    return to_rows(v2_recs), to_rows(v1_recs)


# ---------------------------------------------------------------------------
# 2.5 RVS -- Restart Volatility Score (>=2022, live-data)
# Implementation note (deviation from the derivation doc's own suggested lap_notes text-mining
# screen, disclosed in report/TRACK_PROFILES.md): the pit-cycle exclusion is implemented via
# LAP-COUNT proximity (silver.pit_stops.lap_count within the restart window) rather than a
# race-elapsed-time window comparison -- simpler, avoids an unverified cross-feed time-unit
# assumption, and achieves the same contamination-screening purpose.
# ---------------------------------------------------------------------------
def _restarts_by_race(con):
    """race_id -> [restart_lap, ...] -- caution(2) -> green(1) transitions, section 1.7.
    Sourced from silver.lap_flags alone (NOT silver.flag_events) -- see the dated amendment in
    specs/track_profiles.md: a spot-check found flag_events.lap_number disagrees with
    lap_flags.flag_state for the same race/lap window on some races (not a stable off-by-one,
    a genuine cross-feed data disagreement), so restart detection uses the same single table
    (lap_flags) that the position-window computation already reads, eliminating the cross-feed
    alignment risk entirely."""
    recs = con.sql("""
        SELECT race_id, laps_completed, flag_state FROM silver.lap_flags
        WHERE series_id = 1 ORDER BY race_id, laps_completed
    """).fetchall()
    by_race = defaultdict(list)
    for rid, lap, fs in recs:
        by_race[rid].append((lap, fs))
    restarts = defaultdict(list)
    for rid, seq in by_race.items():
        for (lap0, fs0), (lap1, fs1) in zip(seq, seq[1:]):
            if fs0 == 2 and fs1 == 1 and lap1 == lap0 + 1:
                restarts[rid].append(lap1)
    return restarts


def _green_stretches(seq):
    """seq: sorted [(lap, pos), ...]. Split into maximal consecutive-lap (gap=1) stretches."""
    if not seq:
        return []
    stretches, cur = [], [seq[0]]
    for lap, pos in seq[1:]:
        if lap == cur[-1][0] + 1:
            cur.append((lap, pos))
        else:
            stretches.append(cur)
            cur = [(lap, pos)]
    stretches.append(cur)
    return stretches


def extract_rvs(con, rte, dates):
    restarts = _restarts_by_race(con)
    pos_recs = con.sql("""
        SELECT la.race_id, la.driver_id, la.lap, la.running_pos
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.running_pos IS NOT NULL
        ORDER BY la.race_id, la.driver_id, la.lap
    """).fetchall()
    by_driver = defaultdict(list)
    for rid, did, lap, pos in pos_recs:
        by_driver[(rid, did)].append((lap, pos))
    pit_laps = _pit_laps_by_driver(con)

    race_deltas = defaultdict(list)
    for (rid, did), seq in by_driver.items():
        rlist = restarts.get(rid)
        if not rlist:
            continue
        stretches = _green_stretches(seq)
        p_laps = pit_laps.get((rid, did), set())
        for L in rlist:
            if any(abs(L - pl) <= 3 for pl in p_laps):
                continue  # active-pit-cycle exclusion (lap-count proximity, see module note)
            for stretch in stretches:
                laps_in_stretch = [lp for lp, _ in stretch]
                if L in laps_in_stretch and (L + 3) in laps_in_stretch:
                    idx0 = laps_in_stretch.index(L)
                    idx3 = laps_in_stretch.index(L + 3)
                    delta = abs(stretch[idx3][1] - stretch[idx0][1])
                    race_deltas[rid].append(float(delta))
                    break

    recs = [(rid, float(np.mean(vs)), len(vs)) for rid, vs in race_deltas.items() if vs]
    race_ids = [r[0] for r in recs if r[0] in rte]
    seq_map = assign_race_seq(race_ids, dates)
    rows = []
    for rid, v, e in recs:
        if rid not in rte or rid not in seq_map:
            continue
        track_id, era_key = rte[rid]
        rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid,
                          race_seq=seq_map[rid], v=v, e=e))
    return rows


# ---------------------------------------------------------------------------
# 2.6 PIS -- Pit-Road Importance Score (>=2022, live-data)
# ---------------------------------------------------------------------------
def extract_pis(con, rte, dates):
    recs = con.sql("""
        WITH pit_delta AS (
            SELECT race_id, driver_id, sum(pit_in_rank - pit_out_rank)::DOUBLE AS pit_delta,
                   count(*) AS n_stops
            FROM silver.pit_stops
            WHERE series_id = 1 AND driver_id IS NOT NULL
                AND pit_in_rank IS NOT NULL AND pit_out_rank IS NOT NULL
            GROUP BY race_id, driver_id
        ), sf AS (
            SELECT race_id, driver_id,
                   (starting_position - finishing_position)::DOUBLE AS sf_delta
            FROM silver.results WHERE series_id = 1
                AND starting_position IS NOT NULL AND finishing_position IS NOT NULL
        )
        SELECT sf.race_id, sf.sf_delta, coalesce(pit_delta.pit_delta, 0.0) AS pit_delta,
               coalesce(pit_delta.n_stops, 0) AS n_stops
        FROM sf LEFT JOIN pit_delta USING (race_id, driver_id)
    """).fetchall()
    by_race = defaultdict(list)
    for rid, sf_delta, pit_delta, n_stops in recs:
        by_race[rid].append((sf_delta, pit_delta, n_stops))

    out = []
    for rid, vals in by_race.items():
        if len(vals) < 3:
            continue
        sf = np.array([v[0] for v in vals])
        pit = np.array([v[1] for v in vals])
        n_stops = sum(v[2] for v in vals)
        var_sf = np.var(sf, ddof=1)
        if var_sf <= 0 or n_stops == 0:
            continue
        share = float(np.var(pit, ddof=1) / var_sf)
        out.append((rid, share, int(n_stops)))
    return _mkrows_from_triples(out, rte, dates)


def _mkrows_from_triples(recs, rte, dates):
    race_ids = [r[0] for r in recs if r[0] in rte]
    seq_map = assign_race_seq(race_ids, dates)
    rows = []
    for rid, v, e in recs:
        if rid not in rte or rid not in seq_map:
            continue
        track_id, era_key = rte[rid]
        rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid,
                          race_seq=seq_map[rid], v=v, e=e))
    return rows


def extract_pit_stop_duration(con, rte, dates):
    """PIS secondary: median pit_stop_duration per race (own column, own aggregation)."""
    sql = """
        SELECT race_id, median(pit_stop_duration), count(*)
        FROM silver.pit_stops
        WHERE series_id = 1 AND pit_stop_duration IS NOT NULL AND pit_stop_duration > 0
        GROUP BY race_id
    """
    return _mkrows(con, sql, rte, dates)


def extract_penalty_rate(con, rte, dates):
    """PIS secondary: share of lap_notes rows matching a fixed penalty-keyword list (best-effort
    text match -- no structured penalty field exists post-2022, spec section 2.6)."""
    sql = """
        SELECT race_id,
               avg(CASE WHEN lower(note) LIKE '%penalty%' OR lower(note) LIKE '%pit road violation%'
                        OR lower(note) LIKE '%speeding%' THEN 1.0 ELSE 0.0 END) AS v,
               count(*) AS e
        FROM silver.lap_notes WHERE series_id = 1 AND note IS NOT NULL
        GROUP BY race_id
    """
    return _mkrows(con, sql, rte, dates)


# ---------------------------------------------------------------------------
# 2.8 SFS -- Strategy Flexibility Score (>=2022, live-data)
# ---------------------------------------------------------------------------
def extract_sfs(con, rte, dates):
    stops = con.sql("""
        SELECT race_id, driver_id, lap_count,
               (left_front_tire_changed::INT + left_rear_tire_changed::INT
                + right_front_tire_changed::INT + right_rear_tire_changed::INT) AS tire_take
        FROM silver.pit_stops
        WHERE series_id = 1 AND driver_id IS NOT NULL AND lap_count IS NOT NULL
        ORDER BY race_id, driver_id, lap_count
    """).fetchall()
    stage_bounds = con.sql("""
        SELECT race_id, stage_1_laps, stage_2_laps, stage_3_laps, stage_4_laps
        FROM silver.races WHERE series_id = 1
    """).fetchall()
    bounds_by_race = {}
    for rid, s1, s2, s3, s4 in stage_bounds:
        cum = []
        total = 0
        for s in (s1, s2, s3, s4):
            total += (s or 0)
            cum.append(total)
        bounds_by_race[rid] = cum

    def stage_bucket(rid, lap):
        cum = bounds_by_race.get(rid)
        if not cum or all(c == 0 for c in cum):
            return None
        for i, c in enumerate(cum):
            if c > 0 and lap <= c:
                return i + 1
        return len(cum)

    top10 = set(con.sql("""
        SELECT race_id, driver_id FROM silver.results
        WHERE series_id = 1 AND finishing_position IS NOT NULL AND finishing_position <= 10
    """).fetchall())

    by_driver = defaultdict(list)
    for rid, did, lap, take in stops:
        by_driver[(rid, did)].append((lap, take))

    race_paths = defaultdict(list)   # race_id -> [path tuple per top-10 driver]
    for (rid, did), stop_list in by_driver.items():
        if (rid, did) not in top10:
            continue
        buckets = [stage_bucket(rid, lap) for lap, _ in stop_list]
        if any(b is None for b in buckets):
            continue
        path = (len(stop_list), tuple(t for _, t in stop_list), tuple(buckets))
        race_paths[rid].append(path)

    out = []
    nonmodal = []
    for rid, paths in race_paths.items():
        if len(paths) < 3:
            continue
        counts = defaultdict(int)
        for p in paths:
            counts[p] += 1
        n = len(paths)
        ent = -sum((c / n) * np.log2(c / n) for c in counts.values())
        out.append((rid, float(ent), n))
        modal_path = max(counts, key=counts.get)
        top5_paths = paths[:5] if len(paths) <= 5 else paths
        share_nonmodal = sum(1 for p in top5_paths if p != modal_path) / len(top5_paths)
        nonmodal.append((rid, float(share_nonmodal), n))

    return _mkrows_from_triples(out, rte, dates), _mkrows_from_triples(nonmodal, rte, dates)


# ---------------------------------------------------------------------------
# 2.4 ARS-b (common-cause, live-data lap_notes, >=2022) / ARS-c (major-loss tail, >=2022)
# ---------------------------------------------------------------------------
def extract_ars_b_common_cause(con, rte, dates):
    sql = """
        SELECT race_id, avg(len(driver_ids))::DOUBLE AS v, count(*) AS e
        FROM silver.lap_notes
        WHERE series_id = 1 AND driver_ids IS NOT NULL AND len(driver_ids) >= 3
        GROUP BY race_id
    """
    return _mkrows(con, sql, rte, dates)


def extract_ars_c_major_loss_tail(con, rte, dates):
    best_pos = con.sql("""
        SELECT la.race_id, la.driver_id, min(la.running_pos) AS best_pos
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.running_pos IS NOT NULL
        GROUP BY la.race_id, la.driver_id
    """).fetchall()
    finish = dict(((rid, did), fin) for rid, did, fin in con.sql("""
        SELECT race_id, driver_id, finishing_position FROM silver.results
        WHERE series_id = 1 AND finishing_position IS NOT NULL
    """).fetchall())

    by_race = defaultdict(list)
    for rid, did, best in best_pos:
        fin = finish.get((rid, did))
        if fin is None:
            continue
        by_race[rid].append(1.0 if fin >= best + 15 else 0.0)

    recs = [(rid, float(np.mean(vs)), len(vs)) for rid, vs in by_race.items() if len(vs) >= 5]
    return _mkrows_from_triples(recs, rte, dates)


# ---------------------------------------------------------------------------
# 2.2 TPP -- Track Position Premium (>=2022, live-data, descriptive-association-only)
# ---------------------------------------------------------------------------
def _simple_pass_count(seq):
    """seq: sorted [(lap, pos), ...] green laps for one driver-race. Count of simple (non-
    durable) position gains within contiguous (gap=1) stretches -- section 1.7's plain 'pass',
    distinct from PDI-v2's 'durable pass'."""
    stretches = _green_stretches(seq)
    n = 0
    for stretch in stretches:
        positions = [p for _, p in stretch]
        for i in range(len(positions) - 1):
            if positions[i + 1] < positions[i]:
                n += 1
    return n


def extract_tpp(con, rte, dates):
    green_car_laps = _green_car_laps(con)
    pos_recs = con.sql("""
        SELECT la.race_id, la.driver_id, la.lap, la.running_pos
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        WHERE la.series_id = 1 AND la.running_pos IS NOT NULL
        ORDER BY la.race_id, la.driver_id, la.lap
    """).fetchall()
    by_driver = defaultdict(list)
    for rid, did, lap, pos in pos_recs:
        by_driver[(rid, did)].append((lap, pos))

    # (a) rank persistence: Spearman(start, finish) + mean per-driver lag-1 autocorrelation
    from scipy.stats import spearmanr
    sf = con.sql("""
        SELECT race_id, driver_id, starting_position, finishing_position
        FROM silver.results WHERE series_id = 1
            AND starting_position IS NOT NULL AND finishing_position IS NOT NULL
    """).fetchall()
    by_race_sf = defaultdict(list)
    for rid, did, s, f in sf:
        by_race_sf[rid].append((s, f))
    spearman_by_race = {}
    for rid, pairs in by_race_sf.items():
        if len(pairs) >= 5:
            starts = [p[0] for p in pairs]
            fins = [p[1] for p in pairs]
            rho = spearmanr(starts, fins)[0]
            if not np.isnan(rho):
                spearman_by_race[rid] = float(rho)

    autocorr_by_race = defaultdict(list)
    for (rid, did), seq in by_driver.items():
        positions = np.array([p for _, p in seq], dtype=float)
        if len(positions) >= 5 and np.std(positions[:-1]) > 0 and np.std(positions[1:]) > 0:
            r = np.corrcoef(positions[:-1], positions[1:])[0, 1]
            if not np.isnan(r):
                autocorr_by_race[rid].append(float(r))

    # (b) restart retention, front-half starters only
    restarts = _restarts_by_race(con)
    pit_laps = _pit_laps_by_driver(con)
    start_pos_by_race = defaultdict(dict)
    for rid, did, s, _f in sf:
        start_pos_by_race[rid][did] = s
    field_size = {rid: len(v) for rid, v in start_pos_by_race.items()}

    retention_by_race = defaultdict(list)
    for (rid, did), seq in by_driver.items():
        rlist = restarts.get(rid)
        fsz = field_size.get(rid)
        spos = start_pos_by_race.get(rid, {}).get(did)
        if not rlist or fsz is None or spos is None or spos > fsz / 2:
            continue
        stretches = _green_stretches(seq)
        p_laps = pit_laps.get((rid, did), set())
        for L in rlist:
            if any(abs(L - pl) <= 3 for pl in p_laps):
                continue
            for stretch in stretches:
                laps_in_stretch = [lp for lp, _ in stretch]
                if L in laps_in_stretch and (L + 3) in laps_in_stretch:
                    idx0, idx3 = laps_in_stretch.index(L), laps_in_stretch.index(L + 3)
                    delta = abs(stretch[idx3][1] - stretch[idx0][1])
                    retention_by_race[rid].append(1.0 if delta <= 1 else 0.0)
                    break

    # (c) pass scarcity: -1 * simple passes / green car-laps
    race_passes = defaultdict(int)
    for (rid, did), seq in by_driver.items():
        race_passes[rid] += _simple_pass_count(seq)
    scarcity_raw = {rid: -1.0 * cnt / green_car_laps[rid]
                    for rid, cnt in race_passes.items() if rid in green_car_laps}

    # z-score each component across its own scoring population, then combine 1/3 each
    def zmap(d):
        if len(d) < 3:
            return {}
        ks, vs = list(d.keys()), np.array(list(d.values()), dtype=float)
        mu, sd = vs.mean(), vs.std()
        if sd == 0:
            return {k: 0.0 for k in ks}
        return {k: float((v - mu) / sd) for k, v in zip(ks, vs)}

    z_spearman = zmap(spearman_by_race)
    z_autocorr = zmap({rid: float(np.mean(vs)) for rid, vs in autocorr_by_race.items()})
    z_retention = zmap({rid: float(np.mean(vs)) for rid, vs in retention_by_race.items()
                         if len(vs) >= 1})
    z_scarcity = zmap(scarcity_raw)

    all_race_ids = set(z_spearman) | set(z_autocorr) | set(z_retention) | set(z_scarcity)
    recs = []
    for rid in all_race_ids:
        parts = [z_spearman.get(rid), z_autocorr.get(rid), z_retention.get(rid), z_scarcity.get(rid)]
        # rank persistence itself is 0.5*spearman + 0.5*autocorr per section 2.2's own weights
        persistence = None
        if z_spearman.get(rid) is not None and z_autocorr.get(rid) is not None:
            persistence = 0.5 * z_spearman[rid] + 0.5 * z_autocorr[rid]
        comp = [x for x in (persistence, z_retention.get(rid), z_scarcity.get(rid)) if x is not None]
        if not comp:
            continue
        e = len(restarts.get(rid, []))
        recs.append((rid, float(np.mean(comp)), e))
    return _mkrows_from_triples(recs, rte, dates)


# ---------------------------------------------------------------------------
# 2.7 QIS -- Qualifying Importance Score (gold.wf_features scope, 2022+)
# ---------------------------------------------------------------------------
def _qis_rows(con, rte):
    """One row per (race_id, driver_id) from gold.wf_features, joined to track_id/era via
    race_track_features -- the frozen engine's own eligibility (has_pace, fin_h/pace_h non-null)."""
    recs = con.sql("""
        SELECT race_id, start_feat, fin_h, pace_h, finish
        FROM gold.wf_features
        WHERE has_pace AND fin_h IS NOT NULL AND pace_h IS NOT NULL
    """).fetchall()
    rows = []
    for rid, start_feat, fin_h, pace_h, finish in recs:
        if rid not in rte:
            continue
        track_id, era_key = rte[rid]
        rows.append(dict(track_id=track_id, era_key=era_key, race_id=rid,
                          start_feat=start_feat, fin_h=fin_h, pace_h=pace_h, finish=finish))
    return rows


def _fit_beta_start(obs, mu_start, sd_start, mu_finish, sd_finish):
    """OLS z_finish ~ z_start + fin_h + pace_h; returns beta_start (standardized on the GLOBAL
    scale, spec section 2.7) or None if underdetermined."""
    if len(obs) < 5:
        return None
    z_start = (np.array([o['start_feat'] for o in obs], dtype=float) - mu_start) / sd_start
    z_finish = (np.array([o['finish'] for o in obs], dtype=float) - mu_finish) / sd_finish
    fin_h = np.array([o['fin_h'] for o in obs], dtype=float)
    pace_h = np.array([o['pace_h'] for o in obs], dtype=float)
    X = np.column_stack([np.ones(len(obs)), z_start, fin_h, pace_h])
    try:
        coef, *_ = np.linalg.lstsq(X, z_finish, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return float(coef[1])


def compute_qis(con, rte, family_of, dates, min_races=5, min_events=60, k=SHRINK_K):
    """QIS is not per-race-decomposable (spec 2.7) -- bespoke aggregation, full-sample and
    as-of, reusing blend_values for the final shrink-and-floor step."""
    rows = _qis_rows(con, rte)
    all_start = np.array([r['start_feat'] for r in rows], dtype=float)
    all_finish = np.array([r['finish'] for r in rows], dtype=float)
    mu_s, sd_s = all_start.mean(), all_start.std()
    mu_f, sd_f = all_finish.mean(), all_finish.std()

    by_track_era = defaultdict(list)
    by_fam_era = defaultdict(list)
    race_ids_by_track_era = defaultdict(set)
    for r in rows:
        fam = family_of[r['track_id']]
        by_track_era[(r['track_id'], r['era_key'])].append(r)
        by_fam_era[(fam, r['era_key'])].append(r)
        race_ids_by_track_era[(r['track_id'], r['era_key'])].add(r['race_id'])

    def n_races_events(obs):
        return len({o['race_id'] for o in obs}), len(obs)

    full_sample = {}
    for key, obs in by_track_era.items():
        fam = family_of[key[0]]
        fam_obs = by_fam_era[(fam, key[1])]
        n_races, n_events = n_races_events(obs)
        track_raw = _fit_beta_start(obs, mu_s, sd_s, mu_f, sd_f)
        family_raw = _fit_beta_start(fam_obs, mu_s, sd_s, mu_f, sd_f)
        full_sample[key] = blend_values(track_raw, family_raw, n_races, n_events,
                                         min_races, min_events, k)

    # as-of: for each race in a track/era cell, refit using rows from races with smaller
    # race_seq (metric-scope-relative, over this QIS row universe only)
    seq_map = assign_race_seq([r['race_id'] for r in rows], dates)
    for r in rows:
        r['race_seq'] = seq_map[r['race_id']]

    asof = {}
    for key, obs in by_track_era.items():
        fam = family_of[key[0]]
        fam_obs_all = by_fam_era[(fam, key[1])]
        race_ids_sorted = sorted(race_ids_by_track_era[key], key=lambda rid: seq_map[rid])
        for rid in race_ids_sorted:
            target_seq = seq_map[rid]
            prior_obs = [o for o in obs if o['race_seq'] < target_seq]
            prior_fam_obs = [o for o in fam_obs_all if o['race_seq'] < target_seq]
            n_races, n_events = n_races_events(prior_obs)
            track_raw = _fit_beta_start(prior_obs, mu_s, sd_s, mu_f, sd_f)
            family_raw = _fit_beta_start(prior_fam_obs, mu_s, sd_s, mu_f, sd_f)
            res = blend_values(track_raw, family_raw, n_races, n_events, min_races, min_events, k)
            res['race_id'] = rid
            res['race_seq'] = target_seq
            asof[(key[0], key[1], rid)] = res

    return full_sample, asof


# ---------------------------------------------------------------------------
# 2.10 FVS-model -- frozen engine replayed on gold, as-of by construction (>=2022)
# ---------------------------------------------------------------------------
FVS_SPEC = {'fpts': ['fin', 'pace', 'typed', 'start']}   # HANDOFF's frozen feature set, verbatim


def replay_frozen_engine(con):
    """Mirrors gate_gold.py's gold_sourced_walk_forward() line-for-line (same imported
    pl_fit/wmean/znan, same eligibility/order) with one addition: race_id is tagged onto each
    output row so results can be joined to track_id/era (gate_gold.py itself is NOT edited --
    the D-gate stays untouched). Reuses gate_gold.silver_to_races_list / load_gold_features
    (read-only helpers) for the race-list/gold-feature reconstruction."""
    races = gate_gold.silver_to_races_list(con)
    gold_by_key = gate_gold.load_gold_features(con)
    years = (2022, 2023, 2024, 2025, 2026)
    sample = [r for r in races if r['year'] in years]

    pl_train = {'fpts': ([], [])}
    pl_w = {'fpts': None}
    since_fit = {'fpts': 0}
    rows = []
    HL, BURN, MIN_HIST, MIN_DRV, REFIT_EVERY = 8, 15, 5, 20, 1

    for idx, race in enumerate(sample):
        rid = race['rid']
        drivers = race['drivers']
        elig = [d for d in sorted(drivers)
                if (rid, d) in gold_by_key
                and gold_by_key[(rid, d)]['n_hist'] >= MIN_HIST
                and gold_by_key[(rid, d)]['has_pace']]
        if idx >= BURN and len(elig) >= MIN_DRV:
            g = [gold_by_key[(rid, d)] for d in elig]
            actual = np.array([x['finish'] for x in g], float)
            start = np.array([x['start_feat'] for x in g], float)
            fin_h = np.array([x['fin_h'] for x in g], float)
            pace_h = np.array([x['pace_h'] for x in g], float)
            typ_h = np.array([x['typ_h'] for x in g], float)
            feat_bank = dict(pace=znan(pace_h), fin=znan(fin_h), typed=znan(typ_h), start=znan(start))
            X = np.column_stack([feat_bank[k] for k in FVS_SPEC['fpts']])
            Xs, Os = pl_train['fpts']
            rho = np.nan
            if len(Xs) >= 20:
                if pl_w['fpts'] is None or since_fit['fpts'] >= REFIT_EVERY:
                    pl_w['fpts'] = pl_fit(Xs, Os, w0=pl_w['fpts'])
                    since_fit['fpts'] = 0
                since_fit['fpts'] += 1
                u = X @ pl_w['fpts']
                from scipy.stats import spearmanr
                rho = spearmanr(u, actual)[0]
            order = np.argsort(actual)
            Xs.append(-X)
            Os.append(order)
            rows.append(dict(race_id=rid, date=race['date'][:10], year=race['year'],
                              track=race['track'], n=len(elig), rho=float(rho) if not np.isnan(rho) else None))
    return rows


def extract_fvs_model(con, rte, dates):
    rows = replay_frozen_engine(con)
    recs = [(r['race_id'], r['rho'], 1) for r in rows if r['rho'] is not None]
    return _mkrows_from_triples(recs, rte, dates)


# ---------------------------------------------------------------------------
# 3.2 F16/K7 -- ARS-b make-clustering (draft-alliance adjacency index, SS/drafting only, >=2022)
# ---------------------------------------------------------------------------
SS_DRAFT_FAMILIES = {'Drafting superspeedway', 'Condensed drafting speedway'}


def extract_ars_b_make_clustering(con, rte, family_of, dates):
    ss_track_ids = {tid for tid, f in family_of.items() if f in SS_DRAFT_FAMILIES}
    if not ss_track_ids:
        return []
    ss_race_ids = {rid for rid, (tid, _era) in rte.items() if tid in ss_track_ids}
    if not ss_race_ids:
        return []
    id_list = ','.join(str(r) for r in ss_race_ids)
    pos_recs = con.sql(f"""
        SELECT la.race_id, la.lap, la.running_pos, res.car_make
        FROM silver.laps la
        JOIN silver.lap_flags lf ON lf.series_id = 1 AND lf.race_id = la.race_id
            AND lf.laps_completed = la.lap AND lf.flag_state = 1
        JOIN silver.results res ON res.series_id = 1 AND res.race_id = la.race_id
            AND res.driver_id = la.driver_id
        WHERE la.series_id = 1 AND la.race_id IN ({id_list})
            AND la.running_pos IS NOT NULL AND res.car_make IS NOT NULL
        ORDER BY la.race_id, la.lap, la.running_pos
    """).fetchall()
    by_lap = defaultdict(list)
    for rid, lap, pos, make in pos_recs:
        by_lap[(rid, lap)].append((pos, make))

    race_ratios = defaultdict(list)
    race_car_laps = defaultdict(int)
    for (rid, _lap), cars in by_lap.items():
        cars.sort(key=lambda x: x[0])
        n = len(cars)
        if n < 3:
            continue
        makes = [m for _, m in cars]
        same_adj = sum(1 for i in range(n - 1) if makes[i] == makes[i + 1])
        obs_rate = same_adj / (n - 1)
        counts = defaultdict(int)
        for m in makes:
            counts[m] += 1
        exp_numer = sum(c * (c - 1) for c in counts.values())
        exp_rate = exp_numer / (n * (n - 1))
        race_car_laps[rid] += n
        if exp_rate > 0:
            race_ratios[rid].append(obs_rate / exp_rate)

    recs = [(rid, float(np.mean(vs)), race_car_laps[rid])
            for rid, vs in race_ratios.items() if vs]
    return _mkrows_from_triples(recs, rte, dates)


# ---------------------------------------------------------------------------
# 3.3 F16/H5 -- contender-exclusion sensitivity check (championship-race cells, TDS only)
# ---------------------------------------------------------------------------
def championship_contenders(con):
    """season -> (championship_race_id, {4 contender driver_ids}). Championship race = the Cup
    race with that season's max playoff_round; contenders = the 4 lowest points_position in
    silver.results for that race (spec section 3.3 -- cross-checked against
    silver.live_final.driver_is_in_chase where that feed is complete; points_position is used
    because it has no coverage gap, unlike live_final for at least one season)."""
    races = con.sql("""
        SELECT year, race_id, playoff_round FROM silver.races
        WHERE series_id = 1 AND race_type_id = 1 AND playoff_round IS NOT NULL
    """).fetchall()
    by_year = defaultdict(list)
    for year, rid, rnd in races:
        by_year[year].append((rnd, rid))
    champ_race = {}
    for year, lst in by_year.items():
        max_rnd = max(r for r, _ in lst)
        cands = [rid for r, rid in lst if r == max_rnd]
        if len(cands) == 1:
            champ_race[year] = cands[0]

    out = {}
    for year, rid in champ_race.items():
        pts = con.sql(f"""
            SELECT driver_id, points_position FROM silver.results
            WHERE series_id = 1 AND race_id = {rid} AND points_position IS NOT NULL
            ORDER BY points_position ASC LIMIT 4
        """).fetchall()
        if len(pts) == 4:
            out[year] = (rid, {d for d, _ in pts})
    return out


def extract_tds_h5_sensitivity(con, rte, dates):
    """Returns dict (track_id, era_key) -> dict(full_field, excl_contenders, delta, n_champ_races)
    for every cell containing >=1 championship race. Recomputes TDS_core's per-race raw value
    (section 2.1) with the 4 contenders' own runs dropped from each championship race, then
    compares the track-level (pre-shrinkage) median across ALL qualifying runs, full field vs
    excl-contenders, cell by cell."""
    contenders = championship_contenders(con)
    champ_race_ids = {rid for rid, _ in contenders.values()}
    contender_by_race = {rid: ids for rid, ids in contenders.values()}

    by_driver = _green_laps_by_driver(con)
    pit_laps = _pit_laps_by_driver(con)

    cell_runs_full = defaultdict(list)
    cell_runs_excl = defaultdict(list)
    cell_champ_races = defaultdict(set)
    for (rid, did), seq in by_driver.items():
        if rid not in rte:
            continue
        track_id, era_key = rte[rid]
        key = (track_id, era_key)
        runs = _tds_runs(seq, pit_laps.get((rid, did), set()))
        slopes = [float(theilslopes(run_y, np.arange(len(run_y), dtype=float))[0]) for run_y in runs]
        cell_runs_full[key].extend(slopes)
        is_contender = rid in champ_race_ids and did in contender_by_race.get(rid, set())
        if not is_contender:
            cell_runs_excl[key].extend(slopes)
        if rid in champ_race_ids:
            cell_champ_races[key].add(rid)

    out = {}
    for key, champ_races in cell_champ_races.items():
        full_vals = cell_runs_full.get(key, [])
        excl_vals = cell_runs_excl.get(key, [])
        if len(full_vals) < 8 or len(excl_vals) < 8:
            continue
        full_med = float(np.median(full_vals))
        excl_med = float(np.median(excl_vals))
        out[key] = dict(tds_core_full_field=full_med, tds_core_excl_contenders=excl_med,
                         tds_contender_sensitivity_delta=full_med - excl_med,
                         n_championship_races=len(champ_races))
    return out


# ---------------------------------------------------------------------------
# Orchestration: assemble gold.track_profiles / gold.track_profiles_asof
# ---------------------------------------------------------------------------
# Metrics pinned '>=2022' by their own derivation-doc subsection (spec section 2's stated
# policy: honor the doc's depth annotation verbatim even where the raw feed technically
# extends further). Results-grade metrics (DCI-laps_led, FVS-simple, ARS-a, caution-taxonomy)
# are NOT restricted here -- they already use their own natural (2017+) universe.
LIVE_DATA_2022_METRICS = {
    'tds_core', 'tds_dispersion', 'tpp', 'pdi_v2', 'pdi_v1', 'rvs', 'pis', 'pit_stop_duration',
    'penalty_rate', 'sfs', 'sfs_nonmodal', 'ars_b_common_cause', 'ars_c_major_loss_tail',
    'dci_fastest_laps', 'ars_b_make_clustering',
}


def _normalize_rows(rows):
    """pa.Table.from_pylist infers its schema from the FIRST row's keys only and silently drops
    any column that appears solely in a later row -- verified pyarrow 19.0.0 behavior, not a
    edge case worth trusting implicitly. Every row here can legitimately have a different key
    set (a (track_id, era) cell with only results-grade data has no tds_core_* keys at all), so
    the full column union must be computed and every row filled to it before handing off."""
    all_cols = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                all_cols.append(k)
    return [{c: row.get(c) for c in all_cols} for row in rows]


def _add_metric(full_master, asof_master, prefix, full_sample, asof, extra_cols=None):
    for key, res in full_sample.items():
        row = full_master.setdefault(key, {})
        row[f'{prefix}_value'] = res['value']
        row[f'{prefix}_track_raw'] = res['track_raw']
        row[f'{prefix}_family_raw'] = res['family_raw']
        row[f'{prefix}_n_races'] = res['n_races']
        row[f'{prefix}_n_events'] = res['n_events']
        row[f'{prefix}_below_floor'] = res['below_floor']
    for key3, res in asof.items():
        row = asof_master.setdefault(key3, {})
        row[f'{prefix}_value'] = res['value']
        row[f'{prefix}_track_raw'] = res['track_raw']
        row[f'{prefix}_family_raw'] = res['family_raw']
        row[f'{prefix}_n_races'] = res['n_races']
        row[f'{prefix}_n_events'] = res['n_events']
        row[f'{prefix}_below_floor'] = res['below_floor']


def build_track_profiles():
    os.makedirs(GOLD_DIR, exist_ok=True)
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH)

    family_of = load_track_family(con)
    rte = load_race_track_era(con)
    dates = load_race_dates(con)
    years = load_race_years(con)

    full_master, asof_master = {}, {}
    log_lines = []

    def run_metric(prefix, rows, agg_fn=None, restrict_2022=False):
        if restrict_2022:
            rows = restrict_and_reseq(rows, years, 2022, dates)
        min_races, min_events = FLOORS[prefix]
        fs, asof = compute_profiles(rows, family_of, min_races, min_events, agg_fn=agg_fn)
        _add_metric(full_master, asof_master, prefix, fs, asof)
        log_lines.append(f'{prefix}: {len(rows)} qualifying races, {len(fs)} track/era cells')

    print('[track_profiles_build] extracting results-grade metrics (2017+)...')
    run_metric('dci_laps_led_hhi', extract_dci_laps_led(con, rte, dates))
    sd_rows, deep_rows = extract_fvs_simple(con, rte, dates)
    run_metric('fvs_simple_sd', sd_rows)
    run_metric('fvs_simple_top10_deep_start', deep_rows)
    ars_a_rows = extract_ars_a_rows(con, rte, dates)
    run_metric('ars_a_crash_dnf_rate', ars_a_rows, agg_fn=_beta_binomial_agg('crash'))
    run_metric('ars_a_mech_dnf_rate', ars_a_rows, agg_fn=_beta_binomial_agg('mech'))
    acc_rows, ld_rows = extract_ars_caution_taxonomy(con, rte, dates)
    run_metric('ars_caution_accident_share', acc_rows)
    run_metric('ars_lucky_dog_rate', ld_rows)

    print('[track_profiles_build] extracting live-data metrics (>=2022)...')
    core_rows, disp_rows = extract_tds(con, rte, dates)
    run_metric('tds_core', core_rows, agg_fn=lambda rs: float(np.median([r['v'] for r in rs])),
               restrict_2022=True)
    run_metric('tds_dispersion', disp_rows, restrict_2022=True)
    run_metric('tpp', extract_tpp(con, rte, dates), restrict_2022=True)
    v2_rows, v1_rows = extract_pdi(con, rte, dates)
    run_metric('pdi', v2_rows, restrict_2022=True)
    run_metric('pdi_v1', v1_rows, restrict_2022=True)
    run_metric('rvs', extract_rvs(con, rte, dates), restrict_2022=True)
    run_metric('pis', extract_pis(con, rte, dates), restrict_2022=True)
    run_metric('pit_stop_duration', extract_pit_stop_duration(con, rte, dates), restrict_2022=True)
    run_metric('penalty_rate', extract_penalty_rate(con, rte, dates), restrict_2022=True)
    sfs_rows, sfs_nm_rows = extract_sfs(con, rte, dates)
    run_metric('sfs', sfs_rows, restrict_2022=True)
    run_metric('sfs_nonmodal_top5_share', sfs_nm_rows, restrict_2022=True)
    run_metric('ars_b_common_cause_mean_cars', extract_ars_b_common_cause(con, rte, dates),
               restrict_2022=True)
    run_metric('ars_c_major_loss_tail_p', extract_ars_c_major_loss_tail(con, rte, dates),
               restrict_2022=True)
    run_metric('dci_fastest_laps_hhi', extract_dci_fastest_laps(con, rte, dates), restrict_2022=True)

    print('[track_profiles_build] extracting F16 additions...')
    run_metric('ars_b_make_clustering_index',
               extract_ars_b_make_clustering(con, rte, family_of, dates), restrict_2022=True)

    print('[track_profiles_build] extracting QIS (gold.wf_features, 2022+)...')
    qis_min_races, qis_min_events = FLOORS['qis']
    qis_fs, qis_asof = compute_qis(con, rte, family_of, dates,
                                    min_races=qis_min_races, min_events=qis_min_events)
    _add_metric(full_master, asof_master, 'qis', qis_fs, qis_asof)
    log_lines.append(f'qis: {len(qis_fs)} track/era cells')

    print('[track_profiles_build] extracting FVS-model (frozen engine replay, 2022+)...')
    run_metric('fvs_model', extract_fvs_model(con, rte, dates))

    print('[track_profiles_build] extracting H5 contender-exclusion sensitivity (TDS only)...')
    h5 = extract_tds_h5_sensitivity(con, rte, dates)
    for key, res in h5.items():
        row = full_master.setdefault(key, {})
        row.update(res)
    log_lines.append(f'h5_sensitivity: {len(h5)} championship-race cells')

    # ---- assemble gold.track_profiles (full-sample) -------------------------------------
    all_prefixes = sorted({col.rsplit('_', 1)[0] for row in full_master.values() for col in row
                            if col.endswith('_value')})
    full_rows = []
    for (track_id, era_key), row in full_master.items():
        out = dict(track_id=track_id, era_key=era_key, primary_family=family_of[track_id])
        out.update(row)
        out['tpp_descriptive_association_only'] = True
        out['rvs_lane_approximate'] = True
        full_rows.append(out)

    # ---- assemble gold.track_profiles_asof -----------------------------------------------
    # row-level race_seq: a track/era-LOCAL ordinal (by race_date, across every metric's own
    # eligible races at that cell) -- for human orientation only. Each metric's own as-of BLEND
    # already used its own metric-scope-relative race_seq internally (section 1.6) to decide
    # which prior races count; this display column does not affect that.
    cell_race_ids = defaultdict(set)
    for (track_id, era_key, race_id) in asof_master:
        cell_race_ids[(track_id, era_key)].add(race_id)
    display_seq = {}
    for key, rids in cell_race_ids.items():
        for i, rid in enumerate(sorted(rids, key=lambda r: (dates[r], r)), start=1):
            display_seq[(key[0], key[1], rid)] = i

    asof_rows = []
    for (track_id, era_key, race_id), row in asof_master.items():
        out = dict(track_id=track_id, era_key=era_key, race_id=race_id,
                    race_seq=display_seq[(track_id, era_key, race_id)],
                    primary_family=family_of[track_id])
        out.update(row)
        out['tpp_descriptive_association_only'] = True
        out['rvs_lane_approximate'] = True
        asof_rows.append(out)

    full_table = pa.Table.from_pylist(_normalize_rows(full_rows))
    asof_table = pa.Table.from_pylist(_normalize_rows(asof_rows))
    pq.write_table(full_table, TRACK_PROFILES_PATH)
    pq.write_table(asof_table, TRACK_PROFILES_ASOF_PATH)
    print(f'[track_profiles_build] gold.track_profiles: {full_table.num_rows} rows, '
          f'{full_table.num_columns} columns')
    print(f'[track_profiles_build] gold.track_profiles_asof: {asof_table.num_rows} rows, '
          f'{asof_table.num_columns} columns')

    con.execute(f"CREATE OR REPLACE VIEW gold.track_profiles AS "
                f"SELECT * FROM read_parquet('{TRACK_PROFILES_PATH}')")
    con.execute(f"CREATE OR REPLACE VIEW gold.track_profiles_asof AS "
                f"SELECT * FROM read_parquet('{TRACK_PROFILES_ASOF_PATH}')")
    con.close()
    warehouse.build_warehouse()

    for line in log_lines:
        print('[track_profiles_build]', line)
    return full_table, asof_table


if __name__ == '__main__':
    build_track_profiles()
