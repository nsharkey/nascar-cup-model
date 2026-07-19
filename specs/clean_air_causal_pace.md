# SPEC: Clean-air pace via causal identification (roadmap #5) — pre-registered design

**Status:** pre-registered 2026-07-19 in plan session G1 (Fable 5, spec-only,
no production code). **None of this spec's input data exists yet:** the
silver lap/pit/flag tables it reads are designed
(`specs/medallion_architecture.md` §3.4) but unbuilt (C2 pending), no
Stage-A estimate has ever been computed, and no A/B variant has ever been
run. Every estimand, gate, threshold, and decision rule here precedes its
data by construction — that is the point.

**Freeze map** (per `specs/README.md` discipline):

- **FROZEN on commit:** §0 (execution gate), §1.3 (the prohibition list),
  §6 (Stage-A identification gate), §7 (Stage-B feature gate). Decision
  rules; editable only by the dated-amendment mechanism, and never after
  the data they adjudicate exists.
- **Stable design (amendable by dated note only until G2 starts):** §2–§5
  and §8 — operational definitions, constants (e.g. the 3.0 s gap
  threshold), and field-semantics assumptions marked ▸ pending Phase-0
  verification.
- The `## RESULT` blocks at the end are the designated write-points for
  G2's outcomes; §8's Phase-0 pins are observations recorded there, not
  amendments.

---

## 0. Execution gate (FROZEN)

This spec's execution (plan session G2) is **doubly gated**:

1. **Market gate.** G2 may begin only after
   `specs/market_benchmark_decision_rule.md` (with its amendments) returns
   **EDGE**. Its own words: "EDGE unlocks roadmap #5... NO-EDGE keeps #5
   permanently closed for this model family." **UNDERPOWERED does not
   unlock** — only EDGE does. If the benchmark never returns EDGE, this
   spec is banked and never executed. **That outcome is a success of the
   pre-registration exercise, not a failure** (project doctrine: designs
   are judged by rigor, not outcome; a banked design that correctly never
   ran cost nothing and proved the gate worked).
2. **Pipeline gate.** C2 (silver lap/pit/flag tables), D1 (gold features +
   re-proven engine), and D2 (consumers live) must be complete. G2 consumes
   the post-cutover path of record (medallion §7.1).

No part of Stage A or Stage B may be computed "just to peek" before both
gates open. Writing this spec involved no computation on any lap, pit, or
flag data (none of the silver tables exist).

No live capture is required: the pit, flag, and lap-notes feeds are
archived on cf.nascar.com for all seasons back to ≥2022 (probed
2026-07-18; recorded in `planning/aws_solutions.md`). The only ephemeral
feed (during-race `live-feed` snapshots) is not used by this design.

## 1. The causal question — and the dead end this must not repeat

### 1.1 Question

For each driver-race, estimate **clean-air pace**: the green-flag pace the
car/driver combination would run in free air, purged of traffic (dirty-air)
exposure. The current production signal, `pace_med85` (median of the best
85% of green-lap ratios to the per-lap field median), mixes underlying
speed with track-position luck: a fast car mired in traffic measures slow;
a mediocre car that cycles to the front measures fast.

Model it per usable lap `l` of driver `i`:

    r_i(l) = c_i + π · D_i(l) + ε_i(l)

where `r` is the lap-time ratio, `c_i` the driver-race clean-air pace (the
quantity wanted), `D_i(l)` ∈ [0,1] dirty-air exposure, and `π` ≥ 0 the
dirty-air penalty in ratio units. Recovering `c_i` requires `π` — and `π`
**cannot** be estimated by regressing lap time on track position, because
position is endogenous to speed.

### 1.2 Why the fixed-effects attempt died (report §7 — do not retry)

The audit built exactly the "confound-stripping" regression the old
strategy prescribed (`parse_lib.py` lines 61–105): per-race OLS of log
ratio on driver dummies + tire-age terms + running-position buckets
{P1, P2–5, P6–12, P13–25}. Fast cars run up front, so the position
coefficients absorbed real car speed and attenuated the driver effects.
Result: the adjusted pace was **worse standalone than the crude ratio**
(0.316 vs 0.364, p = 0.002) and added **exactly nothing** in the fitted
model (+0.000, p = 0.89). The audit's verdict stands: making this feature
work "requires causal identification (exploiting restarts and pit-cycle
shuffles as quasi-experiments), not more controls."

### 1.3 Prohibitions (FROZEN)

No analysis under this spec (or its successors on this feature) may:

1. Regress lap time on **contemporaneous** running position, gap, or any
   exposure measure using observational variation as if it were exogenous;
2. Jointly estimate per-race driver effects and position/exposure effects
   from the same confounded variation (the §1.2 design or any
   reparameterization of it — different buckets, splines, matching or
   reweighting on contemporaneous position included);
3. Renegotiate any §6/§7 threshold after the underlying estimate exists.

The permitted shape is: **pre-treatment state as controls, exposure moved
only by a §3/§4 natural experiment, penalty estimated from that variation
alone, then applied as a fixed correction** — estimate the physics first,
adjust second, never jointly.

### 1.4 What is different here — and the honest prior

The two strategies below get their exposure variation from mechanisms
plausibly unrelated to car speed (pit-crew execution noise; *other* cars'
fuel windows), not from where a car happens to run. The driver signal is
then reconstructed by subtracting a causally-estimated penalty, not by
fitting driver dummies against position controls.

Honest prior, recorded before any result: the crude aggregations already
*select toward* clean air (med85 keeps the best 85% of laps; `pace_best`
— the best 20%, literally the prior effort's "clean-air proxy" — **lost**
to med85 in the audit). The marginal value of a proper adjustment may
therefore be small even if identification succeeds, and the §7 adoption
margin (+0.005) is expected to be hard to clear. A well-identified π with
a no-adopt Stage B is a **documented success**: the penalty estimate
itself is an analytics asset (it feeds F3's empirical track profiles), and
the negative permanently closes a question.

## 2. Shared definitions (stable design; ▸ = Phase-0 pin required)

Scope everywhere: `series_id = 1`, `race_type_id = 1` (Cup points races),
seasons **2022+** — the Next Gen car's single aero regime, which is also
the verified archive floor for the pit/flag/notes feeds (recorded
decision: no mixing of aero eras; the backtest sample is 2022+ anyway).

- **Green lap** — lap classified green per `silver.lap_flags`
  (`flag_state` green convention, identical to `parse_lib`'s
  `FlagState == 1`). ▸ cross-check the numeric convention against
  `flag_events` on sample races.
- **Usable lap (i, l)** — green; ≥ 10 cars posted a valid (> 0) time on
  lap `l`; field median `m(l)` over those cars; ratio
  `r_i(l) = lap_time_i(l) / m(l)`. This is exactly the `pace_med85` lap
  universe — no new lap-selection rules.
- **Caution period** — contiguous non-green flag interval, from
  `silver.flag_events` (ordered transitions; primary). **Fallback** where
  a race's `flag_events` is empty/stub (observed upstream for
  `live-flag-data`): contiguous non-green lap blocks in
  `silver.lap_flags`. **Restart lap** = first green lap after the period.
- **Run** — maximal consecutive usable-lap sequence for a driver, broken
  by any non-green lap or a ratio > 1.20 (`parse_lib`'s run-break rule);
  within-run lap index `j` = 1, 2, ….
- **Elapsed clock** — `e_i(L) = Σ_{l ≤ L} lap_time_i(l)` (all laps, any
  flag; pit and caution laps carry true elapsed time so the cumulative
  sum is a valid race clock). A driver's clock is valid only while their
  lap_time series is complete and positive; from the first missing/≤ 0
  entry onward their gaps are undefined (counted in the build report).
  ▸ Phase-0 validation: computed elapsed must agree with
  `pit_stops.pit_in_race_time` and `flag_events.elapsed_time` (median
  absolute deviation < 1.0 s on sampled races), confirming all clocks
  share the green-flag origin.
- **Gap-ahead** at driver i's lap-L line crossing =
  `e_i(L) − max{ e_j(m) : e_j(m) < e_i(L), j ≠ i }` — the time since the
  car **physically ahead on the road** (any lap count — lapped/lapping
  traffic included by construction) last crossed the line. Measured once
  per lap at the line; mid-lap passes blur it (accepted measurement
  error, attenuates toward zero).
- **Dirty lap** — gap-ahead < **3.0 s**; else **clean**. (3.0 s is a
  deliberately generous outer bound on measurable aero disturbance at Cup
  speeds; sensitivity at 2.0 s and 4.0 s is reported as a §7 diagnostic,
  never a gate. The threshold is stable-amendable pre-G2 only — e.g. if
  F3's empirical track profiles measure wake effects first.)
- **Tire age** — green laps since the driver's last pit stop with ≥ 1 of
  the four `*_tire_changed` booleans true; laps since race start before
  any such stop.
- **n_tires** — count of true values among the four booleans on a stop.
- **Box time** — the crew-work duration of a stop: `pit_stop_duration`
  ▸ (Phase 0 confirms it measures box_stop → box_leave, i.e. excludes
  pit-road travel; else compute
  `box_leave_race_time − box_stop_race_time`). In/out travel durations
  are **driver skill and are never part of the instrument**.
- **Routine stop** — ▸ `pit_stop_type` in the routine vocabulary (pinned
  Phase 0; mechanism: exclude penalty/repair/damage-typed stops), AND the
  driver is not incident-implicated for that caution (§3), AND it is the
  driver's only stop during that caution period.

## 3. Strategy S1 — restart reshuffles instrumented by pit-box execution shocks

**Natural experiment.** After a caution, the running order is reset by the
caution-period pit cycle. Within the set of drivers making the same tire
call at the same moment, the order they emerge in is scrambled by pit-crew
execution variance — a stuck lug nut costs 5–10 spots — which is human
noise, not car speed. That displacement changes how much traffic the
driver faces in the following run.

- **Unit:** driver-restart (driver i, caution c) where i made exactly one
  routine stop during c.
- **Cell:** `(race_id, caution_id, n_tires)` with `n_tires ∈ {2, 4}`;
  cells with < 5 stops excluded; 0/1/3-tire stops and multi-stop drivers
  excluded (rare, strategy-confounded).
- **Incident screen:** any driver appearing in
  `silver.lap_notes.driver_ids` on a note with `lap_number` in
  `[caution start lap − 2, restart lap]` is excluded from that caution's
  units (a car with damage pits long AND runs slow — the direct
  confound). Deterministic ID-list membership; no text parsing.
- **Instrument (shock):** `z` = box time − cell median box time,
  winsorized at ±15 s.
- **Pre-treatment controls:** (a) pre-caution pace = mean ratio over the
  last ≤ 10 usable laps of the run preceding c (unit requires ≥ 3 such
  laps) — this makes the design effectively a gain-score; (b) pre-caution
  `running_pos` on the last green lap before c; (c) tire age at restart.
  All pre-treatment; controlling on them is not the §1.2 error, which
  conditioned on *contemporaneous* position.
- **Mediator (reported, not the instrument):** displacement = restart
  order (`running_pos` on the **final caution lap** — fixed before the
  green, so restart-launch/lane skill is excluded) − pre-caution position.
- **Treatment:** dirty-share = fraction of dirty laps among the unit's
  usable laps in the outcome window.
- **Outcome window:** the run following the restart, within-run laps
  `j = 3..15` (first 2 dropped as restart transient, matching
  `parse_lib`; capped at 15 because the field re-sorts toward pace over a
  long run, which would re-introduce exactly the endogeneity this design
  exists to avoid); unit requires ≥ 5 usable window laps.
- **Outcome:** mean ratio over window laps (ratios > 1.25 excluded —
  `parse_lib`'s trim).
- **Estimator:** 2SLS at unit level — outcome on dirty-share, instrumented
  by `z`, with cell fixed effects + the pre-treatment controls; standard
  errors clustered by race. **π̂_S1** = the dirty-share coefficient
  (ratio-unit clean↔dirty differential). First stage (`z` → dirty-share)
  and the mechanism stage (`z` → displacement) both reported.

**Identifying assumption (stated for the record):** conditional on cell
(same race, same caution, same tire call) and the pre-treatment controls,
residual box-time variation is crew execution noise, independent of the
car's potential lap times, and affects the outcome window only through
track position / dirty-air exposure (exclusion restriction).

**Threats to validity, each with its handling:**

| threat | handling |
|---|---|
| Tire strategy (2 vs 4) moves both position and grip | cells conditioned on n_tires; 0/1/3-tire excluded |
| Crash/damage cars pit long AND run slow | incident screen (lap_notes IDs) + routine-type filter + ±15 s winsor |
| Penalties (pass-throughs restart at rear regardless of stop speed) | excluded via `pit_stop_type` / flag-status vocabulary ▸ |
| Driver pit-road skill (entry/exit speed) contaminating the shock | shock is box time only; in/out travel durations excluded by construction |
| Restart launch / lane-choice skill | post position measured on the final caution lap, before any green-flag racing |
| Wave-arounds / lucky-dog cars (position set by rule, old tires) | not units (no routine single stop in c) — they merely shift others' order |
| Interference (one car's shock moves others' positions — SUTVA) | inherent to a field of ~36; second-order for an average-penalty estimand; disclosed, not fixed |
| Within-race correlation of shocks and outcomes | race-level clustering |

## 4. Strategy S2 — pit-cycle offset windows (green-flag cycles)

**Natural experiment.** During green-flag pit cycles, a driver's proximate
traffic changes because **other** cars pit (or because their own staggered
strategy leaves them out alone) — timing set by fuel windows largely fixed
before the race, not by the driver's within-run pace trajectory. A
mid-pack car can spend 10+ laps effectively alone on track.

- **Event:** (a) the car physically ahead of i (the gap-ahead source car)
  enters the pits under green → a dirty→clean transition for i; (b) i
  exits the pits under green into clear or dirty air. **Only pit-caused
  transitions are events.** Gradual gap changes (closing on a car ahead,
  being caught) are excluded — that is where reverse causation lives: a
  car enters dirty air *because* it is running fast.
- **Window:** event lap ± 6 green laps (within the run(s) either side of
  the event; an exit event starts a new run).
- **Sample:** window laps (usable, ratio ≤ 1.25) of driver-runs containing
  ≥ 1 event, in races with pit data.
- **Estimator:** OLS of ratio on the dirty indicator + within-run lap
  index `j` and `j²` (the combined tire-wear/fuel-burn trend — the two are
  collinear within a run and are controlled as one), with driver-run fixed
  effects; clustered by race. **π̂_S2** = the dirty coefficient.
- **Pre-trend placebo (consumed by §6):** among dirty laps in the 4 laps
  before dirty→clean events, regress ratio on laps-until-event; a
  significant slope (two-sided p ≤ 0.05) means the driver was already
  speeding up before the car ahead pitted — closing-speed contamination —
  and S2 fails.

**Identifying assumption:** within a driver-run, conditional on the smooth
lap-index trend, the *timing* of pit-caused exposure transitions (other
cars' fuel windows) is independent of the driver's potential lap times at
those laps.

**Threats:** pace management when alone (drivers save tires in clear air →
biases π̂_S2 **downward**; S2 is the conservative strategy and one reason
S1 is primary); blue-flag behavior around lapped traffic; measurement
error in the binary dirty classification (attenuation). All disclosed;
none correctable within S2.

## 5. Data dependencies (exact; per medallion §3.4 — none of it built yet)

Everything below carries `(series_id, race_id)`. Join keys as listed.

| table | columns used | role | joined on |
|---|---|---|---|
| `silver.laps` | driver_id, lap, lap_time, running_pos | ratios, runs, elapsed clock, gap-ahead, positions | (series_id, race_id, driver_id, lap) |
| `silver.lap_flags` | lap (via laps_completed), flag_state | green classification; caution-block fallback | (series_id, race_id, lap) |
| `silver.flag_events` | event_seq, flag_state, lap_number, elapsed_time, comment, beneficiary | caution/restart timing (primary); elapsed cross-check | (series_id, race_id), ordered by event_seq |
| `silver.pit_stops` | stop_seq, driver_id, lap_count, pit_in/out_race_time, box_stop/box_leave_race_time, pit_stop_duration, total_duration, in/out_travel_duration, pit_in_flag_status, pit_stop_type, positions_gained_lost, pit_in/out_rank, 4× *_tire_changed | stops, shocks, tire age, caution-stop classification | (series_id, race_id, driver_id); stop located by lap_count + race times |
| `silver.lap_notes` | lap_number, note_id, flag_state, driver_ids | S1 incident screen | (series_id, race_id, lap_number) |
| `silver.races` | race_id, year, race_date, track_name, race_type_id, actual_laps, number_of_cautions | scope + track → ttype | (series_id, race_id) |
| `silver.driver_race` | driver_id, finish, start, pace_med85, nlaps | baseline pace + `has_pace` eligibility source; labels | (series_id, race_id, driver_id) |
| `gold.track_typology` | track_name → ttype | penalty pooling classes | track_name |
| `gold.wf_features` | full bank | Stage-B baseline replay surface | (race_id, driver_id) |

**Penalty pooling:** π̂ estimated separately per ttype ∈ {SHORT, INT,
ROAD}; UNIQ/OTHER races consume the pooled non-SS estimate; **SS races are
never adjusted** (pack-racing aero regime makes the clean/dirty dichotomy
meaningless there, and doctrine stands down at SS regardless) — variants'
feature values at SS races equal baseline.

**Known-imperfect inputs, handled:** `pit_stops.driver_id` may be NULL
(§3.4's resolution can fail; medallion ambiguity A4) — NULL-driver stops
are unusable; a race with > 20% unresolved caution-stop rows is excluded
from S1 (counted). Empty/stub `flag_events` → lap_flags fallback (§2).
Incomplete lap_time series → driver's gaps undefined from that lap
(counted).

**Not yet available — the design assumes it exists post-C2:** every silver
table above (C2), gold (D1), the per-feed coverage floors
(`BRONZE_COVERAGE.md`, B3). The pit/flag/notes feeds were probe-verified
to ≥ 2022; early B2 running observations suggest part of 2022 may be
structurally absent for detailed feeds — the floor is whatever B3 records.
Field semantics marked ▸ (duration fields, type/flag vocabularies, lap
numbering, clock origin) are unknown until the data exists; §8 Phase 0
pins them before any estimate.

**Coverage precondition:** `pit_stops` + (`flag_events` or usable
`lap_flags`) present for ≥ 90% of 2022+ non-SS Cup points races. If not
met, G2 stops at Phase 0 with a coverage report; proceeding on reduced
coverage requires a dated owner note (flagged, non-blocking; the era
window stays 2022+ regardless — no re-choosing the sample).

## 6. Stage-A identification gate (FROZEN)

Estimated **once, at G2, on the full available sample** (non-SS Cup points
races in the coverage window). The gate adjudicates whether identification
exists — a physics measurement, not a forecasting feature; Stage B's
walk-forward π̂ series (§7) is separate machinery using the same
estimator.

**S1 passes iff ALL of:**

| # | condition | threshold |
|---|---|---|
| 1 | first-stage strength, z → dirty-share (cluster-robust F, race clusters) | F ≥ 10 |
| 2 | penalty sign & significance | π̂_S1 > 0, one-sided cluster-robust p ≤ 0.05 |
| 3 | physical plausibility | π̂_S1 ≤ 0.05 ratio units |
| 4 | placebo: pre-caution pace regressed on z (same cells/controls minus the pre-pace control) | two-sided p > 0.05 **AND** \|β_placebo\| ≤ 0.5 × \|reduced-form effect of z on the outcome\| |
| 5 | sample floor | ≥ 2,000 units across ≥ 60 races |

**S2 passes iff ALL of:**

| # | condition | threshold |
|---|---|---|
| 1 | penalty sign & significance | π̂_S2 > 0, one-sided cluster-robust p ≤ 0.05 |
| 2 | physical plausibility | π̂_S2 ≤ 0.05 ratio units |
| 3 | pre-trend placebo (§4) | two-sided p > 0.05 |
| 4 | sample floor | ≥ 500 event windows across ≥ 40 races |

(The placebo magnitude clause in S1 #4 exists because a p > 0.05 pass
alone is free at low power; the pre-registered pass requires the point
estimate to be genuinely small, not merely noisy.)

**Verdicts:**

- **Both fail → NO-IDENTIFICATION (terminal).** Record the RESULT block;
  G2 ends; **no Stage-B variant may be built or tested under this spec**
  — including V3, whose classifier is only validated by a positive π.
  Roadmap #5 closes for this model family unless a future spec
  pre-registers a *different* identification strategy, with its own gates
  committed before its own analyses run; nothing may be re-tested against
  this spec's thresholds. A documented NO-IDENTIFICATION is a valid,
  successful outcome.
- **≥ 1 passes → Stage B proceeds.** Primary strategy for π̂: **S1 if S1
  passed, else S2** (recorded a priori: S1 has the larger sample and the
  sharper exclusion argument). Cross-strategy agreement (sign;
  |π̂_S1 − π̂_S2|) is reported as a diagnostic, never a gate.
- Per-ttype estimates are Stage-B machinery (§7); this gate is evaluated
  on the pooled non-SS sample.

## 7. Stage-B feature gate (FROZEN) — walk-forward A/B vs the frozen config

Form follows `specs/dnf_status_feature.md` including the lessons of its
amendments (explicit config assertions, namespaced feature columns,
recorded absolute anchors). The A/B lives in its own script; frozen model
files are untouched unless a variant wins (§7 adoption).

### 7.1 Feature construction

- **pace_clean(i, r)** = the med85 aggregation — identical mechanics to
  baseline: ratios sorted ascending, `k85 = max(3, int(n·0.85))`, median
  of the first k85; NULL iff < 15 usable laps (the lap universe is
  identical to `pace_med85`'s, so the NULL pattern matches baseline
  exactly) — over **adjusted** ratios
  `r′ = r − π̂_tt(r) · dirty(lap)`.
- **π̂_tt(r)** (walk-forward, "as-of-completion"): estimated by the
  §6-passing primary strategy's estimator, verbatim, on Stage-A-usable
  races **strictly before race r** — per-ttype if that ttype has ≥ 30
  prior usable races, else pooled non-SS if ≥ 30 exist, else **race r is
  inactive**: `pace_clean(·, r) := pace_med85(·, r)`. Each race's value is
  computed once, when it completes, and never revised (matches weekly
  production semantics). SS races always inactive.
- **pace_clean_sel(i, r)** (V3's selection version) = med85 over the
  **clean** usable laps only; NULL if < 15 clean usable laps. Activation
  follows the same ≥ 30-prior-races rule (V3 needs no π̂, but a shared
  activation rule keeps the active-race sets aligned across variants);
  inactive races use the baseline value.

### 7.2 Variants (exactly three; no others may be tested under this spec)

The pace history bank (`hp` in the engine: past races' pace values,
half-life 8, subsequence-indexed) is the only thing a variant changes.
Target-race eligibility (`has_pace`, burn, min_hist, min_drv) is **always
computed from baseline `pace_med85` presence, for every variant** — the
scored race set and driver sets are identical by construction (the
DNF-spec V2 trap, killed the same way).

- **V1 `cpace-replace`:** histories append `pace_clean` instead of
  `pace_med85`. Features stay `[fin, pace, typed, start]`.
- **V2 `cpace-add`:** baseline histories untouched; a second bank appends
  `pace_clean`; features `[fin, pace, typed, start, cpace]`.
- **V3 `sel-replace`:** histories append `pace_clean_sel` (NULL → the
  engine's znan → 0 handling, as anywhere else). Features unchanged.

### 7.3 Protocol

1. Runs on the path of record at execution time (post-cutover: gold/D1
   engine surface), using the same replay-copy mechanism as the DNF A/B
   (its §3.2): the step script carries its own copy of the run loop,
   clearly marked, extended with the variant banks; `walkforward.py` is
   not edited.
2. All config assertions from the DNF spec's hardened baseline-gate
   amendment apply verbatim (years = all present, typology = MY_TYPE,
   typed_mode = shrinkage, asserted at runtime).
3. **Baseline replication gate:** base = the production frozen config at
   G2 execution time. Its year ≤ 2025 scored mean ρ must be within ±0.003
   of the recorded reference, and the year ≤ 2025 scored count must equal
   the reference count. Reference chain (pre-registered): 0.4130 / n = 108
   if no A/B has been adopted before G2; otherwise the year ≤ 2025 anchor
   recorded in the most recently adopted spec's RESULT block (the DNF
   spec's absolute-anchors amendment exists to supply exactly this).
   Failure ⇒ STOP; no variant result counts.

### 7.4 Decision rule

Per variant v: paired per-race `d_i = ρ_v,i − ρ_base,i` over all scored
races (identical sets by construction). **Active race** := a scored race
where v's feature bank differs from baseline for ≥ 1 eligible driver (the
walk-forward π̂ ramp-in forces the earliest races inactive with `d_i = 0`
exactly; a margin over all races would be diluted by construction — a
deliberate, pre-registered deviation from the DNF-spec form, recorded here
with its reason).

**Adopt v iff ALL of:**

1. one-sided Wilcoxon signed-rank (`alternative='greater'`, default
   zero-handling) p ≤ **0.0167** (Bonferroni 0.05/3);
2. mean(d) over **active** races ≥ **+0.005**;
3. mean(d) over **all** scored races > 0;
4. ≥ **50** active scored races (else the variant cannot be adopted,
   whatever the p-value — insufficient active sample).

At most one variant is adopted: highest active-race mean(d) wins; exact
tie at 4 decimals → priority **V1 > V3 > V2** (recorded a priori: fewest
features first, adjustment over selection because it uses every lap).

**If none pass: the answer is no.** Record the RESULT, mark roadmap #5
done-with-negative-result, and do NOT re-try tweaked definitions (other
gap thresholds, dose curves, windows, aggregations…) under this spec — any
successor variant requires a new pre-registered spec committed before it
is run.

**Diagnostics (reported, never gates):** standalone walk-forward Spearman
of a cpace-only spec vs a pace-only spec (the audit-§7 comparison the FE
version lost 0.316 vs 0.364); mean(d) by ttype, non-SS subset, 2026+
subset; π̂ per ttype with CIs; descriptive position-bucket dose curve;
gap-threshold sensitivity (2.0 / 4.0 s); final fitted weights; 4,000-
resample bootstrap CI of mean(d) (np seed 7).

### 7.5 Adoption procedure (only if a variant wins)

Mirrors the DNF spec §7, in its own commit after the RESULT is recorded:
`walkforward.py` untouched (audit record); `predict_next.py` extended with
the winning variant's exact definitions; config_version bump + variant
name in the prediction JSON config block; HANDOFF frozen-config paragraph
updated with the evidence; the market benchmark continues
intention-to-treat (its §2) — nothing restarted, no sealed prediction
regenerated.

## 8. G2 execution protocol (order is mandatory)

**Phase 0 — semantics and plumbing (before ANY estimate):**

1. Coverage precondition check (§5).
2. Pin every ▸ item: `pit_stop_duration` semantics/units vs the
   box_stop/box_leave timestamps; `pit_stop_type` vocabulary → the
   routine set; `pit_in_flag_status` vocabulary → caution-stop
   classification; green `flag_state` convention cross-check; elapsed-
   clock validation (median |Δ| < 1.0 s vs pit and flag timestamps).
   Record all pins in the RESULT preamble **before Stage A runs**. Pins
   are observations at designated write-points, not amendments. If a pin
   structurally contradicts a §2–§5 assumption (e.g. no field isolates
   box time), STOP and flag the owner — resolving it is a dated
   amendment, made while Stage-A results still do not exist.
3. Build the derived frames (runs, gaps, cells, events); print inventory
   counts (units, cells, events, exclusions by reason).

**Phase 1 — Stage A** → §6 verdict. STOP here on NO-IDENTIFICATION.

**Phase 2 — Stage B** → §7 verdict → RESULT; adoption (if any) only after
the RESULT is committed.

Scripts (repo step-script convention): `src/step8_clean_air.py` (Phases
0–1), `src/step8_clean_air_ab.py` (Phase 2). Compute is trivial (OLS/2SLS
on ≤ ~10⁵ rows; ~150 cheap expanding-window refits; one replay pass with
4 specs — minutes on a laptop). Session tier per plan: Sonnet 5, thinking
on, xhigh.

## 9. Resolved-ambiguity register (decisions made now, with reasons)

- **2022+ era scope** — Next Gen single aero regime; equals the verified
  pit/flag/notes archive floor; equals the backtest sample. Never widened
  or narrowed post-hoc.
- **Binary dirty at 3.0 s gap, not a position-dose curve** — power and
  interpretability; the dose curve is descriptive only. Threshold
  stable-amendable pre-G2 only.
- **Gap-ahead via pooled line-crossing clocks** — gives physical
  on-road proximity (lapped traffic included) from `silver.laps` alone.
- **Shock = box time only** — in/out travel is driver skill; including it
  would break the exclusion restriction by construction.
- **Cells keyed on n_tires ∈ {2,4}; 0/1/3-tire, multi-stop, and stay-out
  drivers are not S1 units** — small, strategy-confounded groups; the
  experiment only needs the shocked subset, not the whole field.
- **Restart order measured on the final caution lap** — excludes
  restart-launch/lane skill from the displacement mediator.
- **Outcome window j = 3..15** — first 2 laps are the parse_lib restart
  transient; beyond ~15 the field re-sorts toward pace and exposure stops
  being restart-order-driven (the §1.2 endogeneity would leak back in).
- **Placebo pass requires small magnitude, not just p > 0.05** — a
  low-power placebo must not pass for free.
- **Stage-A gate on the full sample; Stage-B π̂ strictly walk-forward** —
  the gate measures whether the physics is identified; the feature must
  be causal race-by-race. Both use the same estimator verbatim (no
  estimator shopping between stages).
- **As-of-completion adjustment** (race r adjusted with π̂ from races
  < r, computed once, never revised) — matches weekly production
  semantics and keeps the feature bank incremental.
- **Shared activation rule across variants, including V3** — aligned
  active-race sets make the §7.4 margins comparable across variants.
- **Eligibility always from baseline pace presence** — identical scored
  sets; the paired test is broken by construction otherwise.
- **UNIQ/OTHER → pooled non-SS π̂; SS never adjusted** — no ttype-level
  estimate exists for UNIQ by definition; SS is a different aero sport
  and a doctrine stand-down.
- **V-priority V1 > V3 > V2 on exact tie** — fewest features first;
  adjustment over selection (uses every lap).
- **Prohibition list (§1.3) frozen** — report §7's dead end must be
  structurally unrepeatable, not just discouraged.

## Flagged genuine ambiguities (owner-visible; none block banking the spec)

- **F-A.** `pit_stop_duration` vs `total_duration` semantics are unknown
  until the data exists. The box-time *concept* is pinned; the field
  mapping is Phase 0. If no field or timestamp pair isolates box time,
  S1's shock needs a dated pre-Stage-A amendment (fallback candidate:
  `total_duration − in_travel_duration − out_travel_duration`).
- **F-B.** `pit_stop_type` / `pit_in_flag_status` vocabularies are
  unknown; the routine-stop filter is mechanism-pinned, vocabulary
  Phase 0.
- **F-C.** `flag_events` stub prevalence is unknown (one 2024 stub
  observed upstream). The lap_flags fallback gives lap-resolution (not
  time-resolution) caution boundaries; acceptable for S1, noted.
- **F-D.** The pit/flag coverage floor may land mid-2022 (early B2
  observations suggest part of 2022 is structurally absent for detailed
  feeds). B3's `BRONZE_COVERAGE.md` adjudicates; the §5 precondition and
  the fixed 2022+ era window handle either outcome without re-choice.
- **F-E.** The 3.0 s dirty threshold is a physics judgment made without
  our own measurement (none exists yet). It is stable-amendable pre-G2
  by dated note (e.g. off F3's track profiles); once G2 starts it is
  fixed, with the 2.0/4.0 s sensitivities reported as diagnostics.

---

## RESULT — Phase 0 pins (to be filled by G2, before Stage A)

*(designated write-point; empty until G2 runs)*

## RESULT — Stage A (to be filled by G2)

*(designated write-point: sample counts and exclusion inventory; S1
F-stats, π̂_S1 + CI, placebo stats; S2 π̂_S2 + CI, pre-trend stats;
per-condition PASS/FAIL tables; verdict per §6; commit hash)*

## RESULT — Stage B (to be filled by G2)

*(designated write-point: baseline anchor + replication-gate value;
per-variant table — active count, mean(d) active/all, Wilcoxon p, CI,
diagnostics; verdict per §7.4; adoption record if any; commit hash)*
