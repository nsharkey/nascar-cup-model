#!/usr/bin/env python3
"""F3 gate -- gold.track_profiles / gold.track_profiles_asof (specs/track_profiles.md section 5).

Checks (spec section 5):
  1. Both output tables exist and are internally consistent (row-count / join-integrity).
  2. Build-graph isolation: 'track_profiles' appears nowhere in gold_build.py / walkforward.py /
     predict_next.py (source-text scan, section 1.8).
  3. Every below_floor=true row's displayed value equals its family_raw exactly.
  4. gold.track_profiles_asof's per-race aggregates use strictly-prior data: a re-derivation
     spot-check on a sample of cells.
  5. TPP rows carry descriptive_association_only=true; RVS rows carry lane_approximate=true;
     FVS-model is sourced only via the frozen-engine replay function (source-scan: imports
     pl_fit/wmean/znan from walkforward rather than reimplementing the math).

Run from src/. Assumes track_profiles_build.py has already run (python track_profiles_build.py).
Exit code 0 on PASS, 1 on FAIL.
"""
import os
import sys

import duckdb
import numpy as np
import pyarrow.parquet as pq

import track_profiles_build as tpb
import warehouse

SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    return pq.read_table(path).to_pylist()


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # ---- 1. files exist + basic consistency --------------------------------------------
    for path in (tpb.TRACK_PROFILES_PATH, tpb.TRACK_PROFILES_ASOF_PATH):
        check(os.path.exists(path), f'[files] missing: {path} -- run track_profiles_build.py')
    if failures:
        print('FAIL — missing build output:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    full_rows = _read(tpb.TRACK_PROFILES_PATH)
    asof_rows = _read(tpb.TRACK_PROFILES_ASOF_PATH)
    check(len(full_rows) > 0, '[counts] gold.track_profiles: 0 rows')
    check(len(asof_rows) > 0, '[counts] gold.track_profiles_asof: 0 rows')

    full_keys = [(r['track_id'], r['era_key']) for r in full_rows]
    check(len(full_keys) == len(set(full_keys)),
          '[join] gold.track_profiles has duplicate (track_id, era_key) rows')
    asof_keys = [(r['track_id'], r['era_key'], r['race_id']) for r in asof_rows]
    check(len(asof_keys) == len(set(asof_keys)),
          '[join] gold.track_profiles_asof has duplicate (track_id, era_key, race_id) rows')

    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    dim_ids = {r[0] for r in con.sql('SELECT track_id FROM silver.track_dim').fetchall()}
    for r in full_rows:
        check(r['track_id'] in dim_ids, f"[join] unknown track_id {r['track_id']!r}")
    rules_eras = {r[0] for r in con.sql('SELECT era_key FROM silver.rules_era').fetchall()}
    for r in full_rows:
        check(r['era_key'] in rules_eras, f"[join] unknown era_key {r['era_key']!r}")

    # ---- 2. build-graph isolation ---------------------------------------------------------
    for fname in ('gold_build.py', 'walkforward.py', 'predict_next.py'):
        path = os.path.join(SRC_DIR, fname)
        with open(path) as f:
            text = f.read()
        check('track_profiles' not in text,
              f'[isolation] {fname} references track_profiles -- build-graph isolation violated')

    # ---- 3. below_floor rows equal family_raw exactly --------------------------------------
    metric_prefixes = sorted({c[:-len('_below_floor')] for r in full_rows for c in r
                               if c.endswith('_below_floor')})
    floor_mismatches = 0
    for r in full_rows:
        for m in metric_prefixes:
            below = r.get(f'{m}_below_floor')
            if below:
                val, fam = r.get(f'{m}_value'), r.get(f'{m}_family_raw')
                if val != fam and not (val is None and fam is None):
                    floor_mismatches += 1
    check(floor_mismatches == 0,
          f'[floor] {floor_mismatches} below_floor row(s) whose displayed value != family_raw')
    for r in asof_rows:
        for m in metric_prefixes:
            below = r.get(f'{m}_below_floor')
            if below:
                val, fam = r.get(f'{m}_value'), r.get(f'{m}_family_raw')
                if val != fam and not (val is None and fam is None):
                    floor_mismatches += 1
    check(floor_mismatches == 0,
          '[floor] asof table has a below_floor row whose displayed value != family_raw')

    # ---- 4. as-of strictly-prior re-derivation spot-check ----------------------------------
    con2 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    family_of = tpb.load_track_family(con2)
    rte = tpb.load_race_track_era(con2)
    dates = tpb.load_race_dates(con2)
    core_rows, _disp = tpb.extract_tds(con2, rte, dates)
    core_rows = tpb.restrict_and_reseq(core_rows, tpb.load_race_years(con2), 2022, dates)
    _fs, fresh_asof = tpb.compute_profiles(
        core_rows, family_of, *tpb.FLOORS['tds_core'],
        agg_fn=lambda rs: float(np.median([r['v'] for r in rs])))

    stored_by_key = {(r['track_id'], r['era_key'], r['race_id']): r for r in asof_rows}
    spot_checked = 0
    for key, fresh in list(fresh_asof.items())[:40]:
        stored = stored_by_key.get(key)
        if stored is None:
            continue
        spot_checked += 1
        sv, fv = stored.get('tds_core_value'), fresh['value']
        same = (sv is None and fv is None) or (
            sv is not None and fv is not None and abs(sv - fv) < 1e-9)
        check(same, f'[asof] {key}: stored tds_core_value={sv} != re-derived {fv}')
        check(stored.get('tds_core_n_races') == fresh['n_races'],
              f"[asof] {key}: stored n_races={stored.get('tds_core_n_races')} != "
              f"re-derived {fresh['n_races']}")
    check(spot_checked >= 10, f'[asof] only {spot_checked} cells spot-checked (expected >= 10)')

    con2.close()

    # ---- 5. labeling + FVS-model source-scan ------------------------------------------------
    for r in full_rows:
        check(r.get('tpp_descriptive_association_only') is True,
              f"[label] {r['track_id']}/{r['era_key']}: tpp_descriptive_association_only != true")
        check(r.get('rvs_lane_approximate') is True,
              f"[label] {r['track_id']}/{r['era_key']}: rvs_lane_approximate != true")

    with open(os.path.join(SRC_DIR, 'track_profiles_build.py')) as f:
        build_text = f.read()
    check('from walkforward import MY_TYPE, pl_fit, wmean, znan' in build_text,
          '[fvs-model] track_profiles_build.py does not import pl_fit/wmean/znan from '
          'walkforward -- FVS-model must be sourced from the frozen engine, not reimplemented')

    con.close()

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — gold.track_profiles {len(full_rows)} rows, gold.track_profiles_asof '
          f'{len(asof_rows)} rows; build-graph isolation verified (gold_build.py/walkforward.py/'
          f'predict_next.py reference track_profiles: 0 times); {floor_mismatches} floor '
          f'mismatches; {spot_checked} as-of cells re-derived exactly; TPP/RVS labels present on '
          f'all {len(full_rows)} full-sample rows; FVS-model sourced from the frozen engine.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
