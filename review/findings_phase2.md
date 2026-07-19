The verification is decisive. All computations are complete — the amended rule restores the spec's α claim (0.044–0.049 vs 0.061–0.096 unamended) at negligible power cost. I now have everything needed for the final report.

# Adversarial review — specs/market_benchmark_decision_rule.md (pre-registration audit, phase 2)

**Scope:** `specs/market_benchmark_decision_rule.md` (frozen 2026-07-18) vs. the live repo at `/Users/nicholassharkey/Downloads/nascar-cup-model` — every §5 power cell recomputed exactly; the §3–§4 bootstrap procedure stress-tested by simulation with the spec's own seed/B (single-look sizes, full sequential operating characteristics, amended-rule verification); admissibility, boundary, and gaming analysis checked against the AMENDED `specs/scoring_methodology.md`, `HANDOFF.md`, `review/findings_phase1.md`, `predictions/race_5618_2026-07-19_prediction.json`, `src/predict_next.py`, `src/update_data.py`, `src/walkforward.py` (MY_TYPE), `src/data/race_list_2026.json`, and `report/NASCAR_AUDIT_REPORT.md`. All computation in `.venv/bin/python` (numpy 2.5.1, scipy 1.18.0); no repo file modified. **Date:** 2026-07-18.

**Verdict: 1 CRITICAL, 3 MAJOR, 4 MINOR, 3 NIT.** The §5 power table is arithmetically perfect (all 20 cells reproduced exactly, including the 3-dp boundary cells). The profit formula, the SS exclusion, the ITT clause, the 0.5300 cross-reference, and the accrual counts all held up. The CRITICAL finding is in the machinery the spec is proudest of: the interim efficacy boundary, as specified, cannot deliver the 0.001 calibration the Haybittle–Peto α claim rests on at the cluster counts the spec's own accrual estimates imply — measured false-EDGE rates run 4×–190× nominal, and the total-α claim fails (measured 0.061–0.096 vs claimed ≈0.05). A corrected procedure is proposed and **verified by simulation to restore total α ≈ 0.045–0.049 at negligible power cost.** Amendment window: per `specs/README.md` these amendments are legal only while no book price has been recorded; HANDOFF says race 5618 prices may be grabbed as soon as this weekend, so the window may close within days.

---

## Findings (most severe first)

### 1. [CRITICAL] — The interim EDGE boundary "bootstrap p ≤ 0.001" is uncalibratable at feasible race counts; the total-α ≈ 0.05 claim fails on the spec's own accrual estimates
**Spec sections:** §3 (test definition), §4 (schedule + "boundaries below keep total α ≈ 0.05"), resolved-ambiguity register ("arbitrarily many cheap interim looks without meaningful α inflation").

**First, what is NOT wrong** (adjudicated deliberately, because the obvious attack fails): §3's p — "fraction of resamples with total ≤ 0" — is not a naive conflation of a bootstrap CI with a null test. It is exactly the inversion of the one-sided percentile-bootstrap confidence bound (reject H0 "E[profit] ≤ 0" at α iff the α-quantile of the bootstrap distribution exceeds 0 iff p < α), a recognized, first-order-valid test. Resampling observed data is legitimate here *by that duality*. The genuine defect is where first-order validity dies: few clusters and an extreme (0.001) threshold.

**Failure mechanism:** the resampling universe is the K scored races. If **every one of K races is net-positive, every resample is positive and p = 0 identically, regardless of magnitudes** — the boundary fires. The schedule arms efficacy at N ≥ 50 *picks*, but N ≥ 50 can mean K = 5 races (at the spec's own 10/race upper estimate) or K = 2 (a 25-matchup board, which large books post). Nothing in the spec imposes a minimum K.

**Evidence — measured size of "p ≤ 0.001" at a single look, exact break-even null (E[profit] = 0 per pick), spec's own B = 10,000 and seed 20260718, 40,000 null simulations per cell:**

| Contributing races K | picks/race, price | measured false-EDGE rate | × nominal |
|---|---|---|---|
| 2 | 25 @ −110 | **0.191** | 191× |
| 5 | 10 @ −110 | **0.020** | 20× |
| 10 | 5 @ −110 | 0.008–0.010 | ~9× |
| 10 | 5 @ −300 | 0.014 | 14× |
| 14 (all of rest-2026) | 5 @ −110 | 0.007 | 7× |
| 20 | 5 @ −110 | 0.004 | 4× |
| 30 | 5 @ −300 | 0.004 | 4× |

(The analytic cross-check matches: P(all K races positive) at K=2×25 picks = 0.437² = 0.191; the bootstrap adds near-all-positive events on top.)

**Full sequential simulation** (44 remaining non-SS races through 2027, looks after every race per §4, exact-boundary null, futility and final rule as written): total P(EDGE) = **0.0610** at 5 picks/race and **0.0964** at 10 picks/race, vs the claimed ≈ 0.05 — the interim spend alone is 0.028 and 0.063 where Haybittle–Peto budgets ~0.001–0.005. Under the spec's favored accrual the design roughly **doubles** its stated type I error, and every extra pick per race makes it worse (more picks → earlier armed looks at smaller K). A false EDGE permanently unlocks roadmap #5 — the single worst failure the gate exists to prevent.

Secondary defects folded in: p has no add-one correction (Monte-Carlo floor p = 0 exists), and the resampling mechanics (RNG algorithm, race ordering, quantile convention, pooled-vs-race-averaged mean for the futility bound) are unpinned, so the "fixed seed makes every look reproducible" claim holds only within one implementation (see finding 6).

**Corrected procedure — verified by simulation before proposing:** a K ≥ 20 floor, an add-one p, and a dual interim boundary (bootstrap AND cluster-t). Measured on the same nulls: total α = **0.0444** (5/race) and **0.0492** (10/race), interim spend 0.004–0.005 — the spec's own claim, restored. Power cost is negligible: at true win rate 0.58 (ROI +10.7%), power 0.492 vs 0.513 unamended at 5/race, and 0.757 at 10/race. (A cluster-t alone was tested and rejected: it degenerates at K = 2 — equal positive race totals give sd = 0 — measured size 0.046.)

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data — no book price has been recorded):
small-sample calibration guards and pinned resampling mechanics (binds §3, §4, §6)

1. **Naming, recorded.** §3's p ("fraction of resamples with total ≤ 0") is the
   inversion of the one-sided percentile-bootstrap confidence bound — a
   first-order-valid test of H0 "E[profit] ≤ 0", retained as the primary
   statistic. The items below fix its small-sample calibration and determinism,
   not its identity.
2. **Race-count floor K ≥ 20.** Let K = number of races contributing ≥ 1 graded
   pick. No decision boundary — interim efficacy, futility, or the final look's
   EDGE arm — may fire at a look with K < 20; a final look with K < 20 returns
   UNDERPOWERED. Reason, computed 2026-07-18: with few clusters, "every
   contributing race net-positive" forces p = 0 regardless of magnitudes; under
   the exact break-even null its probability is ≈ 0.19 at K = 2 (25 picks/race),
   ≈ 0.02 at K = 5 (10/race), ≈ 0.008–0.014 at K = 10 — one to two orders of
   magnitude above the 0.001 the Haybittle–Peto interim boundary assumes.
3. **Add-one convention.** p = (1 + #{resamples with total ≤ 0}) / (B + 1). The
   futility bound is the 9,501st ascending order statistic of the B = 10,000
   resampled mean-profit-per-pick values.
4. **Dual interim boundary.** An interim EDGE requires, in addition to p ≤ 0.001,
   a one-sided one-sample t-test on the K per-race profit totals (H0: mean ≤ 0,
   df = K − 1; a degenerate sd yields no rejection) with p_t ≤ 0.001. Verified
   by simulation 2026-07-18: with the K ≥ 20 floor the combined rule's per-look
   size is ≈ 0.001 at near-even prices (worst measured stress case, all picks
   at −300: ≈ 0.003), and the full sequential design's total type I error is
   0.044 (5 picks/race) / 0.049 (10 picks/race) vs 0.061 / 0.096 unamended,
   at a power cost of ≤ 0.02 at true win rate 0.58.
5. **Pinned mechanics (two independent implementations must agree exactly).**
   Contributing races sorted ascending by (race_date, race_id); rng =
   numpy.random.default_rng(20260718) constructed fresh at each look; index
   matrix = rng.integers(0, K, size=(B, K)); each resample's mean profit per
   pick = pooled resampled total profit / pooled resampled pick count (not a
   mean of per-race means); B = 10,000.
6. **Unchanged:** the §4 thresholds (0.001, 0.045, 95% futility bound), the
   verdicts, and the schedule itself.
```

### 2. [MAJOR] — Admissibility of post-race-committed price entries is undefined, and the scoring spec's provenance amendment delegates it to a rule that does not operatively exist
**Spec sections:** §1 (graded-pick definition), §2 ("record prices **before** the race, never after"); interacts with `scoring_methodology.md`'s book-entry-provenance AMENDMENT.

**Failure scenario (live this weekend):** HANDOFF says 5618's book prices are "not yet recorded — grab them if still possible." Suppose closing prices are transcribed Sunday night from an odds archive, after the race. The scoring spec's provenance amendment flags the row `post-race price entry` and says "admissibility for the market benchmark is governed by that spec's §2" — but this spec's §2 contains no operative exclusion, only a data-collection instruction in a parenthetical; and §1's graded-pick definition (deduped, non-void, well-formed, non-SS, common set, model pick) says nothing about provenance. Implementation A includes the entries (they satisfy every §1 clause); implementation B excludes them (citing §2's parenthetical). **Two compliant implementations count different N** — the circular cross-reference (scoring amendment → market §2 → nothing) leaves the single most gameable input (post-hoc price entry, per phase-1 finding 3) formally admissible. Note also the tension inside the scoring spec itself: its §10 step 4 permits recording prices post-race, while this spec's §2 says "never after" — admissibility must resolve that conflict explicitly.

**Evidence:** §1 lines 19–27 (no provenance clause); §2's only relevant text is parenthetical; scoring amendment text "admissibility ... is governed by that spec's §2" (verbatim); the race's `schedule` block in `src/data/race_list_2026.json` carries `event_name == "Race"`, `start_time_utc = 2026-07-19T23:00:00` — a mechanically usable green-flag instant.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): admissibility of price entries (binds §1, §2)

A `book_prices` entry is **admissible** for this spec's statistic only if the
first git commit whose version of the race's prediction JSON contains that
entry (matched on unordered driver pair + book + recorded_utc) is committed
earlier than the race's scheduled start — the `start_time_utc` of the
`event_name == "Race"` entry in the race's `schedule` block of that year's
`race_list_basic.json`. Inadmissible entries are excluded from graded picks
and from N, and the §6 script reports each one; they remain in the JSON and in
the scoring spec's descriptive counts (flagged `post-race price entry` per its
provenance amendment, whose "admissibility is governed by that spec's §2"
sentence resolves to exactly this rule). Once the repo has a public remote,
the qualifying commit must additionally be an ancestor of a ref pushed before
the scheduled start; until then local committer timestamps govern — the same
integrity basis, and the same known limitation, as the prediction seal itself.
```

### 3. [MAJOR] — The verdict schedule is operator-escapable: the final trigger can be stalled forever, NO-EDGE requires accrual the operator controls, and look timing is tied to discretionary scoring
**Spec sections:** §2 (recording duty), §4 (look trigger "after each race is scored"; final trigger "last 2027 points race scored"; NO-EDGE requires N ≥ 200), §5 (accrual).

**Failure scenarios (all fully compliant as written):**
- **Stalled final look.** The final trigger requires the last 2027 points race to be *scored*. Stop scoring (or stop predicting) in October 2027 and the final look never fires; no verdict is ever rendered. NO-EDGE — the outcome that would permanently close roadmap #5 — is dodgeable by simply not finishing.
- **Accrual throttling.** Terminal NO-EDGE requires N ≥ 200. The operator chooses how many matchups to record: 44 remaining non-SS races × 4 recorded matchups = **176 < 200** — recording four per race *guarantees* the final look cannot return NO-EDGE (only EDGE or UNDERPOWERED, hope preserved indefinitely via the extension bullet). At ≤ 2/race even futility (N ≥ 100) can never arm. §2's "missingness is price-availability-driven" is an assumption with no mechanism behind it: recording is per-matchup discretionary and invisible.
- **Look skipping.** Looks exist only when a race "is scored." Score races 20–24 in one batch and the states at races 20–23 are never evaluated — a futility crossing at race 21 (visible in the weekly public ROI numbers) is legally skipped over.

**Evidence:** §4 line "Looks happen after each race is scored"; final-trigger text; §5's own arithmetic (5–10/race) shows the N = 200 boundary sits just under minimal full-compliance accrual (5 × 44 = 220); no minimum matchups-per-race duty anywhere; scoring cadence is under HANDOFF weekly protocol, i.e., operator-timed.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): deterministic look sequence, calendar
backstop, and full-board recording (binds §2, §4)

1. **Looks are states, not acts.** At every run, the §6 script reconstructs the
   full look sequence — the state after each scored race, in ascending
   (race_date, race_id) order — and the standing verdict is the FIRST boundary
   crossing in that reconstructed sequence. Scoring late, or in batches, cannot
   skip a crossing: the crossing is found retroactively and governs.
2. **Calendar backstop.** The final look occurs at the first of: N ≥ 400; the
   last 2027 points race scored; or the first benchmark run on or after
   2028-02-15 — and one such run must be made and its verdict reported.
   Ceasing to score or record does not prevent the final look; picks graded as
   of that date decide it.
3. **Full-board duty.** For every priced race, record ALL head-to-head matchups
   the primary book offers whose two drivers are in the predicted field — never
   a chosen subset. If capture was partial (market pulled, access failure), the
   race's scores row must carry a note naming what was missed and why; the §6
   script reports the per-race recorded counts at every look so thin recording
   is visible in the open log.
```

### 4. [MAJOR] — The UNDERPOWERED extension hatch permits a post-data extension that inflates α (0.045 → ≈ 0.074) and contradicts the spec's own no-new-rules clause
**Spec section:** §4 bullets ("any extension of the test window must itself be pre-registered (dated addendum) **before** further looks" vs "No other peeking rule … may be introduced after the first price is recorded"); final row labeled "terminal."

**Failure scenario:** final look fires end-2027 with N = 176, p = 0.055, positive ROI → UNDERPOWERED. The owner — now knowing p — pre-registers a "dated addendum" extending through 2028 and retests the pooled stream at 0.045. This satisfies the extension bullet as written ("before further looks" only constrains *future* looks). Computed under the Gaussian idealization: retesting the pooled sample at 0.045 after a first look at N₁ = 176 extended to N₂ = 400 has total one-sided type I error **0.0743** (N₁ = 220 → 0.0710) — a ~65% inflation of the terminal α, chooseable precisely when the result is a near-miss, which is the only time anyone would extend. The clause also flatly contradicts the adjacent bullet forbidding new peeking rules after the first price, and the "terminal" label on the row that produced UNDERPOWERED.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): extension discipline (binds §4)

An extension of the test window may be pre-registered only BEFORE the final
look's trigger fires. Once the final look has been computed, its verdict is
terminal for this design: no extension, retest, or successor analysis of the
same accumulated pick stream may be evaluated against this spec's thresholds.
A successor test may be pre-registered at any time, but its statistic may use
only picks first graded after its own registration date (a fresh sample).
Reason, computed 2026-07-18: retesting the pooled stream at 0.045 after an
UNDERPOWERED final look (N = 176 extended to 400) carries total one-sided
type I error ≈ 0.074. This supersedes the §4 sentence permitting extension
"before further looks", which is recorded here as the defect being patched.
```

### 5. [MINOR] — Rule-precedence gap at the final look: N ∈ [100, 200) with futility bound < 0 yields NO-EDGE or UNDERPOWERED depending on the reader
**Spec section:** §4 table (row 2 "Any look with N ≥ 100" vs row 3 "else if N ≥ 200 → NO-EDGE; else → UNDERPOWERED").

**Failure scenario:** final trigger fires (last 2027 race scored) with N = 150, p = 0.60, one-sided 95% upper bound = −0.02. Reader A: the final look is "a look with N ≥ 100," row 2 applies → **NO-EDGE**. Reader B: the final row exclusively governs the final look; N < 200 → **UNDERPOWERED**. Two compliant implementations produce different *terminal verdicts* — one permanently closes the question, the other leaves the extension path open. (Also noted: the same verdict name "NO-EDGE" carries two evidentiary strengths — futility's affirmative "confidently negative" vs the final row's "failed to demonstrate"; the precedence fix below keeps both but makes which one fired unambiguous.)

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): final-look precedence (binds §4)

At the final look the verdict is evaluated in this order: EDGE if p ≤ 0.045
(subject to the K ≥ 20 floor); else NO-EDGE if N ≥ 200, OR if N ≥ 100 and the
one-sided 95% bootstrap upper bound of mean profit per pick is < 0 (the
futility criterion applies at the final look like any other look); else
UNDERPOWERED. The verdict line must name which arm fired.
```

### 6. [MINOR] — `src/market_benchmark.py` cannot be written from §6 alone: the results source is never named ("single source of truth" is literally false), "scored race" is undefined, and the snapshot-freeze regime the scoring amendment created is never referenced
**Spec sections:** §6; §1 ("a race with a scored prediction"); §3 ("Resample scored races").

**Failure scenario:** §6 declares "Input = the committed prediction JSONs (single source of truth…)" — but grading picks requires *official results*, which §6 never mentions. An implementer must invent: (a) where results come from (network refetch? `_wf.json`? the scoring amendment's frozen `_wf_scored.json`?) — a benchmark that refetches can grade against a *revised* feed and disagree with the scored row, resurrecting exactly the snapshot-drift hazard phase-1 finding 1 closed for the scoring spec; (b) what "scored race" means, given §6 simultaneously bans the scores CSV as input — results-exist-on-feed vs scores_log-row-exists vs snapshot-exists give different race sets; (c) the RNG/quantile/mean conventions of finding 1 item 5. That is at least three judgment calls in a spec family whose stated standard is zero.

**Evidence:** §6 bullet 1 (no results input named); scoring spec's snapshot-freeze AMENDMENT (creates `_wf_scored.json`, written *after* this spec was frozen at 22:48 vs 23:36 file times — this spec predates and never binds to it); `update_data.py` lines 29–35 (the `_wf.json` overwrite path that motivated the freeze).

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): §6 inputs pinned (binds §1, §3, §6)

The script's inputs are exactly two file sets: (a) the committed prediction
JSONs, hash-verified per scoring spec §1.3; (b) for each race, the frozen
results snapshot `src/data/races/{year}_{race_id}_wf_scored.json` written by
`score_race.py` at first scoring (scoring spec's snapshot-freeze amendment).
A race is "scored" for §1/§3 exactly when its snapshot file exists; grading
uses the snapshot only — never `_wf.json`, never the network, never
`scores_log.csv`. §6's "single source of truth" sentence is corrected to:
predictions from the sealed JSONs, outcomes from the frozen snapshots,
nothing else consulted. Resampling mechanics per the calibration-guards
amendment, item 5.
```

### 7. [MINOR] — Multi-book capture plus the dedup's recorded_utc preference lets recording order select best-of-books prices, quietly changing the null being tested
**Spec sections:** §2 (multi-book capture legal; primary-book designation "non-blocking"), §1's import of scoring §5.2 dedup (prefer closing, then **latest recorded_utc**).

**Failure scenario:** the owner records the same closing matchup at two books; dedup keeps the later-timestamped entry, and `recorded_utc` is operator-entered. Recording the better price for the model's side second makes best-price selection systematic while fully compliant. Computed: when two books disagree by more than the two-sided vig (e.g., X at −130/+110 vs X at +110/−130 across books — routine on thin props), taking the best price on a 50% side yields **EV = +0.05 per pick with zero model skill**. H0 "you can't beat the hold at the closing line" is then false under the operated procedure even with a worthless model — the test statistic measures line-shopping plus model, not the model against a closing line. The spec's own register flags primary-book designation but leaves it forever optional ("non-blocking"), i.e., the discretion never has to close.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): primary book binding (binds §2 and §1's
dedup import)

The primary book is named in the same commit as the first recorded price and
is thereafter fixed. Only primary-book entries are admissible to this spec's
statistic; entries recorded at other books remain in the JSON and feed the
scoring spec's descriptive counts only. If the primary book withdraws NASCAR
H2H markets, a successor is named by dated addendum BEFORE any successor-book
price is recorded. Reason, computed 2026-07-18: the imported dedup prefers the
latest recorded_utc, so multi-book capture lets recording order select the
best of several books' prices; where books disagree by more than the two-sided
vig this is +EV under per-book efficiency (±110 disagreement on a 50% pair →
+0.05/pick with zero model skill), which silently converts the tested
proposition from "beat the closing line" into "beat the best of all lines".
```

### 8. [MINOR] — The §5 power table is exact for a test the design never runs; the actual procedure's operating characteristics differ and its futility cost is unstated
**Spec section:** §5 ("Power — computed exactly, so nobody argues with it later"; consequence bullets).

**Failure scenario:** at the final look someone disputes an UNDERPOWERED/NO-EDGE call by citing the table ("the design had 64% power at 0.58"). The table is a **single-look, iid-binomial test of win rate at α = 0.05** — but the pre-registered procedure is sequential (final α 0.045), race-clustered, ROI-scaled, and can stop itself early for futility. Measured by simulation (44 races × 5 picks at −110, looks per race): actual power at true 0.58 = **0.51** (table row N=400 says 0.64; N=200 says 0.36); at a realistic sharp edge of 0.55 = **0.20**, with a **4.6% probability of a false futility stop** — a number appearing nowhere in §5. The spec's own §3 register concedes iid binomial "would overstate significance," which applies equally to the table's implied precision. The arithmetic is flawless (verified, every cell); the framing "so nobody argues with it later" attaches that authority to numbers that do not describe the procedure.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-data): §5 scope note

The §5 table is exact for the test it names — one look, iid binomial win rate,
H0 = 0.53, α = 0.05 — and is context only; it is not the operating
characteristic of the §3–§4 procedure. Simulated 2026-07-18 (44 races × 5
picks at −110, looks after every race, amended boundaries): power ≈ 0.49–0.51
at true win rate 0.58, ≈ 0.18–0.20 at 0.55, false-futility ≈ 0.05 at 0.55 and
≈ 0.01 at 0.58. No decision consumes the table; no argument may cite it
against a verdict.
```

### 9. [NIT] — §1's import scope should state that scoring §5.3's strict-book-favorite filter does NOT apply
**Spec section:** §1 ("schema and dedup exactly as `specs/scoring_methodology.md` §5"). The phrase scopes the import to §5.1–§5.2, so a pick'em-priced entry (devigged 0.5/0.5, excluded from `book_n`) IS a graded pick here — consistent with §1's own rationale (the book's pick is irrelevant; the model bets its side). But a reader who imports "§5" wholesale would drop pick'em entries and count a different N. **Amendment (append):** `Clarification (2026-07-18): §1 imports only the entry schema (scoring §5.1) and the malformed→dedup→void pipeline (scoring §5.2 and its pipeline-order amendment). Scoring §5.3's strict-book-favorite filter does NOT apply: a pick'em-priced entry is a graded pick, so this spec's N is not Σ book_n by design.`

### 10. [NIT] — §3's "stake-weighted mean break-even p*" is vacuous under flat stakes
**Spec section:** §3 secondary. With a 1-unit flat stake on every graded pick, the stake-weighted mean of p* is identically the simple mean; the qualifier invites an implementer to hunt for weights that do not exist. **Amendment (append):** `Clarification (2026-07-18): under 1-unit flat stakes the secondary's "stake-weighted mean break-even p*" equals the simple mean of p* over graded picks, and is computed as such.`

### 11. [NIT] — §5's end-2027 accrual range does not follow from its own inputs, and the honest low end sits 10% above the NO-EDGE boundary
**Spec section:** §5. Verified: exactly **14** non-SS points races remain in 2026 (16 remaining minus Daytona 5623 and Talladega 5631, per `src/data/race_list_2026.json` + `MY_TYPE`) ✓, and ~30 non-SS in a full season ✓ (36 − 6 SS), and 14 × 5–10 = 70–140 ✓. But (14+30) × 5–10 = **220–440**, not "≈ 250–400" (the 400 cap is defensible via the N ≥ 400 final trigger; 250 follows from nothing). The correct low end, 220, is 10% above the N ≥ 200 NO-EDGE threshold — the margin that finding 3's full-board duty protects. **Amendment (append):** `Clarification (2026-07-18): §5's own inputs give N ≈ 220–440 by end-2027 (the 400 figure reflecting the N ≥ 400 final-look cap); the low end is 220, not 250, leaving only a 10% margin over the N ≥ 200 NO-EDGE boundary — which the full-board recording duty exists to protect.`

---

## Verified clean

- **§5 power table — every cell recomputed exactly** (`scipy.stats.binom`, exact critical values k* = 33/62/119/174/229 at N = 50/100/200/300/400, actual sizes 0.0435/0.0437/0.0379/0.0464/0.0489 ≤ 0.05): 80%-power detectable rates 0.7040/0.6550/0.6215→0.622/0.6025→0.603/0.5920 and all twelve power cells match to the printed rounding (e.g., N=200 @ 0.60: 0.5875 → 0.59; N=400 @ 0.65: 0.9994 → 1.00). The 3-dp boundary cells were verified at adjacent grid points (power(0.621|N=200) = 0.797 < 0.80 ≤ 0.806 = power(0.622); power(0.602|N=300) = 0.799 < 0.80 ≤ 0.809). The §5 consequence "only a blowout (≥ 65–70%) triggers early efficacy in 2026" is directionally sound: exact binomial at α = 0.001, N = 70–140 gives power 0.10–0.40 at 0.65 and 0.35–0.85 at 0.70.
- **Profit formula for American odds is correct:** win = +100/|A| (A < 0) or +A/100 (A > 0), loss = −1 — verified against staking identities (−115 → +0.8696, +130 → +1.30); A = ±100 both give +1 consistently; A = 0 already excluded as malformed by the imported schema. "No pushes exist" holds because §1's model-pick condition imports §4's skip rules, which skip tied-finish pairs before grading.
- **Total-vs-mean equivalence in the resample:** every resample draws K races each contributing ≥ 1 pick, so resampled pick count > 0 and "total ≤ 0" ⟺ "mean per pick ≤ 0" — the p-value tests the primary statistic's scale coherently.
- **Efficacy and futility cannot both fire at one look:** p ≤ 0.001 leaves ≤ 0.1% of bootstrap mass at/below zero, so the 95th percentile is necessarily > 0. All other simultaneous-trigger overlaps (N crossing 400 with p ≤ 0.001, etc.) resolve to the same verdict; the sole precedence gap is finding 5's.
- **N-threshold boundary conditions** (≥ 50, ≥ 100, ≥ 200, ≥ 400) are sharp and consistently inclusive; N only changes at scored-race boundaries so "first of" is well-defined.
- **Futility direction and cost are sane:** under the exact-boundary null the futility rule stops 16–22% of paths (working as intended); under a true 10.7%-ROI edge (0.58) false futility is ≈ 1%. The structure — strict interim efficacy, CI-bound futility, single primary scale — is coherent; only the small-K calibration (finding 1) and final-look precedence (finding 5) needed repair.
- **Haybittle–Peto architecture itself:** with a *calibrated* 0.001 interim test, looks after every race are indeed nearly free — the amended rule's measured interim spend is 0.004–0.005 across ~25 armed looks, and total α lands at 0.044–0.049. The spec's register claim was right about the architecture and wrong only about the estimator.
- **Consistency with HANDOFF and the scoring spec:** the 0.5300 reference matches scoring §5.4 and the audit's 52–53% band (−113 two-sided → 0.5305, recomputed); the SS exclusion matches doctrine (Daytona/Talladega/Atlanta = SS in `MY_TYPE`; `track_type` frozen into the sealed JSON at prediction time, so the exclusion is deterministic); the bet-all-picks rationale correctly cites the audit's underconfidence finding (says 64%, reality 74% — report line 90); §6's hash-verification reuse of scoring §1.3 is sound (phase 1 verified the procedure against the real 5618 file); the ITT clause is coherent and the config dict it relies on exists in the sealed JSON.
- **Accrual counts against the real calendar:** exactly 14 actionable non-SS races remain in 2026 (verified race-by-race against `src/data/race_list_2026.json`); ~30 non-SS in a full 36-race season ✓; 70–140 by end-2026 ✓. Only the end-2027 range's low end fails (finding 11).
- **Unit-of-analysis definition (§1), post-amendment:** given the scoring spec's pipeline-order amendment (malformed → dedup → void), the imported dedup/void machinery is deterministic; the common-set and canonical-pick references are exact and were verified in phase 1 against the real prediction file (no canonical prob is exactly 0.5000; picks 100% concordant with pred_rank). Apart from findings 2 and 9's scope notes, two implementations agree on which entries are graded picks.

**Bottom line:** the spec's *decision architecture* — flat-stake ROI, race-clustered resampling, strict interim boundary, futility arm, pre-registered UNDERPOWERED — survives adversarial review, and its arithmetic is impeccable. What does not survive is the presumption that the machinery is pinned tightly enough to run unattended: the interim boundary is uncalibrated exactly where the accrual estimates put it (finding 1, verified fixable at negligible power cost), and four separate discretion channels (post-race entries, accrual throttling, look timing, extension-after-peeking) let an operator steer or stall the verdict without violating a single sentence. Every proposed amendment is legal only until the first book price is recorded — per HANDOFF, possibly this weekend — so adjudication should precede any price capture for race 5618.

---

# Adjudication (orchestrating session, 2026-07-19 pre-race, pre-first-price — per review/STATE.md protocol)

| # | Severity | Verdict | Reason |
|---|---|---|---|
| 1 | CRITICAL | **ACCEPT** — applied verbatim | The all-races-positive → p=0 mechanism is reproducible by construction (analytic cross-check 0.437²=0.191 confirms the K=2 cell); the amendment restores the spec's OWN claimed α (0.044–0.049 vs 0.061–0.096) at ≤0.02 power cost, preserving the architecture. Pre-data calibration repair is exactly what the amendment window exists for. |
| 2 | MAJOR | **ACCEPT** — applied verbatim | Circular admissibility reference verified by reading both specs; the fix grounds it in a mechanically checkable fact (commit time vs schedule start_time_utc, which exists in the race list). |
| 3 | MAJOR | **ACCEPT** — applied verbatim | All three escape scenarios are compliant-as-written; the fixes (looks-as-states, calendar backstop, full-board duty) are what the spec's "cannot be renegotiated" doctrine requires. NOTE FOR OWNER: this creates a real recording duty (all offered matchups at the primary book, every priced race) and a hard final-look date (first run on/after 2028-02-15). |
| 4 | MAJOR | **ACCEPT** — applied verbatim | Post-peek extension α inflation (0.045→~0.074) is the textbook failure; fresh-sample successor rule is standard discipline. |
| 5 | MINOR | **ACCEPT** — applied verbatim | Real precedence contradiction; two compliant readers reach different terminal verdicts. |
| 6 | MINOR | **ACCEPT** — applied verbatim | §6's "single source of truth" was literally false (results source unnamed); binding to the phase-1 snapshot-freeze regime is the only choice consistent with that amendment. |
| 7 | MINOR | **ACCEPT** — applied verbatim | Line-shopping EV (+0.05/pick with zero skill where books disagree beyond the vig) silently changes the tested proposition; the amendment still leaves WHICH book to the owner, so the owner-flagged decision survives — it just becomes binding at first price. |
| 8 | MINOR | **ACCEPT** — applied verbatim | The power table is exact for a test the design never runs; the scope note pins what may and may not be cited. |
| 9–11 | NIT | **ACCEPT** — applied as one clarifications block, sentences verbatim | Import scope, stake-weighting vacuity, and the 220-not-250 accrual low end are all mechanical. |

No OWNER escalation was strictly required (every fix is either a reproducible-math repair or an anti-gaming closure the spec's own doctrine mandates), but three accepted items change the OWNER's obligations and are flagged in the session summary: the full-board recording duty, the 2028-02-15 calendar backstop, and primary-book binding at first recorded price. The owner retains pre-data authority to overturn any of these by dated addendum BEFORE the first price is recorded.
