# Pivot-vetting memo — the multi-market "model book" (propose-only)

**Status:** design-vetting / pre-registration. **Proposes only; builds nothing, binds
nothing, commits nothing.** Changes no frozen spec, no model, no plan file. Produced
2026-07-20 (Opus 4.8 · thinking on · max). The session **STOPS for an owner GO on the
fork (§1)** before any of this is built or any plan/HANDOFF edit is committed.

**Method:** deep read of the frozen specs + audit + F7 + L5/L6 + plan, then **6 independent
adversarial refutation passes** (Opus, each prompted to *refute* one attack surface and my
provisional fix, grounded in the repo code/specs). Their convergent findings reshape the
design and are folded in below (§2). Findings ledger: `scratchpad/adversarial_findings.md`
(session-local).

---

## 0. Bottom line up front

The pivot **survives, but only heavily reshaped and rescoped.** The naive framing — *"shift
the project's center of gravity from beating the closing line to a self-graded multi-market
model book, priced from one coherent joint distribution, graded free on the 163 races"* —
does **not** survive the adversarial passes. Four of its load-bearing claims are refuted:

1. **"Self-graded calibration is a fast, free substitute for the starved benchmark."** False.
   The fast/free part (the on-hand 163-race backtest) is **in-sample** — the frozen config was
   *selected* on those races, the backtest already exists (`step6_calibration.py`) and its SS
   cell is already cited in the README. The only *decision-grade* calibration evidence lives on
   the **forward stream, which accrues at the same rate as the benchmark.** The "fast free thing"
   and the "rigorous thing" are mutually exclusive.
2. **"Coherent ⇒ trustworthy fair odds."** False. Coherence is a structural invariant of the
   readout that holds identically for the true utilities **and for pure noise**, so it carries
   *zero* evidential weight about correctness. (It is also already violated in today's code.)
3. **"Honest fair odds you can bet."** False for the raw model, which the audit measured as
   underconfident (says 64%, reality 74%). Betting a raw-model fair-odds tool against the book
   **is** the EV-threshold filter the market spec already pre-registered *against*.
4. **"Price all bet types."** Over-scoped. Stage/laps-led/margin/fastest-lap markets are **not
   functions of finishing order** and cannot be priced from PL at all — pricing them would drag
   the shelved generative model onto the critical path.

What **does** survive is real and worth building — but narrower and differently motivated than
the pitch: a **diagnostic** implied-price readout (order-derived, non-superspeedway markets)
that (a) doubles as a manual-capture **assist template** that helps *feed* the benchmark, (b)
yields a **genuinely faster calibration signal** for pooled non-SS two-outcome markets
(H2H/top-10 accrue ~30–60× more graded events per race than odds-gated picks — the one place
that truly escapes odds-starvation), and (c) produces documented calibration findings that
honestly **arm F7's generative-model trigger** for non-SS tails while confirming the SS
stand-down.

**Fork recommendation (§1): conditional DEMOTE — build the reshaped calibration/pricing thread,
keep the market benchmark as the sole external check and sole roadmap-#5 gate, and MECHANICALLY
TETHER it with three new gates so it cannot erode. If the tether gates will not be built, the
correct fork is STAY (benchmark remains the named center of gravity; calibration is an
explicitly subordinate thread). DROP is rejected.** In every case the reshaped calibration
work proceeds; the fork is purely about the benchmark's governance status.

---

## 1. The core distinction and the fork (STOP for GO here)

### 1.1 Calibration is not edge

| | **Calibration** | **Edge** |
|---|---|---|
| Compares | model vs **reality** | model vs **market** |
| Needs | on-hand outcomes (163 races) | real **closing prices** (perishable, admissibility-gated) |
| Cost | free | no cheap/ToS-clean NASCAR source exists (L6 §9) |
| Signal | "are our probabilities honest?" | "can we beat the book?" |
| Profit content | **none** — a fair book breaks even by construction | the whole question |
| Gates | nothing (measurement) | roadmap #5 (clean-air causal pace) |

These are **orthogonal axes.** That single fact drives the fork: the calibration thread's value
needs **no** change to the edge thread, so there is no reason to drop or weaken the edge thread
to gain it — and, conversely, a good calibration result can never *establish* an edge (the audit
already ruled calibration-against-reality into the "establishes zero betting edge" category).

### 1.2 The fork: STAY / DEMOTE / DROP

- **DROP** (retire the benchmark; make L5/L6/L2 odds capture optional). **Rejected.** It forfeits
  the project's *only* external, un-gameable adversary — the one metric the model can FAIL against
  something that isn't itself. The entire audit + governance apparatus exists *because* the prior
  effort graded its own homework (C5). Trading the external judge for a *more* self-graded metric,
  on the model's own fitting-era data, is the exact anti-pattern the project was built to prevent.
  It also buys only "freedom from weekly capture," which DEMOTE already provides.

- **STAY** (status quo: the benchmark remains the named center of gravity; calibration is a
  subordinate thread). **The safe default, and the honest floor.** "The benchmark is starved" is
  not the benchmark failing — it is a *deliberately slow external test working as designed* (spec
  §5 pre-registered a multi-year horizon; UNDERPOWERED is a legitimate pre-registered outcome).
  L6 §9.3's own numbers (~12–15 H2H/book, ~0.6–0.7 power by mid-2027) support the optimistic
  reading. STAY does **not** forbid the calibration/pricing work — it just keeps the project's
  *identity and maintenance-attention* on the external check.

- **DEMOTE** (calibration/pricing becomes a co-equal near-term focus; the benchmark stays alive
  and accruing but is no longer the sole thing the project is "about"). **Acceptable only with a
  mechanical tether.** The refutation pass on equity (attack f) is decisive here: a DEMOTE whose
  only protection is *prose* ("calibration is never edge; capture continues") is **strictly worse
  than STAY**, because it introduces a gratifying, low-friction, immediate-feedback self-graded
  scoreboard next to a perishable, tedious, already-0-for-1, no-signal-until-2027 external chore.
  Attention flows downhill by default (no bad faith required): capture lapses, N stays pinned near
  0, and "how's the model doing?" gets silently answered by the calibration number. The project
  would **look governed and be ungoverned** — the audit's sin, one level up. This repo's own
  philosophy is that *prose drifts and only gates hold* (gates 7–10). So DEMOTE is honest **only
  if** the governance boundary is converted from prose to gates, in the **same session** that
  demotes.

### 1.3 Recommendation

**Conditional DEMOTE + mechanical tether** (equivalently: keep the benchmark sovereign in
governance, add the reshaped calibration thread as a first-class parallel deliverable, and
gate-protect the benchmark). Concretely, GO means all of:

1. **Build the reshaped calibration/pricing thread** (§4) — for its *honest* value (operational
   capture-assist that helps feed the benchmark; a faster calibration signal on pooled non-SS
   two-outcome markets; C-trigger evidence), not as an escape from the benchmark's slowness.
2. **Keep the market benchmark as the sole external check and sole #5 gate.** Do not drop it; do
   not let calibration substitute for it; its spec stays frozen and untouched; E1 manual capture
   continues.
3. **Ship three mechanical tether gates** (§3.3) that convert the governance boundary from prose
   to code: a benchmark-liveness gate, a calibration-is-not-edge non-substitution gate, and a
   #5-stays-market-gated check. **Required for DEMOTE; recommended even under STAY.**

**If you do not want to build the tether gates, choose STAY** — the reshaped calibration thread
still gets built, just explicitly subordinate, with the benchmark keeping the named center of
gravity. Either path is defensible. **DROP is not.**

> This is the single most consequential decision and it is yours. The rest of this memo (§2–§6)
> specifies exactly what GO unlocks and how the design survives the adversarial passes, so the
> choice is fully informed. **Nothing below is built until you pick the fork.**

---

## 2. Adversarial findings — how the design survives (or must change)

Six independent passes, each told to *refute*. Verdicts and the fixes now baked into the design:

### (a) Circularity / in-sample optimism — SERIOUS-BUT-FIXABLE
**Refutation.** Walk-forward re-fits the PL *coefficients* as-of, but the *configuration*
(feature set, model class, `MY_TYPE` typology, half-life 8, λ=0.5) was human-selected on the
same 163 races — walk-forward launders βs, not config selection. The 2026 "OOS" is **not a
lockbox**: the audit reported 2026 ρ and per-type breakdowns and *leaned on them to justify
freezing*, so it was a peeked confirmation set. Decision-grade calibration therefore collapses
onto the **forward stream (5618+) = N=1 today** — the same trickle that underpowers the
benchmark. And 20 OOS races cannot populate per-market curves (win = ~20 winner events, never
decision-grade; SS = ~2–3 races).
**Survives via:** decision-grade evidence pre-registered onto the **forward** stream only; the
163-race run is a **development smoke test, labeled in-sample/contaminated, barred from any
decision and from fitting any recalibration map**; 2026 reported as a secondary already-seen
cut. **Residual:** the decision-grade calibration signal is as slow as the benchmark for
anything except pooled dense markets — which is the honest scope (below).
**The one genuine win:** pooled dense **two-outcome** markets (H2H, top-10) yield ~700 pairs /
~380 driver-rows **per forward race**, free and complete (not odds-gated) — ~30–60× the
benchmark's ~12 odds-gated picks/race, reaching usable power in ~one forward season. This is the
real, narrow value; it does **not** extend to win/group/SS/stratified verdicts.

### (b) Metric-shopping — FATAL as framed / FIXABLE only with hard scoping
**Refutation.** "Per-market calibration curves as the deliverable" is a metric×market×metric×
split×recalibration buffet — some cell looks good at nearly every look. The leak channel is
**belief, not a file**: the README *already* promoted one cell (H2H×Brier×SS = 0.2514) into
live stand-down doctrine with zero `scores_log` involvement — so firewalling the frozen scoring
log does nothing. "Descriptive-only" is cosmetic unless there is a **single mechanical verdict**
that no descriptive number can enter (the property that makes EDGE and the pooling adopt-Boolean
un-shoppable).
**Survives via:** the graded *decision* surface collapses to **exactly one pre-registered cell**
— market×metric×population×calibration-state + numeric threshold + a **named downstream
consequence** + a mechanical verdict — accrued on the **fresh forward sample**; the primary cell
is H2H/full-order-consistent (never top-K); all other cells are a **finite, sealed, non-citable**
appendix (no open-ended "…/per market"); Bonferroni over the honestly-counted family + a
practical-significance floor + at-most-one-action + a terminal no-re-litigation clause. The
frozen `scores_log.csv` (ρ + H2H only, top-K still banned) is untouched — the calibration log is
a *separate* artifact, not a §6 amendment.

### (c) Underconfidence / recalibration — SERIOUS-BUT-FIXABLE
**Refutation.** "Honest fair odds" is false for the raw underconfident model, and *using* such a
tool (compare to book, bet edge) **is** the EV-filter the market spec §1 explicitly rejected. The
provisional "recalibrate the readout but not H2H" carve-out is **incoherent** — a per-marginal
patch creates an internal Dutch book across your own quotes. Recalibration is **not an F10
sibling**: F10 gates on ρ, which is rank-invariant and therefore *blind* to any monotone
recalibration.
**Survives via:** **step 1 prices the RAW model as a labeled diagnostic — the word "honest" is
struck.** Recalibration is a **separate, later spec** with a **new proper-scoring gate**
(log-loss/Brier/ECE), applied at the **utility-vector level** (re-propagated to all markets),
**as-of fit** (params from strictly prior races). Key subtlety: the miscalibration **reverses
sign by track type** (non-SS underconfident, SS worse-than-coin-flip), so no single
sign-preserving map both calibrates and leaves the benchmark untouched. Therefore: a **temperature
map** (u→u/T, T<1) is ρ- and H2H-pick-invariant ⇒ benchmark untouched, **no fork**, but SS-
incomplete; a **flexible/per-type map** is not sign-preserving ⇒ it may flip picks and must **fork
a fresh benchmark counter** (the extension-discipline amendment already forbids re-scoring the old
stream). "Bayesian ⇒ better calibrated" is **false** here (posterior averaging pushes toward 0.5,
worsening underconfidence) — do not lean on it.

### (d) Coherence masks misspecification — FIXABLE downward-scoped; one sub-claim FATAL
**Refutation.** Coherence is a structural invariant that holds identically for signal and for
noise ⇒ **zero** evidential weight about correctness; "coherent ⇒ trustworthy/fair" must be
**struck** (FATAL as worded). It also *hides* PL's unidimensional misspecification (F7 §6: one
utility sets center and tails; PL cannot represent win-or-wreck), which corrupts exactly the
tail markets — **win everywhere**, and **all SS markets** (SS is near-pure noise: ρ 0.16,
confident picks 56%, Brier 0.2514 < coin flip). Second FATAL-as-worded point: routing *all* poor
tail/SS calibration into "evidence for the generative model C" is a **diagnosis error** — SS is
**no-signal**, which C does **not** fix (C fixes tail *shape*, not *absence* of ordering info).
**Survives via:** the pricing layer is a **PL-faithful readout, never "correct pricing"**;
coherence is stated as internal-consistency only; mandatory **per-market × per-track-type**
reliability (pooled aggregate reported but never a decision input — it provably hides SS); a
pre-registered **stand-down** on structurally-corrupted markets (all SS; win/tail pending their
own evidence), reusing the existing `stand_down` flag; and an explicit **split**: SS poor
calibration → stand-down/irreducible (**not** a C-trigger); thin-tail **non-SS** poor
calibration → the legitimate C-trigger. Honest actionable scope = **non-SS mid-order markets
(top-5/top-10/H2H on short/int/road)** — exactly the audit-validated region.

### (e) Compute feasibility — MCMC concern OVERSTATED (red herring); MC discipline FIXABLE
**Refutation + rebuttal.** The "MCMC over 163 races × weekly refits" fear targets a path the
pivot does not take: **F10 = exact scalar Kalman filtering — minutes/pass, deterministic, zero
new deps** (MCMC lives only in the NULL generative model C and the blocked Laplace-first F11).
MC pricing raw compute is **cheap** — one 40k-draw Gumbel block per race, reduced into every
order-market (seconds–minutes for the whole backtest, *not* 150–350 × 163). Real risks are
bounded: tail variance bites only at p≲0.5%; **log-loss** can blow up in the tails (p̂=0 → +∞);
reliability regression-dilution can flatter the tails; determinism vs the seed-pinned gates.
**Survives via:** **analytic-where-exact** (win = softmax *exactly* — this removes the worst-tail
market from MC entirely; H2H already analytic; manufacturer = Σ softmax), MC only for joint
top-N/group at p~0.1–0.5 where 40k is ample; a pre-registered probability floor (log-loss never
sees 0); per-market MC-SE bounds with an exclude/raise-N rule; pinned seed/N/RNG/numpy/interpreter
+ a **committed fixture** so the gate reproves rather than re-draws; common random numbers across
the A/B. **Hard scope boundary:** MC prices **order-derived markets only**; stage/laps-led/margin/
fastest-lap are not order functions and route to C's gate, never the cheap readout.

### (f) Abandoning hard-won equity — the fork is the answer (see §1)
**Refutation.** Equity (2) was never the documents — it was the **live subordination of the
project's self-assessment to an external judge**. The pivot keeps the documents and removes the
judge; a frozen-but-unfed benchmark is a *monument* to governance, not governance. Guardrails
stated as prose are exactly the "good-intentions-that-erode" this repo elsewhere refuses to
tolerate.
**Survives via:** the fork recommendation (§1.3) — conditional DEMOTE with a **mechanical tether**
(§3.3), or STAY. The equity is preserved iff the benchmark stays *sovereign and gate-protected*,
not merely frozen.

---

## 3. Doctrine reconciliation

### 3.1 New specs (pre-registered BEFORE any code, per `specs/README.md`)
1. **`specs/pricing_layer.md`** — the Monte-Carlo **diagnostic** readout. Order-derived markets
   only; analytic-where-exact; coherence = internal-only (explicitly *not* correctness); pinned
   seed/N/RNG/numpy/interpreter + committed fixture; prob-floor + per-market MC-SE bounds; a
   **faithful-read gate** (priced marginals reproduce `predict_next`'s existing p_win/p_top5/
   p_top10/h2h_prob within MC error) proving it reads the frozen model without changing it;
   prices labeled **"raw-model implied (known underconfident)"**, stand-down on SS/tail markets.
2. **`specs/calibration_backtest.md`** — the pre-registration. One locked primary decision cell +
   named consequence + mechanical verdict on the **forward** sample; 163 = dev-only/in-sample-
   labeled/barred-from-decision-and-recal-fitting; 2026 = peeked secondary cut; **dual pooled +
   per-track-type reporting with a pooling-launder ban** (SS never hidden); ported small-sample
   machinery (race-count floor, race-clustered bootstrap + pinned seed, terminal/extension
   discipline); published **power triage** (decision-grade scope = pooled dense non-SS two-outcome
   markets; win/group/SS/stratified = descriptive-only until a pre-registered horizon extension).
3. **`specs/recalibration.md`** (later; gated) — utility-level, as-of-fit, **new proper-scoring
   gate**; temperature-first (benchmark-untouched, SS-incomplete) vs flexible-map (forks a fresh
   benchmark counter). Honors `specs/README`'s deliberate deferral of the underconfidence fix.
4. **`specs/allbet_capture_schema.md`** (lowest priority; only if you want non-H2H *book* capture)
   — `book_prices.entries` is H2H-shaped (`driver_id_a/b`, `price_a/b`); win/top-k need a new
   structure, **descriptive-only** (can never feed the H2H-only benchmark). = L6 §9.5's flagged
   future work.

### 3.2 Re-homed / superseded (all proposed, on GO)
- **L5 / L6** (already **done**, `f995e07` — a concurrent session closed them mid-vetting): the
  vendor question is **answered** (§9: no viable vendor; stay manual). No action needed.
- **F20** (this vetting session): → **done** on this memo's commit; deliverable
  `research/pivot_model_book_vetting.md`; decision DEMOTE + tether. The `next` slot passes to M1.
- **L2** (build fetcher): stays **moot** (no vendor). Its "manual-capture assist" role is instead
  delivered by the pricing layer's readout template — exactly L6 §9.7 item 5.
- **F10** (Kalman dynamic-skill): **re-homed** as the pivot's underlying-model upgrade (step 2);
  its frozen ρ-Wilcoxon gate is **unchanged**; the calibration harness is an *additional* eval
  surface (secondary), never a replacement gate. Note: recalibration is **not** F10's job (ρ-blind).
- **F7 formulation C** (generative simulator): the pivot's scored surface **arms its trigger T1** —
  so the plan text "C stays F7-NULL unless a trigger fires" is now **inaccurate** and must be
  reconciled to "T1 armed by the pricing surface; C drafted-justified for **non-SS tails only**;
  SS is stand-down, not a C-target." C stays gated/unbuilt.
- **F2 / F11 / G1-G2**: unchanged. G1/G2 stay **EDGE-gated** (the #5 unlock stays pinned to the
  market verdict — tether gate 3).

### 3.3 The three tether gates (the price of an honest DEMOTE)
1. **Benchmark-liveness gate (new gate 11).** On every `run_gates.sh`, reconstruct and print the
   benchmark's live state (N, K, standing verdict, last admissible priced race); **fail red** if
   the season is live and predictions are accruing while admissible priced races fall behind by
   more than a small tolerance. Converts the silently-droppable capture chore into a loud,
   un-ignorable signal on the same surface that proves the model still reproduces 0.413/0.476/0.447.
2. **Calibration-is-not-edge non-substitution gate.** In the gates-7–10 prose→gate idiom: assert
   no spec/README/HANDOFF/report claims an EDGE or "beats the book" on calibration/proper-scoring
   evidence, and that the #5 execution gate still reads the market verdict.
3. **#5-stays-market-gated.** Encode that `clean_air_causal_pace.md`'s execution gate reads the
   **market-benchmark** verdict, never the calibration verdict — the forbidden inference
   (calibration → edge → #5) cannot be committed without a red gate.

### 3.4 Untouched (frozen)
PL config; all frozen spec sections; `market_benchmark_decision_rule.md` + `scoring_methodology.md`
(including the top-K ban and `scores_log.csv` contract); the 10 gates + the D-gate trio; E1 weekly
capture; doctrine (SS stand-down, no post-hoc, one-step-at-a-time, frozen config needs a gated A/B).

---

## 4. Architecture (reshaped)

**Axis 1 — underlying model (joint finishing-order distribution):** PL (frozen baseline) →
Bayesian-PL (**F10 = exact Kalman**, ρ-gated A/B) → optional PL+Bayesian ensemble (gated on F10) →
[shelved: generative simulator **C**, trigger-armed for non-SS tails only].

**Axis 2 — pricing layer (Monte-Carlo DIAGNOSTIC readout):** from the frozen engine's as-of
utility vector, price **order-derived markets only** (win, top-N, H2H, manufacturer, group
matchups); **analytic where a closed form exists** (win = softmax; H2H = σ(Δu); mfr = Σ softmax),
MC (one pinned 40k Gumbel block/race) only for joint top-N/group; fair American odds. **Coherence
= internal no-self-arbitrage only, explicitly not correctness.** Labeled raw-model-implied;
stand-down on SS and tail markets. Faithful-read gate proves it changes nothing frozen. Doubles as
the **manual-capture assist template** (surfaces the field's valid matchups + model implied
prices for fast, full-board transcription — helping *feed* the benchmark).

**Walk-forward calibration protocol:** reuse the D1 gold as-of utilities; price each race; compare
to realized outcomes; **per-market × per-track-type** Brier/log-loss/reliability; split in-sample
(163, dev-only) / OOS-2026 (peeked, secondary) / **forward (decision-grade)**; one locked primary
cell drives the only mechanical verdict; ported anti-shopping machinery. Poor calibration is a
**pre-registered expected finding**: non-SS tails → arms C; SS → confirms stand-down.

**How F10 plugs in:** an underlying-model A/B, ρ-gated (unchanged); the harness re-prices and
reports its calibration impact (secondary). Recalibration is a *separate* utility-level,
proper-scoring-gated spec — never folded into F10.

---

## 5. Re-sequenced plan (proposed sprint table)

Proposed **new phase M — "Model book (multi-market pricing + calibration)."** Lighter alternative:
fold into Phase F (less shape churn). Recommend the new phase for visibility. All rows gated on the
fork GO. **The single next actionable is M1 (the spec + tether gates) — judgment-shaped, Opus.**

**Phase M goal:** an honestly-scoped diagnostic pricer + pre-registered calibration harness, with
the benchmark mechanically tethered. Model: Opus for the spec (judgment), Sonnet for the builds.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---|---|---|---|---|---|
| M1 | Pricing + calibration **pre-registration spec** + tether-gate design | ⬅ next (on GO) | Opus 4.8 · thinking on · xhigh | ~3–5 h | Write the rulebook before any code: what gets priced, what one number decides anything, and the gates that keep the external benchmark alive. | Author `specs/pricing_layer.md` + `specs/calibration_backtest.md` per §3–§4: order-derived scope, analytic-where-exact, coherence≠correctness, one locked primary cell on the forward sample, dual pooled+per-type with launder ban, ported small-sample machinery, power triage, faithful-read gate; design the 3 tether gates. Judgment-shaped — locking the primary cell, the scope boundaries, and striking the overclaims is where error is expensive. |
| M2 | Build the diagnostic pricer + faithful-read gate + capture-assist template | blocked (M1) | Sonnet 5 · thinking on · high | ~3–5 h | Turn the model's existing simulation into a labeled fair-odds readout that also speeds up the weekly manual capture. | Generalize `predict_next.py`'s 40k-Gumbel readout into order-derived market pricing (analytic where exact); pinned seed/N/numpy + committed fixture; faithful-read gate; emit the capture-assist template. Zero new deps. No frozen model change. |
| M3 | Run the walk-forward calibration backtest (frozen PL) | blocked (M2) | Sonnet 5 · thinking on · xhigh | ~2–4 h | Grade the model's probabilities honestly per the pre-registered rules; report where they're trustworthy and where they're not. | Per-market × per-type Brier/log-loss/reliability over 163 (dev) + 2026 (secondary) + forward (decision-grade); the one primary cell's mechanical verdict; publish the power triage; arm C for non-SS tails, confirm SS stand-down. Numbers must be right — escalate to Opus on any judgment call. |
| M4 | Ship the 3 tether gates + demote (or keep STAY) | blocked (M1) | Sonnet 5 · thinking on · high | ~2–3 h | Make "the benchmark stays sovereign" a machine-checked fact, not a promise. | Gate 11 (benchmark liveness), non-substitution prose→gate, #5-stays-market-gated; wire into `run_gates.sh`/GATES.md; update standfirst/bottom_line/shape_sig. **Ships in the same beat that demotes** (the §1 condition). |
| — | **F10** Dynamic-skill (Bayesian-PL) A/B | blocked (unchanged) | Sonnet 5 · thinking on · xhigh | ~2–4 h | Step 2: test the one Bayesian idea with documented headroom. | Existing frozen ρ-gate unchanged; re-priced + calibration-evaluated (secondary). Gated: ≥8 scored races + gold + F1/F2 decisions. |
| — | **M5** Optional PL+Bayesian ensemble A/B | blocked (F10) | Sonnet 5 · thinking on · xhigh | TBD | Step 3: blend the two models only if it earns its keep. | Short spec + A/B; blocked on F10's outcome. |
| — | **Recalibration** spec + A/B (separate) | blocked | Opus (spec) / Sonnet (run) · xhigh | TBD | Fix the known underconfidence — carefully, with a new kind of gate. | `specs/recalibration.md`: utility-level, as-of-fit, new proper-scoring gate; temperature-first (benchmark-untouched) vs flexible (forks a fresh counter). |
| — | **F7-C** Generative simulator | blocked (trigger armed) | Fable/Opus (spec) / Sonnet (build) | TBD | Step 4: build the tail-honest model only on an explicit trigger-pull. | T1 armed by M3's non-SS tail findings; SS is stand-down, not a C-target. Stays NULL until you elect to pull it with a pre-registered scored surface. |

**Standing:** E1 weekly capture continues (perishable; DEMOTE keeps it; gate 11 protects it). The
market benchmark keeps accruing toward its 2027–2028 verdict.

**Bottom line:** build a narrow, honest, gate-protected calibration/pricing thread; keep the
external judge sovereign; strike every overclaim the passes exposed.

---

## 6. Proposed plan/HANDOFF edits (NOT applied — apply on GO)

- `plan/schedule.yml`: mark **F20 → done** (this vetting session; ref = this memo's commit;
  status_note records the DEMOTE+tether decision + deliverable). **L5/L6 already done** (`f995e07`);
  note **L2 moot** (superseded by M2's readout as the capture assist). Add **phase M** + rows M1–M5
  after phase F (deps-before-dependents: M1 deps F20), with **M1 as the new single `next`**; update
  **F10** status_note (re-homed as pivot step 2); update the **Phase F note** (C's T1 armed by M;
  SS not a C-target); refresh **standfirst / bottom_line / handoff_note** and `--sync-shape`.
- `HANDOFF.md`: new "Current status" entry (this vetting session, fork decision); a doctrine line
  that **calibration is model-quality, never edge, never unlocks #5**; roadmap note that the model
  book is a parallel thread with the benchmark tethered.
- Exactly one `next` preserved (M1); all 10→11 gates green before/after; nothing frozen touched.

Full detail for each edit is in this memo's §3–§5; the diffs are drafted at apply time to avoid
hand-editing rendered files (PLAN.md is generated).

---

## 7. The GO ask

**Pick the fork (§1):** conditional **DEMOTE + tether** (recommended) / **STAY** (calibration
subordinate) / **DROP** (rejected). The reshaped calibration/pricing thread is built under either
of the first two; the choice is the benchmark's governance status and whether the tether gates
ship. On GO I will (in a *separate build session*, per planning-mode doctrine) write the M1 spec
first, then build — nothing before your decision.

---

## 8. DECISION (owner, 2026-07-20)

**Fork: DEMOTE + tether (chosen).** Build the reshaped calibration/pricing thread as a co-equal
near-term focus; the market benchmark stays the **sole external check + sole roadmap-#5 gate**;
the three mechanical tether gates (§3.3) ship in the same beat that demotes. DROP rejected; STAY
was the conservative alternative.

**What this GO settles / does not.** It resolves the fork only. It does **not** authorize building
code, editing any frozen spec, or committing plan/HANDOFF — those remain for the separate M1+
build sessions (planning-mode doctrine). The plan/HANDOFF edits in §6 are **proposed, not
applied**; this memo is uncommitted.

**Next:** the **M1** pre-registration spec session (Opus 4.8 · thinking on · xhigh) — authors
`specs/pricing_layer.md` + `specs/calibration_backtest.md` and the tether-gate design per §3–§4,
and applies the §6 plan/HANDOFF edits, **before any pricing code**.
