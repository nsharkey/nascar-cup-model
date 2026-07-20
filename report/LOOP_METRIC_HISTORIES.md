# Driver loop-metric histories — in-house loop data (F13)

**Spec:** `specs/loop_metric_histories.md`. **Build:** `src/loop_metrics_build.py`.
**Gate:** `src/gate_loop_metrics.py` (PASS). **Tier:** Analytics/reference — never touches the
frozen model, no gated A/B, no `>=8`-scored-races gate.

## 1. What this session built

Six loop-data-style signals — Average Running Position, green-flag pass differential, quality
passes, fastest-lap share, laps-in-top-15, closers — computed entirely in-house from
`silver.laps`/`silver.lap_flags` (C2), with **no new external source and no NASCAR licensing
exposure** (`research/external_knowledge_scan.md` §6.1's headline finding). Complementary to F3's
track-grain profiles (`specs/track_profiles.md`), this session is **driver-history grain**.

Every same-race value is a descriptive outcome, never a pre-race signal (scan §7 item 2) — the
deliverable is `gold.driver_loop_history`, an AS-OF (strictly-prior-races-only) half-life-weighted
history of each component, built the same way `gold.wf_features` builds `fin_h`/`pace_h` today.

## 2. The ARP definition decision (scan §7 item 3)

Public sources circulate three ARP definitions with no accessible official glossary: all-laps,
green-flag-only, lead-lap-only. This session pins **green-flag-only** and freezes it (spec §2.1):

- **Lead-lap-only rejected** — `silver.laps` carries no lead-lap/laps-down flag per row, and
  inferring it from the shared `lap` counter would need an unverified cross-driver proxy, the same
  category of risk F3's own RVS pit-cycle amendment explicitly avoided.
- **All-laps rejected** — doesn't correct for caution-lap position bunching, the exact noise every
  other component here already excludes by construction.
- **Green-flag-only pinned** — reuses machinery F3 already froze and verified
  (`track_profiles_build._green_laps_by_driver`/`_green_stretches`, imported verbatim, not
  reimplemented — confirmed by the gate's import source-scan), keeping all six components on one
  consistent scope.

Durable pass and restart (also pinned in `specs/track_profiles.md` §1.7) are **not used** by any
of the six components here — disclosed in the spec as a non-overlap, not an oversight (NASCAR's
own public "Quality Passes" stat has no durability requirement; none of the six components are
restart-conditioned).

## 3. Build results

| table | rows | grain |
|---|---:|---|
| `gold.driver_loop_race` | 8,949 | `(driver_id, race_id)`, raw/same-race |
| `gold.driver_loop_history` | 8,949 | `(driver_id, race_id, race_seq)`, AS-OF |

Scope: 237 Cup points races, 2020–2026 (the natural `silver.lap_flags` data floor — no manual year
filter needed). `arp` ranges 1.06–40.0 across the archive (mean 18.67, sane for a field that tops
out around 40 cars). 121 driver-races have `n_hist=0` (a driver's first qualifying race in scope —
`composite_h`/`*_h` are `NULL` there by construction, exactly as intended for an AS-OF history).
1,006 of 8,949 raw rows have `closers=NULL` (driver retired before the closing 10%-of-green-laps
window began) — the gate's check 5 confirms every one of these, and only these, fails the
"has a green-flag lap at or after `L_start`" test.

**Composite sanity** (spec §3.1): of 8,949 history rows, 8,808 (98.4%) have a defined
`composite_h` (the rest lack at least one of the six required non-`NULL` components, mostly early
in a driver's own history). Across all defined values, `mean(composite_h) = 0.0022`,
`stddev(composite_h) = 0.727` — a mean near zero is exactly what six-component, per-race
cross-sectional z-scoring should produce by construction; the stddev is `<1` because averaging six
correlated z-scores (a good closer also tends to have a good pass differential, etc.) compresses
variance relative to any single one of them, not a computation error.

**Named spot-check** (race 5618, North Wilkesboro, 2026-07-19 — the project's own scored
forward-test prediction #1): the top `composite_h` in that race's history snapshot belongs to
`driver_id=1361`, who finished P2 that same race (a same-race outcome shown only for orientation —
`composite_h` itself is built from strictly-prior races and never sees this result). The next four
by `composite_h` finished P11, P4, P30, and P19 — a plausible mix (form composites reward sustained
quality-pass/closer/fastest-lap history, not a guarantee of any single race's finish, exactly as
expected of a descriptive history feature that has never been feature-tested).

## 4. Gate result

`gate_loop_metrics.py` — **PASS**. All six spec §5 checks green: table consistency (no duplicate
`(driver_id, race_id)` keys in either table), build-graph isolation (`gold_build.py`/
`walkforward.py`/`predict_next.py` reference `driver_loop_race`/`driver_loop_history`: 0 times),
imported-machinery source-scan (confirmed `_green_stretches`/`_green_laps_by_driver` imported from
`track_profiles_build`, not reimplemented), full re-derivation (every row of both tables — not a
sample — recomputes bit-for-bit identical, a strictly stronger proof than F3/F4's 40-row spot
checks since this dataset is small enough for an exact full rebuild), the closers-nullability rule
(0 violations), and composite re-derivation from stored history columns alone (exact).

Full gate surface: **17/17 green** (16 inherited + this session's new `gate_loop_metrics.py`).

## 5. Zero design-judgment escalations

None. Every choice this spec pins (ARP definition, denominator convention, tie rule, composite
formula, nullability rules) is disclosed with reasoning in `specs/loop_metric_histories.md` §§2–3,
following the same "pin once, freeze, disclose why" discipline F3/F4 established — none of it rose
to the level of a genuine unresolvable ambiguity requiring an owner escalation.

## 6. Scope and governance

Tier A throughout. `gold.driver_loop_race`/`gold.driver_loop_history` are never joined into
`gold.wf_features`, and `gold_build.py`/`walkforward.py`/`predict_next.py` are untouched (gate
check 2). Any future model-feature use of these histories requires its own later pre-registered,
walk-forward-gated A/B, exactly like every other analytics/reference session in phase F.
