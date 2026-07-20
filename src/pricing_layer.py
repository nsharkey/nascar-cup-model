#!/usr/bin/env python3
"""Diagnostic Monte-Carlo pricing layer -- specs/pricing_layer.md (FROZEN spec).

Turns the frozen engine's as-of utility vector for a race into implied fair
odds across order-derived markets (section 1). A PL-faithful readout, nothing
more: coherence (section 4) is internal self-consistency ONLY, never evidence
of correctness. Pure functions -- no network, no engine re-run, no global RNG
state (every draw uses an explicit `numpy.random.default_rng` instance).

Two provenance paths (section 2) both call `price_race` with `utility`
already the frozen engine's own as-of vector -- this module never computes
utility itself and never touches predict_next.py / walkforward.py.
"""
import math

import numpy as np

# ---------------------------------------------------------------------------
# pinned constants (section 5)
# ---------------------------------------------------------------------------
N_MC = 40_000
PRICING_SEED_BASE = 20260720
EPS_FLOOR = 1.0 / (2 * N_MC)          # 1.25e-5 -- analytic scoring floor (5.2)
MC_RELIABILITY_C = 25                 # rarer-cell expected-count floor (5.3)


# ---------------------------------------------------------------------------
# 1. analytic markets (section 3.1) -- exact under Plackett-Luce / IIA
# ---------------------------------------------------------------------------
def softmax(u):
    """p_win_i = e_i / sum(e_k), e_i = exp(u_i - max(u)) (max-shift, shift-invariant)."""
    u = np.asarray(u, float)
    e = np.exp(u - u.max())
    return e / e.sum()


def h2h_matrix(u):
    """p(i ahead of j) = sigma(u_i - u_j), the exact PL pairwise-ordering probability."""
    u = np.asarray(u, float)
    return 1.0 / (1.0 + np.exp(-(u[:, None] - u[None, :])))


def group_bestof(u, ids, member_ids):
    """p(i best in G) = softmax restricted to `member_ids` (a driver-id subset of
    `ids`) -- exact within-group ordering under PL's IIA. h2h is the 2-member case."""
    id_to_idx = {int(d): i for i, d in enumerate(ids)}
    idx = [id_to_idx[int(m)] for m in member_ids]
    sub = softmax(np.asarray(u, float)[idx])
    return {int(m): float(p) for m, p in zip(member_ids, sub)}


def mfr_markets(u, ids, mfr_of):
    """mfr_win_M = sum_{i in M} p_win_i (disjoint union over the FULL field's win
    softmax -- exact). mfr_bestof: softmax restricted to exactly the drivers present
    in `mfr_of` (the caller-supplied union of member cars, i.e. union(script M)),
    aggregated to M. Drivers absent from `mfr_of` are excluded from both markets."""
    ids = np.asarray(ids, int)
    u = np.asarray(u, float)
    p_win = softmax(u)

    win_by_mfr = {}
    for i, d in enumerate(ids):
        m = mfr_of.get(int(d))
        if m is None:
            continue
        win_by_mfr[m] = win_by_mfr.get(m, 0.0) + float(p_win[i])

    known_idx = [i for i, d in enumerate(ids) if int(d) in mfr_of]
    bestof_by_mfr = {}
    if known_idx:
        sub_u = u[known_idx]
        e = np.exp(sub_u - sub_u.max())
        denom = e.sum()
        for col, i in enumerate(known_idx):
            m = mfr_of[int(ids[i])]
            bestof_by_mfr[m] = bestof_by_mfr.get(m, 0.0) + float(e[col])
        bestof_by_mfr = {m: v / denom for m, v in bestof_by_mfr.items()}
    return win_by_mfr, bestof_by_mfr


# ---------------------------------------------------------------------------
# 2. fair-odds conversion (section 3.3)
# ---------------------------------------------------------------------------
def fair_odds(p):
    """Zero-vig fair quotes for probability p in (0, 1). Round half to even
    (Python's built-in round()); p == 0.5 -> +100 exactly."""
    decimal = 1.0 / p
    if p == 0.5:
        american = 100
    elif p >= 0.5:
        american = int(round(-100.0 * p / (1.0 - p)))
    else:
        american = int(round(100.0 * (1.0 - p) / p))
    return {'fair_decimal': decimal, 'fair_american': american}


def score_floor(p, eps=EPS_FLOOR):
    """Clip an analytic probability into [eps, 1-eps] for use by a proper score
    (log-loss). The emitted/display value stays unclipped; callers that SCORE an
    analytic value (e.g. specs/calibration_backtest.md) must apply this floor
    themselves (section 5.2) -- MC values are already add-half smoothed and need
    no further floor."""
    return min(max(p, eps), 1.0 - eps)


# ---------------------------------------------------------------------------
# 3. the one pinned Gumbel block (sections 3.2, 5.1) -- MC markets, no closed form
# ---------------------------------------------------------------------------
def mc_block(u, ids, seed, n_mc=N_MC):
    """Draw N_MC simulated finishing orders from a single Gumbel block, per the
    verbatim recipe (section 5.1, mirrors predict_next.py lines 104-111): drivers
    placed in ASCENDING driver_id order (canonical, feed-independent) for the draw
    itself, result reordered back to the caller's `ids` column order. Returns
    `pos`, an (N_MC, D) int array; pos[:, i] is driver ids[i]'s simulated finishing
    position for each of the N_MC draws (0 = win). Every MC market reduces from
    this one array, so top-N marginals are mutually monotone by construction."""
    u = np.asarray(u, float)
    ids = np.asarray(ids, int)
    D = len(ids)
    sort_idx = np.argsort(ids)            # ascending driver_id order for the draw
    inv_sort_idx = np.argsort(sort_idx)   # inverts sort_idx: pos_sorted[:, inv] -> caller order
    u_sorted = u[sort_idx]

    rng = np.random.default_rng(seed)
    g = rng.gumbel(size=(n_mc, D))
    ranks = np.argsort(-(u_sorted[None, :] + g), axis=1)
    pos_sorted = np.empty((n_mc, D), dtype=np.int64)
    rows = np.arange(n_mc)[:, None]
    pos_sorted[rows, ranks] = np.arange(D)[None, :]
    return pos_sorted[:, inv_sort_idx]


def add_half(k, n_mc=N_MC):
    """Krichevsky-Trofimov add-half estimator: p_hat = (k + 0.5) / (N_MC + 1).
    Never 0, never 1 (section 5.2)."""
    return (k + 0.5) / (n_mc + 1)


def topN_single(pos, ids, N):
    """add-half p(fin_i <= N) for each driver, from the shared `pos` block."""
    k = (pos < N).sum(axis=0)
    p = add_half(k, pos.shape[0])
    return {int(d): float(p[i]) for i, d in enumerate(ids)}


def _member_cols(ids, member_ids):
    id_to_col = {int(d): i for i, d in enumerate(ids)}
    return [id_to_col[int(m)] for m in member_ids]


def count_topN_distribution(pos, ids, member_ids, N):
    """add-half pmf of the count of `member_ids` finishing <= N, over
    k = 0..len(member_ids). Shared machinery for topN_joint (a named driver
    `set`) and group_topN_count (a named `group`) -- both markets are "how many
    of this index subset land in the top N", which is the same statistic; only
    the caller-side label (set vs group) differs. "at least m" / "exactly m"
    are both derivable from this pmf without a second MC pass."""
    cols = _member_cols(ids, member_ids)
    n_mc = pos.shape[0]
    counts = (pos[:, cols] < N).sum(axis=1)
    return {k: float(add_half(int((counts == k).sum()), n_mc)) for k in range(len(cols) + 1)}


def mc_reliability(p_hat, n_mc=N_MC):
    """section 5.3: rarer-cell expected count c = min(N_MC*p, N_MC*(1-p)).
    decision_grade iff c >= 25; else tail_stand_down, with the raise-N
    suggestion the operator MAY use to promote it (never changes pinned N_MC)."""
    c = min(n_mc * p_hat, n_mc * (1.0 - p_hat))
    decision_grade = c >= MC_RELIABILITY_C
    n_prime = None if decision_grade else math.ceil(MC_RELIABILITY_C / min(p_hat, 1.0 - p_hat))
    return {
        'c': c,
        'decision_grade': decision_grade,
        'mc_se': math.sqrt(p_hat * (1.0 - p_hat) / n_mc),
        'tail_stand_down': not decision_grade,
        'n_prime_suggested': n_prime,
    }


# ---------------------------------------------------------------------------
# 4. price_race -- the section 2 signature
# ---------------------------------------------------------------------------
def _entry(p, method, mc_se=0.0, flags=()):
    e = {'p': float(p), 'method': method, 'mc_se': float(mc_se), 'flags': list(flags)}
    e.update(fair_odds(float(p)))
    return e


def _mc_entry(p, flags):
    rel = mc_reliability(p)
    all_flags = list(flags) + (['tail_stand_down'] if rel['tail_stand_down'] else [])
    e = _entry(p, 'mc', mc_se=rel['mc_se'], flags=all_flags)
    e['mc_reliability'] = rel
    return e


def price_race(utility, driver_ids, track_type, race_id,
               manufacturer_of=None, groups=None, sets=None,
               topN=(3, 5, 10), seed=None, n_mc=N_MC):
    """Pure function of a race's as-of utility vector + metadata -> PricedRace
    (a plain dict). See specs/pricing_layer.md section 2 for the contract.

    `seed` defaults to the section-5.5 per-race scheme [PRICING_SEED_BASE,
    race_id]; pass an explicit seed (e.g. the fixture's own pinned value) to
    override.
    """
    u = np.asarray(utility, float)
    ids = np.asarray(driver_ids, int)
    stand_down = (track_type == 'SS')
    ss_flags = ['SS_STAND_DOWN'] if stand_down else []

    if seed is None:
        seed = [PRICING_SEED_BASE, int(race_id)]

    # ---- analytic markets (section 3.1) ------------------------------------
    p_win = softmax(u)
    win = {int(d): _entry(p_win[i], 'analytic', flags=ss_flags) for i, d in enumerate(ids)}

    h2h_p = h2h_matrix(u)
    h2h = {
        int(di): {
            int(dj): _entry(h2h_p[i, j], 'analytic', flags=ss_flags)
            for j, dj in enumerate(ids) if j != i
        }
        for i, di in enumerate(ids)
    }

    group_bestof_out = {}
    for gi, G in enumerate(groups or []):
        probs = group_bestof(u, ids, G)
        group_bestof_out[gi] = {d: _entry(p, 'analytic', flags=ss_flags) for d, p in probs.items()}

    mfr_win_p, mfr_bestof_p = mfr_markets(u, ids, manufacturer_of or {})
    mfr_win = {m: _entry(p, 'analytic', flags=ss_flags) for m, p in mfr_win_p.items()}
    mfr_bestof = {m: _entry(p, 'analytic', flags=ss_flags) for m, p in mfr_bestof_p.items()}

    # ---- one pinned Gumbel block feeds every MC market (section 3.2) ------
    pos = mc_block(u, ids, seed, n_mc=n_mc)

    topN_single_out = {}
    for N in topN:
        p_hat = topN_single(pos, ids, N)
        topN_single_out[N] = {d: _mc_entry(p, ss_flags) for d, p in p_hat.items()}

    topN_joint_out = {}
    for si, S in enumerate(sets or []):
        for N in topN:
            pmf = count_topN_distribution(pos, ids, S, N)
            topN_joint_out[(si, N)] = {k: _mc_entry(p, ss_flags) for k, p in pmf.items()}

    group_topN_count_out = {}
    for gi, G in enumerate(groups or []):
        for N in topN:
            pmf = count_topN_distribution(pos, ids, G, N)
            group_topN_count_out[(gi, N)] = {k: _mc_entry(p, ss_flags) for k, p in pmf.items()}

    # ---- section 4 point 6: analytic p_win vs MC p(fin=1), reported ONLY --
    p_win_mc = topN_single(pos, ids, 1)
    crosscheck = {}
    for i, d in enumerate(ids):
        pa, pm = float(p_win[i]), p_win_mc[int(d)]
        pbar = 0.5 * (pa + pm)
        tol = 4.0 * math.sqrt(2.0 * pbar * (1.0 - pbar) / n_mc)
        crosscheck[int(d)] = {'p_analytic': pa, 'p_mc': pm, 'diff': pa - pm, 'tol': tol,
                               'within_tol': abs(pa - pm) <= tol}

    return {
        'race_id': int(race_id) if race_id is not None else None,
        'track_type': track_type,
        'stand_down': stand_down,
        'seed': list(seed),
        'n_mc': n_mc,
        'win': win,
        'h2h': h2h,
        'group_bestof': group_bestof_out,
        'mfr_win': mfr_win,
        'mfr_bestof': mfr_bestof,
        'topN_single': topN_single_out,
        'topN_joint': topN_joint_out,
        'group_topN_count': group_topN_count_out,
        'crosscheck_win_vs_mc': crosscheck,
        'label': 'raw-model implied (known underconfident)',
    }


def to_jsonable(priced_race):
    """JSON-safe copy of a PricedRace: tuple keys (topN_joint / group_topN_count
    are keyed (set_or_group_index, N)) become 'idx:N' strings; everything else
    round-trips through json natively (int dict keys are stringified by json
    itself). Used by the fixture writer and gate_pricing.py's comparisons."""
    def conv(v):
        if isinstance(v, dict):
            out = {}
            for k, vv in v.items():
                key = f'{k[0]}:{k[1]}' if isinstance(k, tuple) else k
                out[key] = conv(vv)
            return out
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return conv(priced_race)
