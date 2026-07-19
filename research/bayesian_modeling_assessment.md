# Bayesian modeling assessment — appropriate? better? (F7 research spike)

**Status:** research spike, 2026-07-19. **Proposes only** — nothing was fit, nothing
built, no frozen spec touched. The §7 design becomes a pre-registration only when
lifted verbatim into `specs/` in its own commit, before any variant code runs.
**Inputs read in full:** `src/walkforward.py`, `src/predict_next.py`,
`report/NASCAR_AUDIT_REPORT.md`, `specs/` (scoring, market benchmark, DNF, pooling,
README, clean-air), `PLAN.md` Phase F.
**Question (owner, 2026-07-19):** is a Bayesian approach appropriate for this model,
and would it beat the current L2-penalized walk-forward Plackett-Luce — assessed as
three formulations (A hierarchical, B dynamic, C generative), judged on four payoffs
(accuracy, calibrated uncertainty, small-sample behavior, interpretability), with
compute as a first-class constraint.

---

## 0. Verdict up front

| Formulation | Verdict | One line |
|---|---|---|
| **A. Hierarchical Bayesian PL** (posteriors + driver/team/mfr/track pooling) | **CONDITIONAL — bank, don't run yet** | Duplicates the committed F2 pooling A/B and needs B's dynamics to be coherent; execute only after the roadmap-#4 and B decisions are recorded, Laplace-first, fresh spec then. |
| **B. Dynamic state-space skill** (random walk replacing the fixed 0.5^(k/8)) | **RECOMMEND — pursue via §7's A/B** | The only formulation with a documented accuracy mechanism (the audit's own sensitivity says the fixed half-life is mis-set), near-zero compute cost (it's a filtering problem, not an MCMC problem — numpy only, deterministic), and a surgical two-variant A/B. |
| **C. Generative outcome model** (finish jointly with DNF/attrition + cautions) | **NULL for now — recorded, with revisit triggers** | Its real payoff (bimodal outcome distributions, honest tails) lands entirely on surfaces no frozen metric adjudicates; the cheap version of its signal is already pre-registered as F1; heaviest compute, most researcher degrees of freedom. |

The framing premise checks out exactly, and it does most of the work: the current
model is already Bayesian at the point estimate, so "go Bayesian" is four specific
deltas, not a new religion — and each delta has to buy its way in through the same
rho-gated A/B as any other change.

---

## 1. What the current model already is, in Bayesian terms

Reading `walkforward.py` closely, essentially every component is a known Bayesian
estimator with its uncertainty (and its hyperparameters) discarded:

1. **`pl_fit(lam=0.5)` is exactly a MAP estimate.** The objective is
   `λ wᵀw + Σ_races NLL_PL(w)`. The penalty `exp(−λ wᵀw)` is a Gaussian prior with
   variance `1/(2λ)`; at the frozen λ = 0.5 that is **w_j ~ N(0, 1), exactly** —
   a standard-normal prior on each of the 4 weights. Not an analogy; an identity.
2. **The typed shrinkage is an empirical-Bayes posterior mean.**
   `(n·wmean(th) + 3·base)/(n + 3)` is the normal-normal posterior mean with prior
   centered at the driver's overall form and a hand-set pseudo-count of 3.
3. **`wmean(·, hl=8)` is a fixed-gain steady-state Kalman filter.** For a
   local-level model (skill = random walk with innovation variance q, observation
   noise r), the steady-state filter weights past observations geometrically with
   retention 1 − K. The frozen 0.5^(k/8) has per-start retention 2^(−1/8) ≈ 0.917,
   i.e. gain K ≈ 0.083, which corresponds to a signal-to-noise ratio
   **q/r ≈ 0.0075**. The audit's preferred half-life 4 corresponds to K ≈ 0.159,
   **q/r ≈ 0.030 — the sensitivity grid is telling us the assumed skill-drift rate
   is ~4× too low.** (Derivation, not a fit: K = x/(1+x), x = [κ + √(κ²+4κ)]/2,
   κ = q/r.)
4. **`znan` missing → 0 is complete pooling to the field mean.** A debut driver is
   assigned the population average on every feature — the crudest possible prior.
5. **`predict_next.py`'s Gumbel sampling is exact plug-in PL generative sampling.**
   The 40,000 simulated race orders are draws from the PL model at the point
   estimate ŵ — correct model, zero parameter or ability uncertainty.

So the honest decomposition of "go Bayesian" is four deltas: **(i)** carry
posteriors instead of plug-ins; **(ii)** learn the hand-set constants (the gain/
half-life, the pseudo-count 3, λ) from data as-of instead of freezing guesses;
**(iii)** pool jointly across driver/team/mfr/track instead of hand-rolled
shrinkage per feature; **(iv)** model skill as an evolving process. Formulations
A, B, C are bundles of these deltas.

One delta is worth killing immediately: **posteriors on the current 4 global
weights alone buy nothing.** With ~140 training races, each contributing a full
~36-driver ranking (~600 implied pairwise comparisons), the likelihood swamps a
N(0,1) prior on 4 parameters everywhere except the earliest walk-forward windows.
A Laplace approximation around the existing MAP (analytic Hessian, milliseconds)
would show near-point-mass posteriors on w from mid-2022 onward. The payoffs, if
they exist, live in **re-parameterized** models where per-unit data is genuinely
small — per-driver abilities, per-cell track effects, time-varying states. That is
why A/B/C are the right question and "make the current model Bayesian" is not.

---

## 2. The four payoffs, audited against this project's frozen consumers

The four payoffs are not abstract virtues here — each has to cash out against a
frozen spec or it is banked capability, not adoption currency.

### (1) Predictive accuracy vs 0.413 / 0.476 non-SS / 0.449 (2026 OOS)

The only payoff that can *adopt* anything: project doctrine is that no model change
ships without a pre-registered walk-forward A/B on paired per-race Spearman rho
(Wilcoxon one-sided, α Bonferroni-split, mean(d) ≥ +0.005). Assessment per
formulation in §4–§6. Summary: **B has a documented mechanism** (the mis-set
recency gain, §1 item 3); **A's mechanism is mostly already spoken for** by the
committed F2 pooling features and the existing typed shrinkage; **C's mechanism
points at the bottom of the finish order**, where predictable signal is thinnest.

### (2) Calibrated uncertainty — the headline Bayesian pitch, and the trap in it

Two uncomfortable facts, both from this project's own documents:

- **No frozen consumer rewards better uncertainty today.** The scoring spec logs
  full-order rho and threshold-at-0.5 H2H picks only (top-K explicitly banned to
  prevent metric shopping). The market benchmark bets **every** graded pick at flat
  stakes, intention-to-treat — it explicitly rejected EV-threshold filtering
  (because measured underconfidence would bias and starve a filter). Posterior
  width cannot change a pick unless it crosses 0.5, so genuine posteriors would
  leave the adjudicated pick stream essentially untouched.
- **The one measured miscalibration runs the wrong way for the naive pitch.** The
  audit found the model *underconfident* (says 64%, reality 74%). Posterior
  predictive averaging pushes pairwise probabilities *toward* 0.5 (Jensen through
  the sigmoid tails) — i.e. full Bayes on the same prior makes the measured defect
  marginally **worse**, not better. The countervailing effect — a hierarchical
  model *learning* the prior scale instead of freezing λ = 0.5 could de-shrink
  early-window fits — has unknown net sign. Meanwhile the known fix (a
  recalibration map) is non-Bayesian and is **deliberately deferred**
  (`specs/README.md`: "known, real, and deliberately untouched — it would change
  the pick stream mid-benchmark").

What posteriors genuinely fix is **conditional** calibration: today a 5-start
rookie's features are treated as exactly as reliable as a 150-start veteran's, so
pairs involving low-information drivers are overconfident *relative to the bulk*
even while the bulk is underconfident. Ability posteriors width-stratify by
information. That improves the published `p_win/p_top5/p_top10` (public-log
credibility) and is the load-bearing input to any future simulation/DFS surface
(F5's sim map) — real value, but **banked capability**, not something the current
gates can reward. Verdict on payoff (2): genuinely valuable *later*, nearly
worthless *now*, and never a reason to adopt under the current protocol.

### (3) Small-sample / early-season behavior

Real and identifiable. The current fallback ladder is: no history → field mean
(complete pooling); thin history → the pseudo-count-3 shrinkage; and eligibility
(min_hist 5) simply excludes drivers from scoring, though they still appear in
forward predictions with fallback features (flagged `*` in the published files).
Partial pooling to **team/manufacturer** is strictly more informative than pooling
to the field mean — a rookie in a Hendrick seat is not a field-average draw. But
note the effect is *concentrated*: it moves a handful of driver-races per season
plus the first few weeks of each year, so its mean-rho footprint is small by
construction, and the cheap two-stage version of exactly this idea is already
pre-registered as F2 (exclude-self org/mfr features). The honest expectation:
payoff (3) mostly duplicates F2 at the mean-rho level; the increment unique to
full hierarchy (joint estimation, uncertainty-weighted pooling) is second-order.

### (4) Interpretability / coherence

Cuts both ways. Gains: latent skill trajectories with credible bands are the most
legible artifact this project could publish; a driver/team/mfr decomposition
answers "who is carrying whom"; one coherent generative story replaces four
hand-set constants. Costs: the frozen model's entire state is **4 numbers with
signs** — that story is a real asset and it dies in a 200-parameter posterior.
And there is a doctrine collision: the DNF spec prides its decision on being
"deterministic, seed-independent." MCMC-based variants are neither — a
pre-registered seed plus per-step convergence gates (R-hat, divergences) with a
pre-registered red-step fallback would all be mandatory machinery. The
deterministic filtering path (§5, §7) preserves the doctrine exactly; the MCMC
paths strain it.

---

## 3. Compute and tooling — the feasibility question

**Anchor:** the current full walk-forward pass — ~150 scored steps, PL refit
before every race, warm-started L-BFGS on 4 parameters, four specs evaluated in
one replay — runs in **minutes on this laptop** (documented in the DNF spec §5).
Hardware here: 10 physical cores, 32 GB. Any Bayesian variant must be priced
against that anchor, per walk-forward pass, per variant, including discards.

### 3.1 The inference ladder (estimates, not measurements — nothing was run)

| Approach | Per step | Full pass (~150 steps) | Deterministic? | New deps |
|---|---|---|---|---|
| Current MAP (base) | ≲ 1 s | minutes | yes | none |
| Laplace posterior on w (diagnostic) | +ms | minutes | yes | none |
| **B via Kalman/ADF filtering + as-of marginal-likelihood hyperparams (§7)** | ~0.1–0.5 s | **minutes** | **yes** | **none** |
| A via joint Laplace (~200 latent abilities + β) | ~1–5 s | tens of minutes | yes | none |
| A/C via ADVI (mean-field VI) | ~10–30 s | ~1 h/variant | no (seed) | PyMC or numpyro |
| A via per-step NUTS (numpyro, warm-started) | ~1–4 min | **3–10 h/variant/pass** | no (seed + convergence gates) | numpyro (JAX) |
| C via per-step NUTS (custom competing-risks × rank likelihood) | ~2–8 min | 5–20 h/variant/pass | no | numpyro or Stan |

Three structural observations that matter more than the row estimates:

- **Walk-forward evaluation is sequential by construction, and sequential updating
  is exactly what filtering does.** Refitting MCMC from scratch at every step
  fights the problem's structure; a filter (or SMC over the posterior) rides it.
  This is why formulation B is cheap: its natural inference *is* the walk-forward.
- **Per-step MCMC is feasible but expensive in exactly the s60 way** — an
  overnight, hours-not-minutes job per variant per pass, before discards, with a
  convergence gate at every one of ~150 steps where a single red step poisons the
  pass unless the fallback is pre-registered. Budget honestly: a 3-variant
  MCMC A/B is a multi-day compute program. Never required for the recommended path.
- **Mean-field VI is the wrong tool for this project specifically:** its known
  failure mode is *underestimating posterior variance* — it spends the compute
  without delivering payoff (2), and adds stochastic-optimization noise to a
  decision protocol built on determinism. Assessed and rejected as the primary
  path; acceptable only as a point-prediction accelerant, which we don't need.

### 3.2 Tooling in the local .venv

Verified 2026-07-19: `.venv` runs **Python 3.14.6** with numpy 2.5.1 /
scipy 1.18.0 (plus duckdb/pyarrow); the Anaconda interpreter is Python 3.13.5
(numpy 2.1.3 / scipy 1.15.3). Consequences:

- **The recommended path (§7) needs zero new packages** — scalar Kalman
  recursions and L-BFGS-B on a 2-parameter marginal likelihood are numpy/scipy.
  No requirements.txt change, no wheel risk, no compilation.
- If NUTS is ever needed (A-full, C): **numpyro (JAX CPU)** is the preferred
  stack for this likelihood (vectorized suffix-sum logsumexp JITs well; CPU is
  fine at this scale). Caveat: Python 3.14 is new enough that PPL wheel lag
  (jax, pytensor) is a live risk — verify wheels at install time; the conda
  3.13.5 interpreter is the pre-verified fallback (the track-audit gate already
  runs on it). cmdstanpy additionally needs the Xcode CLT + a cmdstan build;
  model compile ~1–2 min but reused across steps. None of this blocks anything
  today because nothing recommended requires it.
- Parallelization, if MCMC passes ever run: variant passes are independent
  read-only consumers of the parsed data (the pooling spec §6 already records
  this hazard check) — 2–3 concurrent passes fit in 10 cores. State the plan,
  stagger starts, don't oversubscribe.

### 3.3 Identifiability and leakage risks (all formulations)

- **As-of discipline is the non-negotiable.** Every learned quantity —
  hyperparameters (q, r, pooling scales, λ), filter states, posterior draws —
  must be computed from races strictly before the race being scored. For
  filters this means **predictive (filtered) states only, never smoothed
  states**: a smoothed trajectory injects future races into past features and
  silently breaks the walk-forward. This is the single most likely
  implementation bug in any B build; it is pinned in §7.
- **The hl=4 signal is motivation, not a free parameter value.** The audit's
  half-life sensitivity was computed across the whole sample — hard-setting
  hl=4 (or q/r = 0.030) in a variant would be tuning on the test set. The A/B
  must let the as-of marginal likelihood *learn* the gain at each step. If the
  learned gain converges toward the hl≈4 region, that is the finding validating
  itself out-of-sample, step by step.
- **PL location invariance (A):** per-race utility shifts cancel in the
  likelihood; with per-race z-scored features this is already handled, but
  latent abilities need one global sum-to-zero constraint or the posterior
  drifts along a flat direction.
- **Driver–team separation (A)** is identified only by driver movement and
  multi-car teams; over a 2022–2026 window it is weakly identified and the
  posteriors will be correlated — fine for prediction, dangerous for
  storytelling ("driver X > driver Y" claims from correlated posteriors).
- **Per-driver dynamics parameters are not identifiable** from 20–160 obs per
  driver; q and r must be shared across drivers (pre-registered in §7). The
  filter still adapts per driver through its variance recursion — early starts
  get high gain automatically. That is the small-sample payoff arriving through
  the dynamics, without per-driver hyperparameters.
- **Superspeedway cells are near-pure noise** (rho ≈ 0.16, model-independent,
  calibration worse than coin flips) — any per-type latent structure at SS
  estimates priors, not signal. Formulations should not spend parameters there.
- **MCMC nondeterminism vs doctrine:** covered in §2(4); pre-registered seeds +
  convergence gates + fallback, or use the deterministic paths.

---

## 4. Formulation A — hierarchical Bayesian PL

**Model sketch.** u_{i,r} = β·x_{i,r} + α_{d(i)} with α_d ~ N(θ_{team},
σ_driver²), θ_team ~ N(φ_mfr, σ_team²), optionally γ_{d,tracktype} with its own
pooling; full posteriors on everything; hypervariances learned. This would
*unify* the typed pseudo-count-3 shrinkage (§1 item 2), the F2 exclude-self
pooling features, and F3's hierarchical track profiles under one joint model —
which is exactly its appeal and exactly its governance problem.

**Payoffs.** (1) Accuracy: the mechanism — pooled information for
low-information drivers plus a persistent ability term — is mostly already
deliverable by the committed F2 features and the existing typed shrinkage; the
audit also found the persistent-form direction weak (overall finish history got
weight ≈ −0.04 ≈ 0 once typed/grid/pace were present). Expected mean-rho gain:
small, sign uncertain. (2) Uncertainty: the real gains (§2), all currently
unadjudicated. (3) Small-sample: A's home turf — pooling to team beats pooling
to field mean — but concentrated on few driver-races. (4) Interpretability:
the decomposition is attractive; the parameter count and (if MCMC) seed
dependence are not.

**The structural flaw:** a *static* α_d over 2022–2026 is false — form moves,
rides change mid-season. Fixing that inside A means either windowing (back to a
hand-set recency knob, the thing we're trying to kill) or adding dynamics —
i.e. formulation B. **A is not coherent as a standalone successor; the coherent
end-state is dynamic-hierarchical, which makes B the right first move.**

**Compute.** Honest per-step NUTS: 3–10 h/variant/pass (§3.1). But A does not
require MCMC: a joint Laplace approximation over (α, β) — a few hundred
parameters, analytic or AD-free finite-difference Hessian — is tens of minutes
per pass, deterministic, numpy-only. If A ever runs, Laplace-first is the
pre-registered inference doctrine, with MCMC only as a check on the winner.

**Verdict: CONDITIONAL — bank the design, do not run yet.** Sequencing is
forced by governance as much as by statistics: F1 and F2 are committed,
pre-registered, and sequenced first (roadmap #4); running A now would either
duplicate F2's question with a different estimator or contaminate its
multiplicity family. Execute A only after the roadmap-#4 decisions **and** the
B decision (§7) are recorded, against the then-frozen baseline, under a fresh
spec whose required contents are outlined in §8. If F2 adopts a pooling feature,
A is the principled consolidation candidate; if F2 nulls **and** B nulls, A's
prior drops sharply and letting it die unrun is a legitimate outcome.

---

## 5. Formulation B — dynamic state-space skill

**Model sketch.** Latent per-driver skill follows a random walk,
α_{d,t} = α_{d,t−1} + η_t (var q), observed through noisy race outcomes
(var r); features are built from the filter's *predictive* mean instead of the
fixed-gain EWMA. The frozen 0.5^(k/8) is the K = 0.083 fixed-gain special case
(§1 item 3) — so B is not a new model so much as **un-freezing a gain that the
project's own audit says is mis-set** (hl=4 ≈ K = 0.159 beat hl=8 "nearly
everywhere" in the 16-config sensitivity grid). The frozen config can only
change through a new pre-registered spec — the DNF spec explicitly sanctions
this path ("any new variant requires a new pre-registered spec committed before
it is run").

**Why this is the strong formulation:**

1. **It is the only one with documented accuracy headroom.** Every other
   formulation argues from theory; B argues from the audit's own sensitivity
   table. And the proper filter is *better* than the best fixed half-life: the
   gain adapts per driver with information count (fast updates early, slow at
   steady state), and uncertainty grows through absences (part-timers, injury
   returns) — two things no fixed-k EWMA can do.
2. **It is a filtering problem, not an MCMC problem.** Twenty years of prior
   art runs dynamic skill models with approximate Bayesian filtering at trivial
   cost: Glicko (Glickman 1999) is ADF on paired comparisons; TrueSkill
   (Herbrich–Minka–Graepel 2006) is EP on multi-competitor races; Glickman &
   Hennessy (2015, JQAS) is precisely a dynamic state-space rank-order-logit
   (PL) model for multi-competitor sports. (Prior-art anchors from model
   knowledge — F6, the external scan now running, should verify these and pull
   anything transferable; Graves–Reese–Fitzgerald 2003, JASA, is the NASCAR
   hierarchical-permutations ancestor for A.) On the feature-series
   formulation below, inference is *exact* scalar Kalman filtering — no
   approximation debate at all.
3. **It has a surgical A/B.** The minimal variant swaps the aggregator
   (`wmean` → learned-gain filter mean) and changes nothing else — same
   features, same PL, same λ, same eligibility, same scored sets. Low paired
   variance (a re-encoding, per the DNF amendment's measured SE 0.0008–0.0023),
   clean attribution, minutes of compute, fully deterministic.

**Payoffs.** (1) Accuracy: the one formulation where a mean-rho gain has a
mechanism *and* prior evidence; still honestly uncertain — the +0.005 floor is
a real bar, and the sensitivity signal was standalone-feature-level, never
tested inside the fitted PL. (2) Uncertainty: filtered variances come for free
and stratify exactly the way §2 wants (wide for rookies/returners) — produced
but deliberately unused by this A/B (see §7 "what this does not ship").
(3) Small-sample: the adaptive gain *is* small-sample handling through
dynamics; init priors pin debut behavior. (4) Interpretability: skill
trajectories with bands, and the learned (q, r) is a publishable fact about the
sport ("Cup form drifts with SNR ≈ x per start") replacing an arbitrary 8.

**Compute.** §3.1: minutes per pass, deterministic, zero new dependencies.
The full latent-utility version (skill inside the PL likelihood, TrueSkill-style
EP) is a later, separately-specced step if the aggregator swap wins and leaves
evidence it under-delivers; do not start there.

**Verdict: RECOMMEND.** Pre-registered A/B design in §7, ready to lift.

---

## 6. Formulation C — generative outcome model

**Model sketch.** Finish order arises from a generative race: latent pace sets
a running order; a hazard process (crash/mechanical, per §F1's taxonomy)
retires drivers, who are classified by laps completed below the finishers —
NASCAR's actual classification rule, which the scoring spec enshrines as the
target ("a driver's official finishing_position is their outcome, full stop").
Cautions enter as race-level shocks driving variance and attrition clustering.

**The genuine insight in C:** PL is unidimensional per driver — one utility
sets both the middle and the tails of the finish distribution, so PL literally
cannot represent "high win probability AND high wreck probability," which is
the actual shape of superspeedway aces and aggressive short-run cars. Any
simulation/DFS surface built on plug-in PL sampling inherits that thin-tailed
lie. A competing-risks × conditional-rank model fixes it.

**Why that doesn't cash out today, on all four payoffs:** (1) Accuracy: the
mechanism operates mostly on the DNF-ordered bottom of the field, the least
predictable region; the *cheap* version of the signal (status-aware features)
is already pre-registered as F1 with an adopt/kill rule — running C first would
moot a committed spec, and F1's result is itself the best evidence about
whether attrition carries exploitable signal at all. (2) Uncertainty: the
bimodality payoff is real and is C's whole case — but it lands on win/top-5
tails and simulation surfaces that **no frozen metric adjudicates** (rho can't
see it; H2H threshold picks can't see it; the market benchmark is H2H-only;
top-K logging is banned). Adopting C under the current protocol is structurally
impossible on its merits. (3) Small-sample: neutral. (4) Interpretability:
attractive (matches the sport's causal structure; overlaps G's clean-air world
and F5's 12-knob sim map) but it is the heaviest model with the most free
design choices — the hardest thing in the program to pre-register honestly.
Compute: heaviest (§3.1), custom likelihood, per-step MCMC.

**Verdict: NULL for now — recorded as a decision, not a deferral by neglect.**
Revisit triggers, any one sufficient to justify drafting a spec:

- **T1.** A simulation/DFS surface with its own pre-registered scoring rule
  (e.g. log-loss/Brier on p_top10 or finish-distribution CRPS) is adopted into
  the plan — C is the model that surface would need.
- **T2.** The market benchmark returns EDGE and the project extends to win/
  futures markets, where tail calibration is what's priced.
- **T3.** F1 adopts a DNF variant and its (diagnostic) per-type splits
  attribute the gain to attrition ordering — evidence the generative structure
  has signal worth modeling deeper than features.

---

## 7. Pre-registered A/B design — dynamic-skill recency ("learned-gain filter")

*Drafted 2026-07-19 in F7, before any variant has been run or coded. Becomes a
binding pre-registration only when lifted verbatim into
`specs/dynamic_skill_recency.md` in its own commit, before any variant code
exists. Written to the DNF/pooling specs' template so the implementing session
makes zero judgment calls.*

### 7.1 Sequencing and gates (project discipline)

- Executes only when `predictions/scores_log.csv` has ≥ 8 scored races (same
  gate as roadmap #4), **after** the F1 (DNF) and F2 (pooling) decisions are
  recorded, on the gold feature layer (post-D1 re-prove). Baseline = the
  then-frozen config, reproduced exactly.
- The A/B runs on the full historical backtest sample (all years present,
  passed explicitly), not on forward races.
- Frozen model files untouched; the A/B lives in `src/step9_dynskill_ab.py`
  (its own copy of the replay loop, clearly marked as derived from
  `walkforward.run`). Adoption, if any, follows the DNF spec §7 procedure
  (predict_next.py + config_version bump, walkforward.py never edited, ITT
  continuity for the market benchmark).

### 7.2 The filter (shared machinery for both variants)

Scalar local-level Kalman filter per history series. For a series y_1..y_n with
hyperparameters (q, r) and init (μ0, σ0²): standard recursions; the **feature
value is always the predictive mean before the current race** — filtered, never
smoothed (§3.3).

- **Hyperparameters, shared across drivers:** (q_fin, r_fin) for finish-scale
  series — used by both the overall series hf[d] **and** the typed series
  ht[(d,tt)] (typed cells are too short to identify their own) — and
  (q_pace, r_pace) for pace series hp[d].
- **As-of estimation, every step:** maximize the exact Gaussian prediction-
  error-decomposition log-likelihood, summed over all driver series with ≥ 2
  observations built from races strictly before the race being scored;
  scipy L-BFGS-B over (log q, log r); deterministic init at r = the as-of
  pooled within-driver variance of that series type and q = 0.0075·r (the
  frozen-config-equivalent SNR — the null hypothesis as the starting point);
  bounds q ∈ [1e-6, ∞), r ∈ [1e-4, ∞). Deterministic by construction: fixed
  init, fixed bounds, no seeds.
- **Init per driver series:** μ0 = the as-of pooled mean of that series type
  across all drivers; σ0² = the as-of pooled variance. (A debut driver's
  predictive mean is the field mean — matching znan's current fallback — and
  moves quickly as observations arrive.)
- Empty series → NaN → 0 via znan, exactly as base. Everything else —
  features [fin, pace, typed, start], znan, PL λ = 0.5, refit-every-race,
  burn 15, min_hist 5, min_drv 20, typology, typed pseudo-count formula —
  byte-identical to base. **Eligibility is untouched**, so all variants score
  the identical race and driver sets (the pairing-integrity rule the DNF spec's
  V2 paragraph exists to protect).

### 7.3 Variants (exactly two; no others may be tested under this spec)

- **BV1 — start-indexed gain swap (pure aggregator replacement).** The state
  evolves once per *driver start* (index k = that driver's own races, exactly
  the current `wmean` indexing). fin = filter-predictive mean of hf[d];
  pace = filter-predictive mean of hp[d]; typed = the frozen shrinkage formula
  verbatim, `(n·typed_f + 3·base_f)/(n+3)` with n = len(ht[(d,tt)]), where
  typed_f and base_f are the filtered means of the typed and overall series.
  One change only: the fixed 0.5^(k/8) gain becomes learned and
  count-adaptive.
- **BV2 — calendar-indexed evolution (adds absence decay).** Identical to BV1
  except the state evolves once per race in the sample sequence regardless of
  participation (predict-only steps when the driver is absent; observation
  update only on participation, pace update only when the pace value exists).
  A part-timer's information now decays while parked and their predictive
  variance grows — the semantics no start-indexed EWMA can express. This is
  deliberately the second variant: it bundles the gain swap with a semantics
  change, and the two-variant design lets the data say whether the semantics
  change adds anything beyond BV1.

### 7.4 Evaluation protocol

Identical in form to the DNF spec §3: one replay evaluates base + BV1 + BV2 on
identical scored races; per-race Spearman rho of each spec's utility vs
official finish. **Baseline replication gate**, hardened per the DNF Finding-2
amendment: the replay must explicitly set and `assert` years (all present,
incl. 2026+), typology (then-frozen), typed_mode ('shrinkage'); base's
year ≤ 2025 scored mean rho must be within ±0.003 of the then-frozen anchor
with the exact then-frozen scored count (0.4130 / n = 108 as of 2026-07-18;
use the latest RESULT-block anchors at execution). Assertions are the primary
defense; the rho gate is coarse.

**Implementation sanity check (diagnostic, never a gate):** with (q, r) fixed
at q/r = 0.0075 and diffuse init, BV1's fin feature should correlate > 0.99
with base's `wmean` values away from series starts — the filter nests the
frozen config approximately; report the correlation and where it degrades.

### 7.5 Kill/keep decision rule (the pre-registration)

Per variant v: paired per-race d_i = ρ_v,i − ρ_base,i over all scored races;
one-sided Wilcoxon signed-rank (`alternative='greater'`, default
zero-handling).

- **Adopt v only if BOTH** p ≤ α_adj **and** mean(d) ≥ +0.005.
- **α_adj, resolved now per the pooling spec's program-wide multiplicity
  precedent:** if the baseline config changed since the roadmap-#4 family
  (i.e. F1 or F2 adopted something), this is a fresh 2-test family →
  α_adj = 0.05/2 = 0.025. If F1 and F2 both adopted nothing, these are tests
  7–8 against the same baseline and data → α_adj = 0.05/8 = 0.00625.
- Both pass → higher mean(d); exact 4-decimal tie → BV1 (fewer semantic
  changes). **At most one variant adopted.**
- Neither passes → **the answer is no**: record the result, and no tweaked
  gains, alternative state models, per-type hyperparameters, or re-indexing
  schemes may be tried under this spec — a new variant needs a new
  pre-registered spec.
- Power note, recorded: both variants are re-encodings of existing histories,
  so expect paired SE ≈ 0.001–0.003 (the DNF amendment's measured range) —
  even α = 0.00625 is reachable well below the practical floor, so **the
  +0.005 floor binds**, exactly as designed program-wide: statistically
  significant micro-gains are rejected on purpose.
- Diagnostics reported, never gates: mean(d) by track type, non-SS, 2026+
  subset, bootstrap CI of mean(d) (4,000 resamples, np seed 7), fitted
  (q, r) trajectory across steps and its implied steady-state half-life, final
  PL weights, the §7.4 nesting correlation.

### 7.6 What this A/B does and does not ship

Adoption changes **feature construction only**. The probability pipeline
(plug-in Gumbel sampling), the pick rule, and the published-file schema are
untouched — no mid-benchmark pick-stream change (ITT discipline). The filter's
predictive **variances** are computed and logged as diagnostics but consumed by
nothing; any future use (uncertainty-weighted features, posterior-predictive
win probabilities, recalibration) requires its own pre-registered spec.

### 7.7 Execution constraints

Single process, deterministic, seed-free (the bootstrap CI's seed 7 is
diagnostic-only). Estimated wall clock for the full pass: **minutes** (per-step
hyperparameter refit is an L-BFGS over a 2-parameter exact likelihood across
~200 scalar series). No new dependencies; runs in the existing .venv. Bordered
summary block per house style; RESULT block appended to the spec per the DNF
spec §6 pattern, including the absolute anchors (mean rho all-years and
year ≤ 2025 with counts) for the next spec's baseline gate.

---

## 8. Conditional design outline — hierarchical PL (banked, not pre-registered)

If A's trigger fires (§4), its spec must resolve, at minimum: **model** —
u = β·x + α_d (+ γ_{d,type} only for non-SS types, §3.3), α pooled through
team-of-record-at-race with renames-as-new-entities (pooling spec precedent),
one sum-to-zero constraint; **inference** — Laplace-first (deterministic,
minutes-scale), NUTS only as a posterior-quality check on a winning variant,
with pre-registered seed and per-step convergence gates if used for the
decision; **variants** — at most two (e.g. driver-intercept-only vs
driver+team hierarchy), against the then-frozen baseline with the then-current
α family; **gate** — identical form (Wilcoxon one-sided, α per the
multiplicity precedent, mean(d) ≥ +0.005, baseline-replication with asserts);
**leakage** — hypervariances estimated as-of per step, never globally. Expected
compute: tens of minutes per pass (Laplace) / hours (NUTS check). This outline
is deliberately not a pre-registration: A's baseline, family, and even its
motivation depend on three decisions (F1, F2, B) that don't exist yet, and
freezing its details now would just be renegotiated later.

---

## 9. Proposed plan edits (owner fold-in; `plan/schedule.yml` not touched)

1. **F7 → ✅ done**, deliverable `research/bayesian_modeling_assessment.md`
   (this file's commit). Executive summary: assessed three Bayesian
   formulations against four payoffs with compute first-class; verdicts
   B = recommend (pre-registered A/B banked), A = conditional (banked outline),
   C = null-with-triggers; the recommended path needs no MCMC, no new
   packages, and minutes of compute.
2. **Add F8 — "Dynamic-skill recency A/B (spec lift + run)".** Gated: ≥ 8
   scored races AND on gold (post-D1) AND after F1→F2 decisions recorded
   (baseline = then-frozen config). Two mechanical steps in one session:
   (a) lift §7 verbatim into `specs/dynamic_skill_recency.md` (own commit,
   before any variant code); (b) implement `src/step9_dynskill_ab.py` and run.
   Model: **Sonnet 5, thinking on, effort xhigh** (same tier as F1/F2 — gated
   eval work where the numbers must be right; the judgment was spent here in
   F7). Wall clock: ~2–4 h including discards; compute itself is minutes.
3. **Add F9 (conditional) — "Hierarchical PL pre-registration + A/B".**
   Blocked on: F8 decision recorded AND (F2 adopted a pooling variant OR the
   owner elects to test the joint-estimation increment after an F2 null).
   Spec session on the top judgment tier (**Fable 5 / then-current judgment
   tier, thinking on, xhigh** — §8 outline to full spec); run session Sonnet 5
   xhigh, Laplace-first. If F2 and F8 both null, recommend letting F9 die
   unrun and recording that.
4. **Record formulation C as decided-null** in the plan prose (no session),
   with §6's three revisit triggers named, so it cannot be re-proposed from
   scratch without meeting one.
5. **F6 cross-link:** the external scan should verify/enrich the §5 prior-art
   anchors (Glickman 1999; Herbrich et al. 2006; Glickman & Hennessy 2015;
   Graves–Reese–Fitzgerald 2003) — they are cited here from model knowledge
   and belong in F6's academic sweep with real citations.

---

## 10. Bottom line

Bayesian methods are **appropriate** here — the current model is already a MAP
estimate wearing four hand-set Bayesian constants — but "better" is only
demonstrated one gated A/B at a time, and only one formulation earns a gate
today. The recommendation is deliberately unglamorous: **un-freeze the recency
gain via exact Kalman filtering (formulation B, §7)** — the one change with
documented headroom in this project's own audit, a deterministic minutes-scale
implementation with zero new dependencies, and a two-variant pre-registered
A/B that slots into the existing program after F1/F2. Hierarchy (A) is banked
behind it; the generative model (C) is a good idea waiting for a surface that
can score it, and is recorded null until one exists. The headline Bayesian
promise — calibrated uncertainty — is real but currently unpurchasable: no
frozen consumer rewards it, and the one measured miscalibration runs opposite
to what posterior-widening delivers. Compute, the central feasibility fear,
turns out to be a non-issue for everything recommended and an honest
overnight-per-variant cost for everything merely banked.
