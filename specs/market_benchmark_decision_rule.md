# SPEC: Market-benchmark decision rule (roadmap #1 gate) — FROZEN

**Status:** pre-registered 2026-07-18, before any book price has been
recorded or any race scored. This spec exists so the decision "a live edge
over the closing line exists" **cannot be renegotiated after results start
arriving** — in either direction. A negative result is a valid outcome
(HANDOFF doctrine).

**Question decided:** does the frozen model, operated per the weekly
protocol, produce head-to-head picks that beat the book's closing prices?
**Consumers:** EDGE unlocks roadmap #5 (causal clean-air pace). NO-EDGE
keeps #5 permanently closed for this model family and the project continues
as a public forward log / feature-research effort only.

---

## 1. Unit of analysis: the graded pick

One graded pick = one deduped, non-void, well-formed `book_prices` entry
(schema and dedup exactly as `specs/scoring_methodology.md` §5) on a race
with a scored prediction, where:

- the race is **non-SS** (`track_type != "SS"`) — doctrine stand-down; SS
  picks are recorded but never enter this statistic;
- both drivers are in that race's common set (classified finishers);
- the model has a pick under the canonical h2h rule (prob ≠ 0.5000).

**The model bets every graded pick** — 1 unit flat stake on the model's
side at that side's recorded price, *including* picks where model and book
agree. Rationale, recorded: "edge over the closing line" means the pick
stream is profitable after hold; restricting to model-perceived +EV spots
was rejected because the audit (§7) showed the model is systematically
*underconfident* (says 64% when reality is 74%), which would bias and
starve an EV-threshold filter. No filter, no discretion.

Profit per pick at American odds `A`: win → `+100/|A|` if `A < 0`, else
`+A/100`; loss → `−1`. Grading by official finishing position (DNFs count;
book-voided entries were already excluded). No pushes exist.

## 2. Data-collection requirements

- Record closing H2H prices (`closing: true`, target within ~30 min of
  green) for **every** race where a prediction was committed, at whichever
  book(s) the owner can access. A race with no recorded prices contributes
  zero picks and does not bias the statistic (missingness is
  price-availability-driven, not outcome-driven — record prices **before**
  the race, never after).
- **Flagged decision for the owner (non-blocking):** designate one primary
  book at first recording and keep using it; the dedup rule handles
  multi-book capture meanwhile. Consistency matters more than which book.
- Config drift: picks are evaluated **intention-to-treat** — every pick made
  by whatever config was frozen at its prediction time counts. If roadmap #4
  adoptions change the config mid-stream, do not restart the counter; the
  prediction JSONs record their config, and the final look reports a
  by-config sensitivity split (descriptive only, not a gate).

## 3. Pre-registered statistic and test

- **Primary statistic:** mean profit per pick (flat-stake ROI), over all
  graded picks accumulated to date.
- **Primary test:** one-sided race-clustered bootstrap of H0 "E[profit] ≤ 0".
  Resample scored races (those contributing ≥1 pick) with replacement,
  B = 10,000, seed = 20260718; each resample's statistic = total profit of
  the resampled races' picks. `p = fraction of resamples with total ≤ 0`.
  Race-level clustering because picks within a race share outcomes.
- **Secondary (descriptive only, never a gate):** pick win rate vs the
  stake-weighted mean break-even `p*` of taken prices, and vs the fixed
  0.5300 reference (scoring spec §5.4).

## 4. Decision schedule (sequential, Haybittle–Peto style)

Let N = cumulative graded picks. Looks happen after each race is scored
(computation is cheap; the boundaries below keep total α ≈ 0.05).

| Trigger | Rule | Verdict |
|---|---|---|
| Any look with N ≥ 50 | bootstrap p ≤ 0.001 | **EDGE** (early stop) |
| Any look with N ≥ 100 | one-sided 95% bootstrap upper bound of mean profit per pick < 0 | **NO-EDGE** (futility stop) |
| Final look — first of: N ≥ 400, or last 2027 points race scored | p ≤ 0.045 → **EDGE**; else if N ≥ 200 → **NO-EDGE**; else → **UNDERPOWERED** | terminal |

- UNDERPOWERED is a legitimate, pre-registered outcome: roadmap #5 stays
  closed, the log keeps accumulating, and any extension of the test window
  must itself be pre-registered (dated addendum) **before** further looks.
- No other peeking rule, threshold, stake scheme, or pick filter may be
  introduced after the first price is recorded. Interim ROI numbers may be
  *reported* weekly (they're in the open repo anyway) but carry no
  decision weight outside this table.

## 5. Power — computed exactly, so nobody argues with it later

Exact one-sided binomial power against H0 win rate = 0.53 (α = 0.05),
computed 2026-07-18 (`comb`-exact, no approximation):

| N picks | 80%-power detectable true win rate | power if true = 0.58 | if 0.60 | if 0.65 |
|---|---|---|---|---|
| 50 | ≥ 0.704 | 0.16 | 0.24 | 0.51 |
| 100 | ≥ 0.655 | 0.24 | 0.38 | 0.77 |
| 200 | ≥ 0.622 | 0.36 | 0.59 | 0.95 |
| 300 | ≥ 0.603 | 0.52 | 0.78 | 0.99 |
| 400 | ≥ 0.592 | 0.64 | 0.88 | 1.00 |

Accrual reality: ~14 actionable (non-SS) races remain in 2026; a full 2027
season adds ~30. At 5–10 priced matchups per race, expect **N ≈ 70–140 by
end-2026 and ≈ 250–400 by end-2027.** Consequences, stated up front:

- One season **cannot** resolve a realistic sharp edge (true 55–58%); only
  a blowout (≥ 65–70%) triggers the early-efficacy boundary in 2026.
- The design therefore runs through 2027 by default, with futility armed
  from N = 100 so a clearly dead model stops burning effort.
- If the final look lands UNDERPOWERED with a positive-but-unproven ROI,
  that is reported as exactly that — not as "basically an edge."

## 6. Implementation notes (for the eventual `src/market_benchmark.py`)

- Input = the committed prediction JSONs (single source of truth; the
  scores_log CSV counts are human-readable summaries and are NOT the input).
- The script recomputes picks/grades from scratch each run (idempotent),
  prints N, total profit, ROI, bootstrap p, the CI bound, current verdict
  per §4, and the by-config split.
- Fixed seed 20260718 makes every look reproducible.
- Verify each JSON's hash (scoring spec §1.3) before using it; skip and
  loudly report any file that fails.
- Not to be written until it has inputs (first priced, scored race). No
  production-code change to the model is involved at any point.

## Resolved-ambiguity register

- Bet-all-graded-picks (not EV-filtered) → underconfidence would bias a
  filter; the null "you can't beat the hold" is the honest null.
- ROI (price-aware) primary, win-rate secondary → "edge over the closing
  line" is a statement about prices, not orderings.
- Race-clustered bootstrap → within-race picks are correlated; iid binomial
  would overstate significance.
- Haybittle–Peto (interims at 0.001, final at 0.045) → arbitrarily many
  cheap interim looks without meaningful α inflation, trivial to implement.
- Futility on the bootstrap CI bound (not win rate) → single primary scale.
- Intention-to-treat across config versions → the thing being tested is the
  operated system; per-config splits are descriptive.

## Flagged (owner decisions, non-blocking)

- Primary book designation (§2). [Superseded by the primary-book-binding
  amendment below: still the owner's choice, but it becomes fixed in the
  same commit as the first recorded price.]
- If NASCAR H2H markets turn out too thin to yield ≥5 priced matchups/race
  at the accessible book, the accrual estimates in §5 shrink; the rule
  itself is unchanged, but expect UNDERPOWERED and plan accordingly.

---

# Amendments — adversarial review, 2026-07-19 (pre-data; no book price has
# been recorded). Source: review/findings_phase2.md, adjudicated per
# review/STATE.md. Verbatim as proposed by the reviewer, who verified the
# statistical repairs by simulation before proposing them.

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

## AMENDMENT (2026-07-18, pre-data): final-look precedence (binds §4)

At the final look the verdict is evaluated in this order: EDGE if p ≤ 0.045
(subject to the K ≥ 20 floor); else NO-EDGE if N ≥ 200, OR if N ≥ 100 and the
one-sided 95% bootstrap upper bound of mean profit per pick is < 0 (the
futility criterion applies at the final look like any other look); else
UNDERPOWERED. The verdict line must name which arm fired.

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

## AMENDMENT (2026-07-18, pre-data): §5 scope note

The §5 table is exact for the test it names — one look, iid binomial win rate,
H0 = 0.53, α = 0.05 — and is context only; it is not the operating
characteristic of the §3–§4 procedure. Simulated 2026-07-18 (44 races × 5
picks at −110, looks after every race, amended boundaries): power ≈ 0.49–0.51
at true win rate 0.58, ≈ 0.18–0.20 at 0.55, false-futility ≈ 0.05 at 0.55 and
≈ 0.01 at 0.58. No decision consumes the table; no argument may cite it
against a verdict.

## AMENDMENT (2026-07-18, pre-data): clarifications from adversarial review

- Clarification (2026-07-18): §1 imports only the entry schema (scoring §5.1)
  and the malformed→dedup→void pipeline (scoring §5.2 and its pipeline-order
  amendment). Scoring §5.3's strict-book-favorite filter does NOT apply: a
  pick'em-priced entry is a graded pick, so this spec's N is not Σ book_n by
  design.
- Clarification (2026-07-18): under 1-unit flat stakes the secondary's
  "stake-weighted mean break-even p*" equals the simple mean of p* over graded
  picks, and is computed as such.
- Clarification (2026-07-18): §5's own inputs give N ≈ 220–440 by end-2027
  (the 400 figure reflecting the N ≥ 400 final-look cap); the low end is 220,
  not 250, leaving only a 10% margin over the N ≥ 200 NO-EDGE boundary — which
  the full-board recording duty exists to protect.
