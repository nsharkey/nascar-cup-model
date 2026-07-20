# SPEC: Calibration backtest — pre-registration (FROZEN on commit)

**Status:** pre-registered 2026-07-20 (plan session **M1**, Opus 4.8 · thinking
on · xhigh), **before any calibration number exists.** NEW pre-registration file
— **not** an amendment to any frozen spec. Descends from
`research/pivot_model_book_vetting.md` (F20; owner fork **DEMOTE + tether**, §8);
honor the adversarial findings §2(a) (in-sample optimism) and §2(b)
(metric-shopping) verbatim.
**Governs:** plan session **M3** (run the walk-forward calibration backtest on the
frozen PL model). Consumes `specs/pricing_layer.md`.
**Implements to:** `src/calibration_backtest.py` (new file; no existing file
modified). No production-code change to the frozen model is involved at any point.

This spec exists so that the question **"is the model's probability readout
calibrated / does it carry decision-grade skill?"** cannot be renegotiated after
results start arriving — in either direction. A well-run null is a success
(project doctrine). Everything below is written so that an implementing session
makes **zero judgment calls.** The frozen sections are immutable once committed
(`specs/README.md`); a dated `## AMENDMENT` is permitted only while the data a
rule adjudicates does not yet exist.

---

## 0. What is and is not decided here (FROZEN)

- **Decided:** whether the raw model's **head-to-head** probability readout carries
  genuine, decision-grade **conditional skill** on non-superspeedway races,
  measured by a proper-scoring skill score on the **forward stream** (§3). One
  locked primary cell, one mechanical verdict, one named consequence (§3).
- **Measured but never a verdict:** every other market/metric/stratum — a finite,
  sealed, non-citable secondary appendix (§6), plus the mandatory dual pooled +
  per-track-type reporting (§5).
- **NOT decided here — out of scope, load-bearing:**
  - **Edge.** Calibration is model-vs-**reality**; a fair book breaks even by
    construction, so calibration yields **zero** profit signal and can never
    establish an edge. Edge is model-vs-**market** and lives, untouched, in
    `specs/market_benchmark_decision_rule.md` (the sole external check, the sole
    roadmap-#5 gate). Nothing here substitutes for it (tether gate 2).
  - **Recalibration.** This spec **measures** calibration; it does not **fix** it.
    Fitting or selecting any recalibration map is a **separate later spec**
    (`specs/recalibration.md`: utility-level, as-of fit, a NEW proper-scoring
    gate). The in-sample and 2026 strata are **barred from fitting or selecting
    any recalibration map** (§2). Recalibration is **not** folded into F10 — F10
    gates on ρ, which is rank-invariant and therefore **blind** to any monotone
    recalibration. **No "Bayesian ⇒ better calibrated" claim** is made or relied
    on: posterior averaging pushes pairwise probabilities toward 0.5, which would
    make the measured underconfidence marginally **worse** (memo §2(c)).

---

## 1. Inputs and the priced quantity (FROZEN)

The harness prices each race's **as-of utility vector** with `specs/pricing_layer.md`
and grades the prices against realized finishing order. It **fits nothing** — the
utilities are the frozen engine's own walk-forward output.

- **Backtest strata (development):** `walkforward.run(pl_specs={'fpts':
  ['fin','pace','typed','start']}, collect_preds=preds, typology=MY_TYPE,
  typed_mode='shrinkage', years=<all present, incl. 2026>)` →
  `preds['fpts'] = [(u, actual, track_type, date), …]` per scored race. The
  baseline-replication assert of the F7/DNF pattern applies: base mean ρ must
  reproduce the frozen anchor (0.413 backtest / 0.476 non-SS / 0.447 2026-OOS at
  the RESULT-block values) before any calibration number is read.
- **Forward stream (decision-grade):** the committed prediction JSONs
  (hash-verified per scoring §1.3) + the frozen results snapshots
  `src/data/races/{year}_{race_id}_wf_scored.json` — the **same** two file sets
  `market_benchmark.py` uses. A forward race is "scored" for this spec exactly
  when its snapshot exists. For each non-SS pair, the model H2H probability is the
  **sealed** `h2h_prob` (`σ(Δu)`) from the JSON; the outcome is the realized order
  in the snapshot.
- **Priced markets:** exactly the order-derived markets of `specs/pricing_layer.md`
  §1, with its probability floor (add-half MC / ε_floor analytic, §5.2) and its
  MC-reliability exclusion (§5.3). No other market is priced.

---

## 2. The three strata and their permissions (FROZEN)

The single most important rule in this spec. Decision-grade evidence rests on the
**forward stream only** (memo §2(a)).

| Stratum | What it is | Permitted use | **Barred from** |
|---|---|---|---|
| **IN-SAMPLE** | the ~108–163 scored races the frozen walk-forward produces over 2022–2026 | a **development smoke test** — labeled *in-sample / config-selected-on-this-era*: does the harness run, are the reliability curves sane, is the plumbing right | **any decision or verdict; fitting or selecting any recalibration map**; being cited as calibration evidence |
| **2026-OOS** | the 20 races of 2026 in the backtest | a **secondary, already-peeked** cut (the audit reported 2026 ρ/per-type and leaned on them to justify freezing — a peeked confirmation set, **not** a lockbox) | the primary decision; being called "out-of-sample validation" |
| **FORWARD** | race 5618 (2026-07-19) onward; **N = 1 race today** | the **only** decision-grade evidence — the primary verdict (§3) accrues here and nowhere else | — |

- **Why in-sample is barred:** walk-forward re-fits the PL *coefficients* as-of,
  but the *configuration* (feature set, `MY_TYPE`, half-life 8, λ 0.5) was
  human-selected on these same races. Walk-forward launders βs, not config
  selection. A calibration verdict on this stratum is circular (memo §2(a)).
- **The residual, stated honestly:** decision-grade calibration is as slow as the
  benchmark for everything **except** the pooled dense markets (§4) — which is why
  the scope is exactly those (§7 power triage).

---

## 3. The one locked primary decision cell (FROZEN)

Exactly one cell drives the only mechanical verdict. Nothing descriptive can enter
it (the property that makes the market benchmark's verdict un-shoppable).

- **Market:** **H2H** — the head-to-head pairwise ordering, analytic `σ(Δu)`
  (`specs/pricing_layer.md` §3.1). Full-order-consistent; **never top-K.**
- **Population:** all **non-SS** forward-stream H2H pairs, canonical lower-id
  orientation (scoring §4), both drivers in the common set, **pooled.**
- **Calibration-state:** **raw** (uncalibrated) model.
- **Metric — a proper-scoring skill score vs a marginal base rate (not a coin
  flip):** the **Brier skill score**
  `BSS = 1 − B_model / B_base`, where
  - `B_model` = mean Brier of the model's H2H probabilities (event = "lower-id
    driver finishes ahead");
  - `B_base` = mean Brier of the **as-of marginal-strength (Bradley–Terry)
    baseline** `P_base(a≻b) = s_a / (s_a + s_b)`, where `s_d` = driver *d*'s as-of
    lifetime **pairwise-win fraction** over prior **non-SS** races
    (`Σ co-finishers d beat / Σ co-finishers`, races strictly before the scored
    race); a driver with `< 5` prior non-SS races takes `s_d = 0.5`; `s_a = s_b`
    → `P_base = 0.5`. **Zero free parameters** — the honest non-coin-flip base
    rate (each driver's marginal H2H strength). Positive BSS ⇒ the model's
    *conditional* probabilities beat knowing only each driver's marginal strength.
- **Small-sample machinery (ported from the market spec verbatim in form):**
  race-clustered bootstrap of `BSS`, `B_CALIB = 10_000`, `CALIB_SEED = 20260720`,
  fresh `numpy.random.default_rng(CALIB_SEED)` at every look, index matrix
  `rng.integers(0, K, size=(B_CALIB, K))`, **add-one** convention for tail
  probabilities, races sorted ascending `(race_date, race_id)`. Cluster on the
  **race** (pairs within a race share one finishing order, so the effective sample
  is `K` races, not `N` pairs).
- **Floors:** `K_FLOOR = 20` non-SS forward races; `δ_prac = 0.01` BSS (a
  practical-significance floor set a priori, the calibration analogue of the
  program-wide `+0.005` ρ floor). `N` is reported but `K` binds.
- **The mechanical verdict (nothing descriptive enters):**
  - **CALIBRATED-SKILL** iff `K ≥ 20` **and** the one-sided 95 % race-clustered
    bootstrap **lower** bound of `BSS` `> 0` **and** the point `BSS ≥ δ_prac`.
  - **NULL** iff `K ≥ 20` and the one-sided 95 % **upper** bound of `BSS`
    `< δ_prac` (futility — cannot reach practical significance).
  - **UNDERPOWERED** otherwise.
  - Sequential looks after each scored forward race, Haybittle–Peto style
    (interim `p ≤ 0.001`-strict is unnecessary for a bounded skill score; the
    binding interim rule is: no verdict below `K = 20`). Terminal look: first of
    `K ≥ 60` non-SS forward races **or** the first run on/after **2028-02-15**.
- **The NAMED downstream consequence (concrete, not decorative):**
  - **CALIBRATED-SKILL** ⇒ (i) the non-SS H2H readout is re-labeled a **validated
    diagnostic** (superseding "raw-model implied only") in `specs/pricing_layer.md`
    §7's sheet, and (ii) this verdict is the **pre-registered precondition for
    opening `specs/recalibration.md`** — you recalibrate a market only once it is
    shown to carry real skill worth recalibrating; recalibrating noise is
    pointless. It does **not** open recalibration by itself and it **never**
    unlocks roadmap #5 (tether gate 3).
  - **NULL** ⇒ the readout stays raw-only; `specs/recalibration.md` is **not**
    opened on this evidence.
  - **UNDERPOWERED** ⇒ keep accruing; any window extension is pre-registered
    **before** the terminal look (§8).

---

## 4. Why the forward H2H signal is the one that accrues fast (context, FROZEN)

Pooled dense **two-outcome** markets are the single place the calibration signal
escapes odds-starvation: a forward non-SS race yields **~700 H2H pairs** and
**~380 driver-rows** (top-N), **free and complete** — ~30–60× the market
benchmark's ~12 odds-gated picks/race. Because pairs within a race are correlated,
the effective sample is `K` **races** (the bootstrap clusters on race), so `K ≥ 20`
non-SS forward races — reachable in **~one forward season** — is the real floor.
This is the "one genuine win" of the pivot (memo §2(a)); it does **not** extend to
win / group / SS / per-type stratified verdicts (§7).

---

## 5. Mandatory dual reporting + the pooling-launder ban (FROZEN)

Every metric is reported **both** pooled **and** stratified by track type
(SS / INT / SHORT / ROAD), on every stratum (in-sample / 2026 / forward).

- **The pooling-launder ban.** **No "calibrated" claim may be made from a pooled
  number that includes SS, and no pooled verdict may stand while the SS stratum is
  unreported.** The primary cell (§3) is **non-SS by construction**, so SS never
  enters it; the SS stratum is **always** reported separately and flagged
  `SS STAND-DOWN`. A headline of the form "the model is calibrated" computed over
  all track types is a protocol violation — it provably hides SS (audit §5/§7: SS
  is near-noise, Brier 0.2514 < coin flip). Report per-type, never launder.
- **Reliability curves:** for each market×stratum, an **equal-count (equal-mass)
  binning with a pinned `N_BINS = 10`** (deciles of predicted probability);
  per-bin mean predicted vs observed frequency, bin counts, and a Brier
  reliability/resolution decomposition. These document the direction of any
  miscalibration (the audit's underconfidence: observed > predicted) and feed
  `specs/recalibration.md`'s later case — but they are **descriptive**; only §3's
  BSS drives a verdict.

---

## 6. The sealed, non-citable secondary family (FROZEN)

Finite and closed — **no open-ended "…/per market."** Exactly these `M = 6` cells,
each with a fixed role. **Bonferroni** over the honestly-counted family
(`α_sec = 0.05 / 6 ≈ 0.0083` one-sided), a **practical-significance floor**
(`|BSS| ≥ δ_prac = 0.01`), and **at-most-one action** from the whole secondary
family per terminal look. These cells are **non-citable**: no secondary number may
be cited against the §3 primary verdict, nor to claim any edge or "calibration"
outside its own pre-registered role.

| # | Cell (all forward unless noted) | Role | Decision-grade? |
|---|---|---|---|
| S1 | H2H **log-loss** skill (pooled non-SS) | robustness of the primary to the proper score chosen | yes (action-eligible) |
| S2 | **top-10** BSS (pooled non-SS) vs climatology base rate `min(10,n)/n` | the second dense two-outcome market | yes (action-eligible) |
| S3 | H2H reliability **slope + intercept** (pooled non-SS, 10 equal-mass bins) | documents under/over-confidence direction; input to `specs/recalibration.md` | **descriptive-only** |
| S4 | **Per-track-type** H2H BSS + reliability (INT / SHORT / ROAD; SS reported, stand-down) | stratified; underpowered per-type | **descriptive-only** |
| S5 | **Win** BSS + reliability (pooled non-SS) — the tail market | arms the F7-C trigger (§9); PL's unidimensional tail | **descriptive-only** |
| S6 | H2H BSS on the **2026 peeked** cut | secondary already-seen confirmation | **descriptive-only** |

- **Action-eligible** cells (S1, S2) may, at the terminal look and only if the
  §3 primary is itself CALIBRATED-SKILL, contribute at most one additional
  recorded action (e.g. certifying top-10 as a validated diagnostic), subject to
  Bonferroni + the practical floor + at-most-one. S3–S6 can **never** drive an
  action; they are reported for documentation and for the triggers of §9.
- **Terminal / extension / no-re-litigation discipline** (ported from the market
  spec's extension-discipline amendment): once the §3 terminal look is computed,
  its verdict is **terminal for this pre-registration** — no extension, retest, or
  successor analysis of the same accumulated pair stream may be re-scored against
  these thresholds. A successor test may be pre-registered at any time but may use
  only pairs first graded **after** its own registration date (a fresh sample).
  An extension of the window must be pre-registered **before** the terminal look.

---

## 7. Power triage (published up front, FROZEN)

State the scope honestly so no one later mistakes a descriptive number for a
verdict:

- **Decision-grade scope = pooled non-SS two-outcome markets only** — the primary
  H2H (§3) and the action-eligible secondary top-10 (S2). These accrue ~one
  forward season to a verdict.
- **Descriptive-only until a pre-registered horizon extension:**
  - **win / group** markets: ~1 winner-event per race ⇒ never decision-grade on
    the forward stream in a realistic horizon;
  - **all SS** markets: near-noise (audit §5/§7) ⇒ stand-down, never a verdict;
  - **per-track-type stratified** cells: ~5–15 forward races per type over a
    season ⇒ underpowered per-type.
  A verdict on any of these requires a **separately pre-registered** window
  extension (dated addendum before its own terminal look) — it is not available
  by default.

---

## 8. Anti-shopping guarantees (FROZEN — the property "descriptive-only" alone can't provide)

The leak channel is **belief, not a file** (memo §2(b)): the README already
promoted one cell (H2H×Brier×SS = 0.2514) into live doctrine with zero
`scores_log` involvement, so firewalling a log does nothing. The guarantee is the
**single mechanical verdict** of §3 that no descriptive number can enter, plus:

1. the primary cell is fixed here (market, population, metric, baseline, state,
   threshold, consequence) **before** the forward stream exists;
2. the secondary family is finite, sealed, and non-citable (§6);
3. the frozen `scores_log.csv` (ρ + H2H picks, top-K still banned) is **untouched**
   — this calibration log is a **separate** artifact, never a §6-of-scoring
   amendment;
4. the three strata's permissions (§2) bar the in-sample/2026 data from any
   decision and from fitting any recalibration map;
5. terminal + no-re-litigation discipline (§6) forbids re-scoring the pooled
   stream after the terminal look.

---

## 9. Expected findings, split by mechanism (FROZEN — reconciles the plan's "C stays F7-NULL")

Poor calibration is a **pre-registered expected finding**, and its **diagnosis
differs by track type** (memo §2(d)). Route it correctly:

- **Non-SS TAIL miscalibration → ARMS F7 formulation-C trigger T1.** A documented
  finding of systematic miscalibration in the **non-SS tail** markets (S5 win;
  thin top-3) is exactly the surface F7's assessment names in trigger **T1**: "a
  simulation/DFS surface with its own pre-registered proper-scoring rule is
  adopted into the plan." This spec **is** that pre-registered scored surface, so
  T1 is **ARMED** for **non-SS tails only**. C is *drafted-justified* for non-SS
  tails — but stays **gated / unbuilt** (F7-C blocked) until the owner elects to
  pull it with its own pre-registration. PL's unidimensionality (one utility sets
  both center and tails; it cannot represent "win-or-wreck") is the mechanism C
  would fix (F7 §6).
- **SS miscalibration → CONFIRMS the stand-down; NOT a C-trigger.** SS is
  **no-signal** (ρ 0.16; confident picks 56 %; Brier 0.2514). C fixes tail
  **shape**, not the **absence** of ordering information — so poor SS calibration
  is **not** evidence for C. It confirms the pre-registered SS stand-down and
  nothing more. Routing SS miscalibration into "evidence for C" is a diagnosis
  error (memo §2(d)) and is forbidden here.
- **Plan reconciliation:** the plan/F20 text "the full generative race simulator
  stays F7-NULL unless a trigger fires" is updated to: **T1 is armed by this
  backtest's non-SS tail findings (S5); C stays NULL/gated until owner election;
  SS is stand-down, not a C-target.** (Applied to the Phase F note and F7's
  row in `plan/schedule.yml` by M1.)

---

## 10. Implementation checklist (mechanical, in order — for M3)

1. `src/calibration_backtest.py`: (a) run the frozen walk-forward with
   `collect_preds` (baseline-replication assert first); (b) build the as-of
   `s_d` marginal-strength table (walk-forward, non-SS); (c) price each race via
   `pricing_layer.price_race`; (d) grade every §1/§6 market on each stratum;
   (e) compute the §3 primary BSS + race-clustered bootstrap verdict on the
   **forward** stratum; (f) compute the §6 secondary family (Bonferroni, floor,
   at-most-one); (g) emit the §5 dual pooled + per-type reliability curves with
   the launder ban enforced; (h) print the §7 power triage and the §9 trigger
   split. Deterministic (`CALIB_SEED`); no network; no engine re-fit beyond the
   frozen replay.
2. Verify the harness on the in-sample stratum as a **smoke test only** — print it
   labeled `IN-SAMPLE (dev, barred from decision & recal-fitting)`.
3. Write `report/CALIBRATION_BACKTEST.md` (all strata, all cells, the verdict, the
   power triage, the trigger split, the numpy/interpreter environment).
4. Fill `## RESULT — calibration backtest` (dated) in this spec.
5. **No frozen-spec edit; no change to `predict_next.py` / `walkforward.py` /
   `scores_log.csv`.** If genuinely ambiguous anywhere, STOP and flag (as C1/D1
   did), do not choose. Escalate any judgment call to Opus.

---

## 11. Resolved-ambiguity register (why, one line each)

- **H2H primary, not top-10** → densest (~700 pairs/race), analytic (no MC noise
  in the decision), audit-continuous (§7 measured H2H directly), benchmark-aligned
  (calibration and edge measured on the same object, cleanly orthogonal), and
  unambiguously not a top-K "pick" family. top-10 is the action-eligible secondary.
- **Bradley–Terry marginal baseline, not a coin flip** → 0.5 is a strawman; the
  as-of pairwise-win-fraction baseline is a genuine, parameter-free marginal, so a
  positive BSS means real *conditional* information beyond each driver's strength.
- **Race-clustered bootstrap, cluster on race** → pairs within a race share one
  finishing order; the effective sample is K races, not N pairs — iid over pairs
  would massively overstate significance.
- **`K ≥ 20`, `δ_prac = 0.01`, lower-bound > 0 AND point ≥ floor** → ports the
  market spec's K-floor and the program-wide "practical floor binds" discipline;
  a statistically-significant-but-trivial skill is rejected on purpose.
- **Forward-only decision; in-sample = dev smoke; 2026 = peeked secondary** →
  config was selected on the historical era, so only the fresh forward stream is
  decision-grade (memo §2(a)).
- **Finite sealed non-citable secondary family + Bonferroni + at-most-one** →
  "descriptive-only" is cosmetic without a single mechanical verdict nothing else
  can enter; the multiplicity family is honestly counted, not open-ended.
- **Recalibration out of scope; not F10; no Bayesian-⇒-calibrated claim** → this
  spec measures, a separate gated spec fixes; F10's ρ-gate is blind to monotone
  maps; posterior averaging worsens the measured underconfidence.
- **Non-SS tail arms C-T1; SS confirms stand-down** → C fixes tail shape, not
  absence of signal; routing SS-noise into "evidence for C" is a diagnosis error.

## 12. Flagged (not resolved — owner input welcome, non-blocking)

- The terminal look's `K ≥ 60` non-SS forward figure is a horizon anchor
  (~two forward seasons of non-SS races); if the owner wants a one-season terminal
  (`K ≥ 30`), that is a pre-registered change to make **before** any forward look
  crosses it, never after.
- A `specs/allbet_capture_schema.md` for **book-side** win/top-k capture
  (descriptive-only; can never feed the H2H-only benchmark) remains the lowest
  priority follow-on (memo §3.1), independent of this spec.

---

# Amendment — F20 spec-conformance review, 2026-07-20 (pre-data: **no forward non-SS
# race has reached the K ≥ 20 floor; K = 0 today**; the calibration numbers this rule
# adjudicates do not yet exist, so this amendment is permitted per `specs/README.md`).

## AMENDMENT (2026-07-20, pre-data): terminal-only primary verdict — fixes the §3 sequential-look α control (binds §3)

**Defect patched (recorded).** §3 as written evaluates the primary verdict after every
scored forward race and lets **CALIBRATED-SKILL fire at any interim look with `K ≥ 20`**
at a one-sided 95 % bootstrap bound, while dropping an interim α-spending boundary on the
stated rationale that *"interim p ≤ 0.001-strict is unnecessary for a bounded skill
score."* **That rationale is unsound: boundedness of the statistic does not prevent
repeated-looks type-I inflation** — taking many one-sided-95 % looks on an accumulating
statistic is exactly the multiplicity the market spec's Haybittle–Peto boundary exists to
control. Under the exact null (true `BSS = 0`) the cumulative probability that *some*
interim look crosses "lower bound > 0 AND point ≥ `δ_prac`" exceeds the nominal 0.05 (the
`δ_prac` floor mitigates but does not restore 0.05). "Haybittle–Peto style" was named
without its mechanism.

**The fix — the primary verdict is a single terminal decision (so no interim α-spending
is needed).**

1. **CALIBRATED-SKILL and NULL are evaluated ONLY at the terminal look** — the first of
   `K ≥ 60` non-SS forward races (or `K ≥ 30` iff the owner exercises the §12 one-season
   option, pre-registered before any look crosses it) **or** the first run on/after
   2028-02-15. At that single look the §3 conditions apply unchanged: CALIBRATED-SKILL iff
   `K ≥ 20` and the one-sided 95 % race-clustered bootstrap **lower** bound of `BSS` > 0
   and point `BSS ≥ δ_prac`; NULL iff `K ≥ 20` and the one-sided 95 % **upper** bound
   < `δ_prac`; else UNDERPOWERED (which a terminal look with `K < 20` necessarily returns).
2. **Every look before the terminal look is UNDERPOWERED by definition.** The interim
   `BSS`, its bootstrap bounds, `K`/`N`, and the reliability curves are **computed and
   reported** each run for monitoring, but carry **no decision weight**; no interim look
   may declare CALIBRATED-SKILL or NULL.
3. **Consequence:** the primary is now a single pre-registered decision point, so its
   one-sided type-I is the nominal 0.05 by construction with no look-multiplicity —
   reaching the same rigor the market benchmark obtains via Haybittle–Peto α-spending, but
   more simply, by not stopping early. Early stopping carries no value here: unlike an
   EDGE (high-value to catch early, effort-gating), a CALIBRATED-SKILL verdict is
   low-stakes — it re-labels the readout and is the precondition for opening
   `specs/recalibration.md`, and **never unlocks roadmap #5**.
4. **Unchanged:** the `BSS` statistic, the as-of Bradley–Terry baseline, `δ_prac = 0.01`,
   the `K ≥ 20` floor, the race-clustered bootstrap mechanics (`B_CALIB = 10_000`,
   `CALIB_SEED = 20260720`, add-one), the named consequences (§3), the §6 secondary family
   with its Bonferroni / practical-floor / at-most-one discipline, and the terminal /
   no-re-litigation rule (§6). Only the **timing** of the primary verdict changes:
   terminal-only, not sequential.

This supersedes the §3 sentence *"Sequential looks after each scored forward race,
Haybittle–Peto style (interim p ≤ 0.001-strict is unnecessary for a bounded skill score;
the binding interim rule is: no verdict below K = 20)"*, which is recorded here as the
defect being patched. Reason: a single pre-registered decision point is the simplest
exact control of look-multiplicity, and it costs nothing in a setting where early
stopping has no value.

---

## RESULT — calibration backtest (to be filled by M3, on run)

*(dated run outcome: baseline replication asserted; the primary H2H BSS verdict on
the forward stream with its K/N and bootstrap bounds; the sealed secondary family;
the dual pooled + per-type reliability curves; the power triage; the C-trigger
split; numpy/interpreter environment. Filled by M3, not M1.)*
