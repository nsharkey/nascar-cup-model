#!/usr/bin/env python3
"""F14 -- Next Gen equipment-share decomposition (specs/equipment_share_decomposition.md).

Hierarchical driver/team/make variance decomposition of Cup finishing order, 2022+ Next Gen
era, ported from van Kesteren & Bergkamp (JQAS 2023)'s rank-ordered-logit / Plackett-Luce
template (spec section 2). Independently re-derived from walkforward.pl_fit (not called; spec
section 2.1 states why): one-hot driver/team/make dummies, a per-entity-type block-ridge penalty
in place of pl_fit's single scalar lam, and its own sign convention (higher fitted worth =
better, no negation) to avoid reusing a documented sign-inversion trap from this codebase's own
history (report/CALIBRATION_BACKTEST.md, M3).

Satisfies external_knowledge_scan.md section 3.2's standing requirement (spec sections 3, 4):
a per-season + pooled strong-connectivity diagnostic (scipy connected_components) and an
explicit block-ridge regularization scheme, its strength chosen by leave-one-season-out
cross-validated log-likelihood via coordinate descent (spec section 4.1).

Two variants: 'primary' (DNF included, this project's own `finish` convention) and
'dnf_excluded' (the source paper's own sensitivity check, spec section 6).

Build-graph isolation (spec section 9, enforced by gate_equip_share.py): none of
equip_share_worths / equip_share_summary / equip_share_connectivity may ever be read by
gold_build.py / walkforward.py / predict_next.py.

Run from src/.
"""
import os
from collections import Counter, defaultdict

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.optimize import minimize
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

import warehouse

REPO_ROOT = warehouse.REPO_ROOT
GOLD_DIR = os.path.join(REPO_ROOT, 'data', 'gold')
WORTHS_PATH = os.path.join(GOLD_DIR, 'equip_share_worths.parquet')
SUMMARY_PATH = os.path.join(GOLD_DIR, 'equip_share_summary.parquet')
CONNECTIVITY_PATH = os.path.join(GOLD_DIR, 'equip_share_connectivity.parquet')

SEASONS = (2022, 2023, 2024, 2025, 2026)
GRID = (0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)      # spec section 4.1
MAX_SWEEPS = 4                                      # spec section 4.1
FACTORS = ('driver', 'team', 'make')
VARIANTS = ('primary', 'dnf_excluded')
TRIGGER_THRESHOLD = 0.25                            # spec section 5.1

WORTHS_SCHEMA = pa.schema([
    ('variant', pa.string()), ('entity_type', pa.string()), ('entity_key', pa.string()),
    ('display_name', pa.string()), ('n_races', pa.int32()), ('worth', pa.float64()),
])

SUMMARY_SCHEMA = pa.schema([
    ('variant', pa.string()), ('n_races', pa.int32()), ('n_drivers', pa.int32()),
    ('n_teams', pa.int32()), ('n_makes', pa.int32()),
    ('lam_driver', pa.float64()), ('lam_team', pa.float64()), ('lam_make', pa.float64()),
    ('sd_driver', pa.float64()), ('sd_team', pa.float64()), ('sd_make', pa.float64()),
    ('sd_driver_empirical', pa.float64()), ('sd_team_empirical', pa.float64()),
    ('sd_make_empirical', pa.float64()),
    ('var_share_driver', pa.float64()), ('var_share_team', pa.float64()),
    ('var_share_make', pa.float64()), ('trigger_armed', pa.bool_()),
    ('built_at', pa.string()),
])

CONNECTIVITY_SCHEMA = pa.schema([
    ('variant', pa.string()), ('window', pa.string()), ('factor', pa.string()),
    ('n_entities', pa.int32()), ('n_components', pa.int32()),
    ('strongly_connected', pa.bool_()), ('offending_entities', pa.string()),
])


# ---- scope + entity keys (spec section 0, 1) -----------------------------------------------
SCOPE_SQL = """
select dr.race_id, dr.year, dr.driver_id, dr.finish, dr.status, dr.make,
       lower(trim(res.team_name)) as team_key, res.team_name, res.driver_fullname
from silver.driver_race dr
join silver.races ra on ra.series_id = dr.series_id and ra.race_id = dr.race_id
join silver.results res
    on res.series_id = dr.series_id and res.race_id = dr.race_id and res.driver_id = dr.driver_id
where dr.series_id = 1 and ra.race_type_id = 1 and ra.parse_status = 'ok' and dr.year >= 2022
order by dr.race_id, dr.finish
"""


def load_scope_rows(con):
    cols = ('race_id', 'year', 'driver_id', 'finish', 'status', 'make', 'team_key',
            'team_name', 'driver_fullname')
    return [dict(zip(cols, row)) for row in con.execute(SCOPE_SQL).fetchall()]


def is_dnf(row):
    return row['status'] != 'running'


def variant_rows(rows, variant):
    if variant == 'primary':
        return rows
    if variant == 'dnf_excluded':
        return [r for r in rows if not is_dnf(r)]
    raise ValueError(variant)


def build_vocab(rows):
    """driver_id / team_key / make vocabularies + display names + per-entity race counts,
    derived from this variant's own rows (spec section 8.1)."""
    drivers = sorted(set(r['driver_id'] for r in rows))
    teams = sorted(set(r['team_key'] for r in rows))
    makes = sorted(set(r['make'] for r in rows))

    driver_name = {}
    driver_races = defaultdict(set)
    for r in rows:
        driver_name.setdefault(r['driver_id'], Counter()).update([r['driver_fullname']])
        driver_races[r['driver_id']].add(r['race_id'])
    driver_display = {d: driver_name[d].most_common(1)[0][0] for d in drivers}

    team_name = {}
    team_races = defaultdict(set)
    for r in rows:
        team_name.setdefault(r['team_key'], Counter()).update([r['team_name']])
        team_races[r['team_key']].add(r['race_id'])
    team_display = {t: team_name[t].most_common(1)[0][0] for t in teams}

    make_races = defaultdict(set)
    for r in rows:
        make_races[r['make']].add(r['race_id'])

    return dict(
        drivers=drivers, teams=teams, makes=makes,
        d_idx={d: i for i, d in enumerate(drivers)},
        t_idx={t: i for i, t in enumerate(teams)},
        m_idx={m: i for i, m in enumerate(makes)},
        driver_display=driver_display, team_display=team_display,
        driver_n_races={d: len(s) for d, s in driver_races.items()},
        team_n_races={t: len(s) for t, s in team_races.items()},
        make_n_races={m: len(s) for m, s in make_races.items()},
    )


def build_race_matrices(rows, vocab):
    """Group rows by race_id, sort by finish ascending (best first, no negation -- spec
    section 2), one-hot encode driver/team/make. Returns {race_id: X} and {season: [X, ...]}."""
    nd, nt, nm = len(vocab['drivers']), len(vocab['teams']), len(vocab['makes'])
    k = nd + nt + nm
    by_race = defaultdict(list)
    race_season = {}
    for r in rows:
        by_race[r['race_id']].append(r)
        race_season[r['race_id']] = r['year']

    race_X = {}
    for race_id, entries in by_race.items():
        entries = sorted(entries, key=lambda r: r['finish'])
        n = len(entries)
        if n < 2:
            continue
        X = np.zeros((n, k))
        for i, r in enumerate(entries):
            X[i, vocab['d_idx'][r['driver_id']]] = 1.0
            X[i, nd + vocab['t_idx'][r['team_key']]] = 1.0
            X[i, nd + nt + vocab['m_idx'][r['make']]] = 1.0
        race_X[race_id] = X

    season_X = defaultdict(list)
    for race_id, X in race_X.items():
        season_X[race_season[race_id]].append(X)
    return race_X, season_X


# ---- PL likelihood, block ridge (spec section 2, 2.1, 4) -----------------------------------
def race_data_nll(w, X):
    u = X @ w
    m = u.max()
    e = np.exp(u - m)
    S = np.cumsum(e[::-1])[::-1]
    return float(np.sum(np.log(S) + m - u))


def race_data_nll_grad(w, X):
    u = X @ w
    m = u.max()
    e = np.exp(u - m)
    S = np.cumsum(e[::-1])[::-1]
    nll = float(np.sum(np.log(S) + m - u))
    inv = np.cumsum(1.0 / S)
    q = e * inv
    grad = q @ X - X.sum(axis=0)
    return nll, grad


def total_data_nll(w, X_list):
    return sum(race_data_nll(w, X) for X in X_list)


def penalized_nll_grad(w, X_list, lam_vec):
    nll = float(np.sum(lam_vec * w * w))
    grad = 2 * lam_vec * w
    for X in X_list:
        n, g = race_data_nll_grad(w, X)
        nll += n
        grad += g
    return nll, grad


def fit(X_list, lam_vec, k, w0=None):
    w0 = np.zeros(k) if w0 is None else w0
    res = minimize(lambda w: penalized_nll_grad(w, X_list, lam_vec), w0, jac=True,
                    method='L-BFGS-B')
    return res.x


def lam_vec_for(lam_driver, lam_team, lam_make, nd, nt, nm):
    return np.concatenate([np.full(nd, lam_driver), np.full(nt, lam_team), np.full(nm, lam_make)])


# ---- leave-one-season-out CV + coordinate descent (spec section 4.1) -----------------------
def cv_score(lam_driver, lam_team, lam_make, season_X, nd, nt, nm, k):
    """Total held-out NLL summed over leave-one-season-out folds (lower is better)."""
    seasons = [s for s in season_X if season_X[s]]
    total = 0.0
    for held in seasons:
        train = [X for s in seasons if s != held for X in season_X[s]]
        if not train:
            continue
        lv = lam_vec_for(lam_driver, lam_team, lam_make, nd, nt, nm)
        w = fit(train, lv, k)
        total += total_data_nll(w, season_X[held])
    return total


def select_lambdas(season_X, nd, nt, nm):
    k = nd + nt + nm
    lam = {'driver': 1.0, 'team': 1.0, 'make': 1.0}

    def score_with(factor, candidate):
        trial = dict(lam)
        trial[factor] = candidate
        return cv_score(trial['driver'], trial['team'], trial['make'], season_X, nd, nt, nm, k)

    for _sweep in range(MAX_SWEEPS):
        changed = False
        for factor in FACTORS:
            best_val, best_lam = None, None
            for cand in GRID:                       # ascending: <= prefers the larger on ties
                val = score_with(factor, cand)
                if best_val is None or val <= best_val:
                    best_val, best_lam = val, cand
            if best_lam != lam[factor]:
                changed = True
            lam[factor] = best_lam
        if not changed:
            break
    return lam['driver'], lam['team'], lam['make']


# ---- connectivity diagnostic (spec section 3) -----------------------------------------------
def entity_key_of(row, factor):
    return {'driver': row['driver_id'], 'team': row['team_key'], 'make': row['make']}[factor]


def connectivity_for_window(rows, factor):
    by_race = defaultdict(list)
    for r in rows:
        by_race[r['race_id']].append((r['finish'], entity_key_of(r, factor)))
    entities = sorted(set(e for _, e in (item for lst in by_race.values() for item in lst)),
                       key=str)
    idx = {e: i for i, e in enumerate(entities)}
    n = len(entities)
    edges = set()
    for entries in by_race.values():
        entries = sorted(entries, key=lambda e: e[0])
        ids = [idx[e] for _, e in entries]
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                if ids[a] != ids[b]:
                    edges.add((ids[a], ids[b]))
    if not edges:
        return n, n, False, list(map(str, entities))
    rows_e = np.array([e[0] for e in edges])
    cols_e = np.array([e[1] for e in edges])
    g = csr_matrix((np.ones(len(edges)), (rows_e, cols_e)), shape=(n, n))
    ncomp, labels = connected_components(g, directed=True, connection='strong')
    strongly_connected = bool(ncomp == 1)
    offending = []
    if not strongly_connected:
        sizes = Counter(labels)
        giant = max(sizes, key=lambda c: sizes[c])
        offending = sorted(str(entities[i]) for i in range(n) if labels[i] != giant)
    return n, int(ncomp), strongly_connected, offending


def build_connectivity_rows(rows_primary):
    out = []
    windows = [('pooled', rows_primary)] + [
        (str(y), [r for r in rows_primary if r['year'] == y]) for y in SEASONS
    ]
    for window, wrows in windows:
        if not wrows:
            continue
        for factor in FACTORS:
            n, ncomp, connected, offending = connectivity_for_window(wrows, factor)
            out.append(dict(
                variant='primary', window=window, factor=factor, n_entities=n,
                n_components=ncomp, strongly_connected=connected,
                offending_entities=(','.join(offending) if offending else None),
            ))
    return out


# ---- one variant end-to-end (spec sections 4, 5, 6) -----------------------------------------
def run_variant(all_rows, variant, built_at):
    rows = variant_rows(all_rows, variant)
    vocab = build_vocab(rows)
    nd, nt, nm = len(vocab['drivers']), len(vocab['teams']), len(vocab['makes'])
    k = nd + nt + nm
    race_X, season_X = build_race_matrices(rows, vocab)

    lam_driver, lam_team, lam_make = select_lambdas(season_X, nd, nt, nm)

    lv_final = lam_vec_for(lam_driver, lam_team, lam_make, nd, nt, nm)
    w = fit(list(race_X.values()), lv_final, k)
    alpha, beta, gamma = w[:nd], w[nd:nd + nt], w[nd + nt:]

    sd_driver = float(np.sqrt(1.0 / (2.0 * lam_driver)))
    sd_team = float(np.sqrt(1.0 / (2.0 * lam_team)))
    sd_make = float(np.sqrt(1.0 / (2.0 * lam_make)))
    denom = sd_driver ** 2 + sd_team ** 2 + sd_make ** 2
    var_share_driver = sd_driver ** 2 / denom
    var_share_team = sd_team ** 2 / denom
    var_share_make = sd_make ** 2 / denom

    worths = []
    for d, a in zip(vocab['drivers'], alpha):
        worths.append(dict(variant=variant, entity_type='driver', entity_key=str(d),
                            display_name=vocab['driver_display'][d],
                            n_races=vocab['driver_n_races'][d], worth=float(a)))
    for t, b in zip(vocab['teams'], beta):
        worths.append(dict(variant=variant, entity_type='team', entity_key=t,
                            display_name=vocab['team_display'][t],
                            n_races=vocab['team_n_races'][t], worth=float(b)))
    for mk, g in zip(vocab['makes'], gamma):
        worths.append(dict(variant=variant, entity_type='make', entity_key=mk,
                            display_name=mk, n_races=vocab['make_n_races'][mk], worth=float(g)))

    summary = dict(
        variant=variant, n_races=len(race_X), n_drivers=nd, n_teams=nt, n_makes=nm,
        lam_driver=lam_driver, lam_team=lam_team, lam_make=lam_make,
        sd_driver=sd_driver, sd_team=sd_team, sd_make=sd_make,
        sd_driver_empirical=float(np.std(alpha)), sd_team_empirical=float(np.std(beta)),
        sd_make_empirical=float(np.std(gamma)),
        var_share_driver=var_share_driver, var_share_team=var_share_team,
        var_share_make=var_share_make,
        trigger_armed=(var_share_team >= TRIGGER_THRESHOLD) if variant == 'primary' else None,
        built_at=built_at,
    )
    return worths, summary


def build_all(con, built_at='build-time'):
    all_rows = load_scope_rows(con)
    worths, summaries = [], []
    for variant in VARIANTS:
        w, s = run_variant(all_rows, variant, built_at)
        worths.extend(w)
        summaries.append(s)
    connectivity = build_connectivity_rows(all_rows)
    return worths, summaries, connectivity


def write_outputs(worths, summaries, connectivity):
    os.makedirs(GOLD_DIR, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(worths, schema=WORTHS_SCHEMA), WORTHS_PATH)
    pq.write_table(pa.Table.from_pylist(summaries, schema=SUMMARY_SCHEMA), SUMMARY_PATH)
    pq.write_table(pa.Table.from_pylist(connectivity, schema=CONNECTIVITY_SCHEMA),
                   CONNECTIVITY_PATH)


def main():
    import datetime
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH)
    built_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    worths, summaries, connectivity = build_all(con, built_at)
    con.close()
    write_outputs(worths, summaries, connectivity)
    warehouse.build_warehouse()  # re-register so gold.equip_share_* views exist
    for s in summaries:
        print(f"[{s['variant']}] n_races={s['n_races']} lam=({s['lam_driver']:.3g},"
              f"{s['lam_team']:.3g},{s['lam_make']:.3g}) "
              f"var_share driver/team/make = {s['var_share_driver']:.3f}/"
              f"{s['var_share_team']:.3f}/{s['var_share_make']:.3f} "
              f"trigger_armed={s['trigger_armed']}")
    print(f"wrote {len(worths)} worths, {len(summaries)} summary rows, "
          f"{len(connectivity)} connectivity rows")


if __name__ == '__main__':
    main()
