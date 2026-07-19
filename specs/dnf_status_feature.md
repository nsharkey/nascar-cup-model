# SPEC: DNF/status-aware history feature — pre-registered A/B (roadmap #4a)

**Status:** pre-registered 2026-07-18, before any variant has been run.
**Sequencing gate (project discipline, not statistics):** execute only when
`predictions/scores_log.csv` has ≥ 8 scored races (per roadmap). The A/B
itself runs on the full historical backtest sample, NOT on the forward-test
races — 8–10 forward races could never power a feature decision.
**Motivation (audit §8):** "finish histories that treat a crash DNF as
information equal to a clean finish — a status-aware history is the most
obvious untested improvement." The `status` field is already parsed.

**Frozen model files are not modified.** The A/B lives in a new script,
`src/step7_dnf_ab.py`. `src/walkforward.py` and `src/predict_next.py` are
touched only if a variant WINS, per §7's adoption procedure, in its own
commit, after the decision is recorded.

---

## 1. Data definitions (frozen)

From `races_parsed.pkl`, each driver-race has
`status = (finishing_status or '').strip().lower()` (set by `parse_lib.py`).
Verified inventory, 163 races / 6,083 driver-rows (2026-07-18): `running`
5,236 (86.1%); `accident` 630; `dvp` 43; remaining 174 rows spread over 28
mechanical-cause strings (`engine` 50, `suspension` 24, `steering` 17,
`brakes` 13, `electrical` 12, …).

- **DNF** := `status != 'running'`. (Empty string → DNF; never occurs in
  the current data but the rule must be total.)
- **Crash-class** := `status ∈ {'accident', 'dvp'}` — dvp (Damaged Vehicle
  Policy) is retirement due to crash damage, hence crash.
- **Mech-class** := DNF and not crash-class. Any status string never seen
  before automatically lands here. No other taxonomy may be introduced.

## 2. Variants (exactly three; no others may be tested under this spec)

All variants keep the frozen config's machinery untouched: pace `pace_med85`,
half-life 8 everywhere, burn 15, min_hist 5, min_drv 20, typology `MY_TYPE`,
typed shrinkage pseudo-count 3, PL λ = 0.5, refit every race, znan feature
standardization (missing → 0). Feature-column sign handling is automatic
(the engine fits on `-X`; PL learns each weight's sign), so no variant needs
manual sign flips.

### V1 — `dnf` rate feature (adds 1 feature)

Maintain `hd[d]`: after every race, append `1.0` if that driver's race was
a DNF else `0.0` (appended for **all** races, same cadence as `hf`).
Feature value = `wmean(hd[d], hl=8)`; no history → NaN → 0 via znan.
PL features: `[fin, pace, typed, start, dnf]`.

### V2 — censored finish histories (adds 0 features)

Running-only histories: `hf_run[d]` and `ht_run[(d, tt)]` append `finish`
**only when `status == 'running'`**. In the feature step, `fin` and `typed`
(including the shrinkage base `wmean(hf_run[d], hl)`) read the censored
histories; everything else unchanged. PL features stay `[fin, pace, typed,
start]`.

**Eligibility is NOT censored** — it stays `len(hf_all[d]) >= min_hist`
(the uncensored count) plus pace-present, exactly as baseline, so all
variants score the **identical race set and driver sets**. A driver with
zero running finishes gets `fin = typed = NaN → 0`. (If eligibility were
censored, the scored set would shift and the paired test would be broken by
construction — this is the trap this paragraph exists to kill.)

### V3 — cause-split rates (adds 2 features)

`hcr[d]` appends `1.0` iff crash-class else `0.0`; `hmr[d]` appends `1.0`
iff mech-class else `0.0` (both every race). Features `crash = wmean(hcr[d],
8)`, `mech = wmean(hmr[d], 8)`. PL features: `[fin, pace, typed, start,
crash, mech]`.

## 3. Evaluation protocol (frozen)

1. Run `update_data.py` first; the sample = **every** race in
   `races_parsed.pkl` at execution time, in date order. Record the count.
   ⚠ `walkforward.run()`'s default `years=(2022..2025)` silently drops
   2026+ — the A/B script must pass all years present explicitly.
2. One walk-forward pass evaluates four PL specs simultaneously on
   identical scored races (the engine's `pl_specs` mechanism):
   `base = [fin, pace, typed, start]`, plus V1, V2, V3. V2 needs the
   censored-history plumbing, so `step7_dnf_ab.py` carries its own copy of
   the `run()` loop (clearly marked as derived from `walkforward.run`),
   extended with `hd/hcr/hmr/hf_run/ht_run` accumulation and the three
   variant feature banks. `walkforward.py` itself is not edited.
3. Per scored race, record Spearman ρ of each spec's utility vs actual
   official finish (identical to the engine's existing `rho_PL_*`).
4. **Baseline replication gate:** mean ρ of `base` over scored races with
   `year <= 2025` must be within ±0.003 of 0.413 (walk-forward is causal,
   so appending 2026+ races cannot change earlier scored races). If it
   fails: STOP, investigate, fix, re-run. No variant result obtained
   alongside a failed baseline counts for anything.

## 4. Kill/keep decision rule (frozen — the pre-registration)

For each variant v: paired per-race differences `d_i = ρ_v,i − ρ_base,i`
over all scored races (identical set by construction).

- Test: one-sided Wilcoxon signed-rank, `scipy.stats.wilcoxon(d,
  alternative='greater')`, default zero-handling.
- **Adopt v only if BOTH:** `p ≤ 0.0167` (Bonferroni 0.05/3 for three
  pre-registered variants) **and** `mean(d) ≥ +0.005`.
- If multiple variants pass: adopt the one with the highest mean(d);
  exact tie at 4 decimals → fewest added features (V2 = 0, V1 = 1, V3 = 2).
  **At most one variant is adopted.**
- If none pass: **the answer is no.** Record the result (§6), mark
  roadmap #4a done-with-negative-result, and do NOT re-try tweaked
  definitions (different half-life for the rate, different taxonomy,
  interactions…) under this spec — any new variant requires a new
  pre-registered spec committed before it is run.
- Diagnostics reported but **never gates**: mean(d) by track type, on the
  non-SS subset, on the 2026+ subset; final fitted weights; 4,000-resample
  bootstrap CI of mean(d) (np seed 7). The decision is the Wilcoxon p and
  the margin, nothing else — deterministic, seed-independent.

Why +0.005: with ~150 scored races the paired SE is ≈ 0.007 (audit: +0.010
was p = 0.17 at n = 128), so significance effectively requires mean(d) ≈
+0.015 — the margin only blocks a freak tiny-but-significant result and
costs no real power. Recorded so nobody "tunes" it later.

## 5. Execution constraints

- Runtime is minutes on a laptop (163-race pass with 4 refit-every-race PL
  specs); no parallelization needed — one process, one pass, all four specs
  share the history replay (which also guarantees identical scored sets).
- The script prints: sample size, scored-race count, baseline-gate value
  and PASS/FAIL, then per-variant mean(d), Wilcoxon p, CI, per-type
  diagnostics, and the verdict per §4 in a bordered block.

## 6. Recording the result

Append to this file a dated `## RESULT` section: sample size, scored count,
baseline-gate value, the per-variant table, verdict, and the commit hash of
the run. Update HANDOFF roadmap #4 status. This is the only edit this file
may ever receive.

## 7. Adoption procedure (only if a variant wins)

Separate commit, in this order:

1. `src/walkforward.py`: no change (it remains the frozen audit artifact).
2. `src/predict_next.py`: extend the history replay + field-feature build
   with the winning variant's exact definitions (§2); update `FEATS`;
   add `config_version: 2` and the variant name to the JSON `config` block.
3. `HANDOFF.md`: update the frozen-config paragraph (new frozen config =
   old + variant, with the walk-forward evidence cited) and roadmap.
4. Forward-test continuity: the market benchmark continues
   intention-to-treat (its spec §2); nothing is restarted or rescored.
   Already-committed predictions are never regenerated.

## Resolved-ambiguity register

- dvp = crash-class → it is a crash-damage retirement by definition.
- Unseen statuses → mech-class, keeping the taxonomy total and mechanical.
- V2 censors both `fin` and `typed` (same principle applied everywhere a
  finish history is read) but never eligibility → identical scored sets.
- Pace history is never censored → laps actually run carry pace signal
  regardless of how the race ended.
- Gate α split 3 ways, one-sided → three pre-registered variants, adoption
  is a directional claim.
- Evaluation on the full backtest, not forward races → power; the forward
  log's role is the market benchmark, not feature selection.
