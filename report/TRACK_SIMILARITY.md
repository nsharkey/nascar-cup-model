# TRACK_SIMILARITY.md -- F4 build report (specs/track_similarity.md)

Empirical Driver Skill Transferability (DST) built by `src/track_similarity_build.py` per
`research/track_audit_derivation.md` section 4 (LAYER C), compared against the vendored
structural-similarity edges, plus a from-scratch pltree cross-validation of MY_TYPE
(`external_knowledge_scan.md` section 3.9). New gate `src/gate_track_similarity.py`, **PASS**.
Full gate surface re-ran **16/16 green** after this build (15 inherited + this session's new
gate); the frozen C-gate and D-gate were untouched and re-confirmed unchanged.

`research/track_audit/` and `silver.track_similarity_prior`/`silver.track_dim`/
`silver.track_xwalk` were read-only inputs (used for `primary_family`, structural edges, and
`my_type` only) -- nothing in this session edits the vendored package. Nothing here feeds
`walkforward.py`/`predict_next.py`/`gate_gold.py`; build-graph isolation is gate-enforced (gate
check 2), and `gate_gold.py` itself is byte-for-byte untouched (gate check 4).

## Row counts

| table | rows | grain |
|---|---:|---|
| `gold.track_dst` | 561 | unordered `(track_id_a, track_id_b)`, `C(34,2)` |
| `gold.track_dst_edges` | 35 | 15 real structural edges (in-scope, non-below-floor) + 20 synthetic type-2 rows |
| `gold.track_pltree` | 34 | one row per in-scope `track_id` |
| `gold.track_pltree_splits` | 6 | internal partition nodes, max depth 3 |

**34 in-scope configs, not the derivation doc's estimated 36** -- close, and the small gap is
explained: 148 races meet the walk-forward eligibility bar (`idx>=BURN`, `>=MIN_DRV` eligible
drivers) and resolve to 35 distinct `track_id`s, but only **128** of those 148 also clear the PL
weight-fit threshold (`len(Xs)>=20`, i.e. the model has accumulated enough prior races to
produce a utility vector `u` at all) -- the exact same 128-race population F3's FVS-model
already established (`report/TRACK_PROFILES.md`'s own count, an independent cross-check that
both sessions' replay logic agree). `road_america`'s sole 2022-2026 race (5165, 2022-07-03)
falls before that threshold is reached, so it never gets a residual and drops out, leaving 34.

## Floor behavior (AMENDMENT-corrected)

A first build pass used only the driver-overlap floor (`n_common_drivers>=5`,
`weight_sum>=15`) and found **zero** of 561 pairs below floor -- including pairs where one side
had exactly 1 qualifying race. The gap and its fix are recorded as a dated AMENDMENT in
`specs/track_similarity.md` (added before any output row was finalized): a third, per-side
requirement `n_races(a)>=5 AND n_races(b)>=5` was added, since driver-overlap alone doesn't
detect a config whose own races are individually too few to trust (7 of the 34 in-scope
configs have exactly 1 qualifying race: `san_diego_street`, `auto_club_2mi`, `bristol_dirt`,
`indianapolis_road`, `charlotte_roval_v1`, `mexico_city`, `chicagoland_oval`).

After the fix: **516 of 561 pairs (92.0%) are `below_floor`**, `no_family_backstop` on 0 rows
(every family-pair combo among the 12 `primary_family` groups present in the 34-config set has
at least one other pair with a defined `pair_raw` to pool). This is a higher below-floor share
than F3's 80-87% -- expected, since a DST pair needs *both* sides to individually clear the
`min_races=5` floor, compounding thinness in a way a single-track metric never has to.

Gate check 3 confirms mechanically: every `below_floor=true` row's `dst_value` equals its
`family_pair_raw` exactly (0 mismatches).

## Comparison protocol vs the structural edges

- **Edge-restricted Spearman: rho = 0.313 (n=15 edge points).** Small n (the floor leaves only
  45/561 pairs with a track-specific value, and of those only 15 also have a structural edge
  between an in-scope pair), but positive and directionally consistent with the structural
  priors -- where both are measurable, empirical and structural similarity agree more often
  than not.
- **Top-3-neighbor Jaccard: mean=0.186, median=0.20, min=0.0, max=0.5 (n=7 qualifying
  tracks).** Only 7 of 34 tracks have both >=3 defined DST neighbors and >=3 in-scope structural
  edges -- the same floor-driven data scarcity. Modest overlap where computable.
- **Disagreements:** 4 type-1 (structurally close, empirically dissimilar) --
  `atlanta_post_2022`<->`daytona_oval`, `martinsville`<->`richmond`, `phoenix_post_2018f`<->
  `richmond` (one pair, `atlanta_post_2022`/`daytona_oval`, appears from both directions). 20
  type-2 (empirically close, structurally absent) -- e.g. `atlanta_post_2022`<->
  `bristol_concrete` (dst=0.50), `bristol_concrete`<->`phoenix_post_2018f` (dst=0.53),
  `daytona_oval`<->`las_vegas` (dst=0.48). Per section 4.2's own doctrine, **empirical wins for
  analytics** where they disagree -- these pairs are candidates for future structural-edge
  refinement, not evidence the structural edges are wrong (they were never claiming to be
  empirical).

## Named callouts (section 2.4)

**H4 (concrete-track transfer nonlinearity).** All three pairs among
`{bristol_concrete, dover, nashville}` (same `primary_family`, "High-banked compact oval") are
`below_floor` (each config individually has 3-6 qualifying races), so all three display the
*same* family-pair-pooled value (0.408) -- the floor mechanism correctly refuses to
differentiate them at the track-specific level given current data. The **raw** (unshrunk,
pre-floor) `pair_raw` values do differ, and invert the structural ranking: structurally,
bristol_concrete<->nashville is rated *least* similar of the three (score 79.37, vs 83.79 for
bristol_concrete<->dover and 88.24 for dover<->nashville), but empirically it has the *highest*
raw correlation (0.476, vs 0.370 and 0.379). This is directionally consistent with H4's
"concrete transfer is nonlinear" hypothesis, but underpowered -- flagged as a **future data
point**, not a resolved test; more scored races at dover/nashville (currently 3 and 4) would
let the floor clear and the displayed values actually separate.

**"Large flat oval" vs production INT.** The package splits `indianapolis_oval`/`pocono` into
`primary_family="Large flat oval"` while `michigan` sits in `"High-speed intermediate"`; MY_TYPE
groups all three as `INT`. All three pairs are `below_floor` (2-4 races each). Raw `pair_raw`
values: `michigan`<->`pocono`=0.372, `indianapolis_oval`<->`michigan`=0.301,
`indianapolis_oval`<->`pocono`=0.349 -- all three in a similar, unremarkable 0.30-0.37 band with
no sharp break between the same-package-family pair (`indianapolis_oval`<->`pocono`, same
"Large flat oval" family) and the different-family pairs. This weakly favors MY_TYPE's unified
INT treatment over the package's family split (no empirical evidence of a meaningful gap), but
is underpowered for the same reason as H4 -- noted as a future data point.

## pltree cross-validation addendum (section 3)

7 leaves at max depth 3 (splits on `length_mi` three times, `banking_max_deg` once, `turns`
once -- see `gold.track_pltree_splits`). **Purity = 85.3% (29/34), Adjusted Rand Index = 0.501**
against MY_TYPE -- independent, physical-covariate-only evidence that broadly corroborates the
frozen typology.

Five tracks disagree with their leaf's MY_TYPE majority -- all interpretable, none surprising
enough to demand action:

- **`atlanta_post_2022`, `daytona_oval`, `talladega_oval`** (all MY_TYPE=`SS`) land in a
  7-track leaf whose majority is `INT` (alongside `auto_club_2mi`, `indianapolis_oval`,
  `michigan`, `pocono`). Physical covariates alone (length/banking/turns/surface) group the
  three drafting superspeedways with other large ovals -- expected, since SS status is a
  rules-package/drafting-aerodynamics distinction, not a raw-geometry one, and pltree's
  covariate set (deliberately, section 3) has no aerodynamic/rules field. This does **not**
  undermine MY_TYPE; it confirms MY_TYPE encodes information (drafting behavior) that pure
  physical geometry cannot recover on its own.
- **`bristol_dirt`** (MY_TYPE=`OTHER`) lands with 3 `SHORT` tracks (`bristol_concrete`,
  `martinsville`, `richmond`) -- physically a short, high-banked oval like its concrete
  counterpart; the `is_dirt` covariate exists as a candidate but the split search never
  selected it (a small-sample greedy search, not guaranteed to find every informative split).
- **`new_hampshire`** (MY_TYPE=`SHORT`) lands with `nashville`/`wwt_gateway` (both `INT`,
  leaf majority `INT`) -- the one genuinely mild surprise, a single-signal data point routed to
  a future pooling-refinement candidate per the spec's own instruction (section 3's "no model
  change either way"), never adopted here.

No model change either way, per the derivation doc's own instruction -- MY_TYPE is untouched.

## What changed, what didn't

- **New:** `gold.track_dst`, `gold.track_dst_edges`, `gold.track_pltree`,
  `gold.track_pltree_splits`; `src/track_similarity_build.py`; `src/gate_track_similarity.py`;
  four new view registrations in `src/warehouse.py` (same pattern F3 used for
  `track_profiles`/`track_profiles_asof`).
- **Untouched:** `walkforward.py`, `predict_next.py`, `gate_gold.py` (gate check 4 confirms no
  reference to this session's tables), `research/track_audit/` (hash-verified, gate check 7),
  `silver.track_similarity_prior`/`silver.track_dim`/`silver.track_xwalk` (read-only inputs).
- **Structural edges keep their sole donor role for zero-history configs** (section 1.5) --
  nothing here replaces `key_comparables`/`structural_nearest_neighbors` for the ~9 configs
  outside the 34-in-scope set (e.g. `north_wilkesboro`, retired pre-2022-only configurations).
