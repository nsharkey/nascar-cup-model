# SPEC: Empirical track similarity vs structural edges — Driver Skill Transferability (F4)

**Status:** pre-registered 2026-07-20, before any DST value has been computed.
**Derivation source (execution contract):** `research/track_audit_derivation.md`
§4 (LAYER C) defines DST and the comparison protocol and is authoritative for
their *intent* — this spec does not re-derive or alter that intent, only pins
the mechanical details §4 delegates or leaves as prose (exactly the same
relationship `specs/track_profiles.md` had to §3, per its own header). The
pltree addendum is pinned per `external_knowledge_scan.md` §3.9 and §9.3's
one-line tightening of F4's scope.

**Governance (restated from INTEGRATION.md and the derivation doc, binding):**
nothing computed here — pairwise, family-pooled, or the pltree partition —
enters the frozen PL prediction model without its own later pre-registered,
walk-forward-gated A/B. This session builds analytics/reference tables only.
`walkforward.py`, `predict_next.py`, `gate_gold.py`, and the vendored
`research/track_audit/` package are not touched.

**Tier:** Analytics/reference (phase F's own note: "Analytics and reference
sessions (F3/F4/F13/F14/F19) never touch the frozen model"). No gated A/B, no
`>=8`-scored-races gate — that gate applies only to the roadmap-#4 model A/B
family (F1/F2/F12/F18), not this session.

**Scope:** Cup only, inherited from the frozen engine's own scope
(`gate_gold.silver_to_races_list`/`load_gold_features`, `series_id=1`). MY_TYPE
and `silver.track_dim`/`silver.track_xwalk` are likewise Cup-scoped by
construction (C3, D1).

---

## 1. Shared machinery

### 1.1 Grain — `track_id` only, NOT `(track_id, era_key)` (deviates from F3; pinned here)

F3's shared grain is `(track_id, era_key)` (`specs/track_profiles.md` §1.1).
DST does **not** use that grain — it pools every qualifying race for a
`track_id` across the full 2022–2026 frozen-engine-replay window into one
cell. This is a deliberate, documented deviation, not an oversight:

- The derivation doc's own worked numbers ("36 in-scope configs → 630 pairs,"
  "per-config race counts of 1–10," "~25–35 drivers" per pair) only
  reconcile at `track_id`-only grain. The 2022–2026 window spans three
  `era_key`s (`nextgen_launch` 2022 only, `nextgen_low_downforce_short_road`
  2023–2025, `nextgen_750hp_sub15_road` 2026+ — `silver.rules_era`); splitting
  each track's window by era would inflate the cell count well past 36 and
  shrink most cells to 1–3 races, breaking both the season-CV design (needs
  ≥2 seasons per side) and the doc's own driver-overlap estimate. A direct
  count against the real frozen-engine-scored race set (§1.2) gives **35**
  in-scope `track_id`s at `track_id`-only grain vs **72** cells at
  `(track_id, era_key)` grain — 35 is the one that reconciles with "36."
- The residual source itself (the frozen PL utility, walk-forward-refit but
  not era-segmented) is not an era-conditioned quantity the way TDS's lap-time
  physics genuinely could be — there is no "DST for the `nextgen_launch` era"
  concept to preserve.
- Era is retained as a **descriptive** column only (`eras_represented`, the
  distinct `era_key`s touched by a cell's contributing races) — never part of
  the join key or the floor/shrinkage computation.

### 1.2 Residual definition and the frozen-engine replay (reuses F3's pattern, extended to driver grain)

`src/track_profiles_build.py`'s `replay_frozen_engine()` (F3, §2.10's
FVS-model) already mirrors `gate_gold.py`'s `gold_sourced_walk_forward()`
line-for-line — same imported `pl_fit`/`wmean`/`znan`, same
`gate_gold.silver_to_races_list`/`load_gold_features` reconstruction, same
`BURN=15`/`MIN_HIST=5`/`MIN_DRV=20`/`PL_REFIT_EVERY=1`/`years=(2022..2026)` —
but collapses each race down to an aggregate `rho`, discarding per-driver
detail. DST needs the per-driver utility, so this session adds
`replay_frozen_engine_by_driver(con)` in its own build module: **the exact
same loop** (same imports, same state machine, same eligibility order,
`gate_gold.py` itself untouched) with one difference from F3's version —
instead of computing `spearmanr(u, actual)` and discarding `u`, each row
retains `(race_id, driver_id, u, finish)` for every driver in `elig` at every
race where the PL weights have been fit (`len(Xs) >= 20`, `pl_w['fpts'] is
not None`). This is the identical scored-race population F3's FVS-model
already established (128 races) — a driver-level superset of the same
computation, not a new one.

- **Expected rank:** `expected_rank(d, race) = 1 + rank(u(d, race))` where
  `rank` is computed over the race's own `elig` field, ascending by `u`
  (lower `u` = better predicted finish, per `walkforward.py`'s own comment at
  the `u = X @ pl_w[name]` line: "w fit on -X, so u aligns with finish
  position"). Tie-break (deterministic, ties are float-improbable but pinned
  for reproducibility): stable sort by `(u, driver_id ascending)` —
  `np.argsort(np.argsort(u, kind='stable'), kind='stable') + 1`.
- **Residual:** `r(d, race) = finish(d, race) - expected_rank(d, race)`.
  Positive = driver finished worse than the frozen engine expected at that
  race; negative = better. Sign matches the derivation doc's literal ordering
  (§4.1: "residual = finish(d,t) − the frozen engine's pre-race expected
  finishing rank").
- **Per-`(track_id, driver_id)` mean residual** = arithmetic mean of
  `r(d, race)` over that driver's qualifying races at that track_id (§1.1's
  pooled, non-era-split window).

### 1.3 Pairwise DST estimator — leave-one-season-out CV, weighted Pearson (pinned)

For track-config pair `(a, b)`, over drivers `d` with ≥1 qualifying race at
**both** `a` and `b`:

- **Statistic — weighted Pearson, not Spearman.** §4.1 says "weighted
  correlation"; §4.2 separately names "Spearman" for the DST-vs-structural-
  score comparison. F4 pins §4.1's per-pair statistic to weighted Pearson
  correlation — the standard, unambiguous meaning of "weighted correlation";
  a weighted Spearman would require rank-weighting machinery neither the
  derivation doc nor F3's precedent calls for. This mirrors F3's own §1.3
  named-exception pattern (TDS_core median vs the rest's mean) — a
  documented split, not a hidden inconsistency.
- **LOSO-CV fold structure.** Let `S` = the union of season-years with ≥1
  qualifying race at `a` or at `b`. For each held-out season `s ∈ S`:
  - `mean_a_notS(d)` = mean residual for driver `d` over `a`'s races with
    `year != s`; `mean_b_notS(d)` likewise for `b`. `n_a_notS(d)`/`n_b_notS(d)`
    = the corresponding per-driver race counts feeding those means.
  - `D_s` = drivers with both means defined. **Fold floor:** the fold is
    skipped (does not contribute to the average) unless `len(D_s) >= 3` — a
    lower bar than the pair-level floor (§1.4) so the CV mechanism can run at
    all for thin pairs, while the pair-level floor still gates what gets
    *displayed*.
  - `ρ_s` = weighted Pearson correlation of `mean_a_notS[D_s]` vs
    `mean_b_notS[D_s]`, weights `w(d) = min(n_a_notS(d), n_b_notS(d))`.
- **`pair_raw(a,b)`** = mean of `ρ_s` over valid folds (`None` if zero valid
  folds). **`pair_loso_sd(a,b)`** = population SD of `ρ_s` over valid folds
  (the uncertainty companion §4.1 asks for; `None` if <2 valid folds).
- **Floor inputs (full-sample, not LOSO-averaged):** `n_common_drivers(a,b)` =
  count of drivers with ≥1 race at both `a` and `b` over the *full* (non-held-
  out) data; `weight_sum(a,b)` = sum over those drivers of
  `min(n_a_full(d), n_b_full(d))`.

### 1.4 Family-pair pooling and floor (reuses F3's `blend_values` verbatim)

- **Floor:** `min_races=5, min_events=15` — F4 reuses F3's TDS floor pair
  (`track_profiles_build.FLOORS['tds_core']`) rather than inventing a new
  constant: both TDS and DST are noisy per-observation statistics reduced to
  one track-level number under the frozen/derived machinery, and TDS is F3's
  closest kin in sample-depth character.
- **`family_pair_raw(family_x, family_y)`** (unordered, `family_x == family_y`
  permitted for intra-family pairs): **one fixed number per family-pair
  combo** — the unweighted mean of `pair_raw` over **every** in-scope
  track-pair whose two configs' families are `(family_x, family_y)`,
  including the intra-family case (all qualifying pairs drawn from the
  single family) and, like F3's own `family_raw`, **without excluding the
  specific pair `(a,b)` being shrunk** — the same number is reused for every
  track-pair sharing that family-pair combo. This mirrors F3 §1.5's own
  non-exclusion precedent ("family_raw is ... pooled across every track_id
  sharing that primary_family" — the target track is not held out — and
  shrinkage "still applies mechanically (harmless)" even in the
  single-member-family case). Reducing two family memberships to one number
  is done by pooling already-computed pair estimates, avoiding an ill-defined
  "family vs itself" raw-data correlation for `family_x == family_y` while
  treating inter- and intra-family combinations identically — F3's family
  pooling operates on one-sided raw data (a natural fit for a single
  track/family), which has no clean two-sided analog here.
- **Blend:** `track_profiles_build.blend_values(track_raw=pair_raw,
  family_raw=family_pair_raw, n_races=n_common_drivers, n_events=weight_sum,
  min_races=5, min_events=15, k=SHRINK_K)` — the identical function F3 uses,
  imported and called directly, not reimplemented. `dst_value` is its
  `value`; `below_floor` is its `below_floor`.
- **No-evidence edge case:** if both `pair_raw` and `family_pair_raw` are
  `None` (possible only when a config's family has no other in-scope member
  with a definable pairing against the other side), `dst_value = NULL`,
  `below_floor = true`, and a `no_family_backstop = true` flag is set. This is
  a legitimate, expected output for genuinely isolated configs (mirrors F3's
  own precedent of documented below-floor/no-data rows, not a defect).

### 1.5 Zero-history configs — structural edges keep their sole donor role

Configs outside the 35-in-scope set (never frozen-engine-scored in
2022–2026 — e.g. `north_wilkesboro`, most pre-2022-only retired
configurations) get **no** `gold.track_dst` row. Per §4.3, the structural
edges and `key_comparables` remain the only donor structure for these — DST
adds nothing there and does not attempt to.

---

## 2. Comparison protocol vs the structural edges

Source: `silver.track_similarity_prior` (C3; 193 rows, verbatim from
`nascar_track_similarity_edges.csv`). Restricted throughout to rows where
both `source_track_id` and `target_track_id` are in the 35-config in-scope
set (§1.1) **and** the corresponding `gold.track_dst` row has
`below_floor = false` — a below-floor DST value is the family posterior, not
a track-specific empirical estimate, so it is not a meaningful test of
track-level agreement.

### 2.1 Edge-restricted Spearman

Ordinary (unweighted) Spearman correlation between each qualifying edge row's
`structural_similarity_score` and its matching `dst_value` (looked up by the
unordered pair regardless of the edge's `source`→`target` direction; if both
directions of a pair are present as separate edge rows, both rows are
included as separate observations, matching "over the 193 edges" literally —
edges are rows, not deduplicated pairs).

### 2.2 Top-3-neighbor Jaccard overlap

For each in-scope `track_id` t with ≥3 defined (non-below-floor) DST pairs
**and** ≥3 structural edges to in-scope targets:

- `structural_top3(t)` = t's up-to-3 highest-`structural_similarity_score`
  edges (targets restricted to in-scope).
- `empirical_top3(t)` = t's up-to-3 highest-`dst_value` pairs.
- `jaccard(t) = |structural_top3(t) ∩ empirical_top3(t)| /
  |structural_top3(t) ∪ empirical_top3(t)|`.

Reported as the mean over qualifying `t`, plus min/median/max (an average
alone would hide a bimodal split).

### 2.3 Named disagreement list (both directions, per §4.2)

For each in-scope `t` with a defined DST ranking:

- `empirical_rank(t, u)` = rank of `dst_value(t,u)` among t's defined DST
  pairs, descending (1 = most similar).
- `empirical_bottom_half(t)` = t's DST pairs with `empirical_rank(t,u) >
  n_defined(t) / 2`.
- **Type 1 ("structurally close, empirically dissimilar"):** for
  `u ∈ structural_top3(t)`, flag `(t, u)` if `u ∈ empirical_bottom_half(t)`.
- **Type 2 ("empirically close, structurally absent" — the reverse):** for
  `u ∈ empirical_top3(t)`, flag `(t, u)` if `u` does not appear anywhere in
  t's structural edges at all (the package caps each config at ≤5 structural
  neighbors, so "absent" is a clean binary condition — no fuzzy threshold
  needed on that side).

### 2.4 Two named report callouts (free adjudications from the same data — no new machinery)

- **H4 (concrete transfer nonlinearity):** report `dst_value(bristol_concrete,
  dover)` and `dst_value(dover, nashville)` against their structural edge
  scores (all three share `primary_family = "High-banked compact oval"`).
- **"Large flat oval" vs production INT:** the package splits
  `indianapolis_oval`/`pocono` into `primary_family = "Large flat oval"`
  while `michigan` sits in `"High-speed intermediate"` — all three are `INT`
  under MY_TYPE. Report the three pairwise `dst_value`s among
  `{michigan, pocono, indianapolis_oval}` against their structural scores (or
  absence, since not all three pairs may have a structural edge at all).

Both callouts are report-only cross-checks — they use §1's already-computed
DST matrix and change nothing about the computation.

---

## 3. pltree cross-validation addendum (`external_knowledge_scan.md` §3.9/§9.3)

**No R/PlackettLuce dependency.** `PlackettLuce::pltree()` is not installed
(R is present on this machine but the package is not, and this project has no
existing R toolchain — `requirements.txt` is pure Python). Introducing a new
language/package dependency for one "cheap... small addendum" (the scan
doc's own framing) is disproportionate. F4 reimplements pltree's *core idea*
— partition on external covariates to find groups with structurally
different ranking behavior, then check whether the partition recovers an
independently-defined typology — directly against this session's own DST
matrix, with **zero new statistical machinery** and **MY_TYPE used only as
the final agreement check, never as a split criterion** (avoiding the
circularity a supervised classifier trained directly on MY_TYPE would have).

- **Candidate covariates** (from `silver.track_dim`, the T1 physical-fact
  columns): `length_mi`, `banking_max_deg`, `road_course` (bool), `turns`,
  plus two derived booleans from the free-text `surface` field:
  `is_dirt` (`'dirt' in surface.lower()`), `is_concrete` (`'concrete' in
  surface.lower()`). `banking_secondary_deg` is excluded (populated for only
  the tri-oval subset — too sparse to be a useful split candidate). Raw
  `surface`/`shape` free text is excluded as a direct categorical split (each
  value is near-unique per track — see the distinct-value dump in the build
  report — so a split on it degenerates to isolating single tracks).
- **Population:** the 35 in-scope `track_id`s (§1.1) — pltree needs a DST
  value to score candidate splits by, so it is restricted to the same
  universe as the DST matrix.
- **Split-selection criterion, fixed a priori:** at a node (a set of
  `track_id`s), for each candidate covariate fully populated across the
  node's tracks (a covariate with any NULL in the current node is skipped
  entirely for that node, not imputed), and each candidate threshold (numeric:
  midpoints between the node's sorted distinct values; boolean: the single
  true/false split), compute
  `separation(L,R) = within_mean_dst(L) + within_mean_dst(R) -
  between_mean_dst(L,R)`, using each pair's *displayed* `dst_value` (pairs
  with no defined value excluded from all three means). Choose the split
  maximizing `separation`, subject to `len(L) >= 3` and `len(R) >= 3`
  (`min_leaf = 3`, fixed a priori — with 35 tracks and a 3-level tree this
  keeps leaves from degenerating to singletons, mirroring pltree's own
  documented instability warning). Recurse into `L`/`R` independently.
- **Stopping rule, fixed a priori:** `max_depth = 3` (shallow, matching the
  scan doc's "cheap" framing and pltree's own high-dimensional-instability
  warning) OR no candidate split at a node improves `separation` over 0, OR
  the node has fewer than `2 * min_leaf = 6` tracks.
- **Agreement metrics (MY_TYPE enters here only):** `silver.track_xwalk.
  my_type` gives each in-scope track's frozen-typology bucket. Per leaf,
  `leaf_majority_type` = the plurality MY_TYPE among its tracks. Report (a)
  **purity** = `sum(size of each track's agreement with leaf_majority_type) /
  35`, and (b) **Adjusted Rand Index** (`sklearn.metrics.
  adjusted_rand_score`, already a project dependency) between the leaf
  assignment and MY_TYPE labels. Tracks whose own MY_TYPE differs from their
  leaf's majority feed the disagreement list (§2.3) as an additional,
  separately-labeled entry (not conflated with the structural-edge
  disagreements).
- **No model change either way**, per the scan doc's own instruction — this
  is independent-method evidence for or against MY_TYPE as a pooling key,
  routed to a future A/B candidate if disagreement is substantial, never
  adopted here.

---

## 4. Output schema

### 4.1 `gold.track_dst`

One row per unordered in-scope `track_id` pair (≤595, `C(35,2)`). Columns:
`track_id_a, track_id_b` (alphabetically ordered, `track_id_a < track_id_b`),
`family_a, family_b`, `eras_represented` (comma-joined distinct `era_key`s
across both sides' contributing races, descriptive only), `pair_raw`
(nullable), `pair_loso_sd` (nullable), `n_loso_folds_valid`,
`family_pair_raw` (nullable), `n_common_drivers`, `weight_sum`, `dst_value`
(the blended/displayed value), `below_floor` (bool), `no_family_backstop`
(bool). Provenance: `built_at`.

### 4.2 `gold.track_dst_edges`

Two row sources, both restricted to in-scope, non-below-floor pairs (§2):

- **Real structural edges** — one row per `silver.track_similarity_prior`
  row that survives the restriction: `source_track_id, target_track_id,
  structural_similarity_score, dst_value, below_floor, empirical_rank,
  structural_rank` (1-based rank of this edge among the source's own
  structural edges by score, for transparency), `disagreement_type`
  (`null` or `'structural_close_empirical_dissimilar'` — §2.3 type 1, which
  by definition only fires on a row where a structural edge exists).
- **Synthetic type-2 rows** — one row per (t, u) flagged by §2.3 type 2
  ("empirically close, structurally absent"): same columns, with
  `structural_similarity_score = NULL`, `structural_rank = NULL`,
  `disagreement_type = 'empirical_close_structural_absent'` — these exist
  precisely *because* no structural edge row exists for `(t, u)`, so they
  cannot be represented as an annotation on a real edge row.

### 4.3 `gold.track_pltree`

One row per in-scope `track_id`: `track_id, leaf_id, leaf_size,
leaf_majority_my_type, my_type, agrees_with_leaf` (bool). A small
`gold.track_pltree_splits` companion (one row per internal node:
`node_id, parent_id, covariate, threshold, separation`) for gate-level
re-derivation.

---

## 5. Build-graph isolation (same discipline as F3, restated)

`gold.wf_features`, `gold.driver_form`, `gold.driver_type_form`, and every
file under `src/gold_build.py`/`src/walkforward.py`/`src/predict_next.py` may
not read from `gold.track_dst`, `gold.track_dst_edges`, or
`gold.track_pltree*`, in source code or SQL, ever — enforced mechanically by
`gate_track_similarity.py`, a source-text scan for the tokens `track_dst`/
`track_pltree` in those three files, asserting zero matches (same pattern as
`gate_track_profiles.py` check 2). The reverse direction (this session's own
build reading `gold.wf_features` via the frozen-engine replay, and
`silver.track_dim`/`track_xwalk`/`track_similarity_prior`) is expected and
fine, matching F3's one-directional isolation.

---

## 6. Gate checklist (`gate_track_similarity.py`)

1. All three output tables/files exist and are internally consistent
   (`gold.track_dst` has no duplicate `(track_id_a, track_id_b)`, both sides
   in the 35-config in-scope set, `track_id_a < track_id_b`; `gold.
   track_pltree` has exactly 35 rows, one per in-scope `track_id`).
2. Build-graph isolation (§5): zero token matches in the three named files.
3. Every `below_floor = true` row's `dst_value` equals its
   `family_pair_raw` exactly (mirrors F3 gate check 3) — or is `NULL` when
   `no_family_backstop = true`.
4. `replay_frozen_engine_by_driver` is sourced only via imported
   `pl_fit`/`wmean`/`znan` from `walkforward` (source-scan, same spirit as
   F3 gate check 5) — not a reimplementation of the PL math.
5. Re-derivation spot-check: for a sample of `gold.track_dst` rows, recompute
   `pair_raw`/`dst_value` from the stored per-driver residuals and confirm
   exact reproduction (mirrors F3 gate check 4's idiom, adapted from as-of
   race-ordering to LOSO-fold re-derivation).
6. Re-derive the root-node split from `gold.track_dim` + `gold.track_dst`
   (the same §3 split-selection search restricted to the root's full
   35-track population) and confirm it matches the stored root row of
   `gold.track_pltree_splits` exactly. (No monotonicity check on `separation`
   across depth is imposed — a deeper node's best `separation` is not
   required to be smaller than its parent's, since it is computed over a
   different, smaller population.)
7. Vendored-package hash gate (`test_track_audit.py`) still passes —
   `research/track_audit/` and `silver.track_similarity_prior`/
   `silver.track_dim`/`silver.track_xwalk` are read-only inputs to this
   session, never rewritten.

---

## 7. Implementation checklist

1. `replay_frozen_engine_by_driver(con)` in `src/track_similarity_build.py`
   (new module) — mirrors `track_profiles_build.replay_frozen_engine` and
   `gate_gold.gold_sourced_walk_forward`, retains `(race_id, driver_id, u,
   finish)`.
2. Compute per-`(track_id, driver_id)` mean residuals over the §1.1 pooled
   window; build the 35-config in-scope set.
3. `pairwise_dst(a, b, residuals_by_track)` implementing §1.3's LOSO-CV
   weighted-Pearson estimator.
4. Compute all `C(35,2)` `pair_raw` values, then `family_pair_raw` per
   family-pair combo (§1.4), then blend via `track_profiles_build.
   blend_values` (imported, not reimplemented).
5. Build `gold.track_dst`; join `silver.track_similarity_prior` to build
   `gold.track_dst_edges` (§2.1–§2.3); compute the two named callouts (§2.4)
   for the report.
6. Build the pltree partition (§3) over `silver.track_dim` covariates and
   `gold.track_dst`; join `silver.track_xwalk.my_type` for agreement metrics;
   write `gold.track_pltree`/`gold.track_pltree_splits`.
7. `gate_track_similarity.py` per §6. `report/TRACK_SIMILARITY.md` summarizing
   row counts, floor/below-floor shares, the Spearman/Jaccard/disagreement-list
   results, the H4 and Large-flat-oval callouts, and the pltree agreement
   numbers.
8. Update `plan/schedule.yml` (F4 → done; promote F13 to `next` per phase F's
   enumerated order F3/F4/F13/F14/F19 — F14 stays blocked-but-unblocked,
   sequenced after F13); re-render (`python src/report_plan.py`); run the
   full gate surface (`src/run_gates.sh`, 16/16 expected); commit.
