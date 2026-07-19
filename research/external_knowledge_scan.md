# External NASCAR knowledge scan — academic, betting/DFS, open-source, data sources (F6)

**Session:** F6 research spike · Fable 5 · 2026-07-19
**Status:** research report — **proposes only.** Nothing here builds anything,
changes any frozen spec, or touches the production model. Doctrine, verbatim
(INTEGRATION.md / plan): **nothing enters the frozen PL prediction model
without its own pre-registered, walk-forward-gated A/B**, and only
licensed / terms-of-service-clean sources are used.
**Deliverable:** the credible, transferable external ideas — each cited,
credibility-assessed, mapped to this project's architecture and governance,
overlap-checked against everything already built or planned, and turned into
candidate plan sessions (§8–§9).

---

## 0. Executive summary

The external landscape converges on five messages:

1. **The strongest transferable idea is a likelihood change, not a feature.**
   The reverse-Plackett-Luce "attrition" model — proposed *for NASCAR*
   (Graves et al. 2003) and shown in a walk-forward F1 study with proper
   scoring rules to clearly beat standard PL on winner/top-3/top-10
   forecasts (Henderson & Kirrane 2018) — models the finishing order
   bottom-up as a dropout process and stops over-punishing good drivers for
   DNF-driven lowly finishes. That is precisely NASCAR's attrition profile,
   and it attacks the same top-of-field miscalibration our audit measured.
   → candidate session F12 (§8.1).
2. **The academic estimability literature does not bind our frozen engine —
   and that must be said precisely.** Hunter (2004) showed per-driver-worth
   PL MLEs fail on real NASCAR data (2002 season); our engine fits four
   ridge-regularized *feature weights*, not per-driver worths, so the trap
   binds only future worth-parameterized extensions (hierarchical
   driver/team effects, dynamic-skill models, PL trees). Recorded here as a
   standing design requirement for any such future spec (§3.2).
3. **"Loop data" mostly reduces to things we can derive ourselves.** The
   practitioner world's loop metrics (average running position, green-flag
   passes, quality passes, fastest laps, closers) are computable as-of from
   our own archived lap data (2022+, ToS-posture identical to the rest of
   the pipeline) — no new source needed for the Next Gen era. What we
   cannot derive: pre-2022 history (nascaR.data carries a per-race loop
   `Rating` column back to 2005 — licensing unresolved) and same-race
   official Driver Rating (circular by construction; lag-only). → candidate
   sessions F13 / F15 (§8).
4. **Practice and weather are cheap-looking and weak.** Same-day practice
   best-lap was already tested in our audit and added nothing (+0.001,
   p=0.29); richer practice data is licensable-only (Sportradar). Weather
   has a verified peer-reviewed null in an F1 rank model (every ELPD delta
   smaller than its SE) *and* practitioner skepticism on pre-race
   usability; Meteostat makes the data free if ever wanted. Both stay
   low-priority (§6.2–§6.3).
5. **One governance item needs owner attention (not alarm).** NASCAR's
   July-2025 NDM Terms of Use added broad scraping and
   model/algorithm-development prohibitions — but the covered-services
   list, embedded in the same document, does **not** name cf.nascar.com;
   the ToS binds services "that link to these Terms of Use"; and the feed
   endpoint carries no ToS link and no bot-block (plain S3/CloudFront),
   unlike www.nascar.com and racing-reference.info, which both 403
   non-browser clients. Formal coverage of the JSON feeds is textually
   unsupported; NASCAR could still argue reach. Recommendation: a short
   owner review session; keep the existing non-commercial research posture
   and the README's "respect the source's terms" stance (§6.5).

Areas that produced **no** credible new modeling idea, recorded so they are
not re-searched: public DFS ownership modeling (nothing beyond marketing
found), H2H market microstructure beyond structure/hold (open), and any
practice-speed edge testable from data we hold (already null).

**Reconciliation note:** while this scan ran, a parallel session committed
F7 (`research/bayesian_modeling_assessment.md`) and its plan fold-in
(F8–F11). Every finding here is reconciled against those verdicts (§2
baseline, §3.4/§3.6–§3.8, §3.11), the F7-requested prior-art anchors are
verified in §3.11, and this report's candidate sessions are numbered
**F12–F15** to follow on from the now-occupied F7–F11.

---

## 1. Method and evidence standard

Two verification rounds, run 2026-07-19:

- **Round 1 — deep-research workflow** (103 agents): 5 search angles →
  21 sources fetched → 99 falsifiable claims extracted → the top 25
  adversarially verified by **three independent votes each** against
  fetched primary sources (PDFs downloaded and text-extracted). Result:
  23 confirmed 3-0, 2 refuted 0-3 (both nascaR.data companion claims,
  Appendix B). All 23 came from the academic/open-source angles — the
  betting/DFS and data-source claims fell outside the verification budget.
- **Round 2 — targeted verification** (6 agents): every load-bearing
  betting/DFS and data-source claim from round 1's extraction was
  re-verified by a dedicated adversarial agent instructed to refute,
  quoting fetched text verbatim (Wayback captures where live pages
  bot-block). Access failures (403s) are reported as findings, not hidden.

Labels used throughout: **[3-0]** = round-1 triple-verified;
**[V]** = round-2 verified (single adversarial verifier, quote-checked);
**[V±]** = partially verified (stated caveats); **[U]** = unverifiable this
session. Source-credibility classes: peer-reviewed · working paper ·
official-primary · practitioner (credentialed, no backtests) · marketing.

**Governance tiers assigned to every idea** (consistent with the F5
report's usage):

| Tier | Meaning |
|---|---|
| **M** | Model-facing: may only ever enter via its own pre-registered, walk-forward-gated A/B |
| **A** | Analytics/reference: buildable freely with provenance labels; never joins model feature banks full-sample |
| **D** | Data/infrastructure: an ingestion or licensing decision |
| **G** | Governance/process: checklist items, ToS posture, spec-template notes |

---

## 2. What already exists (the overlap baseline)

Pinned before any idea is assessed, so overlap statements below are exact:

- **Frozen engine:** walk-forward PL with **linear features** — utility
  `u = X·w`, k=4 weights `[fin, pace, typed, start]`, ridge λ=0.5, L-BFGS,
  refit every race (`src/walkforward.py::pl_fit`). No per-driver worth
  parameters. pace = `pace_med85`; recency = half-life-8 feature histories
  (sensitivity-tested in the audit); typology = frozen `MY_TYPE`.
- **Pre-registered and frozen:** DNF/status *feature* A/B (V1 rate, V2
  censored histories, V3 crash/mech split — `specs/dnf_status_feature.md`);
  team/manufacturer *feature* pooling A/B (W1–W3, exclude-self —
  `specs/team_mfr_pooling.md`); clean-air causal design (G1, EDGE-gated,
  fixed-effects prohibited); scoring + market-benchmark decision rule
  (full-order Spearman primary; H2H flat-stake ROI vs closing line,
  sequential test).
- **Already tested and null in the audit:** same-day practice best-lap
  (+0.001, p=0.29 — the long-run consecutive-lap variant is open but
  untestable from the current feed); FE-adjusted "clean pace" (worse than
  the crude ratio; now a prohibited design); `pace_best` (lost to med85).
- **Planned (F3/F4/F5/C3):** ten calibrated track metrics (TDS, TPP, PDI,
  ARS, RVS, PIS, QIS, SFS, DCI, FVS) at (track_id × era) grain; empirical
  driver-skill-transfer similarity (DST); track dimension tables; config
  novelty/era-reset feature candidates (now plan rows F8/F9); a
  sim-parameter map with v0 priors → v1 calibrated knobs.
- **Adjudicated in parallel (F7, `research/bayesian_modeling_assessment.md`,
  b4c00d7 — committed while this scan ran):** three Bayesian formulations
  assessed against the frozen engine. Verdicts: **(B) dynamic state-space
  skill** — recommend; a pre-registered A/B is banked as plan row **F10**
  (un-freeze the fixed 0.5^(k/8) recency gain via exact scalar Kalman
  filtering with learned (q, r), as-of, deterministic, minutes of compute);
  **(A) hierarchical Bayesian PL** — conditional, banked as **F11**
  (blocked on F10 + F2 decisions); **(C) generative outcome model** — null
  with named revisit triggers. This scan's external findings are reconciled
  against those verdicts idea-by-idea below (§3.4, §3.6–§3.8, §3.11).
- **Data floor:** cf.nascar.com feeds (weekend-feed, lap-times, live-pit,
  live-flag, lap-notes; detailed feeds ≥2022, results-grade possibly
  earlier — B2/B3 will establish); vendored track-audit package.

---

## 3. Academic — rank-model methodology

### 3.1 Fit note that governs this whole section

Most of the verified literature estimates **per-driver (or per-team) worth
parameters**. Our engine does not — it scores drivers through four shared
feature weights. Consequences: (a) estimability pathologies bind our
*extensions*, not our baseline; (b) likelihood-shape results (attrition,
truncation, time-weighting) transfer directly, because they concern the
sampling model, not the parameterization; (c) hierarchical decomposition
results are structural *alternatives* to our feature-pooling specs, not
refinements of them.

### 3.2 E1 — Estimability check + ghost-item regularization [3-0]

- **Sources:** Hunter (2004), *Annals of Statistics* 32(1) — MM algorithms
  for generalized Bradley-Terry; Turner, van Etten, Firth, Kosmidis,
  *Computational Statistics* (2020) + arXiv:1810.12068 (the `PlackettLuce`
  R package). Peer-reviewed; the math is timeless.
- **Verified content:** PL per-driver MLEs do not exist unless the win
  digraph is strongly connected (Hunter's Assumption 1, necessary and
  sufficient); the failure occurs on real NASCAR data — the full 2002
  season required dropping four always-last drivers. Unregularized MLEs
  also overrate part-timers (a one-race driver tops the 2002 list), and
  SEs shrink slower than 1/√races (PL borrows strength from opposition
  quality). The package's default remedy: pseudo-rankings against a
  hypothetical "ghost" item (`npseudo=0.5`) — guarantees connectivity,
  finite estimates for all 87 drivers, and acts as shrinkage toward equal
  worth. Hunter himself sketched an unevaluated fractional-win fix [V]
  (mechanically distinct: pairwise fractional wins vs single ghost item).
  Full-season MM refits are computationally trivial (26 iterations,
  ~0.22M flops) [V].
- **Credibility:** highest in this report — three independent primary
  sources, exact numbers reproduced by verifiers.
- **Fit:** **not binding for the frozen engine** (§3.1). Binding for: any
  hierarchical driver/team worth variant (E5), dynamic-skill models (E7),
  PL trees (E8), or per-driver worth tables for a simulator.
- **Overlap:** none of the built or planned work fits per-entity worths;
  F4's DST uses frozen-engine residuals — unaffected.
- **Tier: G.** No session. **Standing requirement recorded here:** any
  future spec that estimates per-entity worths MUST include (i) a
  per-training-window strong-connectivity diagnostic and (ii) an explicit
  regularization scheme (ghost-item pseudo-rankings or a shrinkage prior),
  with part-timer shrinkage behavior stated.

### 3.3 E2 — Attrition (reverse-PL) likelihood [3-0] — the headline candidate

- **Sources:** Henderson & Kirrane (2018), *Bayesian Analysis* 13(2)
  335–358 (primary PDF verified); Graves, Reese & Fitzgerald (2003, cited
  therein) who proposed it for NASCAR.
- **Verified content:** modeling the finishing order **from last place
  upward** (a survival/dropout process) clearly beat standard PL at
  forecasting winner/top-3/top-10 in a 77-race walk-forward F1 test under
  proper scoring rules (log Bayes factors > 5 after a few races). Vanilla
  PL was badly miscalibrated for a dominant driver — expected ~7.6 Vettel
  wins in 2010–13 vs 34 observed; attrition expected ~23.3. Mechanism: PL
  built top-down treats a crash-caused P35 as strong evidence of low
  worth; the reverse construction lets early exits be absorbed as
  dropout, so top-of-field strength is not dragged down. The
  results-only attrition model was competitive with bookmaker-implied
  championship probabilities. Caveats verified: the F1 forecasting win is
  the evidence (the Graves NASCAR result is in-sample fit only); attrition
  takes a log-score hit on extreme longshot winners.
- **Credibility:** high — peer-reviewed, walk-forward, proper scoring,
  benchmarked against a bookmaker. The single best-evidenced transferable
  method found.
- **Fit:** direct. Same feature utilities, reversed sequential likelihood —
  an alternative `pl_fit` objective; the walk-forward A/B machinery
  (`pl_specs`, paired per-race ρ) applies unchanged. Mechanism-relevant to
  two measured facts: our audit's regularization-induced top-of-field
  underconfidence, and NASCAR's heavy attrition. Honest tension, stated
  now: our frozen primary metric is **full-order ρ**; attrition's
  documented wins are top-of-order probabilities. A spec must pre-register
  the standard adopt rule on ρ and record that a null on ρ with improved
  top-order calibration is a plausible (and reportable) outcome.
- **Overlap:** none with the DNF spec — that changes *features* (V1–V3),
  this changes the *likelihood*. Complementary levers on the same
  phenomenon; multiplicity accounting must extend the roadmap-#4
  program convention (the pooling spec's amendment is the template).
- **Tier: M.** → **Candidate session F12** (§8.1), variants pre-registered
  in one spec: attrition, attrition + likelihood-level time-weighting
  (E3), with truncated-PL (E4) explicitly considered-and-rejected in-spec.

### 3.4 E3 — Likelihood-level geometric time-weighting [3-0]

- **Source:** Henderson & Kirrane (2018), same PDF.
- **Verified content:** weighting each past race's likelihood contribution
  by ψ(x)=ξ^x (x = days since the race; Ibrahim & Chen power priors), with
  ξ tuned sequentially to maximize one-step-ahead log predictive
  probability, improved top-3/top-10 forecasts under the attrition model;
  the authors' single recommended model is time-weighted attrition.
  Caveats verified: sequential ξ *hurt* plain PL; optimal ξ was 1 for long
  stretches; plain attrition "performs admirably" and is simpler.
- **Fit / overlap:** we already weight *feature histories* (half-life 8,
  sensitivity-tested). This weights the *likelihood* — a genuinely
  different lever but with modest expected marginal value on top of
  feature-level recency. **F10 interaction (material):** the banked
  state-space A/B attacks the same underlying question — should recency
  decay be learned rather than fixed — at the feature-history level, with
  a mechanism our own audit's sensitivity grid documents. If F10 adopts,
  the marginal case for likelihood-level weighting shrinks further; F12's
  spec must therefore be written AFTER F10's decision and pre-register the
  conditionality (drop this variant on an F10 adopt unless a distinct
  mechanism argument is recorded pre-data).
- **Tier: M.** → folded into F12 as its second variant, conditional on
  F10's outcome.

### 3.5 E4 — Truncated-PL (top-r likelihood) [3-0]

- **Source:** same paper. Fitting PL on only the top-r positions improved
  winner/top-3 forecasts (r dataset-specific: 6 for winner/top-3, 10 for
  top-10), but **all truncated variants still lost to attrition**, and
  truncation is explicitly wrong for full-order objectives.
- **Fit:** misaligned with our frozen full-order primary metric; NASCAR's
  every-position-scores points system also weakens the reduced-effort
  rationale (the DNF rationale transfers). Relevant only if a win/top-5/
  top-10 product surface ever becomes a scored deliverable.
- **Tier: M (dormant).** → named in F12's spec as considered-and-rejected,
  with this citation, so it cannot be re-proposed casually.

### 3.6 E5 — Hierarchical worth decomposition; the equipment-share question [3-0]

- **Sources:** van Kesteren & Bergkamp, *JQAS* (2023), arXiv:2203.08489
  (v2 PDF verified; open data/code on Zenodo).
- **Verified content:** F1 finishing order modeled as rank-ordered logit
  (PL family) with strength = sum of four cross-classified random effects
  (driver, driver-season, constructor, constructor-season). Hybrid era:
  constructor ≈ 88% of variance (posterior SDs 1.63/0.73/0.54/0.35) —
  cite as model-specific within a 64–88% cross-method range. DNFs were
  excluded from the main decomposition. The authors explicitly warn the
  descriptive architecture is "probably not suitable for prediction"
  (season effects unestimable pre-season) and point to Henderson et al.
  for forecasting [3-0] — the correct porting rule.
- **Fit:** structural alternative to the W1–W3 *feature* pooling already
  pre-registered. Identifiability cost at our sample sizes is real, and E1
  binds. The transferable near-term value is **measurement, not
  modeling**: the NASCAR equipment share under Next Gen parity is an
  unanswered, interesting number (expect far below F1's), computable
  descriptively on gold with no model change.
- **Overlap:** F2 covers the feature version — it runs first. The *model*
  version of this idea is already banked as **F11** (F7's conditional
  hierarchical-Bayesian-PL outline, blocked on F10 + F2 decisions) — this
  scan adds the external, peer-reviewed template and its verified caveats
  (E1 binds; DNF exclusion sensitivity; descriptive≠forecasting) to F11's
  eventual spec inputs, and proposes only the **descriptive** measurement
  as a session.
- **Tier: A now, M later (M = F11's existing lane).** → **Candidate
  session F14** (§8.3): "Next Gen equipment-share decomposition" —
  analytics-only, after D1; its result is direct evidence for or against
  ever triggering F11.

### 3.7 E6 — The DNF modeling ladder [3-0]

- **Sources:** van Kesteren & Bergkamp sensitivity analysis (DNF handling
  materially reorders skill estimates — Maldonado 6th-worst with DNFs
  ranked by distance vs 19th of 38 on finishes only); Ingram (2021, blog)
  joint binomial-finish × rank-conditional model, cited by the paper as
  "another option".
- **Distilled:** three rungs now visible — (i) DNF *features* (our F1
  spec, pre-registered); (ii) attrition *likelihood* (F12); (iii) full
  *joint* finish-probability × conditional-rank model (heaviest; changes
  predictions' semantics). The external evidence says the choice matters
  materially; it does not say rung (iii) beats (ii).
- **Tier: M (dormant).** No session now — recorded as the escalation path
  if F1 and F12 both leave documented structure on the table. Consistency
  note: rung (iii) is adjacent to F7's formulation C (generative outcome
  model), which the Bayesian assessment independently adjudicated NULL
  with named revisit triggers; nothing found externally overturns that —
  the external evidence supports rung (ii) (likelihood), not rung (iii).

### 3.8 E7 — Dynamic PL / dyRank [3-0 on content; source unrefereed]

- **Sources:** Yamauchi working paper + `dyRank` R package (GitHub,
  F1 examples verified).
- **Verified content:** Gaussian random walk on log-ability
  (Δ²=0.5, set not tuned), PL rewritten as multinomial logit with varying
  choice sets (covariates straightforward; Polya-Gamma Gibbs + FFBS), and
  a team extension that keeps a team in the choice set after one of its
  cars is picked — matching NASCAR's multi-car structure. DNFs treated as
  missing data with the mechanism ignored (author acknowledges
  informativeness — a real weakness vs E2/our V2); ratings conflate driver
  and equipment.
- **Credibility:** medium — content verified verbatim, but no peer review
  and no forecasting validation.
- **Fit / overlap:** covers ground our half-life weighting + typed history
  already covers, at much higher machinery cost; worth-parameterized (E1
  binds). **The dynamic-skill lane is already occupied in-project:** F7's
  banked F10 design (exact scalar Kalman on feature histories, learned
  gain) takes the same adaptivity payoff at a fraction of the machinery,
  and the peer-reviewed ancestor of the full state-space rank-model family
  is Glickman & Hennessy 2015 (§3.11), not this working paper.
- **Tier: M (not proposed).** Recorded as the reference implementation if
  the full latent-utility state-space step (F7 §5's named later step,
  post-F10) is ever specced.

### 3.9 E8 — PL trees: data-driven partitioning vs hand-built typology [3-0]

- **Sources:** `PlackettLuce` paper (§ Plackett-Luce trees; `pltree()`
  exported by the package; weather named as an example covariate).
  Verified warnings: instability in high dimensions (bagging/forests
  suggested); per-subgroup identifiability needs enough rankings per
  driver — a real constraint at our sample sizes.
- **Fit / overlap:** `MY_TYPE` is frozen; F4 already plans the
  empirical-vs-structural similarity comparison. The one cheap, new
  question: does a pltree partition on physical covariates
  (length/banking/surface from `silver.track_dim`) *recover* the frozen
  6-bucket typology? Agreement from an independent method family is
  evidence the pooling key is real; disagreement is analyst input to F4's
  disagreement list. No model change either way.
- **Tier: A.** → proposed as a **small addendum inside F4's scope** (§9),
  not a session.

### 3.10 E9–E11 — Toolbox notes, verified

- **E9 [3-0]:** descriptive architectures do not port to forecasting
  unmodified (van Kesteren pointing to Henderson). Matches existing
  doctrine; cite in any porting spec. **Tier G.**
- **E10 [V]:** weather/circuit-type random slopes gave a peer-reviewed
  **null** in the F1 model — every LOO-ELPD delta smaller than its SE
  (basic −3993.36 vs best −3992.29, Δ −1.07, SE 6.35); basic model chosen
  on parsimony. Feeds §6.3's weather assessment. **Tier G.**
- **E11 [V]:** three tool facts for future specs: (a) `PlackettLuce`
  supports ties (Davidson-Luce, arbitrary order) and **subset rankings
  only — NOT top-n**: an unranked driver drops out of that race's
  likelihood entirely, so "DNF as censored-but-implicitly-last" is exactly
  what it cannot express (`hyper2` handles both). Any DNF-as-partial-
  ranking variant must model this explicitly, not assume the package does
  it. (b) Quasi-SEs (qvcalc) give reference-independent driver-comparison
  intervals, accurate to −0.7%/+6.7% across all 3,741 contrasts on the
  2002 NASCAR data — the right uncertainty tool if we ever publish
  driver-worth tables. (c) Full-season PL refits are computationally
  trivial (E1) — refit-every-race remains the right default. **Tier G.**

### 3.11 Prior-art anchors for F10/F11 — verified (the F7 cross-link)

F7 (`research/bayesian_modeling_assessment.md` §5) cited four anchors from
model knowledge and delegated verification here. All four were verified
against fetched primary PDFs (Graves 2003 full text is paywalled — its
reverse-order content rests on verbatim secondary attribution, exactly the
chain flagged) [V]:

1. **Glicko** — Glickman, M.E. (1999), "Parameter estimation in large
   dynamic paired comparison experiments," *JRSS Series C (Applied
   Statistics)* 48(3), 377–394, DOI 10.1111/1467-9876.00159. **Citation
   exact.** The "ADF on paired comparisons" gloss is fair as a
   retrospective label: the paper's own terms are "approximate Bayesian
   estimation" / "non-linear state space model," with the
   Gaussian-projection, prior→posterior→next-period-prior pattern (the
   TrueSkill paper itself credits Glicko for the Gaussian-belief scheme
   and names the across-game pattern "Gaussian density filtering").
   Nuances: batched per rating period, opponents integrated over priors.
   *Transferable extras:* the g(σ²) opponent-uncertainty down-weighting
   and ν²t between-period variance inflation — both directly relevant to
   F10's filter design (part-timers, absences).
2. **TrueSkill** — Herbrich, Minka, Graepel (2006), "TrueSkill™: A
   Bayesian Skill Rating System," *NIPS 19* (2006), 569–576. **Citation
   correct; characterization corrected:** the authors' own top-level term
   is "approximate message passing on a factor graph" — EP within a game
   (moment matching, iterated), Gaussian density filtering *across*
   games; and the domain is online gaming (Halo 2 free-for-alls), not
   races — the model handles race-shaped permutation outcomes, the paper
   never applies it to racing. *Transferable extra:* the draw-margin ε
   with truncated-Gaussian corrections is a ready-made device for
   effectively-tied outcomes (DNF ties), should a worth-parameterized
   variant ever need one.
3. **Glickman & Hennessy** — (2015), "A stochastic rank ordered logit
   model for rating multi-competitor games and sports," *JQAS* 11(3),
   131–144, DOI 10.1515/jqas-2015-0012. **Citation exact and the
   characterization is precisely right:** Gumbel latent performances
   (explicitly "sometimes called the Plackett-Luce model"), each ability
   a Gaussian random walk, MCMC plus a Glicko-style approximate filtering
   algorithm — the peer-reviewed ancestor of F10's approach. Application
   is women's Alpine downhill (268 skiers, 2002–2013), and the paper
   itself cites Graves et al. 2003 for NASCAR. *Transferable extras:*
   tie handling designed verbatim for "races in which some of the
   competitors may not finish and therefore tie for last place," and a
   sum-preserving innovation covariance (Υ = τ²(I − (1/n)11′)) that
   prevents rating drift over long seasons.
4. **Graves, Reese & Fitzgerald** — (2003), "Hierarchical Models for
   Permutations: Analysis of Auto Racing Results," *JASA* 98(462),
   282–291, DOI 10.1198/016214503000053. **Citation exact; NASCAR
   hierarchical-permutations confirmed.** The attrition/reverse-order
   attribution is corroborated verbatim by Henderson & Kirrane 2018
   (primary PDF): Graves et al. proposed the reverse-PL for NASCAR,
   named it the attrition model, and found it "far superior ... when
   analysing the full finishing order" — in-sample. One correction to
   the ancestry: the reverse-PL construction itself predates them
   (Marden 1995's "backwards Plackett" model); Graves et al. contribute
   the NASCAR case, the name, and the hierarchical framework F11 cites.

Net for F7's verdicts: all four anchors stand, two with meaningful
precision corrections (TrueSkill's method/domain; Graves' priority). The
F10 lane gains a direct peer-reviewed ancestor (#3); F12's attrition
candidate gains its full citation chain (#4 → Henderson & Kirrane, §3.3).

---

## 4. Betting / DFS / fantasy

Nothing in this quadrant carries validated evidence (no public backtests
anywhere); its value is market documentation, convergent priors, and trap
identification. Credibility labels matter most here.

### 4.1 H2H market structure [V; promotional explainer + credentialed essay]

- FoxSports (2022, FOX Bet promotional explainer — no byline, no data):
  H2H settles on which of two drivers finishes ahead; single verified
  example line Hamlin −118 vs Logano (2022 Daytona 500, quoted by a FOX
  Bet trading-operations manager). The "lines set by trading staff"
  framing is an inference from the speaker's title, and "near even money
  for comparable drivers" is NOT a sourced generalization — one example
  only.
- Sirois (NASCAR Bets substack, 2025 [V]; real industry practitioner —
  Sportsbook Review analyst, ex-Stokastic — but no published bet record):
  odds-disparity betting "far more useful for low-hold, two-outcome
  markets"; in 36–40-driver outright markets, hold erases tight edges.
- **Fit:** corroborates, from the practitioner side, two decisions the
  project already made independently: H2H matchups as the benchmark
  market, and the audit's ~52–53% pairwise break-even estimate (no
  contradiction with "low-hold": H2H two-outcome hold is low *relative to
  outrights* while still ≈4–6% two-sided — the market-benchmark spec's
  0.5300 reference stands).
- **Overlap:** fully covered by `specs/market_benchmark_decision_rule.md`
  + E1 capture duties. **Nothing new to build.** Open (unanswered by any
  credible source found): line movement, limits, and book-to-book
  variation microstructure. **Tier G** (context for the benchmark).

### 4.2 Practitioner signal inventory [V; credentialed assertion, zero backtests]

Sirois's recommended signals, mapped to our plan:

| Practitioner claim | Our status |
|---|---|
| Loop whole-race metrics (driver rating, laps led, avg green-flag speed) beat finishing position alone | Partially ours already (`pace_med85` is a green-lap pace metric); the *rest* of the loop family → F13 (§8.2) |
| Track similarity by shape/corner character/surface abrasiveness, not length (Darlington ≠ Atlanta) | Convergent with the vendored track audit's family taxonomy and F4's empirical-similarity plan — external corroboration, nothing new |
| Equipment hierarchically: driver vs teammates first, then same-tier/same-engine teams | Convergent with the pooling spec's exclude-self W1 (teammates) and W2 (manufacturer) — external corroboration of the pre-registered ladder |
| Weather/sunlight decide races but are hard to convert into a pre-race edge | Convergent with E10's peer-reviewed null → §6.3 |
| Pit-crew quality, points-position motivation as H2H handicaps [V, FoxSports too] | Genuinely not in our feature set. Pit-crew execution is measurable from `silver.pit_stops` (F3's PIS secondary outputs); "motivation" is unmeasured and stays out absent any evidence |

Credibility summary: internally coherent, evidence-free. Treated as a
source of *hypotheses and corroboration*, never adoption pressure.

### 4.3 DFS pipeline shapes [V]

- **Two-stage qualifying reprice** (tburus repo, primary-source code):
  pre-qualifying projections recalibrated by post-qualifying scripts. We
  already predict post-qualifying (grid is a model feature) — no gap.
- **Simulation-first products** (WIN THE RACE marketing: "simulates each
  race 200,000 times" feeding market prices and a lineup optimizer):
  confirms the F5 sim-surface intuition that a lap-level simulator is the
  natural DFS/betting product layer — and confirms the public versions
  publish **no methodology or validation**. Our F5 doctrine (sim outputs
  labeled, DCI/FVS/lead-changes as validation targets not inputs) is
  already ahead of the public state.
- **Ownership modeling:** nothing public and credible found (the one
  public pipeline has none; commercial products don't document theirs).
  Recorded as an open area — do not cite this scan as evidence it doesn't
  exist, only that it isn't public.
- **A 4-season minimum for track-history features** (tburus README) —
  hobbyist assertion; our data-driven half-life + typed-shrinkage approach
  supersedes it. The repo's actual recipe (verified in code): last 4
  season races + last 4 races at the track, simple averages, Gurobi ILP —
  a useful reminder of what the public baseline actually is: **our 2022
  starting point (recency-weighted finish history) is already at or above
  the public DFS baseline.**

### 4.4 What this quadrant contributes

No new model feature. Two corroborations (track-character similarity,
teammate-first equipment), one confirmed market-structure picture, one
measurable new signal routed to existing plans (pit-crew execution →
F3 PIS), and the trap catalog entries in §7.

---

## 5. Open-source / analytical projects

- **`PlackettLuce` (R; Turner et al.)** [3-0] — the reference
  implementation for worth-parameterized PL: ghost-item regularization,
  ties, subset rankings (not top-n — E11a), trees, quasi-SEs; demonstrated
  on the 2002 NASCAR season. Role for us: methodology reference and
  cross-check harness for any future worth-parameterized spec — not a
  production dependency (our engine is covariate-PL in Python).
- **`nascaR.data` (CRAN v3.1.0, 2026-06-11, GPL-3)** [3-0 + V] — Cup
  results 1949–present, Xfinity 1982–, Truck 1995–; 21 uniform columns
  including start/team/make/laps-led/status-with-cause/stage points and a
  per-race loop-derived **`Rating`** column (NA where unavailable; loop
  data exists from 2005). Monday auto-refresh in season. **Live-probed
  2026-07-19:** parquet directly downloadable, no R needed
  (`https://nascar.kylegrealis.com/cup_series.parquet` → HTTP 200, valid
  parquet, ~983 KB; nxs/truck likewise); the README's CSV endpoints 404.
  **Licensing is the blocker:** the GPL-3 covers the package code; no data
  license exists anywhere; DriverAverages.com (the upstream) publishes
  **no terms of use at all**; "scraped with permission" is a private,
  unscoped grant. Two round-1 claims about it were refuted 0-3 (Appendix
  B). → ingestion is proposed **only as** a vendored, hashed,
  analytics-tier source *after* an owner licensing decision (§8.4).
- **`dyRank` (GitHub)** [3-0] — see E7; reference only.
- **`tburus/nascar_projections` (GitHub, dormant since 2019-06)** [V] —
  hobbyist DFS pipeline (verified in code: 4+4 recency/track averages,
  qualifying reprice, Gurobi ILP, no simulation/ownership). Historical
  interest: it scraped racing-reference loop-data pages with plain
  `requests` in 2019; that path is closed today (Cloudflare 403) — a
  concrete marker of the public-scraping window closing on NASCAR
  properties.

---

## 6. Data sources beyond cf.nascar.com

### 6.1 Loop data (the biggest source question, resolved into three parts)

**What it is** [V, multi-source]: NASCAR's scoring-loop statistics,
2005–present: Driver Rating, Average Running Position, Green Flag Speed,
Fastest Laps Run, Green Flag Passes / Times Passed / Pass Differential,
Quality Passes (passes while running in the top 15), Laps in Top 15,
Closers (positions gained in the final 10%), restart and
early/late-run speed splits, speed by segment.

**Where it lives publicly:**
- **Official per-race box-score PDFs exist and circulate free.** Verified
  by download: a 2026 Phoenix Cup "Box Score" PDF, NASCAR-branded,
  footer "Provided by NASCAR Statistics", rehosted on a practitioner site
  (wintherace.info) [V]. Racing-Reference (a **NASCAR Digital Media
  property** [V — footer + NASCAR's own ToS covered-services table])
  publishes per-race Loop Data pages, browsable by humans, 403 to
  programmatic clients [V]. Machine-readable/filterable loop data is a
  paid practitioner product ($50/mo tier verified at one vendor) [V±].
- **Lagged Driver Rating history at results grain:** nascaR.data's
  `Rating` column, 2005+ where available (§5) — licensing unresolved.

**The in-house derivation point (the real finding):** for 2022+ — the only
era the frozen model trains on — **nearly the whole loop-metric family is
derivable from data we already archive**: `silver.laps` running positions
give ARP, green-flag passes/times-passed/pass-differential, quality
passes, laps-in-top-15, closers; per-lap times give fastest-lap counts and
speed splits; C2's flag table scopes green-flag restrictions. This needs
no new source, inherits the pipeline's existing ToS posture, and the
definitional ambiguities found in public sources (three circulating ARP
variants: all-laps, green-flag-only, lead-lap-only [V — contested,
official glossary inaccessible]) become *our* pre-registered definitional
choices instead of someone else's unstated ones. → **candidate session F13**
(§8.2). Overlap guard: F3's track profiles already plan PDI/TPP/RVS at
*track* grain; F13 is the *driver-history* grain — complementary, and F13's
spec must import F3's definitions where they overlap (passes, green-lap
restrictions) rather than re-choosing them.

**Driver Rating itself** [V±]: finish position (and win) are direct
formula inputs per four independent descriptions including NASCAR's own
stats-hub snippet; exact arithmetic (900÷6 scale, ARP-while-on-lead-lap
×2, max-100 variable bonus = (GF laps led + GF fastest laps)/GF laps) is
single-secondary-sourced (DriverAverages). Same-race Driver Rating is
**circular by construction** (§7.1) — only lagged histories are
legitimate, and a self-built composite from F13 components would be
preferable to importing NASCAR's opaque one.

### 6.2 Practice / qualifying speeds

- **Sportradar** [V] is the official licensable channel: dedicated
  Practice and Qualifying Leaderboard endpoints, all three series, live
  session updates; B2B, authenticated, 30-day/1,000-request trial, **no
  free production tier**. Its documented endpoint list has no pit/caution/
  loop-data endpoints (prose advertises "lap-by-lap coverage" without a
  dedicated endpoint — unresolved on the overview page).
- **Our evidence:** same-day practice best-lap already measured null
  (+0.001, p=0.29). The open variant (long-run practice pace from
  consecutive laps) would require exactly the licensable data above, and
  Next Gen weekends have limited practice anyway.
- **Verdict: no proposal.** Recorded: if the market benchmark ever returns
  EDGE and a licensed live stack is being built anyway, Sportradar is the
  known practice-data channel to price then.

### 6.3 Weather

- **Meteostat** [V]: free historical weather — Python library, keyless
  bulk parquet, JSON API (500 req/mo free tier), NOAA/DWD lineage, point
  interpolation at arbitrary track coordinates. License: **CC BY 4.0**
  per the canonical license page and library README, but a **stale
  CC BY-NC 4.0 sentence is still live in their FAQ** — an unresolved
  publisher-side contradiction; a betting-adjacent commercial use should
  get written confirmation first.
- **Evidence against prioritizing it:** E10's peer-reviewed null (wet/dry
  and circuit-type slopes, every ELPD delta < SE) and the practitioner's
  own "difficult pre-race" concession (§4.2). The mechanistically
  plausible NASCAR uses are narrower than "weather feature": track
  temperature × tire degradation (an F3-TDS covariate) and rain at road
  courses (rare, race-state).
- **Verdict:** LOW-priority analytics spike at most (§8.6); no model
  proposal. The data being free and CC-BY makes deferral costless.

### 6.4 Historical results depth

- **nascaR.data** (§5) is the practical channel (1949+, parquet, weekly
  refresh) — pending the licensing decision. Racing-Reference and
  DriverAverages are browsable references, both without usable terms
  (NASCAR-owned + bot-blocked; no ToS at all, respectively) — neither is
  a programmatic source under our doctrine.
- **Value if ingested:** long-horizon track-history and manufacturer-era
  analytics, F3 shrinkage-prior context, QA cross-checks of bronze
  results (a second independent results source), and the 2005+ `Rating`
  history. **Explicitly not** frozen-model training data: the model's
  2022+ Next Gen window is a deliberate era choice, not a data shortage.

### 6.5 The NASCAR ToS finding (governance — owner attention, not alarm)

Verified from the Wayback capture of the live page (live page bot-blocks;
capture 2025-08-20, latest available; no 2026 revision surfaced) [V]:

- Effective 2025-07-08, the NDM Network Terms of Use prohibit — **without
  NASCAR's prior written consent** — scraping/data-mining of "the NDM
  Network Services, including all images, video, data and other
  information contained on the NDM Network Services ('NASCAR Content')",
  and separately prohibit using NASCAR Content "for the development of any
  software program, model, algorithm, or generative AI tool" (the AI
  language is an "including, but not limited to" expansion — the clause
  reaches any model/algorithm). Downloads, where permitted, are personal
  non-commercial; commercial exploitation is prohibited. A mandatory
  arbitration provision and class-action waiver were added in this
  revision.
- **The coverage question resolved further than expected:** the
  covered-services list is embedded in the same document (the "click
  here" is an in-page anchor, not a separate page). It enumerates
  www.nascar.com and seven specific subdomains — **cf.nascar.com is not
  on the list**. The Terms bind services "that link to these Terms of
  Use"; a single permitted HEAD of one feed endpoint showed plain
  S3/CloudFront, HTTP 200, **no ToS link, no bot-block** — in contrast to
  www.nascar.com and racing-reference.info, which both 403 non-browser
  clients. Net: formal ToS coverage of the JSON feeds is textually
  unsupported by the document; the "all data" language leaves NASCAR room
  to argue reach.
- **What this means for us, concretely:** (i) the repo's existing posture
  is already the right one — code-only redistribution, raw data not
  committed, README's "respect the source's terms", non-commercial
  research framing; (ii) the polite fetch protocol (5 req/s cap, backoff)
  in the medallion spec is also the right operational posture; (iii)
  scraping NASCAR *web properties* (nascar.com pages, racing-reference) is
  clearly out — which the plan never proposed; (iv) the model-development
  clause is the one a cautious owner should read personally, because this
  project *is* a model built from NASCAR timing data, and the consent
  condition + coverage ambiguity is a judgment call that belongs to the
  owner, not to an agent. → **candidate owner session** (§8.5). This
  report takes no legal position; it documents verbatim clauses and
  verified technical facts.

---

## 7. Leakage / circularity trap catalog (consolidated for future specs)

1. **Same-race Driver Rating embeds the finish** (finish and win are
   formula inputs [V]) — any use must be lagged history only; better, a
   self-built composite with pinned definitions (F13).
2. **All loop whole-race metrics are same-race outcomes**, not pre-race
   signals — legitimate only as as-of histories, exactly like `fin`/`pace`
   today. Public DFS content routinely blurs this.
3. **"ARP" has at least three circulating definitions** (all-laps,
   green-flag-only, lead-lap-only [V]) and no accessible official
   glossary — every derived loop metric in F13/F3 must pin its definition
   in the spec, not import "the" public one.
4. **Practice best-lap ≈ qualifying information** — measured null in our
   audit; re-proposals must cite and beat that result, not ignore it.
5. **Market-implied probabilities as model features** would corrupt the
   market-benchmark question (the model would partially *be* the market it
   is tested against). If ever considered post-verdict, it is a new
   program with its own spec — never a feature slipped into this one.
6. **Hindsight-authored priors** (track-audit 1–10s) — already governed by
   F5 §6; unchanged.
7. **Descriptive architectures ported unmodified to forecasting** — E9's
   verified warning; season-level effects are the canonical offender.
8. **Sim products validated on nothing** — the public 200k-sim products
   publish no methodology [V]; F5's rule stands (DCI/FVS/lead-changes are
   validation targets, never sim inputs).
9. **Package-capability assumptions** — `PlackettLuce` cannot express
   DNF-as-implicitly-last (subset rankings only [V]); verify tool
   semantics against the spec's estimand before building on them.

---

## 8. Candidate plan sessions (ranked: payoff band, then effort)

| # | Candidate | Band | Effort | Depends on | Gate | Overlap guard |
|---|---|---|---|---|---|---|
| 8.1 | **F12 — Rank-likelihood A/B: attrition (reverse-PL) ± likelihood time-weighting** (spec then run) | **HIGH** | spec ~1–2 h (Fable) + run ~3–6 h (Sonnet) | F1+F2+F10 decisions recorded (baseline known; time-weighting variant conditional on F10's outcome, §3.4); gold (D1); ≥8 scored races (program discipline) | pre-registered spec; adopt iff Wilcoxon p ≤ threshold AND mean Δρ ≥ +0.005, multiplicity extending the roadmap-#4 family convention | likelihood lever, disjoint from DNF/pooling feature levers AND from F10's feature-history gain lever; truncated-PL named considered-and-rejected in-spec (E4) |
| 8.2 | **F13 — Driver loop-metric histories derived in-house** (ARP, pass differential, quality passes, fastest-lap share, closers — as-of, from silver.laps) | **MED-HIGH** | ~3–5 h | C2 (silver laps/flags) | analytics tables first (Tier A); any feature use via its own later A/B | imports F3's definitions where shared; driver-history grain vs F3's track grain; §7.3 definitional pinning mandatory |
| 8.3 | **F14 — Next Gen equipment-share decomposition** (hierarchical driver/team/make variance split, descriptive, van-Kesteren-style) | MED | ~3–5 h | D1 (gold features + residual machinery) | analytics-only (Tier A); E1 connectivity check + regularization required | the descriptive companion to the already-banked F11 (hierarchical Bayesian PL, conditional): F14's result is direct trigger evidence for/against F11; F2 runs first regardless |
| 8.4 | **F15 — nascaR.data vendored ingestion** (1949+ results + 2005+ Rating, parquet, hashed + immutable like track_audit) | MED | ~2–3 h | **owner licensing decision** (§5) | Tier A/D; never frozen-model training data; QA cross-check vs bronze results is part of the deliverable | duplicates nothing — extends history below the 2022 feed floor |
| 8.5 | **Owner ToS review + posture decision** (read §6.5 clauses; decide posture; optionally seek written consent) | governance (HIGH importance) | ~1 h, owner-led | none — runnable now | Tier G; no code | none |
| 8.6 | **Meteostat weather analytics spike** (track-temp × tire-deg covariate for F3-TDS; rain flags for road courses) | LOW | ~2–3 h | C2/F3 | Tier A; license confirmation first (CC BY vs stale BY-NC [V]) | two documented nulls' worth of skepticism recorded (E10 + audit practice analogy); deferred by default |

Plus two no-session items: the **E1 standing requirement** for any future
worth-parameterized spec (§3.2), and the **E8 pltree typology-validation
addendum** proposed inside F4's existing scope (§9.3).

Sequencing/independence: 8.5 is runnable today and independent of
everything. 8.1 is the mainline model candidate and waits its gates.
8.2 waits on C2; 8.3 on D1; 8.4 on the owner; 8.6 indefinitely deferred
unless F3 wants the covariate.

---

## 9. Proposed plan edits (for the owner to fold in — not applied here)

**9.1 New Phase-F rows** (schedule.yml candidates, following the
now-occupied F7–F11):

> | F12 | Rank-likelihood A/B — attrition (reverse-PL) ± time-weighting | ⛔ blocked | Fable 5 (spec) / Sonnet 5 (run) · thinking on · xhigh | ~1–2 h spec + ~3–6 h run | Test whether flipping the model's likelihood — scoring races from last place upward, the way attrition actually works — beats the current model, using the strongest externally-validated idea from the F6 scan. | Pre-register a spec per research/external_knowledge_scan.md §3.3–§3.5 (variants: attrition; attrition + likelihood-level geometric time-weighting; truncated-PL considered-and-rejected in-spec with citation); baseline = then-frozen config; adopt rule form per DNF spec §4 with program-wide multiplicity accounting extending the pooling amendment; gated on F1+F2+F10 decisions recorded (time-weighting variant conditional on F10 per scan §3.4), D1 gold, ≥8 scored races. |
>
> | F13 | Driver loop-metric histories (in-house loop data) | ⛔ blocked | Sonnet 5 · thinking on · high | ~3–5 h | Build the loop-data signals everyone in public NASCAR analytics uses — average running position, passes, fastest laps, closers — from our own archived lap data, with no new source and no licensing exposure. | From silver.laps/flag_events (C2): as-of driver histories for ARP, green-flag pass differential, quality passes, fastest-lap share, laps-in-top-15, closers; definitions pinned per external_knowledge_scan.md §7.3 (three ARP variants exist publicly — choose and freeze); import F3 definitions where shared. Analytics tables (Tier A); any model feature use requires its own later A/B. |
>
> | F14 | Next Gen equipment-share decomposition | ⛔ blocked | Sonnet 5 · thinking on · xhigh | ~3–5 h | Measure how much of a Cup result is the team/manufacturer vs the driver under Next Gen parity — the NASCAR version of a famous F1 result (~64–88% constructor there), as a descriptive analytics deliverable. | Hierarchical driver/team/make variance decomposition on gold walk-forward data per external_knowledge_scan.md §3.6; requires the §3.2 connectivity check + regularization; descriptive only (Tier A) — direct trigger evidence for/against the banked F11 hierarchical-PL lane; runs after D1, independent of F2's feature-pooling A/B. |
>
> | F15 | nascaR.data vendored ingestion (1949+) | ⛔ blocked | Sonnet 5 · thinking on · high | ~2–3 h | Vendor 77 seasons of historical results (plus 2005+ loop ratings) as a hashed reference source — pending the owner's call on its unresolved data licensing. | Owner licensing decision FIRST (GPL-3 covers package code only; DriverAverages publishes no terms; "with permission" is unscoped — external_knowledge_scan.md §5). If cleared: ingest the three parquet files (live-verified public URLs) as an immutable, hashed, versioned reference source in the track_audit pattern; reconcile vs bronze results as QA; analytics tier only — never frozen-model training data. |

**9.2 New governance row** (Phase A or a small G-row, owner-led,
runnable now):

> | A6 | Owner ToS review — NASCAR NDM terms posture | pending | owner (+ any model as reader) | ~1 h | Read the July-2025 NASCAR terms clauses that touch scraping and model-building, decide the project's posture, and record it. | Review external_knowledge_scan.md §6.5 (verbatim clauses + verified coverage facts: cf.nascar.com absent from the covered-services list, no ToS link on the endpoint, feeds not bot-blocked); decide: keep current non-commercial research posture / seek written consent / adjust capture plans; record the decision in HANDOFF. No code, no model change. |

**9.3 One-line tightenings of existing rows:**

- **F4:** append to its technical summary: "…plus a pltree
  cross-validation: does model-based recursive partitioning on
  silver.track_dim physical covariates recover MY_TYPE? (agreement =
  independent evidence for the frozen pooling key; disagreement feeds the
  named disagreement list; external_knowledge_scan.md §3.9)."
- **F3:** append: "…loop-metric-adjacent definitions (passes,
  green-flag restrictions, ARP variants) pinned per
  external_knowledge_scan.md §7.3 and shared with F13."

**9.4 Explicitly NOT proposed,** with the reason on record: a dyRank-style
full state-space PL (E7 — unrefereed, DNFs-as-missing, and the in-project
dynamic lane is already occupied by the banked F10 design, with the
peer-reviewed ancestry recorded in §3.11); a generative outcome model
(F7's verdict C is NULL with revisit triggers; the external evidence
concurs — §3.7); truncated-PL as a standalone (E4 — loses to attrition,
misaligned with the frozen primary metric); practice-speed features
(audit-measured null; richer data licensable-only); weather as a model
feature (E10 null + practitioner skepticism); market-implied-probability
features (§7.5 circularity with the live benchmark); any use of
racing-reference/DriverAverages/nascar.com page scraping (ToS/no-terms/
bot-blocked).

---

## 10. Open questions (honest residue)

1. Public DFS **ownership modeling**: nothing credible is public; only
   marketing claims exist. Open, and probably answerable only with
   commercial-product access.
2. **H2H market microstructure** beyond structure and hold (line movement,
   limits, book-to-book dispersion): no credible public source found;
   answerable from our own E1 capture data once enough races accumulate.
3. **Official loop-data archives**: per-race NASCAR Statistics box-score
   PDFs demonstrably exist and circulate free, but no systematically
   fetchable, ToS-clean archive was identified (NASCAR properties
   bot-block; practitioner rehosts are unofficial). F13's in-house
   derivation sidesteps this for 2022+; pre-2022 loop history remains
   effectively locked behind nascaR.data's `Rating` column (licensing
   pending) or manual PDF collection.
4. **nascaR.data licensing**: unresolved by construction (no upstream
   terms exist to resolve against) — an owner risk decision, not a
   research question.
5. Whether the **attrition likelihood's advantage replicates on 2022+
   NASCAR walk-forward** — exactly what F12 exists to answer; the external
   evidence is F1-only.

---

## Appendix A — Source ledger

**Peer-reviewed / primary (round-1 triple-verified against fetched PDFs):**

| Source | Used for |
|---|---|
| Hunter (2004), *Ann. Statist.* 32(1) 384–406 — projecteuclid.org/journals/annals-of-statistics/volume-32/issue-1/…/10.1214/aos/1079120141.full | E1 (connectivity, 2002 NASCAR failure, MM), E11c |
| Turner, van Etten, Firth, Kosmidis (2020), *Comput. Stat.* — link.springer.com/article/10.1007/s00180-020-00959-3 + arxiv.org/pdf/1810.12068 | E1 (npseudo), E8 (pltree), E11a/b |
| Henderson & Kirrane (2018), *Bayesian Analysis* 13(2) 335–358 — projecteuclid.org/…/10.1214/17-BA1048.pdf | E2 (attrition), E3 (time-weighting), E4 (truncation) |
| van Kesteren & Bergkamp (2023), *JQAS* — arxiv.org/abs/2203.08489 (v2 PDF) | E5 (decomposition, 88%), E6 (DNF sensitivity), E9, E10 (weather null) |
| Yamauchi, dynamic ranking working paper + github.com/soichiroy/dyRank | E7 (unrefereed — medium confidence) |
| Glickman (1999), *JRSS-C* 48(3) 377–394 — glicko.net/research/glicko.pdf | §3.11 anchor 1 (Glicko/ADF) |
| Herbrich, Minka & Graepel (2006), *NIPS 19* 569–576 — MSR-hosted PDF | §3.11 anchor 2 (TrueSkill) |
| Glickman & Hennessy (2015), *JQAS* 11(3) 131–144 — glicko.net/research/multicompetitor.pdf | §3.11 anchor 3 (dynamic state-space PL) |
| Graves, Reese & Fitzgerald (2003), *JASA* 98(462) 282–291 — via Crossref/JSTOR + Henderson & Kirrane's verbatim attribution (full text paywalled) | §3.11 anchor 4 (NASCAR attrition/hierarchical) |

**Data/infrastructure (round-2 verified, live probes 2026-07-19):**

| Source | Status |
|---|---|
| cran.r-project.org/package=nascaR.data (+ PDF manual, GitHub, pkgdown) | v3.1.0, GPL-3 (code); parquet URLs live 200; CSV endpoints 404; no data license |
| driveraverages.com | no ToS/license pages exist; "not associated with NASCAR" disclaimer; Driver Rating formula page (single-source arithmetic) |
| nascar.com/ndmnetworktermsofuse | live 403 (Cloudflare); verified via Wayback 2025-08-20 capture |
| cf.nascar.com weekend-feed endpoint | one permitted HEAD: 200, S3/CloudFront, no ToS link, no bot-block |
| racing-reference.info | NASCAR Digital Media property; live 403 to all programmatic clients; loop-data pages evidenced via Wayback |
| developer.sportradar.com/racing/reference/nascar-overview (+ account docs) | official/licensable; practice+qualifying endpoints; B2B, trial-only free access |
| dev.meteostat.net (+ meteostat-python README) | free; CC BY 4.0 canonical with stale CC BY-NC FAQ sentence still live |
| wintherace.info (incl. downloaded Phoenix-Cup.pdf) | free PDFs are NASCAR-official Statistics box scores rehosted; paid tier $50/mo; 200k-sim claim = marketing |
| frcs.pro/nascar-loop-data | loop-data metric roster + 2005 start (secondary) |
| foxsports.com Daytona-500 H2H explainer (2022) | market structure; promotional, one example line |
| nascarbets.substack.com (Sirois, 2025) | practitioner methodology essay; credentialed, no backtests |
| github.com/tburus/nascar_projections | primary-source code, dormant since 2019-06 |
| buildingspeed.org (Leslie-Pelecky) | loop-data 2005 introduction corroboration |
| data.scorenetwork.org NASCAR driver-ratings page | Driver Rating component list corroboration |

**Fetched but yielding nothing usable:** stokastic.com projections page
(round-1 extractor: "unreliable", zero claims).

## Appendix B — Refuted claims (kept on record so they are not re-imported)

1. **"nascaR.data's 'scraped with permission' resolves the ToS/licensing
   question"** — refuted 0-3 (round 1) and re-confirmed refuted in round 2
   with specifics: no data license exists; upstream publishes no terms;
   GPL-3 attaches to the package code only.
2. **"nascaR.data is limited to results-level fields (no loop
   data/ratings)"** — refuted 0-3; the schema includes the loop-derived
   `Rating` column (round 2: confirmed at CRAN PDF p. 9).
3. **"PlackettLuce supports top-n rankings"** (round-1 extraction
   overreach) — corrected in round 2: subset rankings only; an unranked
   driver drops out of the likelihood (paper §2.2.1, Table 4).
4. **"H2H lines quoted near even money for comparable drivers"** as a
   general sourced fact — refuted as a generalization; only a single
   example line exists in the source.
5. **"tburus projections use the single most recent track race"** —
   refuted; code shows last **four** track races + last four season races.

---

*Report ends. Nothing was built, no frozen spec was edited, no package
file was touched. Every idea above that could ever touch the production
model is routed through its own pre-registered, walk-forward-gated A/B
(§8's gate column); everything else is labeled analytics, data, or
governance. A well-run negative on any of these candidates is a success
by project doctrine.*
