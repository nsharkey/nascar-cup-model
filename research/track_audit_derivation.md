# Track-audit derivation study — what the vendored package lets us build (F5)

**Session:** F5 research spike · Fable 5 · 2026-07-19
**Status:** research report — **proposes only**. No tables built, no frozen
spec changed, no package file touched. Hash gate
(`cd src && python3 test_track_audit.py`) verified green at session start
and end: `PASS — manifest hashes verified, 43 configurations consistent …
163/163 repo races crosswalked`.
**Doctrine (INTEGRATION.md, restated up front):** nothing from this package
— raw prior, calibrated metric, or similarity structure — enters the frozen
PL prediction model without its own pre-registered, walk-forward-gated A/B.
Everything below is inventory, derivation design, and plan proposals.

---

## 0. Executive summary

The package's value splits cleanly into three layers plus a simulation
surface:

- **Layer A (usable today, zero new data):** 43-configuration physical
  reference + crosswalk + schedule mapping. Joins to all 163 parsed repo
  races now. Proposal: a small **C3 session** materializing
  `silver.track_dim` / `silver.track_xwalk` / `silver.track_priors`
  (priors deliberately quarantined in their own table) plus a handful of
  leakage-free derived features (config age, config race number, era keys,
  2026-750hp flag).
- **Layer B (after C2/D1):** every one of the ten 1–10 analyst priors has a
  concrete, leakage-safe empirical replacement computable from the planned
  silver lap/pit/flag tables and gold walk-forward features. Six of ten
  need only results-grade data; four need the ≥2022 live-data feeds. This
  section is written to be lifted nearly verbatim into F3's pre-registered
  spec.
- **Layer C (after D1):** empirical Driver Skill Transferability (DST) —
  driver-residual correlation between configurations — replaces the
  structural similarity edges for analytics, with the edges retaining one
  permanent legitimate role: donor structure for zero-history
  configurations. This sharpens F4.
- **Sim surface:** a race simulator needs ~12 track knobs; every knob has a
  v0 placeholder derivable from priors (labeled non-empirical) and a
  calibrated v1 source in silver/gold. Three knobs (DCI, finish variance,
  lead changes) should be *validation targets*, not inputs.

The hard governance finding (§6): the ten priors were authored 2026-07-19
with full knowledge of 2015–2026 outcomes, so **any backtest over that
window that uses a prior-derived feature is contaminated by construction**
— walk-forward mechanics cannot cure a constant that already saw the
future. Priors are therefore fit only for: shrinkage centers, v0 sim
placeholders, and zero-data fallbacks — all labeled. The calibrated Layer-B
metrics, computed as-of, carry no such contamination.

---

## 1. Field inventory — all six package files, by evidence class and governance tier

### 1.1 Governance tiers (defined here, used throughout)

| Tier | Contents | Allowed uses | Forbidden uses |
|---|---|---|---|
| **T1 FACT** | Verified Facts + Calculated Results: physical specs, schedule/event counts, era bounds, source ledger | Joins, reference tables, analytics, sim structure, derived features — freely | Nothing tier-specific (model entry still needs its own A/B, as all features do) |
| **T2 INTERPRETIVE** | Strong Inference: family taxonomy, recommended buckets, narrative racing analysis, key_comparables, metric-spec recipes | Pooling/shrinkage hierarchy, analytics grouping, research design | Presenting as measurement; silent use as a model key (MY_TYPE stays the frozen production key) |
| **T3 PRIOR (quarantined)** | Working Hypotheses: the ten 1–10 priors, similarity edges, `structural_nearest_neighbors`, the 8 novel hypotheses | Shrinkage centers, v0 sim placeholders, zero-data fallbacks, hypothesis lists — always with `score_type` labels attached | Backtest features over 2015–2026 (hindsight-contaminated, §6); any unlabeled surface; any production-model use without a gated A/B |

### 1.2 The bundle JSON (programmatic source of truth) — section by section

| Bundle section | Content | Evidence class | Tier |
|---|---|---|---|
| `metadata` (10 keys) | version 1.0, cutoff 2026-07-19, 43 configs, 396+36 race counts, score warning | CR | T1 |
| `evidence_labels` (4) | the VF/CR/SI/WH vocabulary itself | — | governance metadata |
| `schedule_by_year` (12 years) | per-year, per-configuration points-race counts 2015–2026 | CR (from S012–S022, S001/S002) | T1 |
| `completed_2026_through_cutoff` (19 configs) / `future_2026_after_cutoff` (16) | the completed/future split at cutoff | CR / **schedule, not observation** | T1, with the never-mix-future rule |
| `tracks` (43 records × 40 fields) | full per-configuration records | mixed — see §1.3 | mixed |
| `similarity_method` | method + warning ("not historical outcome correlation") | SI | T2 (describes T3 data) |
| `metric_specifications` (10) | the empirical calibration recipes (TPP, PDI, ARS, RVS, TDS, PIS, QIS, SFS, DST, DCI) | SI (method guidance) | T2 — freely adoptable as *specs*; adopted in §3 |
| `novel_hypotheses` (8) | testable ideas (Atlanta aging, restart geometry, durable pass, concrete nonlinearity, championship incentive, street novelty decay, pit geometry, skill vector) | WH (confidence Medium→High) | T3 as claims; T2 as research prompts (§7 items) |
| `sources` (41) | S001–S041 ledger with reliability ratings | VF (provenance) | T1 |
| `limitations` (4) | no loop data; future races unevidenced; small samples need pooling; rules/tires/weather separate | SI | T2 — binding design constraints |

### 1.3 The 43 track records — all 40 fields tagged

| Fields | Evidence class | Tier | Notes |
|---|---|---|---|
| `track_id`, `facility`, `configuration`, `location` | VF | T1 | `track_id` is the universal join key |
| `length_mi`, `shape`, `surface`, `road_course`, `turns`, `banking` | VF (High; length conflicts resolved to official docs) | T1 | `banking` is free text ("31 deg turns; 18 deg tri-oval") — parse on derivation, keep verbatim too |
| `primary_family` (12 values), `secondary_family` | SI | T2 | the shrinkage hierarchy for Layer B; **not** a production pooling key |
| the ten `*_prior` fields (tire_degradation, track_position_premium, passing_difficulty, attrition_risk, restart_volatility, pit_road_importance, qualifying_importance, strategy_flexibility, dfs_dominator_concentration, finish_variance) | **WH, explicitly** | **T3** | the calibration targets of §3 |
| `key_comparables` | SI/WH | T3 | analyst list; superseded by DST where data exists (§4) |
| `key_change_notes` | VF | T1 | reconfiguration facts (e.g. Atlanta 24→28° banking, 55→40 ft width) |
| `racing_analysis`, `dfs_betting_implications` | SI | T2 | narrative; stays in the package, not in fact tables |
| `source_ids`, `confidence`, `status`, `event_count_evidence`, `score_type`, `evidence_class` | provenance | T1 | carry through to any derived table |
| `completed_points_races_2015_2025`, `completed_points_races_2026_through_cutoff`, `future_scheduled_points_races_2026`, `scheduled_points_races_2026_total`, `scope_event_count_including_2026_schedule`, `first_year_in_scope`, `last_year_in_scope_or_schedule` | CR | T1 | completed vs future kept separate; never mix |
| `structural_nearest_neighbors` | CR **computed from WH priors** | **T3** | inherits prior contamination — see §6 |

### 1.4 The other files

- **`nascar_cup_track_configurations.csv`** — flat view of `tracks`; same
  tags as §1.3. Use the JSON as programmatic truth (INTEGRATION.md).
- **`nascar_track_similarity_edges.csv`** — 193 edges, ≤5 within-supergroup
  neighbors per config: `source_track_id, neighbor_rank, target_track_id,
  structural_similarity_score, distance, method`. Method column repeats the
  warning on every row. **T3** end to end.
- **`nascar_track_sources.csv`** — S001–S041; T1 provenance.
- **`README_nascar_track_audit.md`** — manifest (bytes + SHA-256); T1;
  enforced by the gate.
- **Narrative report, content that exists only there** (not in the bundle):
  the **rules-era key table** (6 eras 2015→2026 with the 2026 750-hp VF —
  road courses + all ovals under 1.5 mi), the recommended modeling buckets,
  the minimum empirical data schema, the DFS framework (5 principles), the
  betting framework (5 principles), 8 data-engineering recommendations,
  8 prioritized next steps, Appendix A (deferred non-points events). The
  era table is the one **derivation-critical** narrative-only asset: era
  boundaries are VF (S036–S039), the modeling implications SI.
- **Repo-derived companions** (not package): `crosswalk_track_ids.csv`
  (45 rows; 36 of 43 ids in repo scope; gate-enforced) and
  `INTEGRATION.md`. The crosswalk is the bridge every Layer-A join uses.

---

## 2. LAYER A — join-derivable now (no new data), and the C3 proposal

### 2.1 What the crosswalk already unlocks

`src/track_audit.py::track_id_for(name, season, month)` resolves every one
of the 163 parsed repo races to a `track_id` (gate-verified). That means
every physical fact, family, count, and era bound in §1.3's T1/T2 rows is a
**join away** from `races_parsed.pkl` today and from `silver.races`/
`silver.driver_race` after C1 — no waiting on C2/D1.

### 2.2 Candidate reference tables (the C3 session)

Sit these in **silver** (they are conformed reference data; the vendored
package itself plays the bronze role — immutable, hashed, versioned).
Build in DuckDB/parquet per the medallion's conventions, from the package
files + crosswalk only.

**`silver.track_dim`** — grain: one row per `track_id` (43 rows).

| column group | columns | source |
|---|---|---|
| identity | `track_id` PK, `facility`, `configuration`, `location`, `status` | bundle `tracks` |
| physical (T1) | `length_mi`, `shape`, `surface` (asphalt/concrete/dirt), `road_course` BOOL, `turns`, `banking_text` (verbatim), `banking_max_deg` (parsed DOUBLE), `banking_secondary_deg` (nullable; tri-oval/frontstretch where stated) | bundle; banking parse is a derived, unit-tested transform |
| taxonomy (T2) | `primary_family`, `secondary_family` | bundle |
| era bounds + counts (T1) | `first_year_in_scope`, `last_year_in_scope_or_schedule`, `completed_points_races_2015_2025`, `completed_points_races_2026_through_cutoff`, `future_scheduled_points_races_2026`, `scheduled_points_races_2026_total` | bundle |
| rules flags (T1) | `hp750_2026` BOOL = `road_course OR length_mi < 1.5` (VF S039) | derived |
| provenance | `source_ids`, `confidence`, `evidence_class`, `package_version` ('1.0'), `source_sha256` (bundle hash from the manifest), `built_at` | manifest + build |

**Deliberately excluded:** the ten priors, `key_comparables`,
`structural_nearest_neighbors`, and the narrative fields. A fact table a
naive consumer can join without accidentally treating a Working Hypothesis
as a measurement — that is the design decision.

**`silver.track_xwalk`** — the crosswalk materialized verbatim (45 rows):
`track_id, feed_track_name, season_start, season_end, date_note, mapping,
in_repo_scope, my_type, package_primary_family, notes` + provenance. Plus a
convenience view **`silver.race_track`** = `silver.races` ⋈ xwalk →
`(series_id, race_id, track_id)`, implementing the season-range rule (the
Phoenix-2018 month rule is unreachable in 2022+ data but implemented
anyway, mirroring `track_id_for`).

**`silver.track_priors`** — the quarantine table, long form (43 × 10 rows):
`track_id, prior_name, score (1–10), score_type` (the bundle's verbatim
"Analyst structural prior … not an empirical measurement"), `evidence_class`
('Working Hypothesis'), `package_version`. Every downstream surface that
touches it inherits the label columns. Optionally
**`silver.track_similarity_prior`** — the 193 edges verbatim, same
treatment.

**`silver.rules_era`** — 6 rows from the narrative era table: `era_key,
season_start, season_end, description, source_ids`. Assignment rule:
`era_key = f(season)` globally, `hp750` applies per-track via
`track_dim.hp750_2026`. Repo-scope data (2022+) spans three eras:
`nextgen_launch` (2022), `nextgen_low_downforce_short_road` (2023–2025),
`nextgen_750hp_sub15_road` (2026).

### 2.3 Derived features available at C3 time (all T1, all leakage-free)

| feature | definition | source | note |
|---|---|---|---|
| `config_age_years` | race season − `first_year_in_scope` | track_dim | Atlanta-aging (H1) and repave-maturity covariate |
| `config_race_number` | count of completed points races on this `track_id` strictly before race t | `schedule_by_year` (2015–2021) + repo races (2022+) | exact for any race ≥2015 because the package publishes per-year per-config counts; walk-forward by construction |
| `return_gap_years` | seasons since the config's previous points race | same | Chicagoland returns in 2026 after 6 blank years |
| `era_key`, `era_race_number` | rules era + Nth race of this config within the era | rules_era | the audit recommends partial coefficient resets at era breaks |
| `hp750_2026` | 2026 horsepower-package membership | track_dim | the one era overlay that is per-track, not just per-season |
| physical numerics | `length_mi`, `banking_max_deg`, `turns`, `road_course`, `surface` one-hots | track_dim | continuous alternatives to bucket keys, for analytics and future A/B candidates |

None of these are model features until they win their own A/B; all are
immediately legitimate in analytics, DFS/betting reference views, and sim
configuration.

---

## 3. LAYER B — the ten priors → empirical, walk-forward metrics (F3's scope)

### 3.0 Shared machinery (applies to every metric below)

- **Grain:** `(track_id, era_key)` — the audit's own instruction
  (configuration × rules era; limitations #4).
- **Two variants per metric, different governance:**
  - `gold.track_profiles` — full-sample estimates. Analytics/DFS/betting
    reference **only**; never joinable into model feature banks (enforce by
    build-graph check in the same spirit as the D-gate).
  - `gold.track_profiles_asof` — grain `(track_id, era_key, race_seq)`,
    computed from races strictly before each race. The only variant
    feature-eligible, and only via a gated A/B.
- **Shrinkage:** hierarchical toward `primary_family` (12 families), with
  the T3 prior usable as the family-level *center* only where explicitly
  labeled (§6.3). Shrinkage hyperparameters fixed a priori in the F3 spec,
  not tuned on outcomes (§6.4).
- **Sample reality (compute honestly, report intervals):** package schedule
  2022→cutoff = **164** races (the repo holds 163 until B3 backfills the
  fall-2025 Talladega gap). Per-config counts: Atlanta-post-2022 10;
  Daytona/Vegas/Phoenix/Martinsville/Talladega/Darlington/Kansas 9;
  Richmond/Bristol-concrete 7; a large middle at 4–5; Iowa/Roval-v2/
  COTA-short/Indy-oval 2; Road America/Mexico City/San Diego/Chicagoland 1;
  North Wilkesboro 0 at cutoff. F3's spec must pre-register per-metric
  minimum sample floors (races and events-within-race) below which the
  table reports the family posterior, not a track number.
- **History depth is per-feed:** results-grade sources (weekend-feed →
  `silver.results`/`silver.driver_race`) may extend below 2022 once B2/B3
  discover the actual feed floors; the live feeds (`live-pit-data`,
  `live-flag-data`, `lap-notes`) are verified archived ≥2022 only. Each
  metric below states which side of that line it lives on.

### 3.1 `tire_degradation_prior` → TDS (Tire Degradation Score)

- **Audit spec:** median green-run lap-time slope after fuel correction,
  plus dispersion in driver falloff and old/new crossover frequency.
- **Derivation:** green runs = maximal consecutive green-flag laps per
  driver between pit stops (`silver.laps` lap_time/lap ⋈
  `silver.lap_flags` flag_state; run boundaries from `silver.pit_stops`
  lap_count). Per run ≥8 green laps: Theil–Sen slope of lap_time on
  laps-since-pit. **TDS_core** = median slope (s/lap) across runs;
  **TDS_dispersion** = cross-driver IQR of per-driver median slopes.
  v1 reports the *net* falloff slope (degradation minus fuel-burn gain) —
  that is the sim-relevant quantity; a fuel decomposition and the
  crossover-frequency component are v2 refinements F3 may explicitly
  defer. Sources: `silver.laps`, `silver.lap_flags`, `silver.pit_stops`
  (C2). **≥2022.**

### 3.2 `track_position_premium_prior` → TPP (descriptive composite)

- **Audit spec:** weighted z-score of start→running-position persistence,
  clean-air lap delta, restart retention, green-flag pass scarcity.
- **Derivation (three descriptive components):** (a) rank persistence —
  mean per-race Spearman(start, finish) and mean lap-to-lap green-flag
  running_pos autocorrelation (`silver.laps`); (b) restart retention —
  P(position change ≤1 within 3 green laps | restart) for front-half cars
  (`silver.flag_events` + `silver.laps`); (c) pass scarcity — inverse
  green-flag passes per car-lap (§3.3 numerator). Combine as pre-registered
  fixed-weight z-composite.
- **Deliberate deviation from the audit spec:** the **clean-air lap delta
  component is excluded.** Causal clean-air pace is
  `specs/clean_air_causal_pace.md` territory (G-phase, EDGE-gated, frozen
  identification machinery). F3's TPP is descriptive association only, must
  say so on the surface, and must not ship a "clean-air delta" that a
  reader could mistake for the G-spec's estimand. If G2 ever runs and
  passes its gates, its estimate can join TPP as a v2 component. **≥2022.**

### 3.3 `passing_difficulty_prior` → PDI (Passing Difficulty Index)

- **Audit spec:** inverse of quality-adjusted green-flag passes per
  competitive car-lap, controlling for speed differential, tire age,
  restart proximity.
- **Derivation v1:** Σ `quality_passes` (or `passes_made`) from
  `silver.live_final` ÷ green car-laps (green laps from
  `silver.lap_flags` × cars running, or `silver.races`
  actual_laps − caution_laps). Inverted and z-scored. **Coverage risk:**
  `live_final` exists only where the live-feed final frame survived — C2's
  coverage report decides whether v1 is viable per era.
- **Derivation v2 (durable pass, hypothesis H3):** reconstruct passes from
  `silver.laps` running_pos transitions on green laps; count only position
  gains that persist ≥5 green laps. Sidesteps live_final coverage AND the
  audit's drafting-lane-oscillation warning — at Daytona/Talladega/Atlanta
  the raw ratio is inflated by design; the durable-pass rate is the
  defensible number there. F3 should compute both where possible and
  report divergence. **≥2022.**

### 3.4 `attrition_risk_prior` → ARS (Attrition Risk Score)

- **Audit spec:** hierarchical P(crash/mechanical DNF) + incident-induced
  major position loss; separate common-cause wrecks from individual
  failures.
- **Derivation:** (a) DNF rates — `silver.results` finishing_status
  classified crash vs mechanical (pre-registered string map; `Accident`,
  `DVP`, engine/transmission/etc.), beta-binomial per (track_id, era)
  shrunk to family. **Extends to the results-feed floor — possibly
  pre-2022.** (b) Common-cause structure — `silver.lap_notes` incidents
  with ≥3 `driver_ids` = multi-car events; report the cars-per-incident
  distribution (the audit's betting framework: correlated outcomes at
  drafting/street tracks). **≥2022.** (c) Major-position-loss tail —
  P(finish ≥ 15 places worse than best running_pos) from `silver.laps`.
  **≥2022.**

### 3.5 `restart_volatility_prior` → RVS (Restart Volatility Score)

- **Audit spec:** E|Δrunning_pos| within 2–5 green laps of restarts,
  conditioned on lane and row.
- **Derivation:** restarts = caution→green transitions in
  `silver.flag_events` (lap_number); per restart per driver,
  |running_pos(restart+3) − running_pos(restart)| on green laps, truncated
  at the next caution. Row = ceil(position/2); lane = position parity —
  **parity is a proxy** (actual lane choice isn't in the feeds); the F3
  spec must label the conditioning as approximate. Track-level RVS = field
  mean, shrunk. Exclude restarts inside active pit cycles (wave-around
  contamination screen — reuse the G1 spec's incident-screen idea via
  `silver.lap_notes`, descriptively). **≥2022.**

### 3.6 `pit_road_importance_prior` → PIS (Pit-Road Importance Score)

- **Audit spec:** share of net position change explained by pit-cycle
  gain/loss, penalties, undercut/overcut effectiveness.
- **Derivation:** per driver-race, decompose start−finish into pit-cycle
  Δ (Σ `pit_in_rank` − `pit_out_rank` per stop, or the feed's own
  `positions_gained_lost`), restart-window Δ (§3.5 windows), and green-run
  Δ (remainder), all from `silver.pit_stops` + `silver.laps`. PIS =
  cross-driver variance share of the pit component, averaged over races.
  Secondary outputs: pit_stop_duration median/IQR (crew execution spread),
  penalty rate from `silver.lap_notes` penalty notes. **≥2022.**

### 3.7 `qualifying_importance_prior` → QIS (Qualifying Importance Score)

- **Audit spec:** partial effect of start on finish controlling for
  pre-race speed and driver/team strength.
- **Derivation:** per (track-group, era): regression of finish on start
  with `gold.wf_features` controls (`fin_h`, `pace_h` — as-of by
  construction, which is exactly what "controlling for driver strength
  without leakage" requires), hierarchical partial pooling across
  configs. QIS = standardized start coefficient. This is the metric most
  aligned with what D1 already builds. **Depth = parsed-race depth**
  (2022+ now; extends with any future silver backfill).

### 3.8 `strategy_flexibility_prior` → SFS (Strategy Flexibility Score)

- **Audit spec:** entropy/effectiveness of successful pit sequences and
  fuel/tire paths.
- **Derivation:** strategy path per driver-race from `silver.pit_stops`:
  (stop count, per-stop tire take (0/2/4 from the four tire-changed
  flags), stop-lap position relative to stage boundaries from
  `silver.races` stage_*_laps). SFS = Shannon entropy of paths among
  top-10 finishers, averaged over races; secondary: share of top-5s on a
  non-modal path. **≥2022.**

### 3.9 `dfs_dominator_concentration_prior` → DCI (Dominator Concentration Index)

- **Audit spec:** Herfindahl of laps led and fastest laps, normalized for
  lap count and overtime.
- **Derivation:** HHI over driver shares of `laps_led`
  (`silver.results`/`silver.driver_race`) + HHI over fastest-lap counts
  (per-lap min lap_time from `silver.laps`, or `live_final`
  fastest_laps_run), normalized by actual_laps (overtime handled
  automatically). The cheapest and cleanest of the ten. laps_led component
  extends to the results floor; fastest-laps ≥ lap-times floor.

### 3.10 `finish_variance_prior` → FVS (Finish Variance Score)

- **Audit spec:** (implicit — the prior summarizes outcome spread).
- **Derivation, two rungs:** (a) **FVS-simple** — per-race sd(finish −
  start), share of top-10 finishers starting >15, from
  `silver.driver_race`; results-floor depth. (b) **FVS-model** — per-race
  walk-forward Spearman(model pre-race order, finish) from the **frozen**
  engine replayed on gold (D1's gate machinery already reproduces exactly
  this), aggregated per (track_id, era); low ρ = high-variance track.
  FVS-model is the single most decision-relevant number in the whole
  profile table (it is measured *unpredictability by our own production
  model*) — and it carries the circularity condition of §6.5.

### 3.11 What this means for F3's spec scope

1. **Split the build:** an "easy six" needing only C1/C2 results-grade +
   laps data (DCI, FVS-simple, ARS-DNF, QIS, SFS, TDS-core) and a
   "live-data four" needing flag/pit/notes/live_final coverage (RVS, PIS,
   TPP, PDI + the common-cause and tail components). F3 can land the first
   tranche even if live-feed coverage disappoints.
2. **Pre-register:** the metric definitions (this section), sample floors,
   shrinkage structure and hyperparameters, the FVS frozen-model condition,
   and the TPP clean-air exclusion — before computing anything.
3. **Output:** `gold.track_profiles` (analytics) + `gold.track_profiles_asof`
   (feature-eligible), both carrying per-cell n and intervals, both
   labeled per metric with data floor and variant.

---

## 4. LAYER C — comparability and similarity (F4's scope)

### 4.1 DST (Driver Skill Transferability) — the empirical replacement

- **Audit spec:** cross-validated correlation of driver residual
  performance between track/era pairs after team, car, season controls.
- **Residual definition (pin in F4's spec):** r(d, t) = finish(d, t) −
  the **frozen engine's** pre-race expected finishing rank for driver d at
  race t, replayed from gold (D1 makes this exactly reproducible). Using
  the production model's own residual is the right control set: it nets
  out form, pace history, typed history, and grid.
- **Pairwise estimate:** for configs a, b: weighted correlation over
  drivers of mean residuals at a vs at b (weights min(n_a, n_b) per
  driver), computed under **leave-one-season-out CV** so same-season
  team-form doesn't manufacture correlation.
- **Sample honesty:** 36 in-scope configs → 630 pairs, but per-config race
  counts of 1–10 mean each driver-config mean averages ≤10 noisy
  residuals, and pair correlations run over ~25–35 drivers. The
  deliverable is a matrix **with uncertainty**, pooled hierarchically at
  the family-pair level, with a pre-registered n-floor below which the
  cell reports the family-pair posterior.

### 4.2 The pre-registered comparison vs the structural edges

- Spearman between empirical DST and `structural_similarity_score` over
  the 193 edges (restricted to pairs meeting the n-floor), plus
  top-3-neighbor Jaccard overlap per config, plus a named disagreement
  list (structural top-3 vs empirical bottom-half, and the reverse).
- **Where they disagree, empirical wins for analytics** (already F4
  doctrine). Two package hypotheses get adjudicated for free: H4
  (concrete transfer is nonlinear — check DST(bristol_concrete, dover),
  DST(dover, nashville) against their family edge scores) and the
  Michigan/Pocono/Indy "Large flat oval" grouping vs production INT.

### 4.3 Roles that survive regardless of the comparison

- **Zero-history configs:** San Diego street (1 race), North Wilkesboro
  (0 at cutoff), any future track — DST cannot exist there. The structural
  edges and `key_comparables` remain the **only** donor structure; that is
  their permanent, legitimate role (labeled T3 when used).
- **MY_TYPE stays frozen.** Any DST-derived pooling refinement (e.g.
  similarity-kernel-weighted typed history replacing the 6-bucket typed
  mean) is a *candidate* for a future pre-registered model A/B — F4
  produces the candidate, never the adoption.

---

## 5. SIM parameter map — track knobs for a race simulator

The current engine samples finish orders from a fitted PL model (Gumbel
noise). A lap-level simulator — the natural DFS/betting product layer —
needs the following track knobs. v0 = priors as placeholders (T3, every
output labeled non-empirical); v1 = calibrated from silver/gold.

| Sim knob | v0 placeholder (T3) | Calibrated v1 source | Layer/session |
|---|---|---|---|
| Lap count, stage lengths, field size | — (T1 facts, no placeholder needed) | `silver.races`, `silver.results` | C1/C2 |
| Caution hazard (per green lap) + stage-end cautions | `attrition_risk_prior` + `finish_variance_prior` mapped to a rate band | `silver.races` number_of_cautions/caution_laps; timing from `silver.flag_events` | C2 (no F3 needed) |
| Multi-car crash size distribution | family-level analyst judgment (SS priors 9–10) | `silver.lap_notes` common-cause decomposition (ARS-b) | F3 |
| DNF hazard, crash vs mechanical | `attrition_risk_prior` | ARS-a rates | F3 |
| Tire-deg lap-time slope | `tire_degradation_prior` → s/lap band | TDS-core (+dispersion) | F3 |
| Pass probability given pace delta | `passing_difficulty_prior` | PDI (durable-pass v2 preferred) | F3 |
| Restart shuffle kernel | `restart_volatility_prior` | RVS (row/parity-conditioned) | F3 |
| Pit-stop time loss distribution; 2-vs-4-tire tradeoff | `pit_road_importance_prior` | `silver.pit_stops` empirical distributions; PIS | C2/F3 |
| Strategy menu + path frequencies | `strategy_flexibility_prior` | SFS path inventory | F3 |
| Track-position stickiness (clean air) | `track_position_premium_prior` | TPP (descriptive); causal upgrade **only** via G2 if EDGE | F3 (G2) |
| Start-grid effect on progression | `qualifying_importance_prior` | QIS | F3 |
| Driver pace/skill inputs | — (not track knobs) | `gold.wf_features` / `gold.driver_form` | D1 |

**Validation targets, not inputs:** DCI distribution, FVS, and
`silver.races` number_of_lead_changes. A sim tuned to consume these would
be circular; a sim that *reproduces* their per-track distributions is
validated. Doctrine: a v0 sim is a structural toy for design work — its
outputs carry the same T3 non-empirical label as the priors that feed it,
and nothing sim-derived goes near the production model or public
predictions without the full gate path.

---

## 6. Leakage and circularity assessment

1. **The priors embed hindsight — permanently.** All ten were authored at
   cutoff 2026-07-19 by an analyst who had seen 2015–2026 outcomes
   (Atlanta-post-2022's finish_variance=9 *knows* those 10 races). A
   backtest over any part of that window using a prior-derived feature is
   look-ahead-contaminated **by construction**; as-of mechanics cannot fix
   a constant that has already seen the future. Consequences: (a)
   prior-derived features are inadmissible as backtest kill/keep evidence;
   (b) a genuinely forward-only A/B (2027+) would be clean but slow; (c)
   their proper roles are exactly three — shrinkage centers, v0 sim
   placeholders, zero-data fallbacks — all labeled.
2. **Everything computed *from* priors inherits this** — the similarity
   edges, `structural_nearest_neighbors`, `key_comparables`, any v0 sim
   output. The additional trap specific to edges: "validating" them
   against outcomes and then pooling those same outcomes by the validated
   edges. F4's leave-one-season-out CV plus its fixed comparison protocol
   is the guard.
3. **Prior-as-shrinkage-center is admissible with one condition:** the
   center must be a fixed constant (the 1–10 score mapped by a
   pre-registered transform), not re-fit against outcomes; and the
   resulting posterior must carry the label that its center is T3. Where
   F3 can use a flat/family-empirical center instead, prefer it.
4. **As-of discipline for Layer B:** `*_asof` metrics use races strictly
   before t; shrinkage hyperparameters fixed a priori (or estimated as-of,
   never full-sample-then-applied-historically); full-sample
   `track_profiles` never joins a model feature bank — add a build-graph
   assertion, in the D-gate's spirit, that `gold.wf_features` has no
   dependency edge to `track_profiles`.
5. **FVS/DST use the model's own residuals:** compute them from the
   **frozen** engine only, as-of. A model re-fit to include a feature
   built from its own residuals, then re-scored on the window those
   residuals came from, is circular; the frozen-source + as-of + separate
   A/B rule prevents every leg of that.
6. **Era keys are safe conditioning** — rule-defined (VF announcements),
   not outcome-defined.
7. **The line, verbatim:** **nothing enters the frozen PL prediction model
   without its own pre-registered, walk-forward-gated A/B** (INTEGRATION.md
   doctrine). Analytics, DFS/betting references, and sim surfaces may use
   calibrated metrics freely with labels; the production model may not.

---

## 7. Ranked derivation catalog (payoff band, then effort)

| # | Derivable | Band | Effort | Session | Depends on | Gate |
|---|---|---|---|---|---|---|
| 1 | `silver.track_dim` + `track_xwalk` + `track_priors` (+`rules_era`, `race_track` view, §2.3 features) | **HIGH** | LOW (~1–2 h) | **C3 (new)** | package + crosswalk (exist); DuckDB warehouse conventions (C1 preferred, not required) | none — reference tables; gate extends to re-derivation checks |
| 2 | `gold.track_profiles` easy-six (DCI, FVS-simple, ARS-DNF, QIS, SFS, TDS) | **HIGH** | MED (~4–6 h incl. spec) | **F3 tranche 1** | C1+C2 (+D1 for QIS controls, FVS-model) | pre-registered spec; analytics-only |
| 3 | `track_profiles` live-data four (RVS, PIS, TPP, PDI) + `_asof` variants | **HIGH** | MED | **F3 tranche 2** | C2 live-feed coverage report | same spec; A/B for any model use |
| 4 | DST matrix + structural-edge comparison + disagreement list | MED | MED-HIGH (~3–5 h) | **F4** | D1 residual replay | pre-registered spec; model use via future typed-history A/B |
| 5 | Caution-rate quick table (cautions/lead-changes per track_id×era) | MED | LOW (<1 h) | fold into C2 close or F3 | C2 | analytics |
| 6 | Config-novelty features (config_race_number, config_age, return_gap) as model A/B candidate | MED | LOW | new F-queue item (after F1/F2) | C3 + ≥8 scored races | pre-registered A/B |
| 7 | Era-reset features (hp750_2026 interaction / era_race_number) as model A/B candidate | MED | LOW-MED | new F-queue item | C3, D1 | pre-registered A/B — directly relevant to the live 2026 forward test |
| 8 | Common-cause wreck decomposition (cars-per-incident by track) | MED | MED | inside F3 (ARS-b) | C2 lap_notes | analytics; feeds sim + betting correlation |
| 9 | Race simulator v0→v1 (PL + §5 knobs) | MED | HIGH | new spike (post-F3) | C3 (v0) / F3 (v1) | outputs labeled; no production path |
| 10 | Durable-pass metric (H3) | LOW-MED | MED | inside F3 PDI-v2 or standalone | C2 laps | research |
| 11 | Atlanta aging monitor (H1: per-race TDS/pack-state trend at atlanta_post_2022) | LOW-MED | LOW (post-F3) | ad-hoc analytics | F3 | analytics |
| 12 | Restart-geometry tagging (H2) | LOW | LOW-MED | only if RVS residuals demand it | F3 RVS | research |
| 13 | Street-novelty decay (H6) | LOW | LOW | note only — n=4 street races total | — | — |
| 14 | Pit-geometry features (H7) | LOW | HIGH (external data) | defer; fold into F6's external-source scan | — | — |

Items 1–3 are the mainline; 4 follows D1; 5–7 are cheap adders; 8–14
opportunistic. Independence: #1 is independent of everything and could run
today; #2–#3 gate on the medallion C/D sessions, not on scored races.

---

## 8. Proposed plan edits (for the owner to fold in — not applied here)

**1. New session C3 — Phase C (after C2):**

> | C3 | Track reference tables from vendored audit | pending | Sonnet 5 ·
> thinking on · high | ~1–2 hr | Materialize the vendored track audit into
> queryable reference tables — physical facts, crosswalk, and quarantined
> priors — so every silver/gold table can join on track configuration. |
> Build `silver.track_dim` (43 configs: physical facts + parsed banking +
> era bounds + hp750_2026 flag; priors excluded by design),
> `silver.track_xwalk` (crosswalk verbatim + `race_track` join view),
> `silver.track_priors` (10 priors long-form, score_type labels carried),
> `silver.rules_era` (6 era keys) per research/track_audit_derivation.md
> §2; package files untouched (hash gate stays green); extend
> src/test_track_audit.py with re-derivation checks (row counts, banking
> parse, dim⋈xwalk integrity). |

C3 has no hard dependency on C1/C2 (it reads only the package) — schedule
it anywhere in Phase C; listing it after C2 keeps the phase's build order
tidy.

**2. Tighten F3's technical summary** to reference this report as its
derivation source: pre-register the §3 metric definitions with the
easy-six / live-data-four split, per-metric sample floors and shrinkage
hyperparameters fixed a priori, dual outputs
`gold.track_profiles` (full-sample, analytics-only, build-graph-isolated
from `wf_features`) + `gold.track_profiles_asof` (feature-eligible via
A/B), FVS/residual metrics pinned to the frozen engine, and the explicit
**TPP clean-air exclusion** deferring anything causal to
specs/clean_air_causal_pace.md.

**3. Tighten F4's technical summary:** residual = frozen-engine pre-race
expected rank replayed from gold (D1); leave-one-season-out CV;
family-pair hierarchical pooling with a pre-registered n-floor; comparison
protocol = edge-restricted Spearman + top-3 Jaccard + named disagreement
list; structural edges retained as the sole donor structure for
zero-history configs; MY_TYPE untouched — any pooling refinement exits F4
as an A/B candidate, not an adoption.

**4. Net-new F-queue candidates** (post-F1/F2, ≥8 scored races, each its
own pre-registered spec): config-novelty features (catalog #6) and
era-reset features (#7 — the hp750_2026 break is live in the current
forward test, which makes this the most time-relevant of the new ideas).

**5. Unscheduled placeholder:** simulator spike (#9), explicitly post-F3;
proposing a session now would be premature.

---

*Report ends. Package files untouched; hash gate re-verified green after
writing (see commit). Nothing here builds, adopts, or changes — F3/F4/C3
execution each require their own session and, where applicable, their own
pre-registered spec.*
