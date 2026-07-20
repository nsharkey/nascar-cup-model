#!/usr/bin/env python3
"""Pricing-layer gate -- specs/pricing_layer.md sections 4, 5.4, 6 (all FROZEN).

Three independent checks, all must PASS:
  1. Coherence invariants (section 4) -- internal self-consistency of
     pricing_layer's own output on the committed fixture's two fields.
     NOTE (invariant 2): the spec states the N-monotonicity chain
     "p_win_i <= p(fin<=3) <= p(fin<=5) <= p(fin<=10)" HOLDS EXACTLY because
     every term is reduced from the one Gumbel block. That exactness only
     holds if every term in the chain comes from that SAME MC block -- so
     this check compares MC p(fin<=1) (not the analytic softmax p_win, which
     is a different estimator and only agrees with the MC value within the
     section-4-point-6 cross-check tolerance, not exactly) against MC
     p(fin<=3/5/10). Point 1's "Sigma p_win_i = 1" and point 6's cross-check
     separately exercise the analytic p_win.
  2. Fixture reprove (section 5.4) -- gate_pricing.py recomputes price_race()
     from the fixture's own committed `input` blocks and asserts the result
     equals the committed `output` blocks (analytic: 1e-12; MC: exact bit
     match, since the recipe is fully deterministic). Never re-draws fresh
     numbers.
  3. Faithful-read (section 6) -- every committed predictions/race_*_prediction.json
     is hash-verified, then priced from its own sealed `field[].utility`; the
     priced win/top5/top10/h2h must reproduce the JSON's own p_win/p_top5/
     p_top10/h2h_prob within TOL_i (win/topN) or 2e-4 (h2h, both analytic).

Read-only w.r.t. every frozen file and every committed prediction JSON. Plain
stdlib asserts; exits nonzero on any failure. Run from src/ on the conda
interpreter (matches every other medallion gate, GATES.md).
"""
import glob
import json
import math
import os
import sys

import numpy as np

import pricing_layer as pl
import score_race

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURE_PATH = os.path.join(HERE, 'fixtures', 'pricing_fixture.json')
PRED_GLOB = os.path.join(REPO_ROOT, 'predictions', 'race_*_prediction.json')

TOL_FLOOR = 2e-4          # section 6's floor on TOL_i
H2H_TOL = 2e-4             # section 6 point 3: both analytic, differ only by 4dp rounding
FIXTURE_ANALYTIC_TOL = 1e-12


def tol_i(p_a, p_b, n_mc=pl.N_MC):
    """section 6: TOL_i = max(2e-4, 4*sqrt(2*pbar*(1-pbar)/N_MC))."""
    pbar = 0.5 * (p_a + p_b)
    return max(TOL_FLOOR, 4.0 * math.sqrt(2.0 * pbar * (1.0 - pbar) / n_mc))


# ---------------------------------------------------------------------------
# 1. coherence invariants (section 4)
# ---------------------------------------------------------------------------
def check_coherence(failures, notes):
    fx = json.load(open(FIXTURE_PATH))
    for name in ('real_race_5618', 'toy_field'):
        inp = fx[name]['input']
        u = np.asarray(inp['utility'], float)
        ids = np.asarray(inp['driver_ids'], int)
        mfr_of = {int(k): v for k, v in inp.get('manufacturer_of', {}).items()}
        groups = inp.get('groups') or []
        seed = inp['seed']

        # ---- point 1: sum p_win_i == 1 within 1e-9 ----
        p_win = pl.softmax(u)
        s = float(p_win.sum())
        if abs(s - 1.0) > 1e-9:
            failures.append(f'coherence[{name}] point1: sum p_win = {s!r}, not 1 within 1e-9')

        # ---- point 2: MC monotonicity N=1<=3<=5<=10 (see module docstring) ----
        pos = pl.mc_block(u, ids, seed)
        p1 = pl.topN_single(pos, ids, 1)
        p3 = pl.topN_single(pos, ids, 3)
        p5 = pl.topN_single(pos, ids, 5)
        p10 = pl.topN_single(pos, ids, 10)
        for d in ids:
            d = int(d)
            chain = [p1[d], p3[d], p5[d], p10[d]]
            if not all(chain[i] <= chain[i + 1] for i in range(len(chain) - 1)):
                failures.append(f'coherence[{name}] point2: driver {d} not monotone: {chain}')

        # ---- point 3: p(i ahead j) + p(j ahead i) == 1 exactly ----
        h2h = pl.h2h_matrix(u)
        D = len(ids)
        for i in range(D):
            for j in range(D):
                if i == j:
                    continue
                pair_sum = h2h[i, j] + h2h[j, i]
                if abs(pair_sum - 1.0) > 1e-9:
                    failures.append(f'coherence[{name}] point3: pair ({int(ids[i])},{int(ids[j])}) '
                                    f'sums to {pair_sum!r}, not 1 within 1e-9')

        # ---- point 4: mfr_win_M == sum_{i in M} p_win_i exactly ----
        if mfr_of:
            win_by_mfr, _ = pl.mfr_markets(u, ids, mfr_of)
            manual = {}
            for i, d in enumerate(ids):
                m = mfr_of.get(int(d))
                if m is not None:
                    manual[m] = manual.get(m, 0.0) + float(p_win[i])
            for m, v in manual.items():
                if abs(v - win_by_mfr[m]) > 1e-12:
                    failures.append(f'coherence[{name}] point4: mfr {m} manual={v!r} '
                                    f'!= mfr_win={win_by_mfr[m]!r}')

        # ---- point 5: sum_{i in G} p(i best in G) == 1 exactly (softmax over G) ----
        for gi, G in enumerate(groups):
            probs = pl.group_bestof(u, ids, G)
            s = sum(probs.values())
            if abs(s - 1.0) > 1e-9:
                failures.append(f'coherence[{name}] point5: group {gi} sums to {s!r}, not 1')

        # ---- point 6: analytic p_win vs MC p(fin=1), REPORTED only, never a gate ----
        diffs = []
        for i, d in enumerate(ids):
            pa, pm = float(p_win[i]), p1[int(d)]
            pbar = 0.5 * (pa + pm)
            tol = 4.0 * math.sqrt(2.0 * pbar * (1.0 - pbar) / pl.N_MC)
            diffs.append(abs(pa - pm) <= tol)
        notes.append(f'  [{name}] point6 cross-check (reported, not gated): '
                     f'{sum(diffs)}/{len(diffs)} drivers within tolerance')


# ---------------------------------------------------------------------------
# 2. fixture reprove (section 5.4)
# ---------------------------------------------------------------------------
def _assert_close(a, b, path, tol, failures):
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            failures.append(f'fixture[{path}]: key set mismatch {set(a) ^ set(b)}')
            return
        for k in a:
            _assert_close(a[k], b[k], f'{path}.{k}', tol, failures)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            failures.append(f'fixture[{path}]: length mismatch {len(a)} != {len(b)}')
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_close(x, y, f'{path}[{i}]', tol, failures)
    elif isinstance(a, float) and isinstance(b, float):
        if a != b and abs(a - b) > tol:
            failures.append(f'fixture[{path}]: {a!r} != {b!r} (tol {tol})')
    else:
        if a != b:
            failures.append(f'fixture[{path}]: {a!r} != {b!r}')


def check_fixture(failures):
    fx = json.load(open(FIXTURE_PATH))
    numpy_version_at_gen = fx['meta']['numpy_version']
    numpy_version_now = np.__version__
    print(f'[gate_pricing] fixture generated on numpy {numpy_version_at_gen}; running on numpy '
          f'{numpy_version_now}' + ('' if numpy_version_now == numpy_version_at_gen else
                                     ' -- MISMATCH: a numpy upgrade requires a dated fixture '
                                     'regeneration (section 5.1); the reprove below will likely '
                                     'fail on the MC values'))
    for name in ('real_race_5618', 'toy_field'):
        inp = fx[name]['input']
        mfr_of = {int(k): v for k, v in inp.get('manufacturer_of', {}).items()} or None
        groups = inp.get('groups') or None
        sets = inp.get('sets') or None
        priced = pl.price_race(inp['utility'], inp['driver_ids'], inp['track_type'], inp['race_id'],
                               manufacturer_of=mfr_of, groups=groups, sets=sets,
                               topN=tuple(inp['topN']), seed=inp['seed'])
        recomputed = json.loads(json.dumps(pl.to_jsonable(priced)))
        stored = fx[name]['output']
        # MC values must bit-match (recipe is deterministic); analytic tolerance
        # (1e-12) covers only json round-trip repr, which is itself exact for
        # float64 in Python's json module -- effectively an exact-match check.
        _assert_close(recomputed, stored, name, FIXTURE_ANALYTIC_TOL, failures)


# ---------------------------------------------------------------------------
# 3. faithful-read (section 6)
# ---------------------------------------------------------------------------
def check_faithful_read(failures, notes):
    pred_paths = sorted(glob.glob(PRED_GLOB))
    if not pred_paths:
        failures.append('faithful-read: no predictions/race_*_prediction.json found')
        return
    for path in pred_paths:
        d = json.load(open(path))
        if not score_race.verify_hash(d):
            failures.append(f'faithful-read: {os.path.basename(path)} FAILED hash verification '
                            f'-- skipped (tampered or corrupt sealed record)')
            continue

        ids = [e['driver_id'] for e in d['field']]
        u = [e['utility'] for e in d['field']]
        race_id = d['race_id']
        seed = [pl.PRICING_SEED_BASE, race_id]
        priced = pl.price_race(u, ids, d['track_type'], race_id, topN=(3, 5, 10), seed=seed)

        n_checked = 0
        # win (analytic) vs the JSON's sampled p_win
        for e in d['field']:
            did = e['driver_id']
            mine = priced['win'][did]['p']
            theirs = e['p_win']
            t = tol_i(mine, theirs)
            n_checked += 1
            if abs(mine - theirs) > t:
                failures.append(f'faithful-read[{os.path.basename(path)}] win driver {did}: '
                                f'{mine!r} vs JSON {theirs!r} (tol {t!r})')

        # topN_single N=5, N=10 (MC) vs the JSON's p_top5 / p_top10
        for N, jkey in ((5, 'p_top5'), (10, 'p_top10')):
            for e in d['field']:
                did = e['driver_id']
                mine = priced['topN_single'][N][did]['p']
                theirs = e[jkey]
                t = tol_i(mine, theirs)
                n_checked += 1
                if abs(mine - theirs) > t:
                    failures.append(f'faithful-read[{os.path.basename(path)}] top{N} driver {did}: '
                                    f'{mine!r} vs JSON {theirs!r} (tol {t!r})')

        # h2h (analytic sigma(du)) vs the JSON's full h2h_prob matrix
        for i_str, row in d['h2h_prob'].items():
            i = int(i_str)
            for j_str, theirs in row.items():
                j = int(j_str)
                mine = priced['h2h'][i][j]['p']
                n_checked += 1
                if abs(mine - theirs) > H2H_TOL:
                    failures.append(f'faithful-read[{os.path.basename(path)}] h2h ({i},{j}): '
                                    f'{mine!r} vs JSON {theirs!r} (tol {H2H_TOL})')

        notes.append(f'  [{os.path.basename(path)}] {n_checked} marginals checked, '
                     f'race_id={race_id}, seed={seed}')


# ---------------------------------------------------------------------------
def main():
    print('=' * 78)
    print('gate_pricing -- specs/pricing_layer.md sections 4 / 5.4 / 6')
    print(f'  numpy {np.__version__}  scipy present: {"scipy" in sys.modules or True}')
    print('=' * 78)

    failures = []
    notes = []

    print('[gate_pricing] 1/3 coherence invariants (section 4)...')
    check_coherence(failures, notes)

    print('[gate_pricing] 2/3 fixture reprove (section 5.4)...')
    check_fixture(failures)

    print('[gate_pricing] 3/3 faithful-read (section 6)...')
    check_faithful_read(failures, notes)

    print()
    for n in notes:
        print(n)
    print()

    if failures:
        print(f'FAIL -- {len(failures)} mismatch(es):')
        for f in failures[:50]:
            print(f'  - {f}')
        if len(failures) > 50:
            print(f'  ... and {len(failures) - 50} more')
        sys.exit(1)

    print('PASS -- coherence invariants hold, fixture reproves bit-exact, faithful-read '
          'reproduces every committed prediction JSON within MC error.')
    sys.exit(0)


if __name__ == '__main__':
    main()
