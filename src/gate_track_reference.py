#!/usr/bin/env python3
"""Re-derivation gate for the C3 track reference tables (research/track_audit_derivation.md
section 2; specs/medallion_architecture.md section 3 conventions) -- the sibling check called
for by the C3 kickoff prompt, analogous to gate_silver.py for silver_build.py.

Assumes src/test_track_audit.py (the package's own hash-manifest/schema gate) already passed --
this gate does NOT re-verify package immutability, only that track_reference_build.py's output
tables are structurally correct and mutually consistent. Run `python track_reference_build.py`
first.

Checks:
  1. Row counts: track_dim=43, track_xwalk=44 (see the row-count note below), track_priors=430
     (43x10), track_similarity_prior=193, rules_era=6.
  2. Banking parse: every track_dim row's (banking_max_deg, banking_secondary_deg) exactly
     reproduces a fresh parse_banking() call over the bundle's own verbatim banking text, plus a
     handful of hand-checked known values.
  3. dim<->xwalk join integrity: every xwalk track_id resolves in track_dim and vice versa.
  4. track_priors: exactly one row per (track_id, prior_name), scores 1-10, labels intact.
  5. track_similarity_prior: edge endpoints resolve in track_dim.
  6. rules_era: 6 rows, contiguous, covering 2015-9999 with no gaps or overlaps.
  7. race_track: no duplicate (series_id, race_id), every track_id resolves in track_dim.
  8. race_track_features: Cup-only by design; config_race_number/return_gap_years/hp750_2026
     internally consistent with race_track and track_dim.

Row-count note: research/track_audit_derivation.md section 2.2 and the C3 kickoff prompt both
say the crosswalk is "45 rows" -- the actual committed crosswalk_track_ids.csv has 44 data rows
(43 track_ids, one extra era-range row for sonoma_short's two disjoint windows: 43 + 1 = 44, not
45). Verified this session: no gate anywhere asserts 45, and the file is otherwise fully
self-consistent (test_track_audit.py's coverage/identity checks all pass against it). Treated as
a prose miscount in the two documents, not a data problem -- this gate asserts the real number
(44) and documents the correction rather than silently choosing between them.

Exit code 0 on PASS, 1 on FAIL.
"""
import os
import sys

import duckdb
import pyarrow.parquet as pq

import track_audit as ta
import track_reference_build as trb
import warehouse

SILVER_DIR = trb.SILVER_DIR
EXPECTED_XWALK_ROWS = 44  # see module docstring


def _read(path):
    return pq.read_table(path).to_pylist()


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    for path in (trb.TRACK_DIM_PATH, trb.TRACK_XWALK_PATH, trb.TRACK_PRIORS_PATH,
                 trb.TRACK_SIMILARITY_PRIOR_PATH, trb.RULES_ERA_PATH, trb.RACE_TRACK_PATH,
                 trb.RACE_TRACK_FEATURES_PATH):
        check(os.path.exists(path), f'[files] missing: {path} -- run track_reference_build.py')
    if failures:
        print('FAIL — missing build output:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    track_dim = _read(trb.TRACK_DIM_PATH)
    track_xwalk = _read(trb.TRACK_XWALK_PATH)
    track_priors = _read(trb.TRACK_PRIORS_PATH)
    track_sim = _read(trb.TRACK_SIMILARITY_PRIOR_PATH)
    rules_era = _read(trb.RULES_ERA_PATH)
    race_track = _read(trb.RACE_TRACK_PATH)
    race_track_features = _read(trb.RACE_TRACK_FEATURES_PATH)

    # ---- 1. row counts ------------------------------------------------------
    check(len(track_dim) == 43, f'[counts] track_dim: {len(track_dim)} != 43')
    check(len(track_xwalk) == EXPECTED_XWALK_ROWS,
          f'[counts] track_xwalk: {len(track_xwalk)} != {EXPECTED_XWALK_ROWS}')
    check(len(track_priors) == 430, f'[counts] track_priors: {len(track_priors)} != 430 (43x10)')
    check(len(track_sim) == 193, f'[counts] track_similarity_prior: {len(track_sim)} != 193')
    check(len(rules_era) == 6, f'[counts] rules_era: {len(rules_era)} != 6')
    check(len(race_track) > 0, '[counts] race_track: 0 rows')
    check(len(race_track_features) > 0, '[counts] race_track_features: 0 rows')

    dim_ids = {r['track_id'] for r in track_dim}
    check(len(dim_ids) == 43, '[track_dim] track_id not unique')

    # ---- 2. banking parse spot-checks ----------------------------------------
    bundle_by_id = {t['track_id']: t for t in ta.load_bundle()['tracks']}
    for r in track_dim:
        exp_max, exp_sec = trb.parse_banking(bundle_by_id[r['track_id']]['banking'])
        check(r['banking_max_deg'] == exp_max,
              f"[banking] {r['track_id']}: stored max {r['banking_max_deg']} != re-derived {exp_max}")
        check(r['banking_secondary_deg'] == exp_sec,
              f"[banking] {r['track_id']}: stored secondary {r['banking_secondary_deg']} != "
              f're-derived {exp_sec}')
    hand_checked = {
        'daytona_oval': (31.0, 18.0), 'talladega_oval': (33.0, 16.5),
        'bristol_dirt': (None, None), 'homestead': (20.0, None),
        'new_hampshire': (7.0, None), 'wwt_gateway': (11.0, None),
        'watkins_glen': (None, None),
    }
    by_id = {r['track_id']: r for r in track_dim}
    for tid, (exp_max, exp_sec) in hand_checked.items():
        r = by_id[tid]
        check(r['banking_max_deg'] == exp_max and r['banking_secondary_deg'] == exp_sec,
              f'[banking] {tid}: hand-checked ({exp_max}, {exp_sec}) != stored '
              f"({r['banking_max_deg']}, {r['banking_secondary_deg']})")

    # ---- 3. dim <-> xwalk join integrity -------------------------------------
    xwalk_ids = {r['track_id'] for r in track_xwalk}
    check(xwalk_ids == dim_ids,
          f'[dim-xwalk] id mismatch: xwalk-only={xwalk_ids - dim_ids}, dim-only={dim_ids - xwalk_ids}')
    for r in track_xwalk:
        check(r['track_id'] in dim_ids, f"[dim-xwalk] xwalk row {r['track_id']} not in track_dim")

    # ---- 4. track_priors ------------------------------------------------------
    seen = set()
    for r in track_priors:
        key = (r['track_id'], r['prior_name'])
        check(key not in seen, f'[priors] duplicate {key}')
        seen.add(key)
        check(r['track_id'] in dim_ids, f"[priors] unknown track_id {r['track_id']}")
        check(r['prior_name'] in ta.PRIOR_FIELDS, f"[priors] unknown prior_name {r['prior_name']}")
        check(1 <= r['score'] <= 10, f"[priors] {key}: score {r['score']} outside 1-10")
        check(r['evidence_class'] == 'Working Hypothesis',
              f'[priors] {key}: evidence_class not quarantined')
    check(seen == {(tid, pf) for tid in dim_ids for pf in ta.PRIOR_FIELDS},
          '[priors] (track_id, prior_name) coverage incomplete')

    # ---- 5. track_similarity_prior --------------------------------------------
    for e in track_sim:
        check(e['source_track_id'] in dim_ids, f"[similarity] unknown source {e['source_track_id']}")
        check(e['target_track_id'] in dim_ids, f"[similarity] unknown target {e['target_track_id']}")
        check(e['evidence_class'] == 'Working Hypothesis', '[similarity] not quarantined')

    # ---- 6. rules_era -----------------------------------------------------------
    eras = sorted(rules_era, key=lambda e: e['season_start'])
    check(eras[0]['season_start'] == 2015, '[rules_era] does not start at 2015')
    check(eras[-1]['season_end'] == 9999, '[rules_era] final era is not open-ended (9999)')
    for a, b in zip(eras, eras[1:]):
        check(b['season_start'] == a['season_end'] + 1,
              f"[rules_era] gap/overlap between {a['era_key']} (ends {a['season_end']}) and "
              f"{b['era_key']} (starts {b['season_start']})")
    check([e['era_key'] for e in eras] == [e['era_key'] for e in ta.RULES_ERA],
          '[rules_era] stored table drifted from track_audit.RULES_ERA')

    # ---- 7. race_track -----------------------------------------------------------
    rt_keys = [(r['series_id'], r['race_id']) for r in race_track]
    check(len(rt_keys) == len(set(rt_keys)), '[race_track] duplicate (series_id, race_id) rows')
    for r in race_track:
        check(r['series_id'] in (1, 2, 3), f"[race_track] bad series_id {r['series_id']}")
        check(r['track_id'] in dim_ids, f"[race_track] unknown track_id {r['track_id']}")

    # ---- 8. race_track_features ---------------------------------------------------
    rt_by_key = {(r['series_id'], r['race_id']): r['track_id'] for r in race_track}
    for r in race_track_features:
        check(r['series_id'] == 1, f"[race_track_features] non-Cup row series_id={r['series_id']}"
              " -- table is scoped to Cup only by design (module docstring)")
        key = (r['series_id'], r['race_id'])
        check(key in rt_by_key, f'[race_track_features] {key} not present in race_track')
        check(rt_by_key.get(key) == r['track_id'],
              f"[race_track_features] {key}: track_id {r['track_id']} != race_track's "
              f"{rt_by_key.get(key)}")
        check(r['config_race_number'] >= 1,
              f'[race_track_features] {key}: config_race_number {r["config_race_number"]} < 1')
        check((r['config_race_number'] == 1) == (r['return_gap_years'] is None),
              f"[race_track_features] {key}: config_race_number="
              f"{r['config_race_number']} but return_gap_years={r['return_gap_years']!r} "
              f'(should be None iff this is the config\'s first-ever race)')
        check(r['return_gap_years'] is None or r['return_gap_years'] >= 0,
              f"[race_track_features] {key}: negative return_gap_years {r['return_gap_years']}")
        check(r['era_race_number'] >= 1,
              f'[race_track_features] {key}: era_race_number {r["era_race_number"]} < 1')
        check(r['era_key'] in {e['era_key'] for e in rules_era},
              f"[race_track_features] {key}: unknown era_key {r['era_key']}")
        dim_row = by_id[r['track_id']]
        exp_hp750 = bool(dim_row['road_course']) or dim_row['length_mi'] < 1.5
        check(r['hp750_2026'] == exp_hp750,
              f"[race_track_features] {key}: hp750_2026 {r['hp750_2026']} != track_dim-derived "
              f'{exp_hp750}')

    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    age_rows = con.sql("""
        SELECT f.series_id, f.race_id, f.track_id, f.config_age_years,
               r.year - d.first_year_in_scope AS expected_age
        FROM silver.race_track_features f
        JOIN silver.races r ON r.series_id = f.series_id AND r.race_id = f.race_id
        JOIN silver.track_dim d ON d.track_id = f.track_id
        WHERE f.config_age_years != r.year - d.first_year_in_scope
    """).fetchall()
    con.close()
    check(not age_rows, f'[race_track_features] {len(age_rows)} row(s) with wrong '
          f'config_age_years (year - first_year_in_scope): {age_rows[:5]}')

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — track_dim 43, track_xwalk {EXPECTED_XWALK_ROWS}, track_priors 430, '
          f'track_similarity_prior 193, rules_era 6; race_track {len(race_track)} rows '
          f'({len(race_track_features)} Cup-scoped in race_track_features); banking parse and '
          f'dim<->xwalk join integrity verified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
