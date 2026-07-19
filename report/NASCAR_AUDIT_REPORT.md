# Zero-Trust Audit: the NASCAR Prediction Project

*Independent reproduction and extension of the prior session's empirical claims, run against the live `cf.nascar.com` feeds with entirely new code. July 18, 2026.*

---

The short version: **the prior session's numbers are real, and two of its five conclusions are overstated anyway.** Every headline figure replicates to within ±0.001 from the raw feeds using independently written code — this was honest work, not a fabricated backtest. But the session never ran a significance test, and once you do, its weakest claim (speed beats past finish) turns out to be statistically indistinguishable from zero and fragile to the pace definition, while its market-inefficiency inference from qualifying data is not just unsupported but backwards. Meanwhile its strongest claim — that predictability varies wildly by track type — survives every stress test I could throw at it, including twenty 2026 races the prior session never saw. And its asserted "ceiling" of ~0.38 rank correlation is not a ceiling at all: a properly fitted ranking model breaks 0.41 using nothing but the prior session's own features plus the starting grid.

| Claim | Verdict | One line |
|---|---|---|
| **C1** Speed beats past finish | **Partially reproduced** | Their number replicates (+0.010) but is not significant (p=0.17) and flips sign under other pace definitions |
| **C2** Track-type conditioning is the biggest lift | **Reproduced** | +0.028 replicates, p<0.0001, survives typology correction (+0.031) and all 16 sensitivity configs |
| **C3** Predictability is wildly uneven by type | **Reproduced, strengthened** | Confirmed with corrected typology, confirmed on 2026 out-of-sample, confirmed model-independent |
| **C4** Starting position weaker than past finish | **Method dispute** | The −0.008 gap replicates but p=0.44; the strategic inference drawn from it is inverted (see §6) |
| **C5** Finish order mostly noise, ceiling ~0.38 | **Failed as stated** | 0.413 achieved with their own features properly fitted; 0.449 on 2026; 0.476 on non-superspeedways |

Everything below was computed walk-forward (each race predicted from prior races only), from feeds pulled fresh during this audit. The scripts accompany this report so the audit is itself auditable.

## 1. The data layer holds

The three endpoints in the brief are live, public, and unauthenticated. The 2022–2025 seasons list exactly 144 Cup points races; **143 have complete lap-time and results feeds**, which is precisely the prior session's sample size. The one gap is worth knowing about: the fall 2025 Talladega race (`race_id` 5580) carries a wrong date in the season index (2025-11-17, after the season ended) and its `weekend-feed.json` returns a **null `weekend_race` block** — lap times exist, results don't. That single anomaly, not missing data generally, explains "143 of 144."

Two hygiene notes the prior session never surfaced. First, its feeds occasionally 403 under concurrent load and succeed on retry, so any serious pipeline needs retry logic. Second, the `flags[]` alignment assumption (that `FlagState` at `LapsCompleted = L` labels lap *L*) checks out approximately — caution-flagged laps run 2–3× slower than green under that mapping — but caution-boundary laps are ambiguous, which the lap-trimming absorbs. I additionally found that the eligibility lists inherit the results feed's finish ordering, a trap that silently poisoned my own first calibration pass (§7) and would poison any pairwise analysis written casually.

## 2. The numbers replicate almost exactly; the inferences don't all survive

Running the prior session's exact configuration (their pace definition, half-life 8, burn-in 15, their typology) through my own code on the 143-race sample, scoring 128 held-out races:

| Predictor | Their mean ρ | My mean ρ | vs. finish baseline | Wilcoxon p | 95% CI of difference |
|---|---|---|---|---|---|
| Starting position | 0.345 | 0.346 | −0.008 | 0.44 | [−0.034, +0.018] |
| Past finish (baseline) | 0.354 | 0.354 | — | — | — |
| Adjusted pace | 0.364 | 0.364 | +0.010 | 0.17 | [−0.005, +0.025] |
| Combined | 0.368 | 0.369 | +0.015 | 0.0003 | [+0.007, +0.023] |
| Combined + typed | 0.381 | 0.382 | +0.028 | <0.0001 | [+0.018, +0.038] |

The replication is about as clean as replications get. But the two rightmost columns — which the prior session never computed — split the claims into two tiers. The *combined* and *typed* lifts are statistically solid. The *pace-alone* edge (C1) and the *start-vs-finish* gap (C4) are noise-compatible: their confidence intervals comfortably span zero. The prior session reported all four differences with the same rhetorical confidence. It should not have.

## 3. C1 is fragile; the structural claims are not

The brief correctly demands that findings survive methodology choices other than the original ones. I varied the pace aggregation (their median-of-best-85%, plus a trimmed mean of the best 70%, a 20th-percentile lap, and their own best-20% "clean-air proxy") against four recency half-lives, sixteen configurations in all, plus burn-in and eligibility variations.

The pace-alone edge over past finish is **positive in only half the configurations and significant in just three**, all at a shorter half-life (4 races) than the prior session used. Under the trimmed-mean aggregation it inverts outright, to −0.04 to −0.08. "Speed beats past finish," as a standalone claim about standalone predictors, is an artifact of aggregation choice — a finding of exactly the kind the brief said to look for.

The structural claims are a different story. The typed-conditioning lift is **positive in all sixteen configurations** (+0.005 to +0.050) and significant in thirteen; the plain combined lift is positive in nearly all. The honest restatement of the project's core empirics is therefore not "speed beats finish" but: *pace contains real information that finish history doesn't, which shows up reliably when features are combined — and track-type conditioning amplifies it.* One incidental discovery: recency matters more than they modeled. Half-life 4 beats their half-life 8 nearly everywhere, tripling the C1 edge (+0.031, p=0.001) under their own pace definition.

## 4. The typology was buggy — and the bugs cut against them

The prior session's track-type map keys on exact name strings, and the feed disagrees with several of its keys. `'Chicago Street Race'` (their map says `'Chicago Street Course'`), `'Charlotte Motor Speedway Road Course'`, `'Indianapolis Motor Speedway Road Course'`, `'Road America'`, and `'Autódromo Hermanos Rodríguez'` all silently defaulted to UNIQ — roughly eleven road-course races miscategorized — as did every Dover race and the Bristol dirt races, which appear in no version of their map. Their own caveat that "road courses n≈11 are directional" was self-inflicted: the real road sample is 22.

The damning-sounding bug turns out to be exculpatory in effect. Re-running with a corrected typology (roads complete; Dover to short tracks; Darlington, Pocono, the Indy oval, and WWTR to intermediates; Bristol dirt quarantined), the typed lift *rises* from +0.028 to +0.031. The misclassification deflated their headline result slightly rather than inflating it.

The per-track data also settles the assignments the brief flags as disputable. Atlanta's post-reconfiguration races score 0.227 — squarely superspeedway-like (Daytona 0.067, Talladega 0.198), nowhere near the intermediates (~0.41). Their contested Atlanta→SS coding is empirically right. Dover (0.480) behaves like the short tracks; Pocono (0.447) and Darlington (0.371) sit in the intermediate range, so parking them in UNIQ threw away signal.

## 5. C3 is the project's best result, and it survives everything

Under the corrected typology, on the full sample:

| Track type | n | Typed model ρ | 95% CI | Naive baseline ρ | Model lift |
|---|---|---|---|---|---|
| Short tracks | 35 | 0.515 | [0.47, 0.56] | 0.476 | +0.039 |
| Intermediates | 50 | 0.406 | [0.36, 0.46] | 0.378 | +0.028 |
| Road courses | 22 | 0.355 | [0.26, 0.44] | 0.301 | +0.054 |
| Superspeedways | 20 | 0.162 | [0.09, 0.24] | 0.157 | +0.005 |

Three things make this finding unusually solid. The short-track and superspeedway confidence intervals don't come close to touching. The collapse at superspeedways afflicts the *naive baseline identically* (0.157), so it's a property of the sport, not of any particular model. And on the twenty 2026 races — data that did not exist when the prior session ran — the ordering reproduces intact: short tracks 0.62, intermediates 0.45, roads 0.40, superspeedways 0.19. Note also the fourth column: the model's *edge over baseline* concentrates on roads and short tracks and is essentially zero at superspeedways. Skill doesn't just fail to predict plate racing; skill *differentials* stop mattering there. The strategy's "press where predictable, stand down at Daytona" posture is the correct reading of the data.

## 6. The ceiling was an artifact — and C4's strategy inference is backwards

The prior session combined its features by summing z-scores with hand-picked weights (1, 0.5, 0.5) and concluded the sport tops out around ρ 0.38, "60%+ noise." The brief's §6 suspected this was a weak-combination artifact. It is. I fit a **Plackett–Luce ranking model** with linear features, weights re-estimated each race using only prior races — no hand-tuning, no test-set leakage:

| Model (walk-forward fitted) | Features | Mean ρ | Pairwise acc. |
|---|---|---|---|
| Their z-score sum | pace, finish, typed | 0.382 | 0.640 |
| PL: pace + finish | 2 | 0.377 | 0.637 |
| PL: + typed history | 3 | 0.394 | 0.643 |
| PL: + starting position | 4 | **0.413** | 0.652 |
| PL: + adjusted pace + practice | 6 | 0.414 | 0.653 |

The fitted four-feature model beats their z-sum by +0.025 paired (p=0.001) — proper estimation is worth nearly as much as track-typing was, and it was left on the table while the strategy document chased exotica. On non-superspeedways it reaches **0.476** (pairwise accuracy 0.676); on the 2026 out-of-sample races, **0.449**. The "~0.38 ceiling" and the "60% noise" arithmetic built on it are wrong as stated, though the qualitative point survives: even 0.45 leaves most finish-order variance unexplained, and the last two features added nothing, so the true prior-form asymptote is plausibly in the mid-0.4s.

Where did the jump come from? **Qualifying.** And this is where C4's logic inverts. The prior session observed that starting position is (insignificantly) weaker than finish history *as a standalone ranking* and concluded the market's grid-anchoring "leaves room" — then never used the grid in any of its models. The fitted PL weights tell the real story: typed history 0.17, starting position 0.12, pace 0.12, and overall finish history **−0.04** — approximately zero. Once pace, typed history, and the grid are present, the "baseline everyone uses" is redundant, while the grid — which they dismissed — carries as much weight as their prized pace feature. Qualifying is a same-weekend, car-plus-track-specific speed measurement; of course it's complementary. A weaker standalone predictor is not a less useful feature, and the market-inefficiency story spun from that comparison should be retired.

## 7. The two asserted edges failed their first honest test

The strategy's claimed moat #1 is a "clean-air/fuel/tire-adjusted pace layer," asserted but never built. I built a first serious version: per-race fixed-effects regression of log lap-time ratio on driver dummies, tire-age terms within green-flag runs (restart laps dropped, pit-adjacent laps excluded), and running-position buckets — exactly the confound-stripping the strategy prescribes. The result is a genuine negative: the adjusted pace is **worse standalone than the crude field-median ratio** (0.316 vs 0.364, p=0.002) and adds **exactly nothing** in the fitted model (+0.000, p=0.89). The likely mechanism matters more than the number: track position is *endogenous to car speed* — fast cars run up front — so regression-controlling for position absorbs real speed into the position coefficients and attenuates the driver effects. Making this feature work requires causal identification (exploiting restarts and pit-cycle shuffles as quasi-experiments), not more controls. The strategy calls this layer "the single highest-leverage place to be better than everyone"; the first attempt suggests it is instead the *hardest* place, and that the crude ratio already captures most of what ordering-level prediction can use.

Same-day practice — asserted edge #2 — also added nothing (+0.001, p=0.29). The feed's practice field is a single best lap, usually qualifying simulation, and its information is largely subsumed by the qualifying result itself. The interesting version of this hypothesis (long-run practice pace from consecutive-lap averages) is not testable from this endpoint's `best_lap_time` field alone, so the claim stays open rather than refuted — but it is currently unsupported.

The calibration the strategy calls "the product" was measurable and, for the first time, measured. Plackett–Luce implies exact head-to-head probabilities; across 67,830 walk-forward pairs they show real skill (Brier 0.224 against a 0.250 coin flip) with one systematic, fixable flaw — regularization makes the model *underconfident* (when it says 64%, reality is 74%). The split by track type is the strategically decisive part: on picks where the model claims >60% confidence, it hits 82% at short tracks, 78% on roads, 76% at intermediates — and **56% at superspeedways, where its Brier (0.2514) is literally worse than betting coin flips**. An uncalibrated-by-type bettor bleeds money at Daytona no matter how good the model is elsewhere. That is the strongest quantitative argument yet for the strategy's own stand-down doctrine.

## 8. What the prior session got wrong or missed

**Statistically.** No significance testing anywhere, which let two noise-level differences (C1, C4) harden into strategy. Hand-picked combination weights, costing a real +0.025. A recency half-life twice as long as optimal. Finish histories that treat a crash DNF as information equal to a clean finish — a status-aware history (the `finishing_status` field is right there in the feed) is the most obvious untested improvement. And no per-claim uncertainty: the road-course "n≈11" hedge was its own typology bug.

**Structurally.** The grid was benchmarked as a rival and never used as a feature — the single most valuable omission, worth ~+0.02 on its own. The typology keyed on fragile name strings with a silent UNIQ default; silent defaults in hand-coded maps are how eleven road races vanish without a trace. And the "proprietary pace layer" was promoted from hypothesis to moat in the strategy document without anyone attempting it; the first attempt argues it's a research problem, not an engineering line item.

**Strategically.** The market is still entirely absent. Every result here, including mine, beats *naive baselines*; the brief is right that this establishes zero betting edge, and I'll add what the strategy underweights: NASCAR's thin markets carry *high hold* — head-to-head props are routinely juiced such that break-even is roughly 52–53% pairwise accuracy against the *book's* ordering, which is far sharper than a past-finish baseline. Thin markets are simultaneously less efficient and more expensive to trade; the strategy cites the first property and ignores the second. Logging closing lines remains the unstarted, load-bearing task. Second, in-race and telemetry claims remain fully unaudited (out of scope here, per the brief, but they carry much of the strategy's weight). Third, one small correction in the project's favor: the honest ceiling being ~0.45 rather than ~0.38 modestly *strengthens* the case that prior-form modeling is worth doing at all — while the fitted model's flat response to the last two features suggests the next real gains lie in DNF-aware targets, teammate/manufacturer pooling, and same-weekend data richer than a single practice lap.

## 9. Bottom line

Separating the two questions the brief demands be separated: **the prior session's numbers replicate essentially perfectly; its conclusions survive at roughly a 60% rate.** C2 and C3 — the structural spine of the strategy — are confirmed, strengthened by bug-fixing, and validated on genuinely unseen 2026 data; the stand-down-at-superspeedways doctrine now has calibration-level proof. C1 survives only in weakened, combination-dependent form. C4's number is noise and its strategic moral is inverted. C5's ceiling is broken by the prior session's own features under honest estimation. The two asserted future edges (clean pace, same-day practice) failed their first real tests, and the only benchmark that can ever justify the phrase "best in the world" — the closing line — remains unmeasured. The project is better than its skeptics should have feared and further from its own headline than its documents imply.

---

## Appendix: method, concisely

All data pulled fresh from `cf.nascar.com` during this audit: 163 races parsed (143 of 2022–2025, 20 of 2026), ~1.6M lap records. Pace features are green-flag lap times over the per-lap field median (≥10 cars), aggregated per driver under four variants. Fixed-effects pace: per-race OLS of log ratio on driver dummies + tire age and age² within runs (runs ≥6 laps, first 2 laps dropped, ratio >1.25 excluded) + running-position buckets, driver effects centered. All evaluation is walk-forward with a 15-race burn-in, drivers eligible after 5 prior races, races scored with ≥20 eligible drivers, per-race Spearman ρ averaged across races; paired comparisons use Wilcoxon signed-rank plus a 4,000-resample bootstrap CI over races. The Plackett–Luce model scores drivers by a linear function of within-race z-scored features (missing → 0), fit by L-BFGS on the exact PL likelihood with L2 (λ=0.5) on all previously *scored* races, refit before every race, warm-started. Head-to-head calibration uses the PL-implied pairwise probabilities on randomized pair orientations. Replication config matched the prior session exactly (median-of-best-85% pace, half-life 8, their typology as written, including its silent-UNIQ defaults). Scripts: `download.py`, `parse.py`, `walkforward.py`, `step2_sensitivity.py`, `step3_typology.py`, `step4_models.py`, `step6_calibration.py`.
