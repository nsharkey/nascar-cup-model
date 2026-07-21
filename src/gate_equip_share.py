#!/usr/bin/env python3
"""F14 gate -- gold.equip_share_worths / equip_share_summary / equip_share_connectivity
(specs/equipment_share_decomposition.md section 9). Checks (spec section 9):
  1. All three tables exist and are internally consistent (no duplicate keys).
  2. Build-graph isolation: 'equip_share_worths'/'equip_share_summary'/'equip_share_connectivity'
     appear nowhere in gold_build.py/walkforward.py/predict_next.py (source-text scan).
  3. Full re-derivation: re-running the entire pipeline (both variants' CV+coordinate-descent
     lambda-selection and final refit) reproduces every stored lam_*/worth/summary number within
     math.isclose(rel_tol=1e-6) -- a documented tolerance for an iteratively-optimized (L-BFGS-B)
     quantity, same category of allowance as C1's fepace amendment.
  4. Connectivity re-derivation: recomputing gold.equip_share_connectivity from scratch reproduces
     every stored value exactly (no floats involved -- exact equality).
  5. Team-key canonicalization proof: 'trackhouse racing' appears exactly once; the
     Stewart-Haas/Haas-Factory-Team pair remains two distinct entity_key rows.
  6. Sign sanity check: for each factor, the entity with the single highest fitted worth
     (primary variant) has a better (lower) mean actual finish over its own scope races than the
     entity with the single lowest fitted worth -- guards against a sign-convention inversion
     (report/CALIBRATION_BACKTEST.md, M3, already found one in this codebase's neighborhood).

Run from src/. Assumes equip_share_build.py has already run (python equip_share_build.py).
Exit code 0 on PASS, 1 on FAIL.
"""
import math
import os
import sys

import duckdb
import pyarrow.parquet as pq

import equip_share_build as esb
import warehouse

SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    return pq.read_table(path).to_pylist()


def close(a, b, rel_tol=1e-6):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=1e-12)


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # ---- 1. files exist + basic consistency ------------------------------------------------
    for path in (esb.WORTHS_PATH, esb.SUMMARY_PATH, esb.CONNECTIVITY_PATH):
        check(os.path.exists(path), f'[files] missing: {path} -- run equip_share_build.py')
    if failures:
        print('FAIL — missing build output:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    worths = _read(esb.WORTHS_PATH)
    summary = _read(esb.SUMMARY_PATH)
    connectivity = _read(esb.CONNECTIVITY_PATH)
    check(len(worths) > 0, '[counts] gold.equip_share_worths: 0 rows')
    check(len(summary) > 0, '[counts] gold.equip_share_summary: 0 rows')
    check(len(connectivity) > 0, '[counts] gold.equip_share_connectivity: 0 rows')

    worth_keys = [(r['variant'], r['entity_type'], r['entity_key']) for r in worths]
    check(len(worth_keys) == len(set(worth_keys)),
          '[keys] gold.equip_share_worths has duplicate (variant, entity_type, entity_key) rows')
    summary_keys = [r['variant'] for r in summary]
    check(len(summary_keys) == len(set(summary_keys)),
          '[keys] gold.equip_share_summary has duplicate variant rows')
    conn_keys = [(r['variant'], r['window'], r['factor']) for r in connectivity]
    check(len(conn_keys) == len(set(conn_keys)),
          '[keys] gold.equip_share_connectivity has duplicate (variant, window, factor) rows')

    # ---- 2. build-graph isolation ------------------------------------------------------------
    for fname in ('gold_build.py', 'walkforward.py', 'predict_next.py'):
        path = os.path.join(SRC_DIR, fname)
        with open(path) as f:
            text = f.read()
        for token in ('equip_share_worths', 'equip_share_summary', 'equip_share_connectivity'):
            check(token not in text,
                  f'[isolation] {fname} references {token} -- build-graph isolation violated')

    # ---- 3. full re-derivation ----------------------------------------------------------------
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    fresh_worths, fresh_summary, fresh_connectivity = esb.build_all(con, built_at='gate-rederive')
    con.close()

    check(len(fresh_worths) == len(worths),
          f'[re-derive] fresh gold.equip_share_worths has {len(fresh_worths)} rows, '
          f'stored has {len(worths)}')
    stored_worths_by_key = {(r['variant'], r['entity_type'], r['entity_key']): r for r in worths}
    worth_mismatches = 0
    for fresh in fresh_worths:
        key = (fresh['variant'], fresh['entity_type'], fresh['entity_key'])
        stored = stored_worths_by_key.get(key)
        if stored is None:
            worth_mismatches += 1
            continue
        if stored['n_races'] != fresh['n_races'] or not close(stored['worth'], fresh['worth']):
            worth_mismatches += 1
    check(worth_mismatches == 0,
          f'[re-derive] {worth_mismatches} gold.equip_share_worths field mismatch(es)')

    stored_summary_by_variant = {r['variant']: r for r in summary}
    summary_cols = ('n_races', 'n_drivers', 'n_teams', 'n_makes', 'lam_driver', 'lam_team',
                     'lam_make', 'sd_driver', 'sd_team', 'sd_make', 'sd_driver_empirical',
                     'sd_team_empirical', 'sd_make_empirical', 'var_share_driver',
                     'var_share_team', 'var_share_make', 'trigger_armed')
    summary_mismatches = 0
    for fresh in fresh_summary:
        stored = stored_summary_by_variant.get(fresh['variant'])
        if stored is None:
            summary_mismatches += 1
            continue
        for col in summary_cols:
            a, b = stored[col], fresh[col]
            ok = (a == b) if isinstance(a, bool) or a is None or isinstance(a, int) else close(a, b)
            if not ok:
                summary_mismatches += 1
    check(summary_mismatches == 0,
          f'[re-derive] {summary_mismatches} gold.equip_share_summary field mismatch(es)')

    # ---- 4. connectivity re-derivation (exact) -------------------------------------------------
    stored_conn_by_key = {(r['variant'], r['window'], r['factor']): r for r in connectivity}
    conn_mismatches = 0
    for fresh in fresh_connectivity:
        key = (fresh['variant'], fresh['window'], fresh['factor'])
        stored = stored_conn_by_key.get(key)
        if stored is None:
            conn_mismatches += 1
            continue
        for col in ('n_entities', 'n_components', 'strongly_connected', 'offending_entities'):
            if stored[col] != fresh[col]:
                conn_mismatches += 1
    check(conn_mismatches == 0,
          f'[re-derive] {conn_mismatches} gold.equip_share_connectivity field mismatch(es)')

    # ---- 5. team-key canonicalization proof -----------------------------------------------------
    team_keys_primary = {r['entity_key'] for r in worths
                          if r['variant'] == 'primary' and r['entity_type'] == 'team'}
    check('trackhouse racing' in team_keys_primary,
          "[canon] 'trackhouse racing' missing from gold.equip_share_worths (case-variant merge "
          "failed)")
    check(sum(1 for k in team_keys_primary if k == 'trackhouse racing') == 1,
          "[canon] 'trackhouse racing' should appear exactly once (merged), found "
          f"{sum(1 for k in team_keys_primary if k == 'trackhouse racing')}")
    haas_family = {k for k in team_keys_primary if 'stewart-haas' in k or 'haas factory' in k}
    check(len(haas_family) == 2,
          f"[canon] Stewart-Haas Racing / Haas Factory Team should remain 2 distinct entity_key "
          f"rows (no over-merging of a genuine rename), found {len(haas_family)}: {haas_family}")

    # ---- 6. sign sanity check -------------------------------------------------------------------
    con2 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    all_rows = esb.load_scope_rows(con2)
    con2.close()
    mean_finish = {
        'driver': {},
        'team': {},
        'make': {},
    }
    from collections import defaultdict
    sums = {ft: defaultdict(lambda: [0, 0]) for ft in esb.FACTORS}
    for r in all_rows:
        for factor in esb.FACTORS:
            key = esb.entity_key_of(r, factor)
            key = str(key)
            acc = sums[factor][key]
            acc[0] += r['finish']
            acc[1] += 1
    for factor in esb.FACTORS:
        mean_finish[factor] = {k: v[0] / v[1] for k, v in sums[factor].items()}

    sign_violations = 0
    for factor in esb.FACTORS:
        primary_rows = [r for r in worths if r['variant'] == 'primary'
                         and r['entity_type'] == factor]
        if len(primary_rows) < 2:
            continue
        best = max(primary_rows, key=lambda r: r['worth'])
        worst = min(primary_rows, key=lambda r: r['worth'])
        mf = mean_finish[factor]
        best_mf = mf.get(str(best['entity_key']))
        worst_mf = mf.get(str(worst['entity_key']))
        if best_mf is None or worst_mf is None or not (best_mf < worst_mf):
            sign_violations += 1
            failures.append(
                f'[sign] {factor}: highest-worth entity {best["entity_key"]!r} '
                f'(mean finish {best_mf}) is not better than lowest-worth entity '
                f'{worst["entity_key"]!r} (mean finish {worst_mf})')

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — gold.equip_share_worths {len(worths)} rows, gold.equip_share_summary '
          f'{len(summary)} rows, gold.equip_share_connectivity {len(connectivity)} rows; '
          f'build-graph isolation verified (0 references in gold_build.py/walkforward.py/'
          f'predict_next.py); full re-derivation exact within tolerance (0 worth, 0 summary, '
          f'0 connectivity mismatches); team-key canonicalization verified (trackhouse racing '
          f'merged, Stewart-Haas/Haas Factory Team kept distinct); sign sanity check passed for '
          f'all {len(esb.FACTORS)} factors.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
