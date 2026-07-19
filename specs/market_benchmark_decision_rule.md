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

- Primary book designation (§2).
- If NASCAR H2H markets turn out too thin to yield ≥5 priced matchups/race
  at the accessible book, the accrual estimates in §5 shrink; the rule
  itself is unchanged, but expect UNDERPOWERED and plan accordingly.
