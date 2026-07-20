# TRACK_PROFILES.md -- F3 build report (specs/track_profiles.md)

Ten empirical track/DFS-betting metrics (TDS/TPP/PDI/ARS/RVS/PIS/QIS/SFS/DCI/FVS) built by
`src/track_profiles_build.py` per `research/track_audit_derivation.md` section 3, plus the F16
additions (`domain_knowledge_scan.md` section 10.4). Two output tables: `gold.track_profiles`
(full-sample, analytics/DFS/betting reference only) and `gold.track_profiles_asof` (walk-forward,
the only variant that could ever be feature-eligible, and only via a future gated A/B). New
gate: `src/gate_track_profiles.py`, **PASS**. Full gate surface re-ran **15/15 green** after this
build (14 inherited + this session's new gate); the frozen C-gate and D-gate were untouched and
re-confirmed unchanged.

Package files (`research/track_audit/`) and `silver.track_priors`/`silver.track_similarity_prior`
were read-only inputs (used only for `primary_family`) -- nothing in this session edits the
vendored package. Nothing here feeds `walkforward.py`/`predict_next.py`; build-graph isolation is
gate-enforced (gate check 2).

## Row counts

| table | rows | grain |
|---|---:|---|
| `gold.track_profiles` | 130 | `(track_id, era_key)` |
| `gold.track_profiles_asof` | 329 | `(track_id, era_key, race_id)` |
| columns (each) | 153 | ~20 output columns x ~7 metric groups + identity/label columns |

130 cells span every `(track_id, era_key)` combination with at least one qualifying race in any
metric's own universe -- results-grade metrics (2017+) populate most of the 130; live-data
metrics (>=2022 per their own derivation-doc depth annotation) populate 77-79 of them; QIS/
FVS-model (frozen-engine/`gold.wf_features` scope) populate 52-78.

## Per-metric coverage and floor behavior

| metric | qualifying races | track/era cells | below_floor share |
|---|---:|---:|---:|
| TDS (core / dispersion) | 165 | 79 | 87.3% |
| TPP | 165 | 79 | 87.3% |
| PDI (v2 durable / v1 quality-pass) | 165 | 79 | 87.3% |
| RVS | 165 | 79 | 87.3% |
| PIS | 163 | 78 | 87.2% |
| pit_stop_duration | 164 | 78 | 87.2% |
| penalty_rate | 165 | 79 | 87.3% |
| QIS | 78 cells (driver-race grain) | 78 | 87.2% |
| SFS (entropy / non-modal top-5 share) | 162 | 77 | 87.0% |
| DCI laps_led (results-grade, 2017+) | 328 | 130 | 83.8% |
| DCI fastest-laps (>=2022) | 165 | 79 | 87.3% |
| FVS-simple (sd / deep-start-top10, 2017+) | 328 | 130 | 83.8% |
| FVS-model (frozen engine, >=2022) | 128 | 52 | 80.8% |
| ARS-a crash/mech DNF rate (2017+, beta-binomial) | 328 | 130 | 83.8% |
| ARS-b common-cause (lap_notes, >=2022) | 165 | 79 | 87.3% |
| ARS-c major-loss tail (>=2022) | 164 | 79 | 87.3% |
| ARS caution-accident-share (F16, 2017+) | 328 | 130 | 83.8% |
| ARS lucky-dog rate (F16, 2017+) | 328 | 130 | 83.8% |
| ARS-b make-clustering (F16/K7, SS/drafting only, >=2022) | 27 | 9 | 66.7% |

**The 80-87% below-floor share is the honest, correct output of the floor mechanism, not a
build defect.** It reproduces the derivation doc's own documented sample reality (section 3.0's
table: most `(track_id, era)` cells have 1-9 races in the 2022+ window; the `min_races=5` floor
was fixed a priori specifically because most cells don't clear it). Every below_floor row's
displayed value is exactly its family/era pooled value (gate check 3, verified: 0 mismatches).

## Sanity checks (not gated, cited here as build-quality evidence)

- **FVS-model correctly reproduces the audit's own known finding**: superspeedways are the
  least-predictable regime. Family-mean FVS-model (walk-forward Spearman of the frozen engine's
  own pre-race order vs actual finish, replayed on gold) by `primary_family`: Drafting
  superspeedway **0.042** (n=4 track/era cells) -- the lowest of any family by a wide margin --
  vs Intermediate oval 0.479, Short oval 0.638, Hybrid road course 0.644. This is exactly the
  audit's Brier/rho SS-unpredictability finding, reproduced independently via a completely
  different metric (per-track walk-forward rho instead of aggregate backtest rho).
- **ARS-b make-clustering (K7) shows a real same-make adjacency signal at drafting tracks**:
  adjacency index (observed / chance-expected same-make-adjacent rate) 0.95-1.36 across the 5
  qualifying Daytona/Talladega track/era cells, i.e. up to 36% more same-make adjacency than a
  random arrangement would produce -- consistent with the domain scan's draft-alliance claim,
  now a measured number rather than a broadcast trope. Analytics-only per spec section 3.2; no
  model path proposed or implied.
- **H5 contender-exclusion sensitivity (TDS only, championship-race cells)**: the 4 title
  contenders' exclusion moves the track-level TDS_core value by 0.0002-0.0009 sec/lap across the
  3 Phoenix era cells with >=1 championship race -- negligible relative to the metric's own
  cross-track range (roughly -0.02 to +0.03 sec/lap), confirming F19's own prediction that 0.3%
  exposure can't move a physical pace estimate materially. Championship-contender identification
  (4 lowest `points_position` in `silver.results` for the max-`playoff_round` race each season)
  was cross-checked against `silver.live_final.driver_is_in_chase` for the 5 seasons where that
  feed is complete (2020-2024): **exact agreement, 4/4 drivers, every season.** 2025's finale
  (race 5585, Phoenix) has a known `live_final` coverage gap (1 of ~36 vehicles stored for that
  race, unrelated to the already-documented race 5580 `weekend_race`-null gap), which is exactly
  why `points_position` rather than `live_final` was used as the operational definition (spec
  section 3.3) -- confirmed by name: 2025 contenders resolved as Larson/Hamlin/Briscoe/Byron,
  matching the real 2025 Championship 4.
- **PDI v1 (quality_passes, `live_final`-sourced) vs v2 (durable pass, `laps`-sourced)
  diverge substantially**: Pearson correlation between the two track-level values is **0.296**
  (79 cells with both computed) -- confirming the derivation doc's own coverage-risk flag on v1
  and the audit's warning that raw pass ratios are inflated at drafting tracks by lane-oscillation
  noise that the durable-pass definition (section 1.7, >=5-green-lap persistence) is designed to
  filter out. v2 is the metric's primary value (spec section 2.3); v1 is retained as a labeled
  secondary column for exactly this comparison, not blended into v2.

## Implementation notes and disclosed deviations from the pre-registered spec

Two dated `## AMENDMENT` blocks were added to `specs/track_profiles.md` mid-build, both made
*before* any value in the amended area was computed (permitted under `specs/README.md`'s
pre-data-amendment rule, not a protocol violation):

1. **RVS's active-pit-cycle exclusion** uses lap-count proximity
   (`abs(restart_lap - pit_lap) <= 3`) rather than a `pit_out_race_time`-vs-restart-window
   comparison, avoiding an unverified cross-feed time-unit assumption between `silver.pit_stops`
   and `silver.flag_events`.
2. **Restart detection is sourced from `silver.lap_flags` alone**, not `silver.flag_events`. A
   spot-check found the two feeds genuinely disagree about whether a caution occurred at all in
   some lap windows (race 5287: `flag_events` records a caution lap 20-29; `lap_flags` shows the
   entire window green) -- not a stable off-by-one correctable with a fixed offset, a real
   cross-feed data disagreement. Restart detection and the RVS/TPP position-window computations
   now read the same single table, eliminating the alignment risk entirely.

A third amendment documents that `gold.track_profiles_asof`'s displayed `race_seq` column is a
track/era-local ordinal for human orientation (spanning the union of every metric's own eligible
races at that cell), distinct from each metric's own internal scope-relative sequence used to
decide the as-of cutoff (spec section 1.6) -- a display clarification, not a computation change.

## Environment

- python: 3.13.5 (Anaconda), duckdb 1.5.4, numpy, scipy 1.15.3, pyarrow
- Wall clock: `track_profiles_build.py` full run (all metrics, both output tables) ~24s.

## Scope: what this session did not do

No model feature was added, no A/B was run, and nothing here feeds `walkforward.py`'s frozen
`[fin, pace, typed, start]` feature set -- reference/analytics tables only, per the rebuild's
RE-PROVE-don't-re-choose doctrine and this session's own analytics/reference tier. Driver-level
K7 cooperation scores (mentioned in the domain scan's write-up, not asked for by the F16 folded-in
instruction) are explicitly out of scope, per spec section 3.2. The simulator spike, DST/F4's
similarity-comparison work, and any config-novelty/era-reset model-A/B candidates
(`research/track_audit_derivation.md` section 7 catalog items 4, 6, 7) remain unscheduled
F-queue items, unaffected by this session.
