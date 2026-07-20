#!/usr/bin/env python3
"""F13 gate -- gold.driver_loop_race / gold.driver_loop_history (specs/loop_metric_histories.md
section 5). Checks (spec section 5):
  1. Both output tables exist and are internally consistent (no duplicate (driver_id, race_id)
     rows in either table; every driver_id known to silver.laps).
  2. Build-graph isolation: 'driver_loop_race'/'driver_loop_history' appear nowhere in
     gold_build.py/walkforward.py/predict_next.py (source-text scan).
  3. Imported-machinery source-scan: loop_metrics_build.py imports _green_stretches and
     _green_laps_by_driver from track_profiles_build rather than reimplementing them.
  4. Full re-derivation: recomputing gold.driver_loop_race and gold.driver_loop_history from
     scratch reproduces every stored row exactly (dataset is small enough for an exact full
     re-derivation, not just a sample -- a strictly stronger proof than F3/F4's 40-row spot-checks).
  5. Closers nullability check: every closers=NULL row's driver has no green-flag lap at or after
     that race's own l_start (proves section 2.6's rule is applied, not merely computed).
  6. Composite re-derivation: recomputing composite_h from the stored *_h columns via
     add_composite() reproduces the stored composite_h exactly.

Run from src/. Assumes loop_metrics_build.py has already run (python loop_metrics_build.py).
Exit code 0 on PASS, 1 on FAIL.
"""
import copy
import os
import sys

import duckdb
import pyarrow.parquet as pq

import loop_metrics_build as lmb
import warehouse

SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    return pq.read_table(path).to_pylist()


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # ---- 1. files exist + basic consistency ------------------------------------------------
    for path in (lmb.DRIVER_LOOP_RACE_PATH, lmb.DRIVER_LOOP_HISTORY_PATH):
        check(os.path.exists(path), f'[files] missing: {path} -- run loop_metrics_build.py')
    if failures:
        print('FAIL — missing build output:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    raw_rows = _read(lmb.DRIVER_LOOP_RACE_PATH)
    hist_rows = _read(lmb.DRIVER_LOOP_HISTORY_PATH)
    check(len(raw_rows) > 0, '[counts] gold.driver_loop_race: 0 rows')
    check(len(hist_rows) > 0, '[counts] gold.driver_loop_history: 0 rows')

    raw_keys = [(r['driver_id'], r['race_id']) for r in raw_rows]
    check(len(raw_keys) == len(set(raw_keys)),
          '[join] gold.driver_loop_race has duplicate (driver_id, race_id) rows')
    hist_keys = [(r['driver_id'], r['race_id']) for r in hist_rows]
    check(len(hist_keys) == len(set(hist_keys)),
          '[join] gold.driver_loop_history has duplicate (driver_id, race_id) rows')

    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    known_drivers = {r[0] for r in con.sql(
        'SELECT DISTINCT driver_id FROM silver.laps WHERE series_id = 1').fetchall()}
    for r in raw_rows:
        check(r['driver_id'] in known_drivers,
              f"[join] unknown driver_id in gold.driver_loop_race: {r['driver_id']!r}")
    con.close()

    # ---- 2. build-graph isolation ------------------------------------------------------------
    for fname in ('gold_build.py', 'walkforward.py', 'predict_next.py'):
        path = os.path.join(SRC_DIR, fname)
        with open(path) as f:
            text = f.read()
        for token in ('driver_loop_race', 'driver_loop_history'):
            check(token not in text,
                  f'[isolation] {fname} references {token} -- build-graph isolation violated')

    # ---- 3. imported-machinery source-scan ----------------------------------------------------
    with open(os.path.join(SRC_DIR, 'loop_metrics_build.py')) as f:
        build_text = f.read()
    check('from track_profiles_build import _green_stretches, _green_laps_by_driver' in build_text,
          '[import] loop_metrics_build.py does not import _green_stretches/_green_laps_by_driver '
          'from track_profiles_build -- green-flag-lap/pass must be imported verbatim (spec '
          'section 1), not re-implemented')

    # ---- 4. full re-derivation ------------------------------------------------------------------
    con2 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    fresh_raw = lmb.build_driver_loop_race_rows(con2)
    fresh_hist = lmb.build_driver_loop_history_rows(con2, fresh_raw)
    lmb.add_composite(fresh_hist)
    con2.close()

    check(len(fresh_raw) == len(raw_rows),
          f'[re-derive] fresh gold.driver_loop_race has {len(fresh_raw)} rows, '
          f'stored has {len(raw_rows)}')
    check(len(fresh_hist) == len(hist_rows),
          f'[re-derive] fresh gold.driver_loop_history has {len(fresh_hist)} rows, '
          f'stored has {len(hist_rows)}')

    def same(a, b, tol=1e-9):
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, float) or isinstance(b, float):
            return abs(a - b) < tol
        return a == b

    raw_cols = ('race_seq', 'n_green_race', 'green_flag_laps', 'arp', 'passes_made',
                'times_passed', 'pass_diff', 'quality_passes', 'quality_pass_rate',
                'fastest_laps', 'fastest_lap_share', 'laps_top15', 'laps_top15_rate', 'closers')
    raw_mismatches = 0
    stored_raw_by_key = {(r['driver_id'], r['race_id']): r for r in raw_rows}
    for fresh in fresh_raw:
        stored = stored_raw_by_key.get((fresh['driver_id'], fresh['race_id']))
        if stored is None:
            raw_mismatches += 1
            continue
        for col in raw_cols:
            if not same(stored.get(col), fresh.get(col)):
                raw_mismatches += 1
    check(raw_mismatches == 0,
          f'[re-derive] {raw_mismatches} gold.driver_loop_race field mismatch(es)')

    hist_mismatches = 0
    stored_hist_by_key = {(r['driver_id'], r['race_id']): r for r in hist_rows}
    for fresh in fresh_hist:
        stored = stored_hist_by_key.get((fresh['driver_id'], fresh['race_id']))
        if stored is None:
            hist_mismatches += 1
            continue
        for col in ('race_seq', 'n_hist', 'arp_h', 'pass_diff_h', 'quality_pass_rate_h',
                    'fastest_lap_share_h', 'laps_top15_rate_h', 'n_hist_closers', 'closers_h',
                    'composite_h'):
            if not same(stored.get(col), fresh.get(col)):
                hist_mismatches += 1
    check(hist_mismatches == 0,
          f'[re-derive] {hist_mismatches} gold.driver_loop_history field mismatch(es)')

    # ---- 5. closers nullability check ----------------------------------------------------------
    con3 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    pos_by_driver = lmb._position_rows_by_driver(con3)
    green_lap_values = lmb._race_green_lap_values(con3)
    con3.close()

    closer_rule_violations = 0
    for r in raw_rows:
        rid, did = r['race_id'], r['driver_id']
        g = green_lap_values.get(rid)
        seq = pos_by_driver.get((rid, did))
        if not g or not seq:
            continue
        l_start = lmb.closer_window_start(g)
        max_lap = seq[-1][0]
        has_window_lap = max_lap >= l_start
        if r['closers'] is None and has_window_lap:
            closer_rule_violations += 1
        if r['closers'] is not None and not has_window_lap:
            closer_rule_violations += 1
    check(closer_rule_violations == 0,
          f'[closers] {closer_rule_violations} row(s) violate the section-2.6 nullability rule')

    # ---- 6. composite re-derivation from stored _h columns alone ---------------------------------
    stripped = [
        {k: v for k, v in r.items() if k != 'composite_h'} for r in hist_rows
    ]
    stripped = copy.deepcopy(stripped)
    lmb.add_composite(stripped)
    composite_mismatches = 0
    stripped_by_key = {(r['driver_id'], r['race_id']): r for r in stripped}
    for r in hist_rows:
        recomputed = stripped_by_key[(r['driver_id'], r['race_id'])]
        if not same(r['composite_h'], recomputed['composite_h']):
            composite_mismatches += 1
    check(composite_mismatches == 0,
          f'[composite] {composite_mismatches} composite_h mismatch(es) recomputing from stored '
          f'_h columns alone')

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — gold.driver_loop_race {len(raw_rows)} rows, gold.driver_loop_history '
          f'{len(hist_rows)} rows; build-graph isolation verified (gold_build.py/walkforward.py/'
          f'predict_next.py reference driver_loop_race/driver_loop_history: 0 times); imported '
          f'green-flag-lap/pass machinery confirmed; full re-derivation exact (0 raw, 0 history '
          f'mismatches); {closer_rule_violations} closers-nullability violations; composite_h '
          f're-derives exactly from stored history columns alone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
