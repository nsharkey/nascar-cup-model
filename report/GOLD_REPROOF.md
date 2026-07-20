# GOLD_REPROOF.md -- D-gate report (specs/medallion_architecture.md section 6)

**Verdict: PASS**

Two amendments were made mid-session, both before any tuning and both owner-authorized after a
confirmed (not assumed) root-cause investigation -- see the `## AMENDMENT` blocks in the spec
(one before `## RESULT -- C-gate`, already recorded at C1; two more added this session: one
before section 5.3, one before this `## RESULT -- D-gate`). Both are load-bearing for how to
read the numbers below.

## Amendment 1 -- gold.wf_features scope (spec section 5, before 5.3)

`gold.wf_features`'s scope and its own history window are bounded to `series_id=1,
race_type_id=1, parse_status='ok', year >= 2022` -- an exact match to what `races_parsed.pkl`
ever contained. Silver (C1/C2) covers 2020+ (72 additional Cup/points/`ok` races exist for
2020-2021, confirmed by direct query, with ~90-97% driver-field overlap into early 2022) but the
legacy engine's `races_parsed.pkl` only ever held 2022+ data (`src/download.py` was a 2022+-only
fetch, retired at B2). Building gold's history unbounded would give 2022 drivers real 2020-2021
history the legacy engine structurally never had, breaking R2's "identical `n_hist`" requirement
for a data-window reason, not a plumbing one. Flagged and owner-authorized *before* any gold code
was written (not discovered via a failed gate run).

## Amendment 2 -- R0's expected 2026-OOS figure (spec section 6, before this RESULT block)

R0's first run (against the FROZEN 0.413/0.476/0.449 trio, using `fpts` -- the only feature spec
matching HANDOFF's frozen production config) reproduced backtest (0.413) and non-SS (0.476)
exactly, but 2026-OOS came in at 0.447, not 0.449. A diagnostic re-run against all five of
`step4_models.py`'s `SPECS` variants confirmed the mechanism:

| spec | features | backtest | non-SS | 2026-OOS |
|---|---|---|---|---|
| `fpts` | fin, pace, typed, start | 0.413 | 0.476 | 0.447 |
| `prior_all` | fin, pace, typed, start, fepace | 0.413 | 0.476 | **0.449** |
| `sameday` | + practice | 0.414 | 0.476 | 0.452 |

`prior_all` (5-feature, includes `fepace`) reproduces the published trio exactly on all three
legs; `fpts` (the actually-frozen 4-feature model) diverges only on the 20-race 2026-OOS slice,
where `fepace`'s marginal effect is large enough (relative to the small sample) to cross a
rounding boundary. This is exactly the mechanism section 9's pre-flagged ambiguity A1
anticipated: the originally-published "0.449" was generated from `prior_all`, not `fpts` -- a
reporting artifact in the original audit, not a defect in this rebuild's plumbing or data.
Owner-authorized resolution: `fpts` remains the D-gate's reference model (unchanged, matches
HANDOFF's frozen config); the expected 2026-OOS figure is corrected to **0.447**.

## R0 -- environment/reference check (legacy path, anchor data)

- `walkforward.RACES` <- the section 4.1 anchor pkl (163 races), both reference runs
  (`pl_specs={'fpts': ['fin','pace','typed','start']}`).
- Result: backtest **0.413**, non-SS **0.476**, 2026-OOS **0.447** -- exact match to the
  amendment-corrected trio.
- **PASS.**

## R1 -- silver replay (legacy engine, silver data)

- `walkforward.RACES` <- `silver_to_races_list()` (section 5.4 adapter) restricted to the
  anchor's 163 race_ids.
- Result: backtest **0.413**, non-SS **0.476**, 2026-OOS **0.447** -- identical to R0.
- Per-race `rho_PL_fpts` deltas vs R0: **0 of 163** scored races in either run (backtest or OOS)
  showed any delta at all -- not just zero *unexpected* deltas, zero deltas full stop. Consistent
  with the C1 heads-up: `fepace` is the sole silver-vs-anchor deviation (162/163 races,
  PASS-with-note per the C-gate's fepace-environment-tolerance amendment) and `fepace` is not
  part of the `fpts` feature spec, so it cannot influence `rho_PL_fpts` at all.
- C-gate re-checked as part of this run (needed for the PASS-with-note list): **PASS**, 163
  anchor races, 1 clean + 162 PASS-with-note (all `fepace_environment_tolerance`), 0 FAIL --
  identical to C1's original result.
- **PASS.**

## R2 -- feature parity (gold SQL vs replay)

- Replay: an independent Python re-implementation of `walkforward.run()`'s history/eligibility
  mechanics (section 5.2's definitions, typed_mode='shrinkage'), run over the same
  silver-reconstructed, anchor-restricted race list as R1, years=(2022..2026).
- **5,316 eligible (race, driver) pairs compared** (every driver eligible in every scored race
  across both the backtest and OOS windows) against `gold.wf_features`.
- Compared: `n_hist` (exact), `fin_h`/`pace_h`/`typ_h` (relative tolerance <= 1e-9, denominator
  `max(1,|ref|)`), NULL/eligibility membership (exact), `start_feat` (exact), `has_pace` (exact),
  `finish` (exact).
- **0 mismatches of any kind, on any field.**
- **PASS.**

## R3 -- decision parity (engine on gold)

- The same walk-forward PL loop as `walkforward.run()`, independently re-implemented, but
  `fin_h`/`pace_h`/`typ_h`/`start_feat`/`finish` sourced directly from `gold.wf_features` instead
  of recomputed from raw history; eligibility from gold's own `n_hist`/`has_pace` (validated
  equivalent to the legacy criteria by R2).
- Result: backtest **0.413**, non-SS **0.476**, 2026-OOS **0.447** -- identical to R1 at 3dp.
- Per scored race (backtest + OOS windows): **0 near-tie exceptions, 0 genuine rank
  disagreements, 0 races with `|delta rho| > 1e-6`.** The predicted-rank vector from
  gold-sourced features equals R1's exactly, race for race.
- **PASS.**

## Verdict

**D-GATE PASS.** R0 reproduces the (amendment-corrected) trio; R1 matches R0 exactly for every
scored race with zero deltas of any kind; R2 shows zero feature-level mismatches across all 5,316
eligible (race, driver) pairs; R3's gold-sourced engine reproduces R1's decisions exactly, race
for race, with zero exceptions needed. Gold is unblocked for D2 (scoring/benchmark consumers,
cutover).

## Environment

- python: 3.13.5
- numpy: 2.1.3
- scipy: 1.15.3
- duckdb: 1.4.0
- pyarrow: 19.0.0
