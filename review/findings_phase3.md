Warm-start independence confirmed (~1e-6), so the decision is deterministic. I have everything. Writing the report.

# Adversarial Pre-Registration Review — Phase 3

**Scope:** BOTH roadmap-#4 feature specs — `specs/dnf_status_feature.md` (4a) and `specs/team_mfr_pooling.md` (4b). **Date:** 2026-07-19. **Verdict counts:** 0 CRITICAL, 3 MAJOR, 2 MINOR, 2 NIT. No URGENT items (both A/Bs are gated on `scores_log ≥ 8` scored forward races, which do not yet exist). All amendments below are permitted *now* because the data the rules adjudicate does not yet exist (`specs/README.md` discipline).

---

## [SEVERITY: MAJOR] The "+0.005 costs no power" justification is empirically false, and the margin most-binds the very variant the spec prefers
**Spec + section:** DNF `§4` ("Why +0.005" paragraph); Pooling `§5` (adopts the identical rule + justification by reference). **Attribution: both.**

**The claim.** DNF §4 records, to "stop anybody tuning it later," that paired `SE ≈ 0.007`, so "significance effectively requires `mean(d) ≈ 0.015`," hence the `+0.005` floor "only blocks a freak tiny-but-significant result and costs no real power."

**Why it's wrong.** The paired SE is *not* a single ~0.007 constant — it is variant-specific and collapses for low-variance variants (those that re-read existing features rather than add noisy new ones). Measured on the frozen config (MY_TYPE + shrinkage, all years, n=128 scored):

| proxy variant | mean(d) | sd(d) | **paired SE** | one-sided sig. needs mean(d) ≳ |
|---|---|---|---|---|
| base + `fepace` (near-redundant) | +0.0003 | 0.0096 | **0.0008** | ~0.0017 |
| base + `practice` | +0.0012 | 0.0258 | **0.0023** | ~0.0049 |

**DNF V2 (censored histories) is exactly the low-variance case** — it only re-reads `fin`/`typed` from running-only histories, a tiny perturbation highly correlated with base, so its SE will sit near the `fepace` end (~0.001), not 0.007. For such a variant, statistical significance is reached at `mean(d) ≈ 0.002–0.003`, **well below the +0.005 floor**. The margin therefore *can* veto a genuinely significant, real improvement — a false negative the spec explicitly claims is impossible. Worse, it does so asymmetrically: V2 (0 added features) is the variant the §4 tie-break *most prefers*, yet it is the one the margin most likely blocks; V1/V3 (add features → higher variance) are less affected. The pooling exclude-self features are moderate-variance and less exposed, but inherit the same false justification.

**Failure scenario:** V2 yields `mean(d) = +0.0035`, Wilcoxon `p = 0.004` (significant, SE≈0.0012). Rule rejects it because `+0.0035 < +0.005`. Roadmap #4a is recorded "negative" and V2 may never be retried (spec bars tweaked retries), even though the data showed a robust improvement — solely because a mis-stated SE heuristic was frozen as if it "costs no power."

**Proposed amendment (append to DNF §4; mirror into Pooling §5):**
```
## AMENDMENT (2026-07-19) — margin justification corrected
The frozen "paired SE ≈ 0.007 → significance needs mean(d) ≈ 0.015" reasoning
is variant-specific and does NOT hold for low-variance variants. Measured on
the frozen config (n=128 scored): a near-redundant added feature has paired
SE ≈ 0.0008 and a moderate one ≈ 0.0023 — 3–9x below 0.007. A variant that
merely re-reads existing histories (notably DNF-V2 / any censored-history or
exclude-self re-encoding) can reach p ≤ 0.0167 at mean(d) ≈ 0.002–0.004, i.e.
BELOW the +0.005 floor. Therefore +0.005 is NOT free: it is a deliberate
PRACTICAL-significance floor that can, by design, reject a statistically
significant but small improvement, and it binds hardest on the 0-feature
variant the tie-break otherwise prefers. This is pre-registered as an
intentional trade-off (do not adopt <+0.005 gains even if significant), NOT
as a costless guard. The threshold value (+0.005) is unchanged; only the
recorded rationale is corrected. No result exists yet, so this is in-window.
```

---

## [SEVERITY: MAJOR] Baseline-replication gate (±0.003) is too loose to catch a typology / typed-mode misconfiguration — and the spec warns about only ONE of the three defaulted `run()` args
**Spec + section:** DNF `§3` step 4 (baseline gate) and `§3.1` (years warning); Pooling `§4` (same gate). **Attribution: both.**

`walkforward.run()` defaults **three** args to their audit-*replication* values: `years=(2022..2025)`, `typology=THEIR_TYPE`, `typed_mode='their_fallback'`. The frozen production config needs `MY_TYPE` + `'shrinkage'`. The spec loudly warns about `years=` ("silently drops 2026+") but is **silent** that `typology` and `typed_mode` are equally-wrong defaults in the same signature — creating a false impression that `years` is the only default trap. The baseline gate is the intended safety net, but it cannot catch the other two:

| config (2022–2025, year≤2025 subset) | mean ρ | inside 0.413 ± 0.003 = [0.410, 0.416]? |
|---|---|---|
| **MY_TYPE + shrinkage (correct/frozen)** | **0.4130** | yes |
| THEIR_TYPE + their_fallback (both `run()` defaults) | 0.4118 | **yes — also passes** |

**Failure scenario:** the `step7`/`step8` "own copy of `run()`" is written leaving `typology`/`typed_mode` at their `run()` defaults (the same copy-paste that would leave `years` wrong). Baseline gate reads 0.4118, PASSES (0.0012 < 0.003), and every `d_i` is then computed against the *wrong* baseline. The winning feature is validated against THEIR_TYPE but adopted into the MY_TYPE production config — the validation doesn't correspond to what ships. The gate advertised in §3.4 ("If it fails: STOP") gives false assurance.

**Proposed amendment (append to DNF §3; mirror into Pooling §4):**
```
## AMENDMENT (2026-07-19) — baseline gate hardened
(a) The years= warning is NOT the only default trap: run()'s typology= and
    typed_mode= ALSO default to audit-replication values (THEIR_TYPE,
    'their_fallback'). The A/B baseline MUST be MY_TYPE + typed_mode
    'shrinkage' (pseudo-count 3) per §2. The step7/step8 copy of the loop
    must set all three explicitly; assert them in code.
(b) The ±0.003 gate cannot distinguish the correct config (0.4130) from the
    both-defaults-wrong config (0.4118) — both fall in [0.410,0.416].
    Strengthen the gate: base's year<=2025 scored mean rho must equal
    0.4130 within ±0.0015 AND the year<=2025 scored-race count must equal
    108 (both measured 2026-07-19 on the 163-race pickle; count is causal-
    stable as new 2026 races are appended). A mismatch in either => STOP.
```
*(Evidence: measured this session. The ±0.0015/0.4130/108 values distinguish the two configs; the owner may pick a different tolerance, but it must be < the 0.0012 THEIR-vs-MY gap.)*

---

## [SEVERITY: MAJOR] Bonferroni /3 under-corrects the roadmap-#4 program: six variants, one baseline, one dataset ⇒ FWER ≈ 0.10, not 0.05
**Spec + section:** DNF `§4`; Pooling `§5`. **Attribution: both (bites at the pooling spec).**

Each spec spends the full α = 0.05 on its own three variants (0.05/3 = 0.0167). But the two specs test against the **same frozen baseline on the same historical backtest** whenever the DNF A/B adopts nothing (the null-world outcome, and the most likely one under the project's own "expect negatives" doctrine). In that case roadmap #4 is six one-sided tests at 0.0167 against one baseline: family-wise false-adoption rate ≈ 1−(1−0.0167)^6 ≈ **0.096** — nearly double the 0.05 each spec claims to hold. This is *not* true hierarchical gatekeeping (pooling runs regardless of the DNF outcome, so the second family isn't "protected" by the first rejecting). The correction is only self-consistent in the branch where DNF *adopts* a variant (then pooling's baseline genuinely changes).

**Failure scenario:** DNF returns three nulls (nothing adopted). Pooling's W-variants are then tests 4–6 against the identical 0.413 baseline on identical data; one clears 0.0167 by chance. It is adopted at a nominal 5% FWER that is really ~10%.

**Proposed amendment (append to Pooling §5):**
```
## AMENDMENT (2026-07-19) — program-wide multiplicity
Roadmap #4 is one 6-variant program against one baseline. Resolve the
multiplicity explicitly:
- If the DNF A/B ADOPTED a variant: pooling's baseline is the new frozen
  config (different comparison) -> pooling keeps 0.05/3 = 0.0167.
- If the DNF A/B adopted NOTHING: pooling reuses the identical baseline and
  data as three already-spent tests, so pooling's three variants are tests
  4-6 of a six-test family -> use 0.05/6 = 0.00833 per variant. The
  mean(d) >= +0.005 AND-gate is unchanged.
This is pre-registered before any pooling variant is run.
```

---

## [SEVERITY: MINOR] Pooling baseline gate references a number the DNF RESULT block is not required to record
**Spec + section:** Pooling `§4` (× DNF `§6`). **Attribution: both.**

Pooling §4: if DNF adopted a variant, the baseline reference is "the one recorded in [DNF's] RESULT block." But DNF §6 records only *`baseline-gate value`* (= the pre-adoption base ρ, ~0.413) and a *per-variant table of `mean(d)`* (§5 prints `mean(d)`, Wilcoxon p, CI — all **relative** to base, and over **all** scored races incl. 2026). The number pooling actually needs — the *adopted* config's **absolute** mean ρ on the **year ≤ 2025** scored subset — is not among the required fields. Pooling would either compare its recomputed base+variant to 0.413 (the *wrong*, lower reference → spurious FAIL) or re-derive the number itself (undefined by the gate).

**Failure scenario:** DNF adopts V1 (say base+V1 year≤2025 ρ = 0.419). Pooling's base = base+V1 reproduces 0.419, but the only recorded reference is 0.413 → |0.419−0.413| = 0.006 > 0.003 → baseline gate FAILS spuriously, halting roadmap #4b.

**Proposed amendment (append to DNF §6):**
```
## AMENDMENT (2026-07-19) — RESULT must record absolute anchors
The RESULT block additionally records, for base AND for every variant: mean
rho over ALL scored races and over the year<=2025 scored subset (with that
subset's race count). If a variant is adopted, its year<=2025 subset mean rho
is the explicit reference number the pooling spec's §4 baseline gate compares
against (±0.003).
```

---

## [SEVERITY: MINOR] V2 and base share an identical `FEATS` list — a single shared feature bank silently nulls V2 (or corrupts base)
**Spec + section:** DNF `§2` (V2) and `§3` step 2. **Attribution: DNF.**

Base and V2 both declare PL features `['fin','pace','typed','start']` — *identical keys*. The engine's `pl_specs` mechanism builds ONE `feat_bank` keyed by feature name (`walkforward.py` L142–146) and both specs index `'fin'`/`'typed'`. If the `step7` copy reuses that keying, base and V2 read the *same* `fin`/`typed` column: either V2 gets the uncensored values (V2 ≡ base, `mean(d)=0`, false rejection) or the censored values overwrite the shared column and *base* is corrupted. The spec says step7 "carries its own copy … extended with the variant feature banks" but never states base and V2 must use **distinctly-named** columns (e.g. `fin_all` vs `fin_run`).

**Failure scenario:** implementer builds `feat_bank['fin']=znan(fin_h)` once; V2's spec list `['fin','pace','typed','start']` pulls the uncensored column → V2 is measured identical to base → recorded negative that never tested the hypothesis.

**Proposed amendment (append to DNF §2):**
```
## AMENDMENT (2026-07-19) — V2 column namespacing
Because base and V2 share the FEATS list ['fin','pace','typed','start'], the
step7 feature bank MUST hold SEPARATE columns for base (uncensored hf/ht) and
V2 (censored hf_run/ht_run); V2's 'fin'/'typed' are the censored columns, base's
are the uncensored columns, built in the same replay. Verify V2 != base by
construction: at least one scored race must show fin_run != fin for some driver
with a non-running finish.
```

---

## [SEVERITY: NIT] "~150 scored races" overstates the current sample
**Spec + section:** DNF `§4`. **Attribution: DNF.** The full-pass scored count today is **128** (108 year≤2025 + 20 2026 — measured), not ~150; even after the ≥8 gating forward races it is ~135, reaching ~140s only by 2026 season end. Non-load-bearing (feeds only the corrected-in-finding-1 SE heuristic), but the figure should read "≈130 scored races (128 as of 2026-07-18)."

## [SEVERITY: NIT] `fatigue` (2 rows) and `fire` (4 rows) are binned "mechanical-cause"
**Spec + section:** DNF `§1`/`§3` (V3 mech rate). **Attribution: DNF.** Driver `fatigue` is physiological and `fire` is often crash-adjacent, yet both land in mech-class. Immaterial (6/6083 rows, 0.1%) and the binary taxonomy is deliberately pre-registered as total, so this is disclosure-only — but worth a one-line acknowledgment in the resolved-ambiguity register that mech-class is "non-crash DNF," not strictly "mechanical failure."

---

## Verified clean (checked and held up)

**Data-definition claims (all exact against `src/races_parsed.pkl`, 163 races / 6,083 driver-rows):**
- Status inventory reproduced **exactly**: `running` 5,236 (86.1%), `accident` 630, `dvp` 43, and **174** non-running-non-crash rows over **28** distinct strings (`engine` 50, `suspension` 24, `steering` 17, `brakes` 13, `electrical` 12, …). 31 distinct statuses total; **empty-string count = 0** (spec's "never occurs" holds). Crash-class `{accident, dvp}` is total and unambiguous for the current data (no `crash`/`wreck`/`dvp-…` variants; only the two NITed edge strings).
- `make` complete **6,083/6,083**, values exactly `{Chevrolet 2609, Ford 2226, Toyota 1248}` — pooling §1 W2 "no prerequisite" claim holds.
- `team` is per-car `team_id`: **47 distinct** in the last 30 races (matches spec's "47"); no `org`/`team_name` key exists in the parsed dicts today, confirming pooling §1's rebuild prerequisite is real and necessary.

**Engine behavior (runs on `.venv`, MY_TYPE + shrinkage frozen config):**
- **0.413 baseline reproduced:** base `[fin,pace,typed,start]`, year≤2025 = **0.4130** (108 scored races) — inside ±0.003. 2026-only subset = **0.4473** (≈ audit's 0.449). Full pass = 0.4183 (128 scored).
- **Causal-stability claim TRUE (the trap §2 exists to kill):** the year≤2025 scored rows are **byte-identical** with vs. without 2026 in the sample — same 108 (date,track) keys, **0 rows with any ρ difference**. Appending 2026+ genuinely cannot change earlier scored races, so the baseline-gate subsample is well-defined and stable.
- **`years=` trap real and correctly warned:** default `(2022..2025)` drops all 20 2026 races.
- **Identical scored set across variants** is guaranteed by construction: `elig` is computed once per race from uncensored `hf` + pace-present (`walkforward.py` L100–102), independent of `pl_specs`; variants change feature values/utility only, never the driver set. V2's "eligibility uses `hf_all`, not censored" is the right and necessary design; `znan` runs *after* `elig` and cannot shift it.
- **No walk-forward leakage:** all histories (`hf`, `hd`, `ho[org]`, `hmt`) are appended *after* a race is scored; pooling's exclude-self, once-per-race, oldest→newest `pool_feature` reads only prior races and omits the driver's own finishes — no current-race information enters any feature.
- **Wilcoxon independence assumption holds empirically:** lag-1 autocorrelation of per-race paired differences = −0.17 (fepace proxy) / +0.02 (practice proxy); base-ρ series autocorr = −0.004. No positive serial dependence that would make the pre-registered Wilcoxon anti-conservative.
- **Decision determinism confirmed:** the PL objective (`pl_fit`) is convex (PL NLL + λ‖w‖² ridge) → unique minimum; three very different warm starts converge to within ~1e-6, so refit-every-race warm-starting is path-independent and reimplementation-robust. The bootstrap (np seed 7) feeds only diagnostics, never the gate — the adopt/reject decision is fully deterministic and seed-independent as claimed.
- **One-sided `alternative='greater'` is the correct direction** for a directional adoption claim; the "at most one adopted / highest mean(d) among passers" rule is statistically coherent (Bonferroni over the three controls any-false-pass; selecting the max among genuine passers adds no inflation).
- **No date-tie non-determinism:** all 163 `date` strings are unique to the second (`YYYY-MM-DDThh:mm:ss`), so the date-sorted walk-forward order is deterministic and stable across a pooling-§1 rebuild.

Throwaway scripts under the session scratchpad only; nothing tracked was modified.

---

# Adjudication (orchestrating session, Opus 4.8, 2026-07-19 — per review/STATE.md protocol)

Both specs are gated on ≥8 scored forward races (none exist yet), so every amendment is comfortably in-window. No OWNER escalation required; one finding's proposed fix was corrected by the adjudicator after empirical verification.

| # | Severity | Verdict | Reason |
|---|---|---|---|
| 1 | MAJOR | **ACCEPT** — applied verbatim to DNF §4 + mirrored to Pooling §5 | Reviewer measured that paired SE is variant-specific (~0.0008 for a near-redundant feature, not the frozen 0.007), so +0.005 is a real practical-significance floor that can veto a significant small gain — hardest on V2, the tie-break's preferred variant. The amendment corrects only the frozen *rationale*; the +0.005 threshold is unchanged, so no pre-registered decision boundary moves. Sound. |
| 2 | MAJOR | **ACCEPT diagnosis; FIX CORRECTED by adjudicator** | Diagnosis verified: `run()` silently defaults `typology` and `typed_mode` to audit-replication values, not just `years`, and the ±0.003 gate can't catch it. **But the reviewer's proposed gate is itself broken** — I ran both configs (year≤2025): frozen=0.4130/n=108, both-defaults-wrong=0.4118/n=108. The scored count is IDENTICAL (typology never affects eligibility) and the gap is 0.0011, so neither the proposed ±0.0015 rho tolerance nor a count check separates them. A numeric gate *provably cannot* catch this error. Applied amendment instead makes an explicit **code assertion of all three `run()` args** the primary defense and honestly reframes the rho/count gate as coarse-only (catches gross misconfig, not the typology/typed_mode swap). |
| 3 | MAJOR | **ACCEPT** — applied verbatim to Pooling §5 | Program-wide multiplicity is real: in the likely "DNF adopts nothing" branch, all six variants test the same baseline on the same data at 0.0167 → FWER ≈ 0.096. The conditional fix (pooling → 0.05/6 = 0.00833 when the baseline is unchanged; 0.0167 when DNF adopted and the baseline genuinely differs) is principled and conservative. Residual noted: it lowers program FWER to ≈0.073, not exactly 0.05, because DNF's three tests are frozen at 0.0167; restoring exactly 0.05 would require symmetrically tightening DNF too. Left asymmetric per the reviewer because the different-baseline branch is a genuinely separate family — flagged to owner as the one place a stricter uniform 0.05/6 is a defensible alternative. |
| 4 | MINOR | **ACCEPT** — applied verbatim to DNF §6 | The pooling baseline gate needs the adopted config's absolute year≤2025 mean ρ, which DNF §6's RESULT block wasn't required to record — a spurious-FAIL trap. Recording absolute anchors closes it. |
| 5 | MINOR | **ACCEPT** — applied verbatim to DNF §2 | Base and V2 share the `['fin','pace','typed','start']` key list; a single shared `feat_bank` column would silently make V2≡base (untested hypothesis, false negative) or corrupt base. Namespacing (censored vs uncensored columns) + a construction-time V2≠base check is the right guard. |
| 6 | NIT | **ACCEPT** — applied as clarification to DNF §5 | "~150 scored races" → "≈130 (128 as of 2026-07-18)". Non-load-bearing. |
| 7 | NIT | **ACCEPT** — applied as clarification to DNF §1 | `mech-class` is "non-crash DNF," not strictly mechanical failure (`fatigue`, `fire` land there); binary taxonomy stays total as pre-registered, disclosure only. |

**Verified-clean items I spot-checked and concur with:** 0.413 reproduced (0.4130, n=108, year≤2025); the causal-stability claim (appending 2026 leaves year≤2025 scored rows byte-identical) — this is the property the whole baseline-gate subsample relies on, and it holds; identical scored set across variants by construction (eligibility from uncensored `hf`, independent of `pl_specs`); no walk-forward leakage; PL objective convex → warm-start path-independent → decision deterministic. These underpin the specs' validity and survived an adversarial pass.
