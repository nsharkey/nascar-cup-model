#!/usr/bin/env python3
"""F4 -- empirical track similarity vs structural edges: Driver Skill Transferability
(specs/track_similarity.md). Builds gold.track_dst (pairwise DST matrix, track_id-only grain --
NOT (track_id, era_key), spec section 1.1), gold.track_dst_edges (edge-restricted comparison vs
silver.track_similarity_prior), and gold.track_pltree / gold.track_pltree_splits (the pltree
addendum, external_knowledge_scan.md section 3.9).

Build-graph isolation (spec section 5, enforced by gate_track_similarity.py): this module reads
gold.wf_features (via the frozen-engine replay) and silver.track_dim/track_xwalk/
track_similarity_prior, but nothing in gold_build.py/walkforward.py/predict_next.py may ever read
from gold.track_dst*/gold.track_pltree* -- one-directional, same discipline as F3.

gate_gold.py is NOT edited -- replay_frozen_engine_by_driver() mirrors its
gold_sourced_walk_forward() line-for-line (same imported pl_fit/wmean/znan, same eligibility/
burn/refit cadence), the same pattern track_profiles_build.replay_frozen_engine() already used
for FVS-model, extended here to retain per-driver utility instead of collapsing to aggregate rho.

Run from src/.
"""
import os
from collections import Counter, defaultdict
from itertools import combinations

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

import warehouse
import walkforward
from walkforward import pl_fit, wmean, znan
import gate_gold
import track_profiles_build as tpb

REPO_ROOT = warehouse.REPO_ROOT
GOLD_DIR = os.path.join(REPO_ROOT, 'data', 'gold')
TRACK_DST_PATH = os.path.join(GOLD_DIR, 'track_dst.parquet')
TRACK_DST_EDGES_PATH = os.path.join(GOLD_DIR, 'track_dst_edges.parquet')
TRACK_PLTREE_PATH = os.path.join(GOLD_DIR, 'track_pltree.parquet')
TRACK_PLTREE_SPLITS_PATH = os.path.join(GOLD_DIR, 'track_pltree_splits.parquet')

# ---- frozen-engine replay constants (spec section 1.2 -- identical to gate_gold.py /
# track_profiles_build.py, imported nowhere as a shared constant so pinned here verbatim) --------
BURN, MIN_HIST, MIN_DRV, PL_REFIT_EVERY = 15, 5, 20, 1
SPEC = {'fpts': ['fin', 'pace', 'typed', 'start']}
YEARS = (2022, 2023, 2024, 2025, 2026)

# ---- DST floor + shrinkage (spec section 1.3-1.4) -----------------------------------------------
MIN_COMMON_DRIVERS = 5      # pair-level floor -- reuses F3's TDS floor pair (races side)
MIN_WEIGHT_SUM = 15         # reuses F3's TDS floor pair (events side)
MIN_RACES_PER_SIDE = 5      # AMENDMENT (2026-07-20): each side must independently clear this too
MIN_FOLD_DRIVERS = 3        # fold-level floor, lower than the pair floor by design (spec 1.3)
SHRINK_K = tpb.SHRINK_K

# ---- pltree addendum constants (spec section 3, fixed a priori) ---------------------------------
PLTREE_COVARIATES_NUMERIC = ['length_mi', 'banking_max_deg', 'turns']
PLTREE_COVARIATES_BOOL = ['road_course', 'is_dirt', 'is_concrete']
MIN_LEAF = 3
MAX_DEPTH = 3


# ---------------------------------------------------------------------------
# 1.2 -- frozen-engine replay, driver grain (mirrors gate_gold.gold_sourced_walk_forward /
# track_profiles_build.replay_frozen_engine; gate_gold.py itself untouched)
# ---------------------------------------------------------------------------
def replay_frozen_engine_by_driver(con):
    races = gate_gold.silver_to_races_list(con)
    gold_by_key = gate_gold.load_gold_features(con)
    sample = [r for r in races if r['year'] in YEARS]

    pl_train = {'fpts': ([], [])}
    pl_w = {'fpts': None}
    since_fit = {'fpts': 0}
    rows = []

    for idx, race in enumerate(sample):
        rid = race['rid']
        drivers = race['drivers']
        elig = [d for d in sorted(drivers)
                if (rid, d) in gold_by_key
                and gold_by_key[(rid, d)]['n_hist'] >= MIN_HIST
                and gold_by_key[(rid, d)]['has_pace']]
        if idx >= BURN and len(elig) >= MIN_DRV:
            g = [gold_by_key[(rid, d)] for d in elig]
            actual = np.array([x['finish'] for x in g], float)
            start = np.array([x['start_feat'] for x in g], float)
            fin_h = np.array([x['fin_h'] for x in g], float)
            pace_h = np.array([x['pace_h'] for x in g], float)
            typ_h = np.array([x['typ_h'] for x in g], float)
            feat_bank = dict(pace=znan(pace_h), fin=znan(fin_h), typed=znan(typ_h), start=znan(start))
            X = np.column_stack([feat_bank[k] for k in SPEC['fpts']])
            Xs, Os = pl_train['fpts']
            if len(Xs) >= 20:
                if pl_w['fpts'] is None or since_fit['fpts'] >= PL_REFIT_EVERY:
                    pl_w['fpts'] = pl_fit(Xs, Os, w0=pl_w['fpts'])
                    since_fit['fpts'] = 0
                since_fit['fpts'] += 1
                u = X @ pl_w['fpts']
                for d, uu, ff in zip(elig, u, actual):
                    rows.append(dict(race_id=rid, driver_id=d, u=float(uu), finish=float(ff)))
            order = np.argsort(actual)
            Xs.append(-X)
            Os.append(order)
    return rows


def compute_residuals(driver_rows):
    """residual(d, race) = finish - expected_rank; expected_rank = 1 + ordinal rank of u within
    the race (ascending -- low u = good, per walkforward.py's own 'u aligns with finish position'
    comment), ties broken by driver_id ascending (spec section 1.2)."""
    by_race = defaultdict(list)
    for r in driver_rows:
        by_race[r['race_id']].append(r)
    out = []
    for rid, rows in by_race.items():
        rows_sorted = sorted(rows, key=lambda r: r['driver_id'])
        u = np.array([r['u'] for r in rows_sorted])
        order = np.argsort(u, kind='stable')
        ranks = np.empty(len(u), dtype=int)
        ranks[order] = np.arange(1, len(u) + 1)
        for r, rank in zip(rows_sorted, ranks):
            out.append(dict(race_id=rid, driver_id=r['driver_id'],
                             residual=r['finish'] - float(rank), finish=r['finish']))
    return out


def attach_track_year(residual_rows, rte, year_of):
    """rte: race_id -> (track_id, era_key) (silver.race_track_features, C3). year_of: race_id ->
    year. Rows whose race_id isn't in either map are dropped (not a Cup race_track_features race
    -- mirrors track_profiles_build's own convention)."""
    out = []
    for r in residual_rows:
        rid = r['race_id']
        if rid not in rte or rid not in year_of:
            continue
        track_id, era_key = rte[rid]
        out.append(dict(track_id=track_id, era_key=era_key, year=year_of[rid],
                         driver_id=r['driver_id'], residual=r['residual'], race_id=rid))
    return out


def build_track_driver_residuals(rows):
    """track_id -> driver_id -> list of dict(year, residual, race_id) (spec section 1.1's pooled,
    non-era-split window)."""
    out = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r['track_id']][r['driver_id']].append(
            dict(year=r['year'], residual=r['residual'], race_id=r['race_id']))
    return out


def build_track_eras(rows):
    out = defaultdict(set)
    for r in rows:
        out[r['track_id']].add(r['era_key'])
    return out


def compute_n_races_by_track(track_driver_residuals):
    """track_id -> count of distinct qualifying race_ids (AMENDMENT, spec section 1.4's added
    per-side floor input -- independent of any pair)."""
    out = {}
    for t, by_driver in track_driver_residuals.items():
        race_ids = {o['race_id'] for obs in by_driver.values() for o in obs}
        out[t] = len(race_ids)
    return out


# ---------------------------------------------------------------------------
# 1.3 -- pairwise DST estimator: leave-one-season-out CV, weighted Pearson
# ---------------------------------------------------------------------------
def _driver_means(obs_by_driver, exclude_year=None):
    out = {}
    for d, obs in obs_by_driver.items():
        vals = [o['residual'] for o in obs if exclude_year is None or o['year'] != exclude_year]
        if vals:
            out[d] = (float(np.mean(vals)), len(vals))
    return out


def _weighted_pearson(x, y, w):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    w = np.asarray(w, float)
    mx = np.average(x, weights=w)
    my = np.average(y, weights=w)
    vx = np.average((x - mx) ** 2, weights=w)
    vy = np.average((y - my) ** 2, weights=w)
    if vx <= 0 or vy <= 0:
        return None
    cov = np.average((x - mx) * (y - my), weights=w)
    return float(cov / np.sqrt(vx * vy))


def pairwise_dst(obs_a, obs_b):
    """obs_a/obs_b: driver_id -> list of dict(year, residual). Spec section 1.3."""
    years_a = {o['year'] for obs in obs_a.values() for o in obs}
    years_b = {o['year'] for obs in obs_b.values() for o in obs}
    season_set = years_a | years_b

    fold_rhos = []
    for s in sorted(season_set):
        means_a = _driver_means(obs_a, exclude_year=s)
        means_b = _driver_means(obs_b, exclude_year=s)
        common = sorted(set(means_a) & set(means_b))
        if len(common) < MIN_FOLD_DRIVERS:
            continue
        x = [means_a[d][0] for d in common]
        y = [means_b[d][0] for d in common]
        w = [min(means_a[d][1], means_b[d][1]) for d in common]
        rho = _weighted_pearson(x, y, w)
        if rho is not None:
            fold_rhos.append(rho)

    pair_raw = float(np.mean(fold_rhos)) if fold_rhos else None
    pair_loso_sd = float(np.std(fold_rhos)) if len(fold_rhos) >= 2 else None

    means_a_full = _driver_means(obs_a)
    means_b_full = _driver_means(obs_b)
    common_full = sorted(set(means_a_full) & set(means_b_full))
    n_common_drivers = len(common_full)
    weight_sum = sum(min(means_a_full[d][1], means_b_full[d][1]) for d in common_full)

    return dict(pair_raw=pair_raw, pair_loso_sd=pair_loso_sd,
                n_loso_folds_valid=len(fold_rhos),
                n_common_drivers=n_common_drivers, weight_sum=weight_sum)


def compute_all_pairs(track_driver_residuals):
    tracks = sorted(track_driver_residuals)
    pair_results = {}
    for a, b in combinations(tracks, 2):
        pair_results[(a, b)] = pairwise_dst(track_driver_residuals[a], track_driver_residuals[b])
    return tracks, pair_results


# ---------------------------------------------------------------------------
# 1.4 -- family-pair pooling (reuses track_profiles_build.blend_values verbatim)
# ---------------------------------------------------------------------------
def compute_family_pair_raw(pair_results, family_of):
    by_fam_pair = defaultdict(list)
    for (a, b), res in pair_results.items():
        if res['pair_raw'] is None:
            continue
        fam_pair = tuple(sorted((family_of[a], family_of[b])))
        by_fam_pair[fam_pair].append(res['pair_raw'])
    return {fp: float(np.mean(vs)) for fp, vs in by_fam_pair.items()}


def build_track_dst_rows(tracks, pair_results, family_of, track_eras, n_races_by_track):
    fam_pair_raw = compute_family_pair_raw(pair_results, family_of)
    rows = []
    for (a, b), res in pair_results.items():
        fam_pair = tuple(sorted((family_of[a], family_of[b])))
        family_raw = fam_pair_raw.get(fam_pair)
        # AMENDMENT (2026-07-20): each side must independently clear MIN_RACES_PER_SIDE, on top
        # of the driver-overlap floor -- zero out the floor's n_races input (not blend_values
        # itself) when either side is too thin, so blend_values' own below_floor test naturally
        # fires without reimplementing its formula.
        per_side_ok = (n_races_by_track.get(a, 0) >= MIN_RACES_PER_SIDE
                       and n_races_by_track.get(b, 0) >= MIN_RACES_PER_SIDE)
        n_races_for_floor = res['n_common_drivers'] if per_side_ok else 0
        blend = tpb.blend_values(res['pair_raw'], family_raw, n_races_for_floor,
                                  res['weight_sum'], MIN_COMMON_DRIVERS, MIN_WEIGHT_SUM, k=SHRINK_K)
        eras = sorted(track_eras.get(a, set()) | track_eras.get(b, set()))
        rows.append(dict(
            track_id_a=a, track_id_b=b, family_a=family_of[a], family_b=family_of[b],
            eras_represented=','.join(eras),
            pair_raw=res['pair_raw'], pair_loso_sd=res['pair_loso_sd'],
            n_loso_folds_valid=res['n_loso_folds_valid'],
            n_races_a=n_races_by_track.get(a, 0), n_races_b=n_races_by_track.get(b, 0),
            family_pair_raw=family_raw, n_common_drivers=res['n_common_drivers'],
            weight_sum=res['weight_sum'], dst_value=blend['value'],
            below_floor=blend['below_floor'], no_family_backstop=blend['value'] is None,
        ))
    return rows


# ---------------------------------------------------------------------------
# Section 2 -- comparison protocol vs the structural edges
# ---------------------------------------------------------------------------
def load_structural_edges_by_source(con):
    rows = con.sql("""
        SELECT source_track_id, target_track_id, structural_similarity_score
        FROM silver.track_similarity_prior
        ORDER BY source_track_id, structural_similarity_score DESC
    """).fetchall()
    by_source = defaultdict(list)
    for src, tgt, score in rows:
        by_source[src].append((tgt, score))
    return by_source


def build_dst_lookup(track_dst_rows):
    return {(r['track_id_a'], r['track_id_b']): r for r in track_dst_rows}


def build_empirical_neighbors(dst_lookup_map):
    """track_id -> [(other, dst_value), ...] sorted descending, non-below-floor pairs only."""
    neighbors = defaultdict(list)
    for (a, b), row in dst_lookup_map.items():
        if row['below_floor'] or row['dst_value'] is None:
            continue
        neighbors[a].append((b, row['dst_value']))
        neighbors[b].append((a, row['dst_value']))
    for t in neighbors:
        neighbors[t].sort(key=lambda x: -x[1])
    return neighbors


def structural_top3(track_id, by_source, in_scope):
    return [tgt for tgt, _score in by_source.get(track_id, []) if tgt in in_scope][:3]


def empirical_top3(track_id, empirical_neighbors):
    return [tgt for tgt, _v in empirical_neighbors.get(track_id, [])[:3]]


def empirical_bottom_half(track_id, empirical_neighbors):
    lst = empirical_neighbors.get(track_id, [])
    n = len(lst)
    return {tgt for i, (tgt, _v) in enumerate(lst) if (i + 1) > n / 2}


def empirical_rank_of(track_id, other, empirical_neighbors):
    for i, (tgt, _v) in enumerate(empirical_neighbors.get(track_id, [])):
        if tgt == other:
            return i + 1
    return None


def structural_rank_of(track_id, other, by_source):
    for i, (tgt, _score) in enumerate(by_source.get(track_id, [])):
        if tgt == other:
            return i + 1
    return None


def build_edge_restricted_rows(dst_lookup_map, by_source, in_scope):
    """Real structural edge rows restricted to in-scope, non-below-floor pairs (section 2), each
    tagged with dst_value/ranks/type-1 disagreement flag; plus synthetic type-2 rows for
    empirically-close/structurally-absent pairs (section 2.3 / 4.2)."""
    empirical_neighbors = build_empirical_neighbors(dst_lookup_map)

    def lookup(a, b):
        return dst_lookup_map.get((a, b)) or dst_lookup_map.get((b, a))

    rows = []
    for src, edges in by_source.items():
        if src not in in_scope:
            continue
        s_top3 = structural_top3(src, by_source, in_scope)
        e_bottom = empirical_bottom_half(src, empirical_neighbors)
        for tgt, score in edges:
            if tgt not in in_scope:
                continue
            dst_row = lookup(src, tgt)
            if dst_row is None or dst_row['below_floor'] or dst_row['dst_value'] is None:
                continue
            dtype = 'structural_close_empirical_dissimilar' if (tgt in s_top3 and tgt in e_bottom) else None
            rows.append(dict(
                source_track_id=src, target_track_id=tgt, structural_similarity_score=score,
                dst_value=dst_row['dst_value'], below_floor=dst_row['below_floor'],
                empirical_rank=empirical_rank_of(src, tgt, empirical_neighbors),
                structural_rank=structural_rank_of(src, tgt, by_source),
                disagreement_type=dtype,
            ))

    # type-2: empirically top-3 but structurally absent from the source's own edge list at all
    for t in sorted(in_scope):
        e_top3 = empirical_top3(t, empirical_neighbors)
        structural_targets = {tgt for tgt, _s in by_source.get(t, [])}
        for u in e_top3:
            if u in structural_targets:
                continue
            dst_row = lookup(t, u)
            if dst_row is None:
                continue
            rows.append(dict(
                source_track_id=t, target_track_id=u, structural_similarity_score=None,
                dst_value=dst_row['dst_value'], below_floor=dst_row['below_floor'],
                empirical_rank=empirical_rank_of(t, u, empirical_neighbors),
                structural_rank=None,
                disagreement_type='empirical_close_structural_absent',
            ))
    return rows


def compute_edge_restricted_spearman(edge_rows):
    pts = [(r['structural_similarity_score'], r['dst_value']) for r in edge_rows
           if r['structural_similarity_score'] is not None]
    if len(pts) < 3:
        return None, len(pts)
    xs, ys = zip(*pts)
    return float(spearmanr(xs, ys)[0]), len(pts)


def compute_top3_jaccard(in_scope, by_source, dst_lookup_map):
    empirical_neighbors = build_empirical_neighbors(dst_lookup_map)
    vals = []
    for t in sorted(in_scope):
        s3 = set(structural_top3(t, by_source, in_scope))
        e3 = set(empirical_top3(t, empirical_neighbors))
        if len(s3) < 3 or len(e3) < 3:
            continue
        union = s3 | e3
        if not union:
            continue
        vals.append(len(s3 & e3) / len(union))
    return vals


# ---------------------------------------------------------------------------
# Section 3 -- pltree cross-validation addendum
# ---------------------------------------------------------------------------
def load_track_dim_covariates(con):
    rows = con.sql("""
        SELECT track_id, length_mi, banking_max_deg, road_course, turns, surface
        FROM silver.track_dim
    """).fetchall()
    out = {}
    for tid, length_mi, banking, road, turns, surface in rows:
        s = (surface or '').lower()
        out[tid] = dict(length_mi=length_mi, banking_max_deg=banking, road_course=bool(road),
                         turns=turns, is_dirt='dirt' in s, is_concrete='concrete' in s)
    return out


def load_my_type(con):
    rows = con.sql("SELECT track_id, my_type FROM silver.track_xwalk").fetchall()
    return {r[0]: r[1] for r in rows if r[1]}


def _node_candidates(track_ids, covs):
    cands = []
    for name in PLTREE_COVARIATES_NUMERIC:
        if all(covs[t][name] is not None for t in track_ids):
            cands.append((name, False))
    for name in PLTREE_COVARIATES_BOOL:
        cands.append((name, True))
    return cands


def _mean_dst(pairs, dst_by_pair):
    vals = [dst_by_pair[p] for p in pairs if dst_by_pair.get(p) is not None]
    return float(np.mean(vals)) if vals else None


def _separation(L, R, dst_by_pair):
    def within(group):
        pairs = [tuple(sorted(p)) for p in combinations(group, 2)]
        return _mean_dst(pairs, dst_by_pair)

    def between(g1, g2):
        pairs = [tuple(sorted((a, b))) for a in g1 for b in g2]
        return _mean_dst(pairs, dst_by_pair)

    wl, wr, bt = within(L), within(R), between(L, R)
    if wl is None or wr is None or bt is None:
        return None
    return wl + wr - bt


def best_split(track_ids, covs, dst_by_pair):
    best = None
    for name, is_bool in _node_candidates(track_ids, covs):
        if is_bool:
            L = [t for t in track_ids if covs[t][name]]
            R = [t for t in track_ids if not covs[t][name]]
            candidates = [(None, L, R)]
        else:
            vals = sorted({covs[t][name] for t in track_ids})
            candidates = []
            for i in range(len(vals) - 1):
                th = (vals[i] + vals[i + 1]) / 2
                L = [t for t in track_ids if covs[t][name] <= th]
                R = [t for t in track_ids if covs[t][name] > th]
                candidates.append((th, L, R))
        for th, L, R in candidates:
            if len(L) < MIN_LEAF or len(R) < MIN_LEAF:
                continue
            sep = _separation(L, R, dst_by_pair)
            if sep is None:
                continue
            if best is None or sep > best[0]:
                best = (sep, name, th, L, R)
    return best


def build_pltree(track_ids, covs, dst_by_pair):
    leaves, splits = [], []
    node_counter = [0]

    def recurse(node_ids, depth, parent_id):
        my_id = node_counter[0]
        node_counter[0] += 1
        if depth >= MAX_DEPTH or len(node_ids) < 2 * MIN_LEAF:
            leaves.append(dict(leaf_id=my_id, track_ids=list(node_ids)))
            return
        best = best_split(node_ids, covs, dst_by_pair)
        if best is None or best[0] <= 0:
            leaves.append(dict(leaf_id=my_id, track_ids=list(node_ids)))
            return
        sep, name, th, L, R = best
        splits.append(dict(node_id=my_id, parent_id=parent_id, covariate=name,
                            threshold=th, separation=sep))
        recurse(L, depth + 1, my_id)
        recurse(R, depth + 1, my_id)

    recurse(sorted(track_ids), 0, None)
    return leaves, splits


def compute_pltree_agreement(leaves, my_type_of):
    rows = []
    for leaf in leaves:
        types = [my_type_of.get(t) for t in leaf['track_ids'] if my_type_of.get(t)]
        majority = Counter(types).most_common(1)[0][0] if types else None
        for t in leaf['track_ids']:
            mt = my_type_of.get(t)
            rows.append(dict(track_id=t, leaf_id=leaf['leaf_id'], leaf_size=len(leaf['track_ids']),
                              leaf_majority_my_type=majority, my_type=mt,
                              agrees_with_leaf=(mt == majority) if (mt and majority) else None))
    return rows


# ---------------------------------------------------------------------------
# main build
# ---------------------------------------------------------------------------
def _normalize_rows(rows):
    all_cols = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                all_cols.append(k)
    return [{c: row.get(c) for c in all_cols} for row in rows]


def build_track_similarity():
    os.makedirs(GOLD_DIR, exist_ok=True)
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH)

    print('[track_similarity_build] replaying frozen engine (driver grain, 2022-2026)...')
    driver_rows = replay_frozen_engine_by_driver(con)
    residual_rows = compute_residuals(driver_rows)

    rte = tpb.load_race_track_era(con)
    year_of = tpb.load_race_years(con)
    residual_rows = attach_track_year(residual_rows, rte, year_of)
    family_of = tpb.load_track_family(con)

    track_driver_residuals = build_track_driver_residuals(residual_rows)
    track_eras = build_track_eras(residual_rows)
    n_races_by_track = compute_n_races_by_track(track_driver_residuals)
    tracks, pair_results = compute_all_pairs(track_driver_residuals)
    print(f'[track_similarity_build] {len(tracks)} in-scope track_ids, {len(pair_results)} pairs')

    dst_rows = build_track_dst_rows(tracks, pair_results, family_of, track_eras, n_races_by_track)
    dst_table = pa.Table.from_pylist(_normalize_rows(dst_rows))
    pq.write_table(dst_table, TRACK_DST_PATH)
    print(f'[track_similarity_build] gold.track_dst: {dst_table.num_rows} rows')

    print('[track_similarity_build] comparison protocol vs structural edges...')
    by_source = load_structural_edges_by_source(con)
    dst_lookup_map = build_dst_lookup(dst_rows)
    in_scope = set(tracks)
    edge_rows = build_edge_restricted_rows(dst_lookup_map, by_source, in_scope)
    edges_table = pa.Table.from_pylist(_normalize_rows(edge_rows))
    pq.write_table(edges_table, TRACK_DST_EDGES_PATH)
    print(f'[track_similarity_build] gold.track_dst_edges: {edges_table.num_rows} rows')

    rho, n_edge_pts = compute_edge_restricted_spearman(edge_rows)
    jaccards = compute_top3_jaccard(in_scope, by_source, dst_lookup_map)
    n_disagree_1 = sum(1 for r in edge_rows if r['disagreement_type'] == 'structural_close_empirical_dissimilar')
    n_disagree_2 = sum(1 for r in edge_rows if r['disagreement_type'] == 'empirical_close_structural_absent')

    print('[track_similarity_build] pltree addendum...')
    covs = load_track_dim_covariates(con)
    my_type_of = load_my_type(con)
    dst_by_pair = {(r['track_id_a'], r['track_id_b']): r['dst_value'] for r in dst_rows}
    leaves, splits = build_pltree(tracks, covs, dst_by_pair)
    pltree_rows = compute_pltree_agreement(leaves, my_type_of)
    pltree_table = pa.Table.from_pylist(_normalize_rows(pltree_rows))
    pq.write_table(pltree_table, TRACK_PLTREE_PATH)
    splits_table = pa.Table.from_pylist(_normalize_rows(splits)) if splits else pa.table(
        {'node_id': pa.array([], type=pa.int64()), 'parent_id': pa.array([], type=pa.int64()),
         'covariate': pa.array([], type=pa.string()), 'threshold': pa.array([], type=pa.float64()),
         'separation': pa.array([], type=pa.float64())})
    pq.write_table(splits_table, TRACK_PLTREE_SPLITS_PATH)
    print(f'[track_similarity_build] gold.track_pltree: {pltree_table.num_rows} rows, '
          f'{len(splits)} internal split nodes')

    purity_rows = [r for r in pltree_rows if r['agrees_with_leaf'] is not None]
    purity = float(np.mean([r['agrees_with_leaf'] for r in purity_rows])) if purity_rows else None
    ari_rows = [r for r in pltree_rows if r['my_type']]
    ari = (float(adjusted_rand_score([r['my_type'] for r in ari_rows],
                                      [r['leaf_id'] for r in ari_rows]))
           if len(ari_rows) >= 2 else None)

    con.execute(f"CREATE OR REPLACE VIEW gold.track_dst AS "
                f"SELECT * FROM read_parquet('{TRACK_DST_PATH}')")
    con.execute(f"CREATE OR REPLACE VIEW gold.track_dst_edges AS "
                f"SELECT * FROM read_parquet('{TRACK_DST_EDGES_PATH}')")
    con.execute(f"CREATE OR REPLACE VIEW gold.track_pltree AS "
                f"SELECT * FROM read_parquet('{TRACK_PLTREE_PATH}')")
    con.execute(f"CREATE OR REPLACE VIEW gold.track_pltree_splits AS "
                f"SELECT * FROM read_parquet('{TRACK_PLTREE_SPLITS_PATH}')")
    con.close()
    warehouse.build_warehouse()

    report = dict(
        n_tracks=len(tracks), n_pairs=len(pair_results),
        n_below_floor=sum(1 for r in dst_rows if r['below_floor']),
        n_no_backstop=sum(1 for r in dst_rows if r['no_family_backstop']),
        edge_restricted_spearman=rho, n_edge_points=n_edge_pts,
        jaccard_mean=float(np.mean(jaccards)) if jaccards else None,
        jaccard_min=float(np.min(jaccards)) if jaccards else None,
        jaccard_median=float(np.median(jaccards)) if jaccards else None,
        jaccard_max=float(np.max(jaccards)) if jaccards else None,
        n_jaccard_tracks=len(jaccards),
        n_disagree_type1=n_disagree_1, n_disagree_type2=n_disagree_2,
        pltree_leaves=len(leaves), pltree_splits=len(splits),
        pltree_purity=purity, pltree_ari=ari,
        dst_lookup=dst_lookup_map, edge_rows=edge_rows, dst_rows=dst_rows,
        family_of=family_of, covs=covs, my_type_of=my_type_of,
    )
    return report


if __name__ == '__main__':
    r = build_track_similarity()
    print('=' * 78)
    print('TRACK SIMILARITY BUILD (F4) -- report')
    print('=' * 78)
    print(f"  in-scope tracks: {r['n_tracks']}, pairs: {r['n_pairs']}, "
          f"below_floor: {r['n_below_floor']}, no_backstop: {r['n_no_backstop']}")
    print(f"  edge-restricted Spearman: {r['edge_restricted_spearman']} (n={r['n_edge_points']})")
    print(f"  top-3 Jaccard: mean={r['jaccard_mean']} median={r['jaccard_median']} "
          f"min={r['jaccard_min']} max={r['jaccard_max']} (n_tracks={r['n_jaccard_tracks']})")
    print(f"  disagreements: type1(structural_close_empirical_dissimilar)={r['n_disagree_type1']} "
          f"type2(empirical_close_structural_absent)={r['n_disagree_type2']}")
    print(f"  pltree: {r['pltree_leaves']} leaves, {r['pltree_splits']} splits, "
          f"purity={r['pltree_purity']}, ARI={r['pltree_ari']}")
    print('=' * 78)
