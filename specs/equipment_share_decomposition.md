# SPEC: Next Gen equipment-share decomposition — driver/team/make variance (F14)

**Status:** pre-registered 2026-07-20, before any variance component has been
estimated (the connectivity diagnostic in section 3 below was run during
derivation, per the standing requirement's own ordering — see that section's
note — but no worth parameter or variance share has been fit).

**Derivation source (execution contract):** `research/external_knowledge_scan.md`
§3.6 (E5 — van Kesteren & Bergkamp, *JQAS* 2023, arXiv:2203.08489) is
authoritative for the *template*: F1 finishing order modeled as a
rank-ordered logit / Plackett-Luce model with strength decomposed into
cross-classified random effects (their four: driver, driver-season,
constructor, constructor-season; hybrid-era constructor ≈ 88% of variance,
posterior SDs 1.63/0.73/0.54/0.35; DNFs excluded from their main
decomposition; their own explicit warning that the architecture is "probably
not suitable for prediction," descriptive only). §3.2 (E1 — Hunter 2004 +
Turner/van Etten/Firth/Kosmidis 2020) is authoritative for the **standing
requirement** this session inherits and must satisfy before estimating
anything: (i) a per-training-window strong-connectivity diagnostic per
Hunter's Assumption 1, and (ii) an explicit regularization scheme, with
part-timer shrinkage behavior stated. Both sections are imported **in full**
as this session's execution contract, per the kickoff prompt.

**Governance (restated, binding):** nothing computed here enters the frozen
PL prediction model without its own later pre-registered, walk-forward-gated
A/B. This session builds analytics/reference tables only. `walkforward.py`,
`predict_next.py`, and `gold_build.py` are not touched, and nothing here is
ever joined into `gold.wf_features`.

**Tier:** Analytics/reference (phase F's own note: "Analytics and reference
sessions (F3/F4/F13/F14/F19) never touch the frozen model"). No gated A/B, no
`>=8`-scored-races gate.

**Deliverable framing:** this is a **3-factor structural analogue** of the
paper's 4-effect model — driver, team, make — not a literal port of all four
terms. The kickoff, `plan/schedule.yml`'s F14 `exec_summary`, and phase F's
own framing all specify a driver/team/manufacturer split, not a
driver-season / constructor-season one. Season-varying interaction terms are
an explicit **non-goal** here (§7).

---

## 0. Scope (verified 2026-07-20, at spec-write time)

Cup only (`series_id=1`, `race_type_id=1`, `parse_status='ok'`), `year >=
2022` — **the same universe `gold.wf_features` defines** (D1's scope
amendment), reused for consistency with every other gold table, not
re-chosen. Verified counts at spec-write time: **164 races** (36+36+36+35+21
across 2022/2023/2024/2025/2026, 2026 partial-season-in-progress), **6,120**
`(driver_id, race_id)` rows, **101** distinct drivers, **3** makes
(Chevrolet/Ford/Toyota), **31** canonical teams (§1.2), field sizes 36–41,
zero finish-position ties in any race, DNF share 850/6,120 = 13.9%
(`status != 'running'`).

"Gold walk-forward data" (kickoff wording) is read here as **gold's scope
definition**, not `gold.wf_features`'s history columns — this session needs
each race's actual full finishing order plus same-race team/make, which
`wf_features` (a history-feature table) does not carry. Resolved, not
ambiguous: `gold.wf_features`'s own scope amendment (§10b of
`DATA_DICTIONARY.md`) is the citable, already-frozen definition of "the gold
walk-forward universe"; this session reuses that scope, sourced from
`silver.driver_race` (finish, status, make) joined 1:1 to `silver.results`
(team_name) on `(series_id, race_id, driver_id)` — verified clean at
spec-write time (6,120/6,120 rows joined, zero missing `team_name`, `make ==
car_make` agreement 6,120/6,120).

---

## 1. Entities (this session's own pre-registered choices)

### 1.1 Driver

`driver_id`, unchanged. 101 distinct in scope, ranging from 19 drivers with
exactly one race in the window to 14 drivers present in every one of the 164
races — the long part-timer tail §5.3's shrinkage claim is checked against.

### 1.2 Team — the organization key (resolved, citing prior art)

**Pinned:** `team_key := lower(trim(team_name))`, sourced from
`silver.results.team_name` (verified 6,120/6,120 populated, joined cleanly to
`silver.driver_race`).

**`team_mfr_pooling.md` §1 precedent, imported verbatim:** that spec already
established, for a different purpose (a teammate-pooling A/B feature), that
the parsed `team` field (`silver.driver_race.team`) is **per-car**
(`team_id`), not per-organization, and pinned the organization key as
`team_name`. It also pre-registered, as a deliberate simplicity choice, that
**org renames are distinct entities** — no manual alias table, "zero
judgment calls beats slightly longer histories." This session imports both
choices verbatim rather than re-deriving them: same organization key
(`team_name`), same rename policy.

**One addition this session makes, disclosed:** `team_key` applies a trivial
`lower(trim(...))` canonicalization on top of `team_name`, because a real
data artifact exists in scope that isn't a rename at all — `'TrackHouse
Racing'` (2022) vs `'Trackhouse Racing'` (2023–2026) is the **same**
organization with a mid-window capitalization change in the feed, verified
by checking `owner_id` continuity (both spellings share `owner_id=5229`, car
numbers `1/87/88/91/97/99` throughout). Collapsing this one pair is a
mechanical string-normalization fix, not a judgment call about
organizational identity — it merges exactly one pair (32 raw `team_name`
strings → 31 canonical keys, verified at spec-write time) and does **not**
touch any of the genuine renames below, which remain distinct exactly as
`team_mfr_pooling.md` prescribes:

| distinct entity (by `owner_id`) | `team_name` values kept apart | why kept apart |
|---|---|---|
| `owner_id` 3193 vs 4084 (both historically "Stewart-Haas Racing") | n/a — see below | two different charter-pairs, not one org (see rejected alternative) |
| SHR → Haas Factory Team (`owner_id` 4084) | `Stewart-Haas Racing` / `Haas Factory Team` | real ownership change (Gene Haas buyout), spans 2022–2026 in our own scope |
| `Roush Fenway Keselowski Racing` / `RFK Racing` | kept apart | rename, same policy |
| `Petty GMS` / `Petty GMS Motorsports` | kept apart | same-year label variant, not a pure case/whitespace artifact — trim+lower does not merge these two strings, and no alias table is introduced to force it, per the imported policy |

**Rejected alternative, verified empirically:** `silver.results.owner_id`
was considered instead of `team_name` (F16's domain-knowledge scan noted
`owner_id` "survives the SHR→Haas Factory rename that `team_name`
breaks" — true, `owner_id=4084` does span both names). But `owner_id` is
**not** a clean per-organization key either: querying the scope data shows
Stewart-Haas/Haas Factory Team's four 2022–2024 cars split across **two**
`owner_id`s (3193: cars `#4`/`#10`; 4084: cars `#14`/`#41`) despite all four
sharing one shop and one engineering organization throughout — `owner_id`
tracks charter-pair ownership entities, a **finer** grain than the
competitive-resource-sharing unit this decomposition's "team" component is
meant to measure (the F1-paper analogy is "constructor" — one organization,
several cars, one shared technical/engineering pool). Using `owner_id` here
would under-pool exactly the shared-resource signal the decomposition exists
to detect. `team_name` (organization/brand identity) is the closer proxy and
is kept, with the one disclosed case-normalization above.

**Team–make non-collinearity, verified:** 5 of 31 canonical teams fielded
more than one manufacturer within scope (`Haas Factory Team`: Ford→Chevrolet;
`Rick Ware Racing`, `Legacy Motor Club`, `Team Hezeberg`, `Live Fast
Motorsports`: each 2 makes) — team and make are empirically **not**
perfectly collinear in this data, so both components are separably
identified from the data itself, not only from the regularization prior
(§4).

### 1.3 Make

`silver.driver_race.make` directly (`Chevrolet`/`Ford`/`Toyota`) — already
the frozen parity field, no re-derivation, no prerequisite (`team_mfr_pooling.md`
§1 already noted `make` "needs no prerequisite ... already parsed and
complete").

### 1.4 DNF

`status != 'running'` — `DATA_DICTIONARY.md` §1b's exact convention
("DNF = anything ≠ `running`"), imported verbatim. This session's **primary**
variant keeps DNF drivers in each race's full order (using `finish` exactly
as every other frozen/gold table does — "DNFs are ranked here by laps
completed," already baked into `finish` upstream); the **sensitivity**
variant (§6) drops them. See §6 for why the primary/sensitivity roles are
assigned this way round relative to the source paper.

---

## 2. Model

Full-order Plackett-Luce / rank-ordered logit — the same likelihood family
`walkforward.pl_fit` already uses for the frozen model's continuous
features, generalized here to one-hot per-entity dummy features with a
**per-entity-type** (block) ridge penalty rather than `pl_fit`'s single
scalar `lam`. For driver `i`, team `j`, make `k` co-occurring in one race-row:

```
eta = alpha[i] + beta[j] + gamma[k]
```

Likelihood: standard PL sequential top-down construction (identical
suffix-sum trick to `pl_fit`'s `nll_grad` — same mathematics, re-derived, not
imported by call — see §2.1 for why).

Order convention per race: entries sorted by `finish` ascending (best
first — position 1 = winner), **not negated**. `u = X @ w` with higher `u`
= ranked earlier/better, matching vanilla PL's `P(top choice = i) ∝
exp(u_i)` with no sign inversion.

### 2.1 Why this is re-derived, not a call into `walkforward.pl_fit`

Three concrete, disclosed reasons, not a stylistic preference:

1. **Different penalty shape.** `pl_fit`'s ridge is a single scalar `lam *
   w @ w` across all features. This session needs a **block-diagonal**
   penalty (`lam_driver`, `lam_team`, `lam_make` independently) — a
   materially different call signature, not a parameter `pl_fit` exposes.
2. **Different feature type.** `pl_fit` is called on ~4 continuous
   z-scored features; this session needs ~135 one-hot dummy columns
   (101 + 31 + 3). The likelihood math is identical; the feature
   construction is not.
3. **Sign-convention hygiene.** `report/CALIBRATION_BACKTEST.md` (M3)
   documents a real, previously-caught sign bug in this exact neighborhood
   (`walkforward.run`'s `collect_preds` utility fit on `-X` with an inverted
   convention that had to be negated and re-verified). Rather than reusing
   `pl_fit`'s negate-`X`-then-interpret-`u` convention (a documented source
   of confusion elsewhere in this codebase), this session defines its own
   convention from scratch (§2, no negation, "higher `u` = better") and
   verifies it directly (§8.1's sign sanity check) instead of inheriting an
   inversion that has already bitten this project once.

This is the same **replay, not reuse** idiom F3/F4 already established for
the frozen engine (`gate_track_similarity.py`'s `replay_frozen_engine_by_driver()`
"mirrors `gate_gold.py`'s `gold_sourced_walk_forward()` line-for-line"): the
mathematical structure is verified equivalent, the code is independent.

### 2.2 Identifiability

PL log-likelihood is invariant to adding a constant to every entity within
one factor block simultaneously with an offsetting shift elsewhere (`eta`
only depends on the sum `alpha+beta+gamma`) — an unpenalized fit has two
unresolved degrees of freedom. The strictly-convex block-ridge penalty
(§4) has a **unique** minimum-norm solution among all `eta`-equivalent
parameterizations, so no manual reference-category constraint is needed —
identifiability is resolved by the same mechanism the standing requirement
already mandates for regularization, not by an additional invented
convention.

---

## 3. Standing requirement (i) — per-training-window strong-connectivity diagnostic

**"Training window" pinned as: each season (2022, 2023, 2024, 2025, 2026)
individually, plus the full pooled 2022–2026 window** the headline model
actually fits on. Per-season is the natural windowing choice for this
project (E1's own illustrating example — "the full 2002 [F1] season required
dropping four always-last drivers" — is itself a single-season window), and
avoids inventing a rolling/expanding-window scheme this Tier-A, single
pooled-estimate session has no other use for (that belongs to F11 if it is
ever triggered, §9).

**Method:** for the driver factor (the binding one — team/make are checked
too but expected trivial given only 31/3 nodes respectively, densely
inter-raced), build a directed graph per window: edge `u -> v` if driver `u`
finished ahead of driver `v` in the same race at least once inside that
window. Hunter's Assumption 1 (finite MLE for every item) requires this
graph to be **strongly connected**. Checked via
`scipy.sparse.csgraph.connected_components(directed=True,
connection='strong')` (available in this repo's conda environment; no new
dependency).

**Verified finding at spec-write time (this diagnostic was run now,
pre-data, exactly as the standing requirement demands — before any variance
component is estimated):**

| window | n drivers | components | strongly connected? |
|---|---:|---:|---|
| pooled 2022–2026 | 101 | 1 | **yes** |
| 2022 | 62 | 2 | **no** |
| 2023 | 64 | 1 | yes |
| 2024 | 62 | 2 | **no** |
| 2025 | 60 | 1 | yes |
| 2026 (partial) | 52 | 1 | yes |

Two of five season windows fail — a real, concrete confirmation of the
standing requirement's own text ("NASCAR data genuinely fails this on some
real windows"), not a hypothetical. Both failures have an identical,
Hunter-canonical signature (his own example: "always-last drivers"): a
single driver who ran **exactly one** race that season, finished **dead
last**, and DNF'd — `driver_id` 3816 (Andy Lally, 2022, finished 39/39,
`status='suspension'`) and `driver_id` 3170 (David Starr, 2024, finished
37/37, `status='steering'`) each form a singleton component: they were
beaten by the whole field but beat no one, so they are unreachable *from*
the rest of the graph even though reachable *to* it.

**This diagnostic is informational, not a blocking gate:** per Hunter/E1's
own point, the regularization scheme (§4) makes the penalized MLE finite and
unique regardless of connectivity — the two season-level failures do not
block the pooled 2022–2026 fit (itself already connected) and would only
bind if this were ever re-run as a rolling per-season walk-forward (F11's
territory, not this session's). The finding is still reported in full
(`gold.equip_share_connectivity`, §7) precisely because a silently-passing
pooled fit would otherwise hide that the underlying per-season data is
fragile — exactly the transparency the standing requirement exists to force.

---

## 4. Standing requirement (ii) — regularization scheme

**Pinned: block-diagonal L2 (ridge) penalty**, one scalar per entity type:

```
penalty(alpha, beta, gamma) = lam_driver * sum(alpha^2)
                             + lam_team   * sum(beta^2)
                             + lam_make   * sum(gamma^2)
```

**Disclosed as the "equivalent shrinkage prior" the standing requirement
names as an alternative to literal ghost-item pseudo-rankings** (its own
wording: "ghost-item pseudo-rankings **or an equivalent shrinkage prior**").
Reasoning for choosing this over literally replicating Hunter/Turner's
ghost-item mechanism:

1. **Mathematical equivalence.** A ridge penalty `lam * w^2` on a parameter
   is the negative log-density (up to a constant) of a Gaussian prior
   `w ~ N(0, 1/(2*lam))`. The penalized MLE (MAP) is the mode of that
   posterior. This is the *direct frequentist analogue* of the source
   paper's own model (their "random effects" are literally Gaussian-shrunk
   per-entity parameters, fit by MCMC to a Normal prior) — closer to the
   paper's actual generative model than ghost-item pseudo-ranking is, which
   was designed for a single-factor classic PL/BT setting.
2. **No citable multi-factor extension of ghost-item pseudo-ranking
   exists.** Hunter (2004) and Turner et al. (2020) define it for one item
   set. This session needs three simultaneous cross-classified factors
   (driver, team, make) sharing one likelihood — inventing a 3-way ghost-item
   generalization with no precedent would itself be an unregistered design
   judgment call. Block ridge generalizes to any number of factors with no
   new invention.
3. **Reuses this project's own established idiom.** `pl_fit` already
   ridge-penalizes the frozen model's PL fit (`lam=0.5`, HANDOFF's frozen
   config) — this session generalizes that scalar to a block vector rather
   than importing an unrelated algorithm, consistent with the "reuse the
   frozen engine's own machinery" convention F3/F4/F13 all follow.
4. **Same two guarantees ghost-item pseudo-ranking provides:** a strictly
   convex penalty gives a finite, unique MLE for every entity regardless of
   connectivity (resolving Hunter's Assumption-1 failure exactly as
   ghost-item pseudo-ranking does, §3's finding notwithstanding), and it
   shrinks extreme/sparse entities toward the common baseline (§5.3).

### 4.1 Selecting `lam_driver`, `lam_team`, `lam_make` (pinned procedure, pre-registered)

**Leave-one-season-out cross-validation, maximizing total held-out PL
log-likelihood**, selected by **coordinate descent** over a shared,
a-priori, log-spaced grid:

```
GRID = [0.03, 0.1, 0.3, 1, 3, 10, 30]   # same 7 values for all three factors
```

One grid shared across factors (not factor-specific ranges) — a common a
priori grid avoids any appearance of a range chosen after looking at
results; 7 points span ~3 orders of magnitude, wide enough to include both
near-unregularized and heavily-shrunk fits for any of the three factor
scales.

**Procedure:**

1. Initialize `(lam_driver, lam_team, lam_make) = (1, 1, 1)`.
2. One coordinate-descent **sweep** = three steps: hold `lam_team, lam_make`
   fixed and pick the `GRID` value for `lam_driver` that maximizes total
   held-out log-likelihood summed over the 5 leave-one-season-out folds;
   then the same for `lam_team`; then `lam_make`.
3. Repeat sweeps up to **4** total. Stop early if a full sweep changes none
   of the three values (converged).
4. **Tie-break** (exact ties in mean held-out log-likelihood, to the
   precision computed): prefer the **larger** grid value — the more
   regularized, more conservative fit. This is a Tier-A descriptive session;
   when the data cannot distinguish two penalty strengths, preferring more
   shrinkage over less is the more conservative default.
5. **Folds:** leave-one-season-out, 5 folds = {2022, 2023, 2024, 2025,
   2026}. For each fold: fit on the other 4 seasons' races with the
   candidate `(lam_driver, lam_team, lam_make)`; evaluate the **unpenalized**
   PL log-likelihood of the held-out season's actual race orders using the
   fitted `w`. An entity present only in the held-out season contributes a
   zero column to every training race, so its fitted weight is exactly `0`
   at the penalized optimum (no data gradient, pure penalty term) — this
   *is* the "no information → baseline worth" prediction for a driver/team/
   make unseen in training, and requires no special-cased fallback code; it
   falls directly out of the convex optimization.
6. The **final** model (used for §7's output) refits on **all 164 races**
   at the selected `(lam_driver*, lam_team*, lam_make*)` — the CV folds are
   used only to select the penalty strength, never as the reported fit.

**This does not contradict the imported "descriptive, not forecasting"
warning (§6).** Using held-out log-likelihood to choose a regularization
strength is a standard statistic technique for hyperparameter selection
(exactly analogous to choosing ridge-regression λ by cross-validated
prediction error) — it says nothing about whether the *fitted model's
output* should be used to forecast future races operationally, which the
warning is about and which this session does not do.

---

## 5. Headline metric — variance shares

For each entity type `X` in {driver, team, make}:

```
SD_X            = sqrt(1 / (2 * lam_X*))                      # prior-implied SD (headline)
SD_X_empirical  = population_stddev(fitted worths for X)       # secondary cross-check
var_share_X     = SD_X^2 / (SD_driver^2 + SD_team^2 + SD_make^2)
```

`SD_X` (the Gaussian-prior SD implied by the CV-selected penalty) is the
**headline** number, directly analogous to the source paper's own reported
posterior SDs (1.63/0.73/0.54/0.35) and to their variance-share framing
(constructor ≈ 88%). `SD_X_empirical` (population SD of the **fitted, ridge-
shrunk** point estimates themselves) is reported alongside as a disclosed,
known-**downward-biased** cross-check — shrinkage systematically compresses
fitted point estimates toward zero, so the raw empirical spread of
`alpha_hat`/`beta_hat`/`gamma_hat` understates the true between-entity
variance; `SD_X` corrects for this by estimating the prior's spread directly
rather than the shrunk posterior points' spread (standard mixed-model
practice — REML/ML variance-component estimation, not raw BLUP variance, for
exactly this reason).

### 5.1 F11 trigger decision rule (pre-registered, before any number exists)

**Primary criterion, on the primary (DNF-included) variant only:**

> `var_share_team >= 0.25` → F11 trigger **ARMED** (evidence *for* eventually
> spec'ing the banked hierarchical-Bayesian-PL lane).
> `var_share_team < 0.25` → F11 trigger **NOT ARMED** (stays banked/dormant).

**Reasoning for the 0.25 bar (disclosed, fixed before computing anything):**
25% represents a materially non-trivial share of total structural
variance — enough that a model explicitly encoding team/equipment could
plausibly move a walk-forward accuracy needle — while remaining far below
F1's own cross-method range (64–88%). Re-using F1's own bar here would be
circular: Next Gen's parity rules exist specifically to *defeat* the kind of
constructor dominance F1 shows, so expecting anywhere near that share would
contradict the very premise this session tests. 25% is calibrated instead to
"clearly more than noise, on the same order of magnitude as a meaningful
chunk of total variance" — consistent with this project's house style of
pre-registering one concrete practical-significance number with a stated
rationale (the DNF/pooling specs' `+0.005` mean-delta-rho floor is the same
pattern) rather than leaving the bar vague or picking it after seeing
results.

Driver share, make share, and the DNF-excluded sensitivity variant's shares
(§6) are reported in full for transparency but do **not** independently
move the decision — one pre-registered number, checked once, avoids
post-hoc multiplicity.

### 5.2 Empirical sanity checks (report, not gated beyond §8.1's assertion)

Named spot-checks in `report/EQUIPMENT_SHARE.md`: the team with the single
highest fitted `beta` should have a better (numerically lower) mean actual
`finish` in the raw scope data than the team with the lowest fitted `beta`
(same for driver/`alpha` and make/`gamma`) — a directional check computed
from the data itself, not a hardcoded organization name (team/driver
identities are allowed to be whatever the fit finds, only the *direction* is
asserted). `gate_equip_share.py` §8.1 makes this an actual assertion, not
just a report note.

### 5.3 Part-timer shrinkage (stated up front, per the standing requirement)

Entities with fewer races contribute less log-likelihood pull against the
fixed quadratic penalty term, so they are shrunk toward `0` (the common
baseline worth) **more aggressively in relative terms** than full-time
entities — standard ridge/partial-pooling behavior, the same mechanism
Hunter's ghost-item pseudo-ranking produces by a different route. Verified
directly in the report: a driver with 1–2 races in scope should show a
fitted `alpha` close to `0` regardless of that driver's raw (unregularized)
finishing average, while a 164-race full-time driver's fitted `alpha` is
allowed to move further from `0`. This is the resolved, disclosed answer to
"part-timer shrinkage behavior stated" — no separate minimum-sample floor is
applied on top of it (unlike F3's discrete `below_floor` convention): the
regularization *is* the floor, continuously, by construction, which is the
point of choosing it over a hard-coded sample-size cutoff.

---

## 6. Sensitivity variant — DNF exclusion (E5/E6, imported verbatim)

Van Kesteren & Bergkamp's own sensitivity analysis (scan §3.7, E6) found DNF
handling "materially reorders skill estimates." Their **main** decomposition
excludes DNFs entirely; this session's **primary** variant does not (§1.4) —
a deliberate, disclosed **reversal of primary/sensitivity roles** relative
to the paper:

**Why:** this project has one established, disclosed convention for race
outcomes — `finish`, with DNFs ranked by laps completed, used identically by
the frozen production model, `silver.driver_race`, and `gold.wf_features`.
F3/F4/F13 all reuse this project's existing conventions rather than
reinventing per-session; F14 does the same. The paper's own DNF-exclusion
choice is imported as the **sensitivity check** instead — exactly the role
it plays in their own paper, just with which variant is "primary" swapped to
match this project's house convention rather than theirs.

**Mechanics:** re-run the identical model (§2), identical CV+coordinate-descent
λ-selection procedure (§4.1), on the same 164 races with DNF rows
(`status != 'running'`) dropped from each race's order before fitting (their
convention exactly) — shorter partial orders per race, same likelihood
construction otherwise. Report its own `var_share_driver/team/make` trio
(`gold.equip_share_summary`, `variant='dnf_excluded'`) alongside the primary
variant. Does not change §5.1's decision (which keys off the primary variant
only) — reported for transparency and to satisfy the imported sensitivity
check, not as a second vote.

---

## 7. Imported warning (verbatim)

> "\[The\] architecture is probably not suitable for prediction" — season
> effects are unestimable pre-season, and the model is descriptive of
> already-observed outcomes, not a forecasting tool. (van Kesteren &
> Bergkamp, 2023, as characterized in `external_knowledge_scan.md` §3.6.)

This session's output is **never** used to forecast, never joined into any
feature bank, and never changes the frozen model — Tier A throughout,
exactly like F3/F4/F13/F19.

**Explicit non-goal:** driver-season and constructor-season interaction
terms (the paper's other two random effects) are not attempted here. With
~33 races/season, a driver-season factor could reach up to 101×5 = 505
cells (most backed by a single season's ~1–30 races), and a team-season
factor similarly — compounding the connectivity/estimability difficulty
exactly where §3 shows NASCAR already struggles at the single-factor level,
for a Tier-A session whose deliverable is explicitly framed (kickoff,
`plan/schedule.yml`) as a 3-way driver/team/make split. Season-varying
structure is reserved for F11's fuller treatment if that session is ever
triggered (§5.1).

---

## 8. Output schema

### 8.1 `gold.equip_share_worths`

One row per `(variant, entity_type, entity_key)`. `variant` in
`{'primary', 'dnf_excluded'}`; `entity_type` in `{'driver', 'team', 'make'}`;
`entity_key` (driver_id as string / canonical `team_key` / make name);
`display_name` (driver's most-common raw name / most-common raw `team_name`
for that key / make name); `n_races` (count of that variant's scope races
the entity appears in); `worth` (fitted `alpha`/`beta`/`gamma`).

### 8.2 `gold.equip_share_summary`

One row per `variant`: `variant, n_races, n_drivers, n_teams, n_makes,
lam_driver, lam_team, lam_make, sd_driver, sd_team, sd_make,
sd_driver_empirical, sd_team_empirical, sd_make_empirical, var_share_driver,
var_share_team, var_share_make, trigger_armed` (bool, `primary` row only —
`NULL` on the `dnf_excluded` row, since §5.1's decision keys off `primary`
alone). Provenance: `built_at`.

### 8.3 `gold.equip_share_connectivity`

One row per `(variant, window, factor)`: `variant` (currently `'primary'`
only — the sensitivity variant's connectivity is a §4.1 re-run detail, not a
separately reported headline diagnostic), `window` (season year or
`'pooled'`), `factor` (`'driver'`/`'team'`/`'make'`), `n_entities`,
`n_components`, `strongly_connected` (bool), `offending_entities` (comma-
joined entity keys in every non-giant component, `NULL` if connected).

---

## 9. Build-graph isolation gate (frozen; mirrors F3 §5 / F4 §6 / F13 §5)

`gate_equip_share.py` asserts, on every run:

1. **Existence + internal consistency**: all three tables exist; no
   duplicate `(variant, entity_type, entity_key)` rows in
   `gold.equip_share_worths`; no duplicate `variant` rows in
   `gold.equip_share_summary`; no duplicate `(variant, window, factor)` rows
   in `gold.equip_share_connectivity`.
2. **Isolation**: none of `equip_share_worths`, `equip_share_summary`,
   `equip_share_connectivity` appears anywhere in `src/gold_build.py`,
   `src/walkforward.py`, or `src/predict_next.py` (source-text scan,
   identical idiom to F3/F4/F13).
3. **Full re-derivation**: re-running the entire pipeline (both variants'
   CV+coordinate-descent λ-selection and final refit) from
   `silver.driver_race`/`silver.results` reproduces every stored `lam_*`,
   `worth`, and summary/variance-share number within
   `math.isclose(rel_tol=1e-6)` — a documented numerical tolerance for an
   iteratively-optimized (L-BFGS-B) quantity, the same category of allowance
   C1's `fepace` amendment already established for this codebase (not
   bit-exact-by-fiat where an iterative solver is involved).
4. **Connectivity re-derivation**: recomputing `gold.equip_share_connectivity`
   from scratch reproduces every stored `n_components`/`strongly_connected`/
   `offending_entities` value exactly (no floating point involved here —
   exact equality, not tolerance-based).
5. **Team-key canonicalization proof** (named, not just a count): asserts
   `'trackhouse racing'` appears exactly once in `gold.equip_share_worths`
   (the known case-variant pair correctly merged) **and** that the
   Stewart-Haas/Haas-Factory-Team pair remains **two** distinct
   `entity_key` rows (proving the canonicalization is exactly as narrow as
   §1.2 claims — no over-merging of genuine renames).
6. **Sign sanity check**: for each of driver/team/make, the entity with the
   single highest fitted `worth` (primary variant) has a better (lower)
   mean actual `finish` over its own scope races than the entity with the
   single lowest fitted `worth` — computed from the data itself (no
   hardcoded name), guarding against the exact class of sign-convention
   inversion `report/CALIBRATION_BACKTEST.md` (M3) already found once in
   this codebase's neighborhood (§2.1).

---

## 10. Implementation checklist

1. `src/equip_share_build.py` (new module) — imports `warehouse` for the DB
   connection (same style as every other gold build module); builds the
   scope query (§0), the entity vocabularies (§1), the re-derived PL
   likelihood + block-ridge fit (§2, §2.1), the CV+coordinate-descent
   λ-selection (§4.1), the connectivity diagnostic (§3), both variants
   (§6), and writes all three output tables to
   `data/gold/equip_share_worths.parquet` /
   `equip_share_summary.parquet` / `equip_share_connectivity.parquet`.
2. Register all three as `gold.*` DuckDB views in `warehouse.py`'s gold
   view loop (same rebuildable-from-disk pattern as every other gold
   table).
3. `src/gate_equip_share.py` — §9's six checks.
4. `report/EQUIPMENT_SHARE.md` — headline variance-share numbers (both
   variants), the connectivity finding (§3's table, named offending
   drivers), the part-timer/full-timer shrinkage spot-check (§5.3), the
   sign-direction spot-checks (§5.2), and the explicit §5.1 trigger verdict
   for F11.
5. Extend `DATA_DICTIONARY.md` (new §10h) and `GATES.md` (new gate,
   inserted immediately after `gate_loop_metrics.py`/F13 in the gate order,
   pushing the existing 10–17 down to 11–18); add `gate_equip_share.py` to
   `src/run_gates.sh`'s registry in the same position.
6. Update `plan/schedule.yml` (F14 → done; promote the next unblocked
   session per phase F's own enumerated order — see HANDOFF for which one)
   and re-render via `python src/report_plan.py`.
7. Run the full gate surface (`src/run_gates.sh`) — must reach 18/18 green
   (17 existing + this session's new `gate_equip_share.py`).

---

## RESULT — F14

*(filled in after the build; only permitted edit to this file besides a
dated `## AMENDMENT` per `specs/README.md`'s pre-registration discipline)*
