# SPEC: Driver loop-metric histories — in-house loop data (F13)

**Status:** pre-registered 2026-07-20, before any metric has been computed.
**Derivation source (execution contract):** `research/external_knowledge_scan.md`
§6.1 (loop data) is authoritative for *what* to build and *why* it's
derivable in-house; §7 items 1–3 (same-race Driver Rating is circular by
construction, all loop whole-race metrics are same-race outcomes not
pre-race signals, ARP has ≥3 circulating definitions with no accessible
official glossary) are this session's binding leakage/circularity
constraints. `specs/track_profiles.md` §1.7 (F3's already-pinned
loop-metric-adjacent definitions) is authoritative for green-flag lap and
pass — imported verbatim below, not re-derived.

**Governance (restated, binding):** nothing computed here enters the frozen
PL prediction model without its own later pre-registered, walk-forward-gated
A/B. This session builds analytics/reference tables only. `walkforward.py`,
`predict_next.py`, and `gold_build.py` are not touched, and nothing here is
ever joined into `gold.wf_features`.

**Tier:** Analytics/reference (phase F's own note: "Analytics and reference
sessions (F3/F4/F13/F14/F19) never touch the frozen model"). No gated A/B,
no `>=8`-scored-races gate.

**Scope:** Cup only (`series_id=1`, `race_type_id=1`), every race with at
least one `flag_state=1` row in `silver.lap_flags` — this is a natural data
floor (the lap-times feed, per B2, exists from 2020+; 2017–2019 races simply
produce zero qualifying rows here, no manual year filter needed). Driver
grain, not track grain — complementary to F3, not a duplicate of it.

---

## 1. Imported machinery (frozen elsewhere; not re-chosen here)

Per `specs/track_profiles.md` §1.7 and this session's own overlap guard,
the following are **imported verbatim by calling `track_profiles_build.py`'s
own functions**, not re-implemented:

- **Green-flag lap** := `silver.lap_flags.flag_state = 1` at that
  `laps_completed` value, joined to `silver.laps.lap` within
  `(series_id, race_id)` — `parse_lib.py`'s own convention, reused via the
  same `lf.laps_completed = la.lap AND lf.flag_state = 1` join predicate
  used throughout `track_profiles_build.py`.
- **Pass** (a driver-lap position gain) := on two consecutive green-flag
  laps `L, L+1` for driver `d`, `running_pos(d, L+1) < running_pos(d, L)`.
  Contiguity (no caution/pit gap between `L` and `L+1`) is required —
  `track_profiles_build._green_stretches` is imported and reused directly
  to split each driver's green-flag lap sequence into maximal
  consecutive-lap stretches before any pass is counted, exactly as PDI/RVS
  already do.

**Not imported (no overlap — disclosed, not an oversight):**

- **Durable pass** (F3's PDI-v2 concept: a pass held for 5 subsequent green
  laps) is not used by any of this session's six components. NASCAR's own
  public "Quality Passes" definition has no durability requirement (§2.2
  below) — durability is a track-difficulty-proxy choice F3 made for its
  own metric, not part of the public loop-stat definitions this session
  reproduces. Using it here would be re-purposing an F3 engineering choice
  as if it were an external definition, which it isn't.
- **Restart** is not used — none of this session's six components are
  restart-conditioned (closers is defined against the race's own green-flag
  lap count, §2.6, not against restart events).

---

## 2. Metric definitions (this session's own pre-registered choices)

All six are computed once per `(driver_id, race_id)` from `silver.laps` +
`silver.lap_flags` (Cup, green-flag laps only — §7 item 2's trap: every
value below is a **same-race** descriptive fact; only the AS-OF history in
§3 is ever legitimate as a pre-race signal).

**Shared denominator convention:** every *rate* metric below (quality-pass
rate, fastest-lap share, laps-in-top-15 rate) divides by
`n_green_race` = the race's own total count of distinct green-flag lap
values (`count(*)` from `silver.lap_flags` where `flag_state=1`, that
`race_id`) — **not** by the driver's own lap count. One consistent
denominator avoids inventing two different normalization rules across three
near-identical "count of laps satisfying X" metrics. Pass differential and
closers are kept as **raw per-race counts**, matching NASCAR's own public
convention for these two stats (neither is publicly reported as a rate
either) — an explicit, disclosed asymmetry, not an inconsistency.

A driver-race's whole row is `NULL` on every field below except `closers`
if that driver has **zero** green-flag lap rows that race (e.g., collected
in a pre-green incident). `closers` has its own, narrower nullability rule
(§2.6).

### 2.1 Average Running Position (ARP) — **pin one of three; frozen**

Public sources circulate three definitions with no accessible official
glossary (scan §7 item 3): **all-laps**, **green-flag-only**, and
**lead-lap-only**. This spec pins:

> **ARP := mean(`running_pos`) over the driver's own green-flag laps that
> race (§1's imported definition).**

Reasoning (disclosed per-choice, as `specs/README.md` requires):

- **Lead-lap-only is rejected as not cleanly computable from archived
  data.** `silver.laps` carries no lead-lap/laps-down flag per row,
  and inferring "on the lead lap at lap L" from the shared `lap` counter
  would require a cross-referenced proxy (comparing a driver's own lap
  count to the leader's at the "same" point in time) that is not verified
  against ground truth anywhere in this pipeline — the same category of
  risk F3 explicitly avoided when it rejected an unverified cross-feed
  time-window assumption for RVS's pit-cycle screen (`track_profiles.md`
  AMENDMENT, 2026-07-20). Inventing an unverified proxy here would repeat
  exactly the mistake F3's own amendment exists to warn against.
- **All-laps is rejected because it doesn't correct for caution-lap
  bunching** (single/double-file restart artifacts inflate or compress
  `running_pos` spread in ways unrelated to green-flag racecraft) —
  exactly the noise green-flag-only screens out, and the same noise every
  other component in this spec is already scoped to exclude.
- **Green-flag-only is pinned**: it reuses machinery F3 already froze and
  verified (§1), needs no new proxy, and keeps every one of this session's
  six components on one consistent green-flag-only scope.

### 2.2 Quality passes

A **pass** (§1) where the position *after* the pass
(`running_pos(d, L+1)`) is `<= 15` — NASCAR's own public "Quality Passes"
definition ("green flag pass performed on a car running in the top 15"),
no durability requirement (§1's "not imported" note). Reported as a raw
count (`quality_passes`) and a rate (`quality_pass_rate =
quality_passes / n_green_race`).

### 2.3 Green-flag pass differential

`pass_diff := passes_made − times_passed`, both counted via §1's pass
definition applied within each contiguous green-flag stretch (a driver is
"passed" at `L → L+1` when `running_pos(d, L+1) > running_pos(d, L)`).
Raw per-race count (§2's denominator note).

### 2.4 Fastest-lap share

For each green-flag lap value `L` in a race, the driver(s) with the
minimum `lap_time` among all drivers' rows at `(race_id, L)` are credited
one "fastest lap" for that `L`. **Tie rule (disclosed, deterministic):**
if multiple drivers are tied at the exact minimum for a given `L`, all are
credited — ties are not expected to occur at floating-point-recorded lap
times in practice, but the rule is pinned rather than left implicit.
Reported as a raw count (`fastest_laps`) and a rate (`fastest_lap_share =
fastest_laps / n_green_race`). Sourced from the same lap-time rows
`track_profiles_build._green_laps_by_driver` already extracts (reused
directly, not re-queried).

### 2.5 Laps in top 15

Count of the driver's own green-flag laps with `running_pos <= 15`
(`laps_top15`), and rate `laps_top15_rate = laps_top15 / n_green_race`.

### 2.6 Closers

Positions gained in the final 10% of the race's green-flag laps (by
count, NOT by real-race-time — consistent with every other component here
being lap-indexed rather than time-indexed).

Let `G` = the race's sorted distinct green-flag `laps_completed` values
(from `silver.lap_flags`, `flag_state=1`). Let
`L_start = G[floor(0.9 * len(G))]` and `L_end = G[-1]` (the window is the
final `ceil(10%)` of the race's own green-flag laps by count).

For driver `d`: `pos_start` = `running_pos` at `d`'s own green-flag-lap row
with the smallest `lap >= L_start`; `pos_end` = `running_pos` at `d`'s own
green-flag-lap row with the largest `lap` (their last recorded green-flag
lap of the race — at or before `L_end` by construction, since `L_end` is
the race's own final green-flag lap).

`closers := pos_start − pos_end` (positive = positions gained during the
window). **Nullability:** if driver `d` has no green-flag-lap row with
`lap >= L_start` (they retired before the closing window began), `closers`
is `NULL` for that race — there is nothing in the window to measure. This
is the one component whose nullability is independent of the "zero
green-flag laps at all" rule that gates every other field.

---

## 3. AS-OF driver histories (the deliverable; §7 item 2's trap)

Every value in §2 is a **same-race outcome** — legitimate only as a
strictly-prior history, exactly like `fin`/`pace` in the frozen model
today (scan §7 item 2). `gold.driver_loop_history` therefore carries, for
every `(driver_id, race_id)` in scope, the recency-weighted average of
that driver's own §2 values from **strictly prior** qualifying races only
(`prior.race_seq < target.race_seq`, never `<=`) — mirroring
`gold_build.py`'s `WF_FEATURES_SQL` `prior_pairs` pattern exactly (same
`p.race_seq < t.race_seq` self-join shape, same "rank within the filtered
subsequence, not within all prior races" discipline that
`gold_build.py`'s own docstring calls "the classic transcription bug").

**`race_seq`** here is a single **global** ordinal across every in-scope
race (`row_number() OVER (ORDER BY race_date, race_id)`), not
per-track — driver-history grain has no track dimension to key off, unlike
F3's `(track_id, era_key)` grain.

**Half-life:** reuses the frozen production half-life (**8** races,
`HANDOFF.md`'s frozen config / `gold_build.py`'s `HALF_LIFE`) for the
recency weight `pow(0.5, rk / 8)`. This is a reuse of an already-established
constant, not a new tuned parameter — there is no evidence basis in this
Tier-A session to justify inventing a different decay rate, and reusing the
frozen one keeps the history philosophy consistent with every other as-of
aggregate already in this codebase.

**Two independent subsequences** (mirroring `fin_agg` vs `pace_agg` in
`gold_build.py`):

- `arp_h, pass_diff_h, quality_pass_rate_h, fastest_lap_share_h,
  laps_top15_rate_h` — all five are `NULL` together exactly when the
  driver's prior race had zero green-flag laps (§2's shared rule), so they
  share one subsequence, one `rk`, one `n_hist`.
- `closers_h` — its own subsequence (only prior races where that driver's
  own `closers` was non-`NULL`, §2.6), its own `rk`, its own
  `n_hist_closers`.

### 3.1 Self-built composite (replaces NASCAR's Driver Rating)

NASCAR's own Driver Rating is **not imported**: finish and win are direct
formula inputs (scan §6.1), making any same-race use circular by
construction, and even a *lagged* history of it would inherit an opaque,
single-secondarily-sourced arithmetic this project has no way to verify
(scan §6.1: "exact arithmetic ... is single-secondary-sourced"). Per the
derivation doc's own recommendation, a self-built composite from this
session's own six AS-OF components supersedes it:

For each row of `gold.driver_loop_history`, compute the cross-sectional
z-score of each of the six `_h` columns **within that `race_id`** (i.e.,
across every driver who has a row for that race), sign-flipping `arp_h`
(lower ARP is better, everything else higher-is-better):

```
z(x) = (x - mean(x over drivers in this race_id)) / stddev(x over drivers in this race_id)
composite_h = mean(z(-arp_h), z(pass_diff_h), z(quality_pass_rate_h),
                    z(fastest_lap_share_h), z(laps_top15_rate_h), z(closers_h))
```

**Nullability (disclosed, deterministic, no invented threshold):**
`composite_h` requires **all six** `_h` components to be non-`NULL` for
that row; otherwise `composite_h` is `NULL`. A partial-component average
would need its own minimum-count threshold (e.g. "at least 4 of 6") with
no evidence basis to justify picking one number over another in a Tier-A
session — requiring all six avoids inventing that constant. Per-`race_id`
z-scoring additionally requires `stddev > 0` and `>= 2` drivers with a
non-`NULL` value for that specific component in that race; otherwise that
component's `z` is `NULL` for everyone in that race (propagating to
`composite_h = NULL` under the all-six rule above).

---

## 4. Output schema

### 4.1 `gold.driver_loop_race` (raw, same-race — internal/audit table)

One row per `(driver_id, race_id)` in scope. Columns: `driver_id, race_id,
race_seq, n_green_race, green_flag_laps, arp, passes_made, times_passed,
pass_diff, quality_passes, quality_pass_rate, fastest_laps,
fastest_lap_share, laps_top15, laps_top15_rate, closers`.

This table is **same-race** (§2) and exists only as the auditable raw
material §3's history is built from — it is never itself a candidate
pre-race signal and is not the session's headline deliverable.

### 4.2 `gold.driver_loop_history` (AS-OF — the deliverable)

One row per `(driver_id, race_id)` for every race where that driver has at
least one strictly-prior qualifying race. Columns: `driver_id, race_id,
race_seq, n_hist, arp_h, pass_diff_h, quality_pass_rate_h,
fastest_lap_share_h, laps_top15_rate_h, n_hist_closers, closers_h,
composite_h`. Provenance: `built_at`.

---

## 5. Build-graph isolation gate (frozen; mirrors F3 §5 / F4 §6)

`gate_loop_metrics.py` asserts, on every run:

1. Both output tables exist and are internally consistent (no duplicate
   `(driver_id, race_id)` rows in either table; every `driver_id` in
   `gold.driver_loop_history` known to `silver.driver_race`/`silver.laps`).
2. **Isolation**: neither `driver_loop_race` nor `driver_loop_history`
   appears anywhere in `src/gold_build.py`, `src/walkforward.py`, or
   `src/predict_next.py` (source-text scan, mirroring F3/F4's check
   exactly — the frozen model's build graph must never reference this
   session's tables).
3. **Imported-machinery source-scan**: `loop_metrics_build.py` imports
   `_green_stretches` and `_green_laps_by_driver` from
   `track_profiles_build` rather than reimplementing them (a lightweight
   source-scan, same spirit as F3/F4's frozen-engine-replay checks) — this
   is the mechanical proof that §1's "imported verbatim, not re-chosen"
   claim is actually true in code, not just in prose.
4. **AS-OF strictly-prior re-derivation spot-check**: for a sample of
   `gold.driver_loop_history` rows, recomputing the history using only
   `gold.driver_loop_race` rows with strictly smaller `race_seq` for that
   driver reproduces every stored `_h` column and `n_hist`/`n_hist_closers`
   exactly (same idiom as F3's asof check / F4's residual re-derivation
   check).
5. **Closers nullability check**: every `closers` value in
   `gold.driver_loop_race` for a driver whose maximum green-flag lap is
   `< L_start` for that race is `NULL` (proves §2.6's rule is applied, not
   merely computed) — mirrors F3's `below_floor` proof-of-application
   idiom.
6. **Composite re-derivation spot-check**: for a sample of rows with
   non-`NULL` `composite_h`, recomputing the six per-race-id z-scores from
   the stored `_h` columns and averaging reproduces the stored
   `composite_h` exactly.

---

## 6. Implementation checklist

1. `src/loop_metrics_build.py` (new module) — imports
   `track_profiles_build` for `_green_stretches`/`_green_laps_by_driver`
   and `warehouse` for the DB connection, same style as
   `track_similarity_build.py` importing `track_profiles_build as tpb`.
2. Build order: (a) `loop_scope_races` (global `race_seq`, §3); (b) §2's
   per-`(driver_id, race_id)` raw extraction → `gold.driver_loop_race`;
   (c) §3's AS-OF aggregation (two subsequences) → `gold.driver_loop_history`
   (without `composite_h`); (d) §3.1's composite pass (cross-sectional
   z-score per `race_id`) added to `gold.driver_loop_history`; (e) write
   both tables to `data/gold/driver_loop_race.parquet` /
   `driver_loop_history.parquet`, register as `gold.*` views in
   `warehouse.py` (same rebuildable-from-disk pattern as every other gold
   table).
3. `src/gate_loop_metrics.py` — §5's six checks.
4. `report/LOOP_METRIC_HISTORIES.md` — row counts, ARP-definition
   rationale recap, composite distribution sanity (mean ≈ 0 by
   z-score construction), a handful of named-driver sanity spot-checks.
5. Extend `DATA_DICTIONARY.md` (new §10g) and `warehouse.py`'s gold-table
   view loop; add gate 17 to `GATES.md` and `run_gates.sh`.
6. Update `plan/schedule.yml` (F13 → done; promote F14 to `next` per phase
   F's own enumerated order F3/F4/F13/F14/F19) and re-render via
   `python src/report_plan.py`.
7. Run the full gate surface (`src/run_gates.sh`) — must stay 17/17 green
   (16 existing + this session's new `gate_loop_metrics.py`).

---

## RESULT — F13
