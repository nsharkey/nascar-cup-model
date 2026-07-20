# SPEC: Pricing layer — a diagnostic Monte-Carlo readout (pre-registered design)

**Status:** pre-registered 2026-07-20 (plan session **M1**, Opus 4.8 · thinking
on · xhigh), before any pricing code exists. NEW pre-registration file — **not**
an amendment to any frozen spec. Descends from `research/pivot_model_book_vetting.md`
(the F20 vetting memo; owner fork **DEMOTE + tether**, §8) — honor §2(d)/§2(e)
verbatim.
**Governs:** plan session **M2** (build the diagnostic pricer + faithful-read gate +
capture-assist template) and is consumed by **M3** (the calibration backtest,
`specs/calibration_backtest.md`).
**Implements to:** `src/pricing_layer.py` + `src/gate_pricing.py` +
`src/fixtures/pricing_fixture.json` (new files; no existing file is modified).

Everything below is written so that an implementing session makes **zero judgment
calls.** Where a choice existed, it is resolved here, with the reason recorded.
The frozen sections (marked **FROZEN**) are immutable once committed, per
`specs/README.md`; a dated `## AMENDMENT` is permitted only while the data a rule
adjudicates does not yet exist, and the calibration numbers this layer feeds do
not exist until M3 runs.

---

## 0. What this layer is — and, emphatically, is not (FROZEN)

This layer turns the **frozen engine's as-of utility vector** for a race into
**implied fair odds across order-derived markets.** It is a **PL-faithful
readout**, nothing more.

- It is **a diagnostic**, not "honest fair odds you can bet." The raw model was
  measured **underconfident** (audit §7: says 64%, reality 74%) and near-noise at
  superspeedways (Brier 0.2514 < coin flip). Every price this layer emits is
  labeled **"raw-model implied (known underconfident)"**. The word *honest* is
  struck (memo §2(c)).
- **Coherence here means internal no-self-arbitrage ONLY — explicitly NOT
  correctness** (§4). The consistency invariants of §4 hold **identically** for
  the true utilities and for pure noise, so they carry **zero** evidential weight
  about whether the prices are right. "Coherent ⇒ trustworthy/fair" is struck
  (memo §2(d), FATAL-as-worded).
- It **changes nothing frozen.** It does not modify `predict_next.py`,
  `walkforward.py`, the scoring spec, or the market-benchmark spec. It does not
  touch the H2H pick rule that feeds the market benchmark (§3.4). The
  **faithful-read gate** (§6) proves this mechanically.
- It **does not recalibrate.** Recalibration is a separate, later, gated spec
  (`specs/recalibration.md`, not yet written); no monotone map is applied here.
- It **prices order-derived markets only** (§1). Stage / laps-led / margin /
  fastest-lap are **out of scope** — they are not functions of finishing order and
  cannot be priced from a finishing-order model at all; they route to the shelved
  generative model **C** (F7 formulation C), never this layer.

---

## 1. Market scope — order-derived only (FROZEN)

A market is **in scope** iff its settlement is a deterministic function of the
**finishing order** (the permutation of drivers, i.e. each driver's
`finishing_position`). Nothing else.

### 1.1 In scope

| Market key | Settlement (function of finishing order) |
|---|---|
| `win` | driver *i* finishes 1st |
| `h2h` | driver *i* finishes ahead of driver *j* (unordered pair) |
| `group_bestof` | driver *i* finishes best (lowest position) among a named group *G* |
| `mfr_win` | the race winner's car belongs to manufacturer *M* |
| `mfr_bestof` | the best-finishing car among a named manufacturer set belongs to *M* |
| `topN_single` | driver *i* finishes in the top *N* (`N ∈ {3,5,10}` pinned; others by explicit request) |
| `topN_joint` | ≥ *m* of a named driver set *S* finish in the top *N* |
| `group_topN_count` | exactly / at-least *m* of a named group *G* finish in the top *N* |

### 1.2 Out of scope (route to F7 formulation C, never this layer) (FROZEN)

Stage results / stage points, laps led, margin of victory, fastest lap, most
positions gained, caution counts — **any market not a function of the finishing
permutation.** PL emits only a finishing-order distribution; these markets need
the generative race model. Pricing them here is a protocol violation. See memo
§2(e)'s hard scope boundary.

### 1.3 The stand-down markets (FROZEN)

- **Superspeedway (`track_type == 'SS'`) races:** every market is priced and
  printed for completeness but flagged **`SS STAND-DOWN — not actionable`**,
  reusing the existing `stand_down` flag (`stand_down == (track_type == 'SS')`).
  Reason: at SS the engine is near-pure noise (audit §5: ρ 0.162, model lift
  +0.005; §7: confident picks 56%, Brier 0.2514). Never act on an SS price.
- **Tail markets:** any priced value failing the §5.3 MC-reliability rule (single
  rarer-cell expected count < 25) is flagged **`tail_stand_down`** and excluded
  from any decision-grade use downstream (still printed with the flag).

---

## 2. Inputs (FROZEN)

The layer is a pure function of a race's **as-of utility vector** and its
metadata. Two provenance paths, one identical pricer:

1. **Forward (live race) — the capture-assist path (§7).** The as-of utilities
   are the frozen engine's, exactly as `predict_next.py` computes them:
   `util = -(X @ w)` (higher = better), with `X`, `w` produced by the frozen
   config (`pace_med85`, hl 8, `MY_TYPE`, shrinkage typed, features
   `[fin,pace,typed,start]`, λ 0.5). For the weekly readout the layer **reads the
   committed prediction JSON** (`field[].utility`, `field[].driver_id`,
   `track_type`, `stand_down`) — it never re-runs the engine and never re-draws
   the forward probabilities (§7 emits fair odds from the frozen JSON's own
   `p_win/p_top5/p_top10/h2h_prob`, adding no new numbers to the sealed forward
   record).
2. **Backtest (M3) — the calibration path.** The as-of utilities are the
   walk-forward predictive utilities the frozen engine already produces:
   `walkforward.run(pl_specs={'fpts': ['fin','pace','typed','start']},
   collect_preds=preds, typology=MY_TYPE, typed_mode='shrinkage',
   years=<all present>)` yields, per scored race,
   `preds['fpts'] = [(u, actual, track_type, date), …]` (see
   `src/walkforward.py` lines 155–157). The pricer prices each race from its `u`.
   **No engine change; the utilities are read, never recomputed differently.**

The pricer's signature is fixed:

```
price_race(utility, driver_ids, track_type, race_id,
           manufacturer_of=None, groups=None, sets=None,
           topN=(3, 5, 10)) -> PricedRace
```

- `utility` — 1-D float array, higher = better (the engine's convention).
- `driver_ids` — int array aligned to `utility`.
- `manufacturer_of` — optional dict `driver_id -> mfr_str`; drivers absent from
  it are excluded from manufacturer markets (noted).
- `groups`, `sets` — optional lists of driver-id lists for `group_bestof` /
  `topN_joint` / `group_topN_count`; absent → those markets are not priced.
- Determinism is fixed by §5. `PricedRace` carries every priced value, its method
  (`analytic` | `mc`), its MC-SE (0 for analytic), and its flags.

---

## 3. Pricing methods — the analytic/MC seam, pinned (FROZEN)

This resolves the existing code seam (`predict_next.py` prices `win`/top-k from
the 40k joint sample but `h2h` analytically). The rule: **analytic wherever the
event is a within-subset ordering (closed form under PL's IIA); MC only for
absolute-position joint events with no closed form.**

### 3.1 Analytic markets (exact under Plackett–Luce; no MC)

Let `e_i = exp(u_i - max_k u_k)` (max-shift for numerical stability; shift-
invariant). All below are exact PL consequences of the Gumbel-max / Luce IIA
property — a within-subset ordering depends only on that subset's utilities.

- **`win`**: `p_win_i = e_i / Σ_k e_k` (softmax over the full field).
- **`h2h`** (unordered pair {i,j}): `p(i ahead of j) = e_i / (e_i + e_j)
  = σ(u_i − u_j)`. This is softmax over the two-driver subset — the pairwise
  ordering probability in PL is **exact**, not a Bradley–Terry approximation.
  **This is byte-identical to `predict_next.py`'s `h2h` (line 112) given the same
  utilities**; the pick rule that feeds the market benchmark is unchanged (§3.4).
- **`group_bestof`** (group *G*): `p(i best in G) = e_i / Σ_{k∈G} e_k` (softmax
  over *G*). The 2-member case is exactly `h2h`; `group_bestof` is its
  generalization. **Resolution of an apparent tension with the memo's "group
  markets → MC":** pure within-group *ordering* (best-of / full order among a
  fixed subgroup) is analytic by IIA; only group markets keyed on *absolute
  finishing position* (top-N of a group, §3.2) require MC. This pinning is
  deliberate and consistent with `h2h` being analytic.
- **`mfr_win`** (manufacturer *M*): `Σ_{i∈M} p_win_i` (a disjoint union of win
  events — exact).
- **`mfr_bestof`** (best car among a manufacturer set 𝓜, resolved to *M*):
  `Σ_{i∈M} e_i / Σ_{k∈(∪ 𝓜)} e_k` (softmax over the union of member cars,
  aggregated to *M*).

### 3.2 MC markets (one pinned Gumbel block per race; no closed form)

Drawn **once** per race from a single Gumbel block (§5), so every MC market is
reduced from the **same** simulated orders and is mutually consistent (§4).

- **`topN_single`**: `p(fin_i ≤ N)` for each driver.
- **`topN_joint`**: `p(≥ m of set S in top N)`.
- **`group_topN_count`**: `p(exactly / ≥ m of group G in top N)`.

Every MC market value uses the **add-half estimator** (§5.2), never a raw count,
so it is never exactly 0 or 1. Method flag = `mc`; MC-SE per §5.3.

### 3.3 Fair-odds conversion (FROZEN)

For a priced probability `p` (already floored per §5.2), the **fair** (zero-vig)
quotes are:

- decimal `= 1 / p`;
- American `= round(-100 · p / (1 − p))` if `p ≥ 0.5`, else
  `round(+100 · (1 − p) / p)` (round half to even; the floor in §5.2 keeps the
  denominator away from 0). `p == 0.5` → `+100`.

These are **fair** odds (no hold) — explicitly a diagnostic, not a betting price;
a fair book breaks even by construction (memo §1.1). The label
**"raw-model implied (known underconfident)"** is attached to every quote.

### 3.4 What is preserved verbatim — ITT continuity (FROZEN)

The layer does **not** sit between the model and the market benchmark. The frozen
H2H path is untouched: `predict_next.py` still writes `h2h_prob` as `σ(Δu)`;
`score_race.py` / `market_benchmark.py` still read it with the canonical
lower-id, `p > 0.5` pick rule (`specs/scoring_methodology.md` §4). Adopting this
layer changes **no** pick, no `book_prices` schema, no benchmark input —
intention-to-treat continuity, exactly as the market spec requires.

---

## 4. Coherence = internal consistency ONLY, not correctness (FROZEN)

The layer asserts the following **internal** invariants (a self-consistency
check, `gate_pricing.py`). **Every one holds identically whether `u` is the true
skill vector or pure noise — they therefore carry zero evidential weight about
correctness.** This is the whole point of stating them: to forbid the inference
"coherent ⇒ trustworthy," which the vetting refuted.

1. `Σ_i p_win_i = 1` within `1e-9` (analytic softmax).
2. For each `i`: `p_win_i ≤ p(fin_i ≤ 3) ≤ p(fin_i ≤ 5) ≤ p(fin_i ≤ 10)` —
   monotone in `N`. Holds **exactly** because all top-N marginals are reduced from
   the **one** Gumbel block (a sim with rank < 3 has rank < 5 < 10). This is why
   a single joint block is mandatory.
3. `p(i ahead of j) + p(j ahead of i) = 1` exactly (analytic `σ`), before the
   4-dp rounding that `predict_next.py` applies.
4. `mfr_win_M = Σ_{i∈M} p_win_i` exactly (disjoint union).
5. `Σ_{i∈G} p(i best in G) = 1` exactly (softmax over *G*).
6. Cross-check (reported, **not** a gate): the analytic `p_win_i` and the MC
   `p(fin_i = 1)` agree within `4 · √(2 · p̄(1−p̄)/N)` — a faithfulness report of
   the two internally-consistent estimators, never used to claim correctness.

**Stated for the record:** none of §4 measures whether the prices match reality.
That is what `specs/calibration_backtest.md` does, on out-of-sample outcomes, and
it is a **separate** question with a **separate** verdict.

---

## 5. Determinism (FROZEN)

Every number this layer produces is reproducible bit-for-bit on the pinned
environment. The pins:

### 5.1 Environment and RNG

- **Interpreter:** the **Anaconda `python` (3.13.x)** stack — the same interpreter
  the model/medallion gates run on (`GATES.md`; F7 §3.2 records numpy 2.1.3 /
  scipy 1.15.3 there). **Not** the `.venv` 3.14 interpreter (that runs only the
  plan gate).
- **numpy version pinned:** the fixture (§5.4) is valid for the numpy present on
  the conda interpreter at commit time; `gate_pricing.py` records and asserts the
  numpy version in its output. A numpy upgrade that changes any fixture value
  requires **regenerating the fixture in a dated amendment** (the amendment is
  permitted: the fixture pins mechanics, not adjudicated data).
- **RNG:** `numpy.random.default_rng(seed)` → the **PCG64** bit generator
  (numpy's default). No global `np.random` state is ever used.
- **N (Monte-Carlo draws):** `N_MC = 40_000` — matches `predict_next.py`.
- **Draw + reduction (verbatim recipe, mirrors `predict_next.py` lines 104–111):**
  drivers placed in **ascending `driver_id`** order (a canonical, feed-independent
  order — deterministic, unlike dict-insertion order); `g = rng.gumbel(size=(N_MC,
  D))`; `ranks = argsort(-(u[None,:] + g), axis=1)`; `pos[rows, ranks] =
  arange(D)`; a driver's simulated finishing position is its `pos` value
  (0 = win). All MC markets reduce from this one `pos` matrix.
  (Marginals are invariant to the column order in expectation — using ascending
  `driver_id` rather than `predict_next.py`'s field order changes which Gumbel
  column a driver draws, not the distribution of its rank; §6 verifies the two
  agree within MC error.)

### 5.2 Probability floor / add-α (so log-loss never sees 0) (FROZEN)

- **MC markets — add-half (Krichevsky–Trofimov):** for an event realized `k`
  times in `N_MC` sims, `p̂ = (k + 0.5) / (N_MC + 1)`. Never 0, never 1; a proper
  smoothed estimate. This is the value the layer emits and the value M3 scores.
- **Analytic markets — floor for scoring:** softmax/`σ` values already lie in
  `(0, 1)` but a `σ` at extreme `Δu` can round to `0.0000 / 1.0000`. For **any**
  probability consumed by a proper score (log-loss), clip to
  `[ε_floor, 1 − ε_floor]` with **`ε_floor = 1 / (2 · N_MC) = 1.25e-5`**. The
  emitted (display) analytic value is the unclipped one; the **scored** value is
  the clipped one. (The clip is defined here so M3 inherits one pinned floor.)

### 5.3 Per-market MC-reliability rule — exclude-or-raise-N (FROZEN)

For each MC market value `p̂`, let the rarer-cell expected count be
`c = min(N_MC · p̂, N_MC · (1 − p̂))`.

- **Admit as decision-grade iff `c ≥ 25`** (relative MC-SE ≤ 20 % in the rarer
  cell). At `N_MC = 40_000` this only ever bites for `p̂ < 6.25e-4` or
  `> 1 − 6.25e-4` — genuine tails.
- **If `c < 25`:** flag the value `tail_stand_down`, **exclude** it from
  decision-grade use (M3 never scores it), and **report** it with the flag. The
  operator MAY promote it by re-pricing that race at
  `N' = ceil(25 / min(p̂, 1 − p̂))` draws (a documented, per-race N override that
  never changes the pinned default `N_MC`; the override is logged).
- Analytic markets carry MC-SE 0 and are never tail-excluded by this rule (their
  own SS/tail flags come from §1.3).
- Every MC value also reports `MC_SE = √(p̂(1 − p̂) / N_MC)` for transparency.

### 5.4 Committed fixture — the gate reproves, never re-draws (FROZEN)

`src/fixtures/pricing_fixture.json` pins a small, fully-specified input and the
**exact** expected outputs the §5.1 recipe produces on the pinned interpreter:

- Input: a fixed `utility` vector (a real race's as-of vector — race 5618's
  `field[].utility`, committed verbatim — and a synthetic 5-driver toy field for
  the coherence invariants), `driver_ids`, `track_type`, a `manufacturer_of` map,
  one `group`, one `set`, `topN = (3,5,10)`, and the pinned `seed`.
- Output: every priced value (analytic exact; MC to full float precision),
  method flags, MC-SE, and flags — the numbers the recipe deterministically
  yields. `gate_pricing.py` **recomputes and asserts equality** against the
  committed fixture (analytic: exact to `1e-12`; MC: exact bit-match, since the
  recipe is deterministic), so the gate reproves the pinned numbers rather than
  re-drawing fresh ones. Regenerating the fixture is a deliberate, dated act
  (numpy bump per §5.1), never a silent overwrite.

### 5.5 Seed scheme (FROZEN)

- **Per-race, deterministic, independent:** the MC block for a race uses
  `rng = numpy.random.default_rng([PRICING_SEED_BASE, race_id])`, with
  **`PRICING_SEED_BASE = 20260720`** (this spec's date; a pinned constant). The
  two-element seed feeds a `SeedSequence`, giving each race an independent,
  reproducible stream — so the 163-race backtest carries **no** cross-race MC
  correlation (distinct from `predict_next.py`'s single hard-coded 5618, which is
  fine for one live race but would correlate a backtest).
- The fixture (§5.4) pins its own explicit `seed` so its numbers are fixed
  regardless of `race_id`.

---

## 6. Faithful-read gate (FROZEN) — proof the layer changes nothing frozen

`gate_pricing.py` proves the from-utilities pricer is a faithful generalization of
the frozen `predict_next.py`, on the frozen model's own committed output:

1. **Input = a committed prediction JSON** (race 5618's,
   `predictions/race_5618_2026-07-19_prediction.json`; and every other committed
   `race_*_prediction.json` as they accrue). Verify its hash first
   (`score_race.verify_hash`); skip and loudly report any that fails.
2. Extract the sealed as-of utilities (`field[].utility`) and driver ids; run
   `price_race(...)` on them at the pinned seed/N/recipe.
3. **Assert reproduction within MC error:**
   - `win` (analytic softmax) vs the JSON's sampled `p_win`: within `TOL_i`.
   - `topN_single` for N=5, N=10 (MC) vs the JSON's `p_top5` / `p_top10`: within
     `TOL_i`.
   - `h2h` (analytic `σ(Δu)`) vs the JSON's `h2h_prob` (canonical lower-id):
     within `2e-4` (both analytic; differ only by the JSON's 4-dp rounding).
   where **`TOL_i = max(2e-4, 4 · √(2 · p̄_i(1 − p̄_i) / N_MC))`**, `p̄_i` the mean
   of the two compared values. (A ~4–5.6σ envelope on the sampling difference:
   a faithful implementation effectively never fails; a real defect — wrong
   feature, factor error, misaligned ids — fails loudly.)
4. **Green iff every driver's every checked marginal is within tolerance** on
   every committed prediction. This proves the priced marginals reproduce
   `predict_next.py`'s existing `p_win / p_top5 / p_top10 / h2h_prob` within MC
   error — i.e. the layer reads the frozen model without changing it.

`gate_pricing.py` runs **both** the fixture reprove (§5.4) and the faithful-read
check, exits nonzero on any failure, and is added to `run_gates.sh` / `GATES.md`
as a new gate in **M2** (it becomes repo gate #11-or-later; numbering is assigned
at wiring time relative to the tether gates of `specs/tether_gates.md`).

---

## 7. The capture-assist template (FROZEN behavior; format stable-amendable)

The forward readout doubles as the manual-capture assist (memo §1(a); this is the
role L6 §9.7 flagged and the reason L2 is moot). For a **live** race it:

1. Reads the committed prediction JSON (hash-verified).
2. Emits the **full board** of valid H2H matchups — **all** unordered pairs of
   drivers in the predicted field — each with the model-implied `h2h_prob`
   (from the JSON, `σ(Δu)`) and its fair American odds (§3.3), sorted for fast
   transcription (by driver-a grid, then driver-b grid).
3. Emits per-driver `win / top5 / top10` implied fair odds (from the JSON's
   `p_win/p_top5/p_top10`).
4. Marks SS races `SS STAND-DOWN` and tail markets `tail_stand_down`, and labels
   the whole sheet **"raw-model implied (known underconfident) — diagnostic, not
   a betting price."**

It writes a `predictions/race_{id}_{date}_capture_template.csv` (a working aid;
the sealed JSON is unchanged). Its purpose is to make the human's weekly
book-price capture **fast and full-board**, so the market benchmark is **fed**,
not starved — the capture-assist helps the external judge, it does not replace it.
The forward path **adds no probability to the sealed record**; it re-expresses the
frozen JSON's own numbers as odds.

---

## 8. Implementation checklist (mechanical, in order — for M2)

1. `src/pricing_layer.py`: pure functions `softmax(u)`, `h2h_matrix(u)`,
   `group_bestof(u, G)`, `mfr_markets(u, ids, mfr_of)`, `mc_block(u, ids, seed)`
   (the §5.1 recipe), `topN_single/joint/count(pos, …)` (§3.2, add-half §5.2),
   `fair_odds(p)` (§3.3), `price_race(...)` (§2 signature) returning `PricedRace`;
   `mc_reliability(p̂)` (§5.3). No network, no engine re-run, no global RNG.
2. `src/fixtures/pricing_fixture.json`: generate once on the conda interpreter
   from the pinned recipe (§5.4); commit it; record the numpy version inside it.
3. `src/gate_pricing.py`: the §4 coherence invariants + the §5.4 fixture reprove +
   the §6 faithful-read check; plain stdlib asserts, exits nonzero on any failure;
   prints the numpy version and a bordered summary. Read-only w.r.t. every frozen
   file.
4. Add `gate_pricing.py` to `src/run_gates.sh` (conda interpreter) and document it
   in `GATES.md`. Confirm it goes **red** on an injected defect (e.g. a doubled
   utility, a dropped feature) — a gate that cannot fail is not a gate.
5. `src/capture_template.py` (or a `--capture` mode of `pricing_layer.py`): §7.
6. Run the full gate surface; leave the tree clean. **No frozen-spec edit; no
   change to `predict_next.py` / `walkforward.py`.**

---

## 9. Resolved-ambiguity register (why, one line each)

- **Group best-of is analytic, not MC** → within-group ordering is exact softmax
  under PL's IIA; `h2h` is its 2-member case and is already analytic. Only
  absolute-position group markets (top-N of a group) need MC.
- **Win taken analytic (softmax), though `predict_next` samples it** → softmax is
  the exact PL win probability; the faithful-read gate proves it matches the
  sampled value within MC error, so nothing frozen shifts.
- **One Gumbel block per race** → makes all top-N marginals mutually monotone
  (coherence invariant 2) by construction and keeps compute at seconds/race.
- **Ascending-driver-id draw order** → deterministic and feed-independent;
  marginals are order-invariant in expectation, so faithful-read still holds.
- **Add-half for MC, ε_floor for analytic** → proper smoothing so M3's log-loss
  never sees 0/1; two mechanisms because MC values are counts and analytic values
  are exact reals.
- **`c ≥ 25` rarer-cell rule** → a relative-error criterion that flags genuine
  tails (where log-loss blows up) while leaving mid-order markets untouched;
  analytic `win` removes the worst tail from MC entirely (memo §2(e)).
- **PRICING_SEED_BASE = 20260720, per-race SeedSequence `[base, race_id]`** →
  independent reproducible streams, no cross-race MC correlation in the backtest.
- **Conda 3.13 interpreter, numpy pinned, committed fixture** → the gate reproves
  fixed numbers instead of re-drawing; a numpy bump is a deliberate dated
  fixture-regeneration, never silent drift.
- **Coherence stated as internal-only** → it holds for signal and noise alike, so
  it can never be cited as evidence of correctness; correctness is
  `specs/calibration_backtest.md`'s separate question.

## 10. Flagged (not resolved — owner input welcome, non-blocking)

- The **book's** offered H2H board may be a subset of all field pairs; §7 emits
  all pairs so the human transcribes whatever the primary book actually lists.
  If a future *book-side* capture schema for win/top-k is wanted, that is
  `specs/allbet_capture_schema.md` (memo §3.1, lowest priority, descriptive-only —
  it can never feed the H2H-only benchmark).
- Group / manufacturer market **membership** (who is in which manufacturer, which
  group a book offers) is passed in by the caller; a canonical manufacturer map
  can be sourced from silver later, but pricing does not depend on it existing.

---

## RESULT — pricing layer (M2, 2026-07-20)

**Built, all green, tree clean.** `src/pricing_layer.py` (pure functions: `softmax`,
`h2h_matrix`, `group_bestof`, `mfr_markets`, `mc_block` (§5.1 recipe), `topN_single`,
`count_topN_distribution` (shared machinery for `topN_joint`/`group_topN_count`),
`mc_reliability` (§5.3), `fair_odds`/`score_floor` (§3.3/§5.2), `price_race` (§2
signature)); `src/generate_pricing_fixture.py` + `src/fixtures/pricing_fixture.json`
(two sub-fixtures: `real_race_5618` — race 5618's real 37-driver `field[].utility`
verbatim, win/h2h/topN only — and `toy_field` — a synthetic 5-driver `SS`-typed field
exercising `manufacturer_of`/one `group`/one `set`/coherence/the tail-flag path);
`src/gate_pricing.py`; `src/capture_template.py` (§7). Conda interpreter: Python
3.13.5, numpy 2.1.3, scipy 1.15.3 (recorded in the fixture's `meta` block and
asserted live by the gate).

**Gate (11th in `run_gates.sh`/`GATES.md`) — PASS on all three checks:**
1. **Coherence (§4):** points 1/3/4/5 hold to floating-point precision (≤1e-9,
   the achievable bound for IEEE754 — literal bit-exact `==` is not attainable for
   §4 point 3's pairwise sum, a genuine floating-point property of computing
   `σ(Δu)` and `σ(-Δu)` via two independent divisions, not a defect). Point 2's
   "holds exactly" is proved by comparing **all four** terms (N=1/3/5/10) from the
   **same** MC block — not the analytic `p_win` against MC top-N, which are
   different estimators and only agree within the point-6 cross-check tolerance
   (documented in `gate_pricing.py`'s module docstring; both fields' point-6
   cross-checks pass, 37/37 and 5/5 drivers within tolerance).
2. **Fixture reprove (§5.4):** bit-exact match on both sub-fixtures after a fresh
   `price_race` recompute from the fixture's own committed `input` blocks.
3. **Faithful-read (§6):** race 5618's committed prediction JSON — the only one
   committed to date — hash-verified, then 1,443 marginals checked (37 win + 37
   top5 + 37 top10 + 1,332 h2h, the full matrix, a superset of the canonical
   lower-id minimum) against the JSON's own `p_win`/`p_top5`/`p_top10`/`h2h_prob`,
   all within `TOL_i` (h2h within 2e-4). Max observed slack vs. tolerance: win
   ≤1.4e-3 under bound, top5 ≤3.5e-3, top10 ≤4.9e-3, h2h max diff 6.97e-5 (vs. the
   2e-4 floor) — comfortable margins, consistent with a faithful, defect-free
   implementation.

**Red-on-defect confirmed:** an injected doubled-utility defect (`utility *= 2`
inside `price_race`) was run against the live fixture reprove and produced 6,000+
mismatches, exit code 1 — the gate is not vacuously green.

**Resolved (not flagged) during build, for the record:**
- §4 point 3's "exactly" and point 2's "holds exactly" read as floating-point-exact
  (≤1e-9), not bit-exact `==`, for the reasons above — a numerical-practice
  correction to the gate's own assertions, not a spec ambiguity requiring an
  amendment (the spec's own point 1 already states "within 1e-9").
- `mfr_bestof`'s market-defining set 𝓜 is taken as exactly the drivers present in
  the caller's `manufacturer_of` dict (∪𝓜), matching the §3.1 formula literally;
  the pinned `price_race` signature has no separate 𝓜 parameter.
- `topN_joint`/`group_topN_count` emit the full count pmf (k = 0..|subset|) rather
  than a single "≥m"/"exactly m" value, since the pinned signature carries no `m`
  parameter — the pmf is a strict superset from which any m is derivable without a
  second MC pass, and both markets share one `count_topN_distribution` helper
  (same statistic, different caller-side label).
- The fixture's `toy_field` is `track_type='SS'` (not a neutral non-SS type) so the
  `SS_STAND_DOWN` flag path is exercised by the same committed fixture that also
  exercises `manufacturer_of`/group/set, rather than adding a third sub-fixture.

**No frozen-spec edit; no change to `predict_next.py` / `walkforward.py`.** H2H
pick rule (ITT continuity, §3.4) untouched — `gate_pricing.py` only reads the
sealed JSON. `src/capture_template.py` re-expresses race 5618's own sealed numbers
as fair odds (smoke-tested against race 5618, output not committed — race 5618 is
already closed out, so a capture sheet for it now serves no live purpose; the
script is the deliverable). Gate surface was 10/10 green going into this session
(M1's last verification, untouched by the intervening spec-only commit); 11/11
green (the new `gate_pricing.py` included) after this build; tree left clean.
