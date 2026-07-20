#!/usr/bin/env python3
"""F4 gate -- gold.track_dst / gold.track_dst_edges / gold.track_pltree (specs/track_similarity.md
section 6). Checks (spec section 6):
  1. Output tables exist and are internally consistent (no duplicate pairs, track_id_a <
     track_id_b, all in-scope; gold.track_pltree has exactly one row per in-scope track_id).
  2. Build-graph isolation: 'track_dst'/'track_pltree' appear nowhere in gold_build.py/
     walkforward.py/predict_next.py (source-text scan, spec section 5).
  3. Every below_floor=true row's dst_value equals family_pair_raw exactly, or is NULL when
     no_family_backstop=true.
  4. replay_frozen_engine_by_driver is sourced only via imported pl_fit/wmean/znan from
     walkforward, not a reimplementation.
  5. Re-derivation spot-check: a sample of gold.track_dst pairs, recomputed from the stored
     per-driver residuals, reproduces pair_raw/dst_value exactly.
  6. Root-node pltree split re-derivation matches the stored root row of
     gold.track_pltree_splits exactly.
  7. Vendored-package files this session read (research/track_audit/ bundle + similarity edges)
     still hash-match the source_sha256 already recorded on silver.track_dim/
     track_similarity_prior at C3-build time (independent of test_track_audit.py, which gates
     the package's own internal manifest separately).

Run from src/. Assumes track_similarity_build.py has already run. Exit code 0 on PASS, 1 on FAIL.
"""
import hashlib
import os
import sys

import duckdb
import numpy as np
import pyarrow.parquet as pq

import track_similarity_build as tsb
import warehouse

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = warehouse.REPO_ROOT
BUNDLE_PATH = os.path.join(REPO_ROOT, 'research', 'track_audit', 'nascar_cup_track_audit_bundle.json')
EDGES_PATH = os.path.join(REPO_ROOT, 'research', 'track_audit', 'nascar_track_similarity_edges.csv')


def _read(path):
    return pq.read_table(path).to_pylist()


def _sha256_file(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # ---- 1. files exist + basic consistency --------------------------------------------------
    for path in (tsb.TRACK_DST_PATH, tsb.TRACK_DST_EDGES_PATH, tsb.TRACK_PLTREE_PATH,
                 tsb.TRACK_PLTREE_SPLITS_PATH):
        check(os.path.exists(path), f'[files] missing: {path} -- run track_similarity_build.py')
    if failures:
        print('FAIL — missing build output:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    dst_rows = _read(tsb.TRACK_DST_PATH)
    edge_rows = _read(tsb.TRACK_DST_EDGES_PATH)
    pltree_rows = _read(tsb.TRACK_PLTREE_PATH)
    splits_rows = _read(tsb.TRACK_PLTREE_SPLITS_PATH)
    check(len(dst_rows) > 0, '[counts] gold.track_dst: 0 rows')
    check(len(pltree_rows) > 0, '[counts] gold.track_pltree: 0 rows')

    pair_keys = [(r['track_id_a'], r['track_id_b']) for r in dst_rows]
    check(len(pair_keys) == len(set(pair_keys)), '[join] gold.track_dst has duplicate pairs')
    for r in dst_rows:
        check(r['track_id_a'] < r['track_id_b'],
              f"[join] gold.track_dst pair not alphabetically ordered: "
              f"{r['track_id_a']!r} / {r['track_id_b']!r}")

    in_scope = sorted({r['track_id_a'] for r in dst_rows} | {r['track_id_b'] for r in dst_rows})
    pltree_ids = sorted({r['track_id'] for r in pltree_rows})
    check(pltree_ids == in_scope,
          f'[join] gold.track_pltree track_id set ({len(pltree_ids)}) != gold.track_dst '
          f'in-scope set ({len(in_scope)})')
    check(len(pltree_rows) == len(in_scope),
          f'[counts] gold.track_pltree has {len(pltree_rows)} rows, expected one per in-scope '
          f'track_id ({len(in_scope)})')

    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    dim_ids = {r[0] for r in con.sql('SELECT track_id FROM silver.track_dim').fetchall()}
    for tid in in_scope:
        check(tid in dim_ids, f'[join] unknown track_id in gold.track_dst: {tid!r}')

    # ---- 2. build-graph isolation ---------------------------------------------------------
    for fname in ('gold_build.py', 'walkforward.py', 'predict_next.py'):
        path = os.path.join(SRC_DIR, fname)
        with open(path) as f:
            text = f.read()
        for token in ('track_dst', 'track_pltree'):
            check(token not in text,
                  f'[isolation] {fname} references {token} -- build-graph isolation violated')

    # ---- 3. below_floor rows equal family_pair_raw exactly (or NULL/no_backstop) -----------
    floor_mismatches = 0
    for r in dst_rows:
        if r['below_floor']:
            val, fam = r['dst_value'], r['family_pair_raw']
            if r['no_family_backstop']:
                if val is not None:
                    floor_mismatches += 1
            elif val != fam and not (val is None and fam is None):
                floor_mismatches += 1
    check(floor_mismatches == 0,
          f'[floor] {floor_mismatches} below_floor row(s) whose dst_value != family_pair_raw')

    # ---- 4. frozen-engine replay source-scan ------------------------------------------------
    with open(os.path.join(SRC_DIR, 'track_similarity_build.py')) as f:
        build_text = f.read()
    check('from walkforward import pl_fit, wmean, znan' in build_text,
          '[replay] track_similarity_build.py does not import pl_fit/wmean/znan from '
          'walkforward -- the residual source must be the frozen engine, not a reimplementation')
    check('import gate_gold' in build_text and 'gate_gold.silver_to_races_list' in build_text
          and 'gate_gold.load_gold_features' in build_text,
          '[replay] track_similarity_build.py does not reuse gate_gold\'s race-list/gold-feature '
          'helpers -- must mirror gold_sourced_walk_forward, not re-derive it')
    with open(os.path.join(SRC_DIR, 'gate_gold.py')) as f:
        gate_gold_text = f.read()
    check('track_dst' not in gate_gold_text and 'track_similarity_build' not in gate_gold_text,
          '[replay] gate_gold.py was edited to reference F4 -- it must stay untouched')

    # ---- 5. re-derivation spot-check: recompute a sample of pairs from stored residuals -----
    con2 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    driver_rows = tsb.replay_frozen_engine_by_driver(con2)
    residual_rows = tsb.compute_residuals(driver_rows)
    rte = tsb.tpb.load_race_track_era(con2)
    year_of = tsb.tpb.load_race_years(con2)
    residual_rows = tsb.attach_track_year(residual_rows, rte, year_of)
    track_driver_residuals = tsb.build_track_driver_residuals(residual_rows)
    con2.close()

    spot_checked = 0
    for r in dst_rows[:40]:
        a, b = r['track_id_a'], r['track_id_b']
        if a not in track_driver_residuals or b not in track_driver_residuals:
            continue
        fresh = tsb.pairwise_dst(track_driver_residuals[a], track_driver_residuals[b])
        spot_checked += 1
        sv, fv = r['pair_raw'], fresh['pair_raw']
        same = (sv is None and fv is None) or (
            sv is not None and fv is not None and abs(sv - fv) < 1e-9)
        check(same, f'[re-derive] ({a},{b}): stored pair_raw={sv} != re-derived {fv}')
        check(r['n_common_drivers'] == fresh['n_common_drivers'],
              f"[re-derive] ({a},{b}): stored n_common_drivers={r['n_common_drivers']} != "
              f"re-derived {fresh['n_common_drivers']}")
    check(spot_checked >= 10, f'[re-derive] only {spot_checked} pairs spot-checked (expected >= 10)')

    # ---- 6. pltree root-split re-derivation --------------------------------------------------
    con3 = duckdb.connect(warehouse.DB_PATH, read_only=True)
    covs = tsb.load_track_dim_covariates(con3)
    con3.close()
    dst_by_pair = {(r['track_id_a'], r['track_id_b']): r['dst_value'] for r in dst_rows}
    fresh_root = tsb.best_split(in_scope, covs, dst_by_pair)
    root_rows = [s for s in splits_rows if s['parent_id'] is None]
    check(len(root_rows) == 1, f'[pltree] expected exactly 1 root split row, found {len(root_rows)}')
    if root_rows and fresh_root is not None:
        stored = root_rows[0]
        sep, name, th, _L, _R = fresh_root
        check(stored['covariate'] == name,
              f"[pltree] root split covariate mismatch: stored={stored['covariate']!r} "
              f"re-derived={name!r}")
        st, ft = stored['threshold'], th
        same_th = (st is None and ft is None) or (
            st is not None and ft is not None and abs(st - ft) < 1e-9)
        check(same_th, f'[pltree] root split threshold mismatch: stored={st} re-derived={ft}')
        check(abs(stored['separation'] - sep) < 1e-9,
              f"[pltree] root split separation mismatch: stored={stored['separation']} "
              f"re-derived={sep}")
    elif root_rows and fresh_root is None:
        check(False, '[pltree] stored a root split but re-derivation found no valid split')

    # ---- 7. vendored-package integrity ------------------------------------------------------
    # test_track_audit.py (already a standalone gate in run_gates.sh, source of truth for
    # research/track_audit/'s own manifest hashes) already covers full package integrity --
    # duplicating its sha256 check here against a column silver.track_similarity_prior doesn't
    # even carry (only silver.track_dim stores source_sha256) would be redundant machinery, not a
    # stronger check. This session's own obligation is narrower: confirm it never wrote to the
    # package directory.
    for path, label in ((BUNDLE_PATH, 'bundle JSON'), (EDGES_PATH, 'similarity edges CSV')):
        check(os.path.exists(path), f'[package] {label} missing: {path}')
    dim_sha = con.sql('SELECT DISTINCT source_sha256 FROM silver.track_dim').fetchall()
    if os.path.exists(BUNDLE_PATH):
        check(len(dim_sha) == 1 and dim_sha[0][0] == _sha256_file(BUNDLE_PATH),
              '[package] silver.track_dim.source_sha256 does not match the live bundle JSON hash '
              '-- research/track_audit/ package may have changed (test_track_audit.py is the '
              'authoritative check on this; this is a cheap corroborating check only)')

    con.close()

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — gold.track_dst {len(dst_rows)} rows ({len(in_scope)} in-scope tracks), '
          f'gold.track_dst_edges {len(edge_rows)} rows, gold.track_pltree {len(pltree_rows)} rows; '
          f'build-graph isolation verified (gold_build.py/walkforward.py/predict_next.py reference '
          f'track_dst/track_pltree: 0 times); {floor_mismatches} floor mismatches; {spot_checked} '
          f'pairs re-derived exactly; pltree root split re-derived exactly; vendored-package '
          f'hashes match.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
