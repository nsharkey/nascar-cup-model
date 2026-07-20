# SPEC: Track-audit prior calibration — empirical track profiles (F3)

**Status:** pre-registered 2026-07-20, before any metric has been computed.
**Derivation source (execution contract):** `research/track_audit_derivation.md`
§3 (LAYER B) defines all ten metrics and is authoritative for their
*definitions* — this spec does not re-derive or alter them, only pins the
mechanical details the derivation doc explicitly delegates to F3 ("F3's spec
must pre-register per-metric minimum sample floors," §3.0) plus the plumbing
needed to actually build SQL/Python against them. Loop-metric-adjacent
definitions (passes, green-flag restrictions) are pinned per
`external_knowledge_scan.md` §7 item 3 (cited in the plan as "§7.3") and are
shared verbatim with the future F13 session. F16 additions per
`domain_knowledge_scan.md` §10.4/§6.3/§5.3.

**Governance (restated from INTEGRATION.md and the derivation doc, binding):**
nothing computed here — track-specific or family-pooled, full-sample or
as-of — enters the frozen PL prediction model without its own later
pre-registered, walk-forward-gated A/B. This session builds analytics/
DFS/betting reference tables only. `walkforward.py`, `predict_next.py`,
and the vendored `research/track_audit/` package are not touched.

**Tier:** Analytics/reference (phase F's own note: "Analytics and reference
sessions (F3/F4/F13/F14/F19) never touch the frozen model"). No gated A/B,
no `>=8`-scored-races gate — that gate applies only to the roadmap-#4 model
A/B family (F1/F2/F12/F18), not this session.

**Scope:** Cup only (`series_id=1`, `race_type_id=1`). All ten metrics, the
frozen model, `silver.race_track_features`, and every per-config count in
the derivation doc are Cup-scoped; QIS and FVS-model additionally require
`gold.wf_features`, which is Cup-only by construction (D1). Extending to
Xfinity/Trucks is out of scope — not proposed anywhere in the derivation
doc's catalog (§7).

---

## 1. Shared machinery (frozen; applies to all ten metrics)

### 1.1 Grain and join path

Grain: `(track_id, era_key)`, per §3.0. Join path: `silver.race_track_features`
(C3; Cup-only, one row per `(series_id=1, race_id)` with `track_id, era_key`
already resolved) joined to whichever data table a metric's definition names.
`primary_family` (12 groups) comes from `silver.track_dim` via `track_id`.

### 1.2 Two governed outputs

- **`gold.track_profiles`** — full-sample. Analytics/DFS/betting reference
  **only**. Build-graph-isolated from `gold.wf_features` (§5 below) — no
  code path that builds `wf_features` may read `track_profiles`, in either
  direction is actually the safer invariant and both directions are checked
  (§5.2).
- **`gold.track_profiles_asof`** — grain adds `race_seq`: one row per
  qualifying `(track_id, era_key, race_id)` where every aggregate (track
  and family) is computed from races **strictly before** that race, per
  metric-scope (§1.6). The only variant that could ever be feature-eligible,
  and only via its own later gated A/B — this session does not propose one.

### 1.3 Aggregation hierarchy (F3's own concrete rule, fixed a priori)

Every metric reduces to **one raw value `v_r` per qualifying race `r`**
(§2 gives each metric's own per-race statistic — a rate, a median slope, an
HHI, a standardized regression coefficient, etc. — computed from that
race's own sub-race events: laps, pit stops, restarts, cautions). Each race
also produces an **event count `e_r`** — the within-race count of the
metric's natural event unit (green runs, restarts, pit stops, driver-race
rows, etc.), used only for the events-within-race floor (§1.4).

Track/era and family/era aggregates — **both full-sample and as-of** — are
the **unweighted mean of qualifying per-race values** `v_r` (one observation
per race regardless of that race's own event count, so a handful of
high-event races cannot dominate a track's cell). This is a deliberate F3
simplification of the derivation doc's less exact language ("median slope
across runs," "mean per-race Spearman," etc.) into one uniform, implementable
rule: compute the per-race statistic exactly as the audit subsection
describes, then average per-race values at the track/family level. Two
named exceptions, because the audit spec is explicit about them:

- **TDS_core** uses **median**, not mean, of per-race values (audit spec:
  "median slope … across runs" — median is the aggregator named in the
  metric's own definition, so it is kept).
- **ARS-a (DNF rate)** uses the beta-binomial posterior mean (§2.4), which
  subsumes the mean-of-per-race-rates step (the beta-binomial's counts are
  pooled directly, not averaged-then-shrunk twice).

### 1.4 Sample floors (fixed a priori; below floor → report the family value)

Two floors per metric: `min_races` (qualifying races at the track/era cell)
and `min_events` (`sum(e_r)` over those races). **Both must be met** for the
cell to report a track-specific (shrunk) value; if either is unmet, the
displayed value is the family/era aggregate at the same time cutoff, and
`below_floor = true` is recorded (the underlying `track_raw`/`n_races`/
`n_events` are still stored for transparency, just not surfaced as "the"
value). Default `min_races = 5` unless a metric overrides it below.

| metric | min_races | min_events | event unit |
|---|---:|---:|---|
| TDS | 5 | 15 | qualifying green runs (≥8 laps) |
| TPP | 5 | 10 | restarts (weakest of its 3 components — see §2.2) |
| PDI | 5 | 300 | green car-laps |
| ARS-a (DNF rate) | 5 | 100 | driver-race entries |
| ARS-b (common-cause, lap_notes) | 5 | 8 | qualifying incidents (≥3 driver_ids) |
| ARS-c (major-position-loss tail) | 5 | 150 | driver-race observations with running_pos |
| ARS caution-cause / lucky-dog (F16) | 5 | 10 | caution segments |
| ARS-b make-clustering (F16/K7) | 5 | 500 | green car-laps (SS/drafting family only) |
| RVS | 5 | 20 | restart-driver observations |
| PIS | 5 | 40 | pit stops |
| QIS | 5 | 60 | driver-race regression observations |
| SFS | 5 | 40 | identified top-10 strategy paths |
| DCI | 5 | 5 | races (no sub-race floor) |
| FVS-simple | 5 | 5 | races (no sub-race floor) |
| FVS-model | 5 | 5 | scored races under the frozen engine's own eligibility |

### 1.5 Shrinkage (fixed a priori; never tuned on outcomes, per §6.4)

Empirical-Bayes blend toward the family/era value at the same time cutoff:

```
weight_track = n_races / (n_races + K)        K = 5 (races), fixed
displayed    = weight_track * track_raw + (1 - weight_track) * family_raw
             if races >= min_races AND events >= min_events
             else family_raw   (below_floor = true)
```

`family_raw` is the same §1.3 mean-of-per-race-values, pooled across every
`track_id` sharing that `primary_family` **within the same `era_key`** (era
boundaries are rule-defined, per §6.6 of the derivation doc — pooling never
crosses an era). If a `primary_family` has only one `track_id` in scope
(`Condensed drafting speedway`, `Dirt oval` — see §2 counts below),
`family_raw == track_raw` by construction; shrinkage still applies
mechanically (harmless — it just doesn't change anything) and is not
special-cased.

QIS and ARS-a use their own within-metric pooling machinery (§2.7, §2.4)
in place of the generic mean; the same `min_races`/`min_events`/`K=5`
floor-and-blend numbers still gate what is *displayed*.

### 1.6 `race_seq` (metric-scope-relative; NOT the same integer as `gold.wf_features.race_seq`)

Each metric operates over its own eligible race universe (§2's per-metric
depth floor: 2017+ results-grade, or 2022+ live-data/frozen-engine). For
`gold.track_profiles_asof`, `race_seq` is the 1-based index of race `r`
within **that metric's own eligible universe**, ordered by `(race_date,
race_id)` ascending — mirroring `gold.wf_features`'s own walk-forward-clock
convention (`gold_build.py`'s `SCOPE_RACES_SQL`) but recomputed per metric
because the universes differ in size. A future consumer joining
`track_profiles_asof` to `wf_features` must join on `race_id`, never on
`race_seq` — the two are indexes into different universes and will collide
by coincidence, not by design.

### 1.7 Loop-metric-adjacent definitions (pinned per external_knowledge_scan.md §7 item 3; shared with F13)

- **Green-flag lap** := `silver.lap_flags.flag_state = 1` at that
  `laps_completed` value, joined to `silver.laps.lap` within `(series_id,
  race_id)`. This is not a new choice — it is `parse_lib.py`'s own existing
  convention (`FlagState == 1`, `DATA_DICTIONARY.md` §6), reused verbatim
  so silver/gold agree with the frozen parser everywhere green-flag laps
  are used.
- **Pass** (a driver-lap position gain) := on two consecutive green-flag
  laps `L, L+1` for driver `d`, `running_pos(d, L+1) < running_pos(d, L)`.
- **Durable pass** (H3; used by PDI-v2 and TPP's pass-scarcity component)
  := a pass at `L → L+1` where, for every green-flag lap `k` in `L+1 …
  min(L+5, last available green lap before the next caution or race end)`,
  `running_pos(d, k) < running_pos(d, L)` (the gained position is never
  fully surrendered within the next 5 green laps, or however many remain
  before a caution/race-end truncates the window — a short trailing window
  is still evaluated over what's available, not discarded).
- **Restart** := a `caution → green` transition in `silver.flag_events`
  (`flag_state` 2 → 1 at consecutive `event_seq`), anchored at the `green`
  event's `lap_number`.
- **Restart row / lane** (RVS conditioning only) := `row = ceil(position /
  2)`, `lane = position mod 2` — a **proxy**, not the actual choose-rule
  lane (unavailable in any feed), labeled `approximate` on every RVS output
  row per §3.5's own instruction.
- These four definitions are the ones F13 (§8.2 of the external scan) must
  import rather than re-choose, per its own overlap guard.

### 1.8 Build-graph isolation (frozen; the D-gate's spirit applied here)

`gold.wf_features`, `gold.driver_form`, `gold.driver_type_form`, and every
file under `src/gold_build.py` may not read from `gold.track_profiles` or
`gold.track_profiles_asof`, in source code or SQL, ever. Enforced
mechanically by `gate_track_profiles.py` (§6): a static source-text scan of
`src/gold_build.py`, `src/walkforward.py`, and `src/predict_next.py` for the
token `track_profiles`, asserting zero matches. The reverse direction (this
session's own build reading `gold.wf_features` for QIS/FVS-model) is
expected and fine — the isolation is one-directional, matching "never
joinable into model feature banks" (§3.0).

### 1.9 Vendored priors stay untouched

`research/track_audit/` (six files), `src/track_audit.py`,
`silver.track_priors`, `silver.track_similarity_prior` are read-only inputs
to this session (used only for `primary_family`, `evidence_class` labeling
context, and — nowhere else — nothing here rewrites or "validates" a prior
against the metrics computed below; that comparison, if ever wanted, is a
distinct future research question, not part of this build).

---

## 2. Metric definitions

Each metric computes a per-race raw value `v_r` (§1.3) from the named
source tables, exactly per its `research/track_audit_derivation.md`
subsection. Depth annotations are copied verbatim from that document — a
metric's stated depth is authoritative even where the underlying raw feed
technically extends further (e.g., TDS is pinned "≥2022" by its own
subsection despite `silver.laps` technically reaching back to 2020) —
"compute each per its own subsection's definition; do not invent
alternatives" applies to depth as much as to formula.

### 2.1 TDS — Tire Degradation Score (§3.1; **≥2022**)

- **Runs**: for driver `d` in race `r`, sort `d`'s green-flag laps (§1.7)
  ascending by `lap`. Boundaries = `{0, race-end} ∪ {silver.pit_stops.
  lap_count for (d, r)}`. Within each boundary-to-boundary interval, the
  maximal consecutive-lap (gap = 1) green-flag subsequences are runs.
  Runs with `< 8` laps are dropped (audit spec's own floor).
- **Per-run slope**: Theil–Sen slope (`scipy.stats.theilslopes`) of
  `lap_time` on lap-index-within-run (seconds/lap; positive = degrading).
- **`v_r` (TDS_core)** = median per-run slope, pooling every qualifying run
  in race `r` across all drivers. `e_r` = count of qualifying runs in `r`.
- **TDS_dispersion** (secondary) = cross-driver IQR, within race `r`, of
  each driver's own median run-slope (one value per driver with ≥1
  qualifying run). Same aggregation (§1.3 mean) at track/family level.
- Sources: `silver.laps`, `silver.lap_flags`, `silver.pit_stops`.
- **v2 fuel-decomposition and crossover-frequency** (audit spec's other two
  components) are explicitly deferred — v1 reports net slope only, per
  §3.1's own "v1 reports the net falloff slope … v2 refinements F3 may
  explicitly defer."

### 2.2 TPP — Track Position Premium (§3.2; **≥2022**; causal exclusion binding)

Fixed-weight z-composite of three descriptive components (equal weights —
1/3 each; a deliberate F3 choice since the audit spec names the components
but not their relative weights, and equal weighting is the neutral default
that avoids implicitly asserting one component matters more):

- **(a) Rank persistence**: per race `r`, `0.5 * z(Spearman(start, finish))
  + 0.5 * z(mean lap-to-lap green-flag running_pos autocorrelation, lag 1)`
  — the autocorrelation is computed per driver over their green-flag-lap
  `running_pos` sequence, then averaged across drivers in `r`.
- **(b) Restart retention**: per race `r`, `P(|Δposition| <= 1 within 3
  green laps of a restart | starting position <= field_size/2)` (front-half
  cars only, per §3.5's audit spec) — `silver.flag_events` + `silver.laps`.
- **(c) Pass scarcity**: inverse of green-flag passes (§1.7) per car-lap in
  race `r` — `-1 * (count of passes) / (green car-laps, §2.3's denominator)`,
  z-scored (higher = scarcer passing = higher track-position premium).
- `v_r` = mean of the three z-scored components computed for `r`, using
  each component's own scoring-population z (across all qualifying races
  in scope, computed once, not re-z-scored per track). `e_r` = count of
  restarts in `r` (component (b)'s natural unit — the sparsest of the
  three, so it sets the metric's own event floor per §1.4).
- **Binding exclusion (verbatim from §3.2):** no clean-air lap-delta
  component. Causal clean-air pace is `specs/clean_air_causal_pace.md`
  territory (G-phase, EDGE-gated). TPP's output columns must be labeled
  `descriptive_association_only = true` and must not be named or documented
  in any way a reader could mistake for the G-spec's causal estimand.

### 2.3 PDI — Passing Difficulty Index (§3.3; **≥2022**)

- **Green car-laps** (shared denominator, also used by §2.2c): per race
  `r`, `(count of laps with flag_state=1 in silver.lap_flags) * (count of
  distinct driver_id in silver.laps for r)`.
- **v1** (coverage-risk-flagged): `Σ quality_passes` (or `passes_made` if
  `quality_passes` null) from `silver.live_final` for race `r`, divided by
  green car-laps, inverted (`-1 *`) and z-scored. Reported only for races
  with `silver.live_final` coverage; `null` elsewhere.
- **v2 (durable pass, primary)**: count of durable passes (§1.7) across all
  drivers in race `r`, divided by green car-laps, inverted and z-scored.
  Always computed where `silver.laps`/`lap_flags` exist (no live_final
  dependency) — the audit spec's own stated preference ("the durable-pass
  rate is the defensible number [at drafting tracks]").
- `v_r` = v2 (durable pass) — the metric's primary, always-computed value.
  v1 is stored as a secondary column (`pdi_v1_quality_pass`, nullable) and
  the two are compared in the build report per §3.3's "F3 should compute
  both where possible and report divergence." `e_r` = green car-laps.

### 2.4 ARS — Attrition Risk Score (§3.4; three sub-components, mixed depth)

- **ARS-a — DNF rate (results-grade, extends to 2017+)**: from
  `silver.results.finishing_status`, classified via the frozen taxonomy
  already pre-registered in `specs/dnf_status_feature.md` §1 (crash-class =
  `{accident, dvp}`, mech-class = DNF and not crash-class, case-folded/
  stripped) — reused verbatim rather than re-chosen, per that spec's own
  taxonomy being the project's one existing DNF classification. Per
  `(track_id, era)`: beta-binomial posterior mean of crash-DNF rate and of
  mech-DNF rate separately, prior = `Beta(2, 18)` (a weakly informative
  prior centered near the empirical ~10% crash-DNF base rate observed
  project-wide, fixed a priori, not fit per cell), pooled at the
  `(primary_family, era)` level for the family term exactly as §1.5's
  formula (the beta-binomial's `alpha/beta` pseudo-counts play the role of
  `K` here — `K_eff = alpha + beta = 20`, close to the shared default and
  not separately tuned). `v_r` for this sub-component is the race's own
  crash-DNF and mech-DNF counts/denominator (driver-race rows); the
  aggregation is the beta-binomial update, not a plain mean (§1.3's named
  exception).
- **ARS-b — common-cause structure (live-data, ≥2022, per audit spec)**:
  from `silver.lap_notes`, incidents with `len(driver_ids) >= 3` = multi-car
  events. `v_r` = mean cars-per-multi-car-incident in race `r` (null if
  zero qualifying incidents). `e_r` = qualifying-incident count.
- **ARS-c — major-position-loss tail (≥2022)**: from `silver.laps`, per
  driver-race, `best_running_pos` (min over green laps) vs `finish`
  (`silver.driver_race.finish`, joined by `race_id, driver_id`).
  `v_r` = `P(finish >= best_running_pos + 15)` over race `r`'s driver
  population. `e_r` = driver-race count with valid running_pos data.
- **F16 additions (2017+, via C4) — new sub-components, NOT replacing
  ARS-b/c above:**
  - **`ars_caution_accident_share`**: per race `r`, share of
    `silver.caution_segments` rows with `reason IN ('Accident', 'Spin')`
    out of all caution segments in `r`. `e_r` = caution-segment count.
  - **`ars_lucky_dog_rate`**: per race `r`, share of `silver.caution_
    segments` rows with non-null `beneficiary_car_number` out of all
    caution segments in `r`. Same `e_r`.
  - Both use §1.3/§1.5's generic mean-and-shrink (not the beta-binomial
    treatment reserved for ARS-a).
- All five sub-components ship as separate columns (`ars_a_crash_dnf_rate`,
  `ars_a_mech_dnf_rate`, `ars_b_common_cause_mean_cars`,
  `ars_c_major_loss_tail_p`, `ars_caution_accident_share`,
  `ars_lucky_dog_rate`) plus `ars_b_make_clustering_index` (§3 below,
  SS/drafting-family cells only) — no single scalar "ARS" is computed by
  collapsing them (the audit spec itself treats DNF-rate, common-cause, and
  tail as three distinct outputs, not one number).

### 2.5 RVS — Restart Volatility Score (§3.5; **≥2022**; approximate-lane-labeled)

- Per restart (§1.7) per driver `d` in race `r`: `|running_pos(d, restart+3)
  - running_pos(d, restart)|` on green laps, truncated at the next caution.
  Row/lane per §1.7 (labeled `approximate`).
- `v_r` = mean `|Δrunning_pos|` across all driver-restart observations in
  `r`, excluding restarts inside active pit cycles (a driver whose own
  `silver.pit_stops` row has `pit_out_race_time` within the restart window
  is excluded from that restart's contribution — the wave-around screen).
  `e_r` = qualifying driver-restart observation count.

### 2.6 PIS — Pit-Road Importance Score (§3.6; **≥2022**)

- Per driver-race: decompose `start - finish` into pit-cycle `Δ` (Σ
  `pit_in_rank - pit_out_rank` per stop from `silver.pit_stops`), restart-
  window `Δ` (§2.5's windows), green-run `Δ` (remainder).
- `v_r` = cross-driver variance share explained by the pit-cycle component
  in race `r` (`Var(pit_Δ) / Var(start - finish)`, both computed over race
  `r`'s driver population). `e_r` = pit-stop count in `r`.
- Secondary outputs (own columns, same aggregation): `pit_stop_duration`
  median/IQR per `(track_id, era)`; penalty rate from `silver.lap_notes`
  notes matching a fixed case-insensitive substring list (`penalty`,
  `pit road violation`, `speeding`) — a labeled best-effort text match, not
  a structured field (none exists post-2022 per the domain scan's
  `infractions[]` dead-end finding).

### 2.7 QIS — Qualifying Importance Score (§3.7; depth = `gold.wf_features` scope, 2022+)

- Per `(track_id, era)`: OLS of `z_finish ~ z_start_feat + fin_h + pace_h`
  over `gold.wf_features` rows joined to that `track_id/era` (via
  `race_track_features`), restricted to rows with `has_pace = true` and
  non-null `fin_h`/`pace_h` (i.e., exactly the frozen engine's own
  eligibility). `z_start_feat`/`z_finish` are standardized using the
  **global** (whole Cup 2022+ scope) mean/sd — fixed once, not per cell —
  so the resulting `β_start` is comparable across tracks (a genuinely
  "standardized start coefficient," §3.7's own phrase). `fin_h`/`pace_h`
  enter as raw controls (their scale doesn't affect `β_start`'s
  comparability).
- `v_r` — QIS is not race-decomposable the way the other nine are (a
  regression needs a pooled sample); §1.3's "one value per race" rule is
  replaced here by the audit spec's own hierarchical-partial-pooling
  language, concretely as: `track_raw` = `β_start` fit on race rows at
  `(track_id, era)` only; `family_raw` = `β_start` fit on race rows across
  the whole `(primary_family, era)`. The §1.5 blend (`weight = n_races /
  (n_races + K)`, `n_races` = distinct races contributing rows) still
  applies — QIS's "partial pooling" is implemented as this same shrinkage
  mechanism applied to a regression coefficient instead of a mean, kept
  uniform with every other metric rather than introducing a separate
  mixed-effects estimator. `e_r`/`min_events` counts driver-race rows, not
  races (§1.4: 60).
- **As-of QIS**: refit both regressions using only rows from races with
  smaller `race_seq` (§1.6) than the target race — a real walk-forward
  refit, not a lookup, since a regression coefficient can't be
  incrementally windowed the way a mean can; computationally cheap (≤
  ~150 rows per family at any point in the current data).

### 2.8 SFS — Strategy Flexibility Score (§3.8; **≥2022**)

- Per driver-race among race `r`'s top-10 finishers: path = `(stop_count,
  tire_take_sequence, stage_bucket_sequence)` where `tire_take` per stop ∈
  `{0, 2, 4}` (count of true flags among the four `*_tire_changed` columns
  in `silver.pit_stops`) and `stage_bucket` per stop = which of stages 1–4
  the stop's `lap_count` falls in, via `silver.races.stage_1_laps` /
  `stage_2_laps` / `stage_3_laps` / `stage_4_laps` cumulative boundaries.
- `v_r` = Shannon entropy (bits, `log2`) of the empirical path distribution
  among race `r`'s top-10 finishers. Secondary: share of top-5 finishers on
  a non-modal path (the path with the highest count in `r`). `e_r` = count
  of top-10 finishers with a fully resolved path (all stops' `driver_id`
  and `lap_count` present).

### 2.9 DCI — Dominator Concentration Index (§3.9; laps_led results-floor / fastest-laps lap-times-floor)

- **`dci_laps_led_hhi`** (results-grade, extends to 2017+): per race `r`,
  HHI of `silver.results.laps_led` shares among drivers with `laps_led >
  0`. `v_r` for this column.
- **`dci_fastest_laps_hhi`** (**≥2022**, lap-times floor): per race `r`,
  HHI of fastest-lap-count shares, preferring `silver.live_final.
  fastest_laps_run` where present; falling back to a direct count (per
  green lap, the driver with `min(lap_time)` gets one fastest-lap credit)
  from `silver.laps` where `live_final` is absent for that race. `v_r` for
  this column, `null` before 2022 (no lap-times).
- **`dci_combined`** = mean of the two where both are non-null, else
  whichever is available. `e_r` = races (§1.4: no sub-race floor — HHI is
  already a race-grain statistic).

### 2.10 FVS — Finish Variance Score (§3.10; two rungs, different depth)

- **FVS-simple** (results-grade, extends to 2017+): per race `r`,
  `sd(finishing_position - starting_position)` over `silver.results`, plus
  `P(finish in top 10 AND start > 15)`. Two columns, same §1.3 aggregation.
  `e_r` = races.
- **FVS-model** (**frozen engine only**, `gold.wf_features` scope 2022+):
  per race `r`, walk-forward Spearman(predicted order, actual finish) from
  a **replay of the exact frozen-engine mechanics** (`pl_fit`, `wmean`,
  `znan` imported unmodified from `walkforward.py`; same eligibility/order
  as `gate_gold.py`'s `gold_sourced_walk_forward`) over `gold.wf_features`,
  with `race_id` retained per output row (a new function in this session's
  own build module — not an edit to `gate_gold.py` — that mirrors its
  replay loop and tags `race_id` for the `(track_id, era)` join;
  `gate_gold.py` itself is untouched). Low ρ = high-variance track — "the
  single most decision-relevant number in the whole profile table" per
  §3.10, and it carries §6.5's circularity condition (below).
- **§6.5 circularity condition, restated and enforced:** FVS-model is
  computed from the **frozen** engine's own residuals, as-of, and is never
  used to refit or re-select that engine within this session. Any future
  use of FVS-model as a *feature* is barred from also being used to justify
  changing the engine whose residuals produced it, without its own
  pre-registered A/B making that dependency explicit.

---

## 3. F16 additions (`domain_knowledge_scan.md` §10.4)

### 3.1 Caution-cause taxonomy + lucky-dog beneficiary (2017+ depth)

Implemented as ARS's `ars_caution_accident_share` / `ars_lucky_dog_rate`
sub-components, §2.4 above — new columns, not a replacement for the
existing ≥2022 `ars_b_common_cause_mean_cars` (which needs `lap_notes`'
`driver_ids` list, unavailable from `caution_segments`, and stays ≥2022).

### 3.2 ARS-b make-clustering (K7, `domain_knowledge_scan.md` §6.3)

- **Scope:** SS/drafting-family cells only — `primary_family IN
  ('Drafting superspeedway', 'Condensed drafting speedway')` (Daytona,
  Talladega, Atlanta-pre-2022's condensed configuration per the package's
  own taxonomy). **Analytics only** — the domain scan's own verdict is
  explicit that this can never clear the program's model-adoption bar
  (§6.3: "implausible signal-to-noise, and the payoff would land in races
  the project refuses to act on"). No model path is proposed here or
  implied by building this column.
- **Per green lap** in race `r`: cars ordered by `running_pos`
  (`silver.laps`), joined to `car_make` (`silver.results.car_make`).
  Adjacent-pair same-make rate = `(count of consecutive-position pairs
  sharing car_make) / (field_size - 1)`.
- **Expected rate under a uniformly random arrangement** (closed form, no
  simulation needed): `Σ_k [n_k * (n_k - 1)] / [N * (N - 1)]`, where `n_k`
  is the count of cars from make `k` still running at that lap and `N` is
  the total cars running.
- `v_r` = mean over race `r`'s green laps of `(observed_rate /
  expected_rate)` — the **adjacency index**; `> 1` indicates make
  clustering beyond chance. `e_r` = green car-laps (§2.3's denominator,
  restricted to SS/drafting-family races).
- **Driver-level cooperation scores** (mentioned in the domain scan's K7
  write-up as a fuller proxy) are **out of scope for this session** — the
  F16 folded-in instruction (§10.4) asks only for "a make-clustering
  component," track-grain, which is what `ars_b_make_clustering_index`
  delivers. A driver-level extension would be a distinct future session.

### 3.3 H5 contender-exclusion sensitivity check (`domain_knowledge_scan.md` §5.3)

- **Championship race identification:** the unique race per season with
  `silver.races.playoff_round` equal to that season's max value (verified
  empirically: exactly one such race/season, 2020–2025, always Phoenix).
- **Championship-4 identification:** the 4 drivers with the lowest
  `silver.results.points_position` in that race (in-race live standings,
  100% coverage). **Verified against `silver.live_final.driver_is_in_chase`
  where that feed is complete** — exact agreement for 2020–2024 (4/4 flagged
  drivers match the 4 lowest-`points_position` drivers); 2025's
  `live_final` has a known single-row coverage gap for that race (only 1 of
  ~36 vehicles stored), so `points_position` — not `live_final` — is the
  metric actually used, for completeness. This cross-check is recorded in
  the build report, not re-run as a gate (a one-time empirical
  verification of the operational definition, not an invariant that could
  drift).
- **Sensitivity target: TDS only** — H5's own wording ("physical pace
  estimates should use the full field and avoid assuming contenders are
  representative") names pace estimates specifically; TDS is the physical
  pace/degradation metric. Applying the same check to all ten metrics would
  go beyond what F16 asked and beyond what H5's own text supports.
- **Output:** for every `(track_id, era)` cell containing at least one
  championship race, two additional columns: `tds_core_full_field` (the
  ordinary §2.1 value, unchanged) and `tds_core_excl_contenders` (TDS_core
  recomputed with the 4 contenders' driver-races removed from every
  championship race in that cell's race set — non-championship races in
  the same cell are unaffected either way since they have no contenders to
  exclude). `tds_contender_sensitivity_delta` = the difference. This is
  **not a model feature** and does not feed `predict_next.py` — it answers
  the methodological question H5 raises (does the track's own pace
  signature change once its analytically-relevant outliers are removed),
  routed here per F19's close-out.

---

## 4. Output schema

### 4.1 `gold.track_profiles`

One row per `(track_id, era_key)` with at least one qualifying race in any
metric's scope. Columns: `track_id, era_key, primary_family, n_races_total`
(races in this cell across all sources, informational), then for every
metric/sub-component in §2–§3: `<metric>_value` (the §1.5-blended displayed
value), `<metric>_track_raw` (nullable), `<metric>_family_raw`,
`<metric>_n_races`, `<metric>_n_events`, `<metric>_below_floor` (bool). TPP
additionally carries `tpp_descriptive_association_only = true` on every
row (§2.2's labeling requirement). RVS additionally carries
`rvs_lane_approximate = true`. Provenance columns: `package_version` (from
`silver.track_dim`), `built_at`.

### 4.2 `gold.track_profiles_asof`

Same column set, grain adds `race_id, race_seq` (§1.6, per-metric-scope).
One row per `(track_id, era_key, race_id)` for every race that is itself a
qualifying race for at least one metric — that race's own outcome is never
included in its own row's aggregates (strict `<`, not `<=`).

---

## 5. Build-graph isolation gate (frozen)

`gate_track_profiles.py` (§6 checklist) asserts, on every run:

1. Both output tables exist and are internally consistent (row-count and
   join-integrity checks mirroring `gate_track_reference.py`'s style).
2. **Isolation**: `track_profiles` appears nowhere in `src/gold_build.py`,
   `src/walkforward.py`, `src/predict_next.py` (source-text scan, §1.8).
3. Every `below_floor = true` row's displayed value equals its
   `family_raw` exactly (no partial credit) — proves the floor rule is
   applied, not merely computed.
4. `gold.track_profiles_asof`'s per-race aggregates use strictly-prior
   data: for a sample of cells, recomputing the as-of value using only
   races with smaller `race_seq` reproduces the stored value exactly
   (a re-derivation spot-check, same idiom as `gate_track_reference.py`'s
   banking-parse re-derivation).
5. TPP rows carry `descriptive_association_only = true`; RVS rows carry
   `lane_approximate = true`; FVS-model rows are sourced only via the
   frozen-engine replay function (asserted by checking that function
   imports `pl_fit`/`wmean`/`znan` from `walkforward` rather than
   reimplementing the math — a lightweight source-scan, same spirit as
   check 2).

---

## 6. Implementation checklist

1. `src/track_profiles_build.py` (new module), built the same way as
   `track_reference_build.py`/`gold_build.py` — DuckDB SQL where a metric
   reduces cleanly to SQL (TDS run-slopes, DCI HHI, DNF classification,
   caution-cause shares, make-clustering), Python/numpy where a metric
   needs `scipy.stats.theilslopes`, an OLS fit, or the frozen-engine replay
   (QIS, FVS-model, TDS's Theil–Sen step).
2. Build order: (a) per-race raw tables (§2's `v_r`/`e_r`, one query/loop
   per metric); (b) full-sample track/family aggregation + shrinkage
   (§1.3–§1.5) → `gold.track_profiles`; (c) as-of aggregation (§1.6) →
   `gold.track_profiles_asof`; (d) F16 additions (§3); (e) write both
   tables to `data/gold/track_profiles.parquet` /
   `track_profiles_asof.parquet`, register as `gold.*` views in
   `warehouse.py` (same rebuildable-from-disk pattern as every other gold
   table).
3. `src/gate_track_profiles.py` — §5's five checks.
4. `report/TRACK_PROFILES.md` — row counts per metric, floor/shrinkage
   effect (how many cells are `below_floor` per metric), PDI v1-vs-v2
   divergence where both exist, TDS contender-sensitivity deltas at
   championship cells, and the H5 `driver_is_in_chase` cross-check result.
5. Extend `DATA_DICTIONARY.md` (new §10f) and `warehouse.py`'s gold-table
   view loop.
6. Update `plan/schedule.yml` (F3 → done) and re-render via
   `python src/report_plan.py`.
7. Run the full gate surface (`src/run_gates.sh`) — must stay 15/15 green
   (14 existing + this session's new `gate_track_profiles.py`).

---

## AMENDMENT (2026-07-20, mid-build, made before any RVS value was computed — the data this
amendment's rule adjudicates does not yet exist, so this is a permitted pre-data amendment per
specs/README.md, not a protocol violation)

**§2.5 RVS's active-pit-cycle exclusion is implemented via lap-count proximity, not a
race-elapsed-time window.** As originally written, §2.5 said the screen would use "`silver.
pit_stops`' own `pit_out_race_time` within the restart window." Implementing that literally
requires treating `pit_stops.pit_out_race_time` and `silver.flag_events.elapsed_time` as the
same race-clock unit with no independent verification that they are (a cross-feed assumption
this session did not want to ship unverified), and requires picking an arbitrary time-width for
"the restart window" (lap duration varies by track, so a fixed-seconds width would itself be an
unregistered choice). The actual implementation instead excludes a driver-restart observation
when that driver has any `silver.pit_stops` row with `lap_count` within 3 laps of the restart
lap (`abs(restart_lap - pit_lap) <= 3`) — simpler, uses only fields already in the same table
family, and screens the same wave-around/active-pit-cycle contamination the original wording
targeted. Every other part of §2.5 (restart definition, `L+3` delta, row/lane labeling) is
unchanged.

## AMENDMENT (2026-07-20, mid-build, made before any RVS value was computed — pre-data, permitted)

**§1.7's restart definition is sourced from `silver.lap_flags` alone, not `silver.flag_events`.**
A spot-check while implementing RVS found that `flag_events.lap_number` and `lap_flags.
flag_state` genuinely disagree on some races about whether a caution occurred in a given lap
window at all (race 5287: `flag_events` shows a caution starting at lap 20 and clearing at lap
30; `lap_flags` shows every lap 15–32 as green, flag_state=1, no caution recorded at all) — not
a stable off-by-one that could be corrected with a fixed offset, a real cross-feed data
disagreement (plausibly two different upstream collection systems for the same event).
Restart detection (and the RVS position window built on it) now reads `silver.lap_flags`
exclusively: a restart lap = any `laps_completed` where `flag_state` transitions `2 → 1` at
consecutive lap numbers. This is the same table already used for position tracking, so restart
detection and position windows can never disagree about which laps are green. `silver.
flag_events` is unaffected elsewhere (not used by any other metric in this spec).

## AMENDMENT (2026-07-20, mid-build, made before any output table was finalized — pre-data,
permitted)

**`gold.track_profiles_asof`'s displayed `race_seq` column is a track/era-LOCAL ordinal
(by `race_date`, across the union of every metric's own eligible races at that cell), not any
single metric's own scope-relative sequence from §1.6.** §1.6 is unchanged for *internal*
purposes: each metric's as-of blend still decides "strictly before this race" using that
metric's own eligible-universe ordering (a results-grade metric's internal race_seq and a
live-data metric's internal race_seq for the same `race_id` are still different integers, and
the blend computation is unaffected by this amendment). What changed is only which number is
*displayed* in the output row's `race_seq` field — a single shared column across all ~20
per-metric sub-columns needs one consistent value for human orientation ("this is the 3rd race
run at this track/era"), and no single metric's internal sequence is privileged to be that
value. This is a display/labeling clarification, not a change to any metric's computation.

## AMENDMENT LOG

None yet — this spec is frozen as of first commit. Per `specs/README.md`,
any future edit must be either a dated `## RESULT` block (this spec
provides for one below, to be filled after the build) or a dated
`## AMENDMENT` appended before the data an amended rule adjudicates exists
(inapplicable here retroactively — this is descriptive analytics with no
kill/keep decision, so no amendment should ever be needed against a
decision rule the way the model-A/B specs need one).

## RESULT — F3 (2026-07-20)

Built. `gold.track_profiles` (130 rows, `(track_id, era_key)`) and `gold.track_profiles_asof`
(329 rows, `(track_id, era_key, race_id)`), all ten metrics plus the three F16 additions
(caution-cause taxonomy, K7 make-clustering, H5 contender-exclusion sensitivity). New gate
`src/gate_track_profiles.py` **PASS**; full repository gate surface **15/15 green** (14
inherited + this session's new gate), C-gate and D-gate unaffected. Two dated pre-data
amendments recorded above (RVS pit-cycle screen mechanics; restart detection sourced from
`silver.lap_flags` alone after a genuine cross-feed disagreement was found in `silver.
flag_events`) plus one display-only clarification (`track_profiles_asof.race_seq` is a
track/era-local ordinal). 80-87% of track/era cells are `below_floor` for most live-data
metrics — the correct, expected consequence of the a priori `min_races=5` floor against the
genuinely small per-track sample sizes documented in section 3.0, not a defect. Sanity checks
(not gated, see the report): FVS-model independently reproduces the audit's known SS-
unpredictability finding (Drafting superspeedway family mean rho 0.042 vs 0.48-0.64 elsewhere);
K7 make-clustering shows a real same-make adjacency signal at Daytona/Talladega (index 0.95-1.36);
H5's contender exclusion moves TDS_core by 0.0002-0.0009 sec/lap at championship cells (negligible,
as predicted); PDI v1/v2 diverge (r=0.296), confirming v1's flagged coverage risk. No frozen spec,
`walkforward.py`, or `predict_next.py` touched; vendored `research/track_audit/` untouched. Full
detail: `report/TRACK_PROFILES.md`.
