#!/usr/bin/env python3
"""Calibration backtest -- specs/calibration_backtest.md (FROZEN, section 10's checklist,
including the 2026-07-20 terminal-only amendment). Grades the frozen PL model's probability
readout (via M2's src/pricing_layer.py) against realized results on three strata:

  IN-SAMPLE  -- ~2022-2026 walk-forward-scored races, a development smoke test, barred from
               any decision or from fitting a recalibration map (section 2).
  2026-OOS   -- the 2026 subset of IN-SAMPLE, a peeked secondary confirmation (S6).
  FORWARD    -- race 5618 onward, via the sealed prediction JSON + frozen results snapshot;
               N=1 today. The ONLY decision-grade stratum (section 2), and per the terminal-only
               amendment its primary verdict is computed and reported at every look but a
               CALIBRATED-SKILL/NULL verdict may only be DECLARED at the terminal look
               (K>=60 non-SS forward races, or 2028-02-15, whichever first).

Zero design judgment: every number below is either pinned directly in the spec or a mechanical
consequence of bridging two already-frozen interfaces. Two implementation choices were required
to do that bridging (walkforward.run's collect_preds hook does not expose driver_id, and the
forward stream is priced differently from the backtest stream); both are resolved here on
grounds recorded in this docstring and in the RESULT block, not escalated to the owner:

  1. Baseline replication runs against `data/anchors/races_parsed_anchor_20260719.pkl` (the SAME
     frozen anchor gate_gold.py's R0 uses, reusing gg.load_anchor/run_reference/headline_trio
     verbatim) rather than the live, weekly-growing `races_parsed.pkl` -- the spec's own words
     ("must reproduce THE FROZEN ANCHOR") name this exact artifact. The live pickle now includes
     race 5618 itself (completed and scored the day after this session's prior step), so running
     against it would no longer reproduce 0.447 exactly (a 21st 2026 race would enter that mean) --
     using the anchor is the only reading that keeps the assert meaningful and deterministic.
  2. walkforward.run(collect_preds=...) returns (u, actual, track_type, date) tuples with no
     driver_id, so a second, minimal replay (`replay_elig_sequence`) reproduces ONLY the
     eligibility/ordering bookkeeping (never the PL fit itself) against the same RACES object, to
     recover the driver_id list each tuple's u/actual are aligned to -- verified byte-for-byte
     (same length, same date, same actual-vs-recomputed-finish) against all 128 collected races
     before use. This is the same "faithful side-channel replay" pattern gate_gold.py's own R2/R3
     already use to recover per-driver identity from this engine without editing it.

Forward-stream markets are read directly from the sealed prediction JSON's own p_win/p_top10/
h2h_prob (never re-priced via price_race) -- this is what specs/pricing_layer.md section 2 point 1
and specs/calibration_backtest.md section 1's forward-stream definition both specify ("the sealed
h2h_prob... from the JSON"; "adding no new numbers to the sealed forward record"). price_race is
used only for the IN-SAMPLE/2026-OOS strata, which have no existing sealed JSON.

Run from src/ on the conda interpreter (matches every other medallion gate). No network. No change
to predict_next.py / walkforward.py / scores_log.csv.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np

import gate_gold as gg
import market_benchmark as mb
import pricing_layer as pl
import score_race as sr
from walkforward import MY_TYPE

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
REPORT_PATH = os.path.join(REPO_ROOT, 'report', 'CALIBRATION_BACKTEST.md')

# ---------------------------------------------------------------------------
# pinned constants (spec sections 3, 6; terminal-only amendment)
# ---------------------------------------------------------------------------
B_CALIB = 10_000
CALIB_SEED = 20260720
K_FLOOR = 20
DELTA_PRAC = 0.01
N_BINS = 10
ALPHA_SEC = 0.05 / 6
TERMINAL_K = 60
TERMINAL_CALENDAR = '2028-02-15'

FORWARD_RACE_ID = 5618
FORWARD_YEAR = 2026
FORWARD_DATE = '2026-07-19'

ALL_TTYPES = ('SS', 'INT', 'SHORT', 'ROAD', 'OTHER')
NONSS_TTYPES = ('INT', 'SHORT', 'ROAD', 'OTHER')  # everything MY_TYPE emits except SS


def clip(p):
    return pl.score_floor(float(p))


# ---------------------------------------------------------------------------
# step (a): baseline replication assert -- MUST pass before any calibration number is read
# ---------------------------------------------------------------------------
def assert_baseline_replication():
    anchor_path, anchor_races = gg.load_anchor()
    preds_bt, preds_oos = {}, {}
    bt_rows, oos_rows = gg.run_reference(anchor_races, collect_preds_bt=preds_bt,
                                          collect_preds_oos=preds_oos)
    trio = gg.headline_trio(bt_rows, oos_rows)
    ok = (round(trio[0], 3) == gg.EXPECTED_BACKTEST and round(trio[1], 3) == gg.EXPECTED_NONSS
          and round(trio[2], 3) == gg.EXPECTED_OOS)
    print(f'[calibration_backtest] baseline replication: backtest={trio[0]:.3f} '
          f'non-SS={trio[1]:.3f} 2026-OOS={trio[2]:.3f} '
          f'(expected {gg.EXPECTED_BACKTEST}/{gg.EXPECTED_NONSS}/{gg.EXPECTED_OOS})')
    if not ok:
        sys.exit('[calibration_backtest] BASELINE REPLICATION FAILED -- stopping before any '
                  'calibration number is read (spec section 1). This is a STOP-and-flag '
                  'condition, not a modeling question.')
    print('[calibration_backtest] baseline replication PASS.')
    return anchor_path, anchor_races, preds_oos, trio


# ---------------------------------------------------------------------------
# step (b) helper: recover driver_id per scored race (see docstring point 2)
# ---------------------------------------------------------------------------
def replay_elig_sequence(races, years, pace_key='pace_med85', burn=15, min_hist=5, min_drv=20):
    """Mirrors ONLY walkforward.run()'s eligibility/history bookkeeping (never the PL fit) to
    recover, for each race that would receive a collect_preds entry, the ordered driver_id list
    its u/actual arrays are aligned to. Verified byte-identical against the real run's output
    before use (see calling code)."""
    sample = [r for r in races if r['year'] in years]
    hf, hp = {}, {}
    qualified_count = 0
    out = []
    for idx, race in enumerate(sample):
        drivers = race['drivers']
        if idx >= burn:
            elig = [d for d in drivers
                    if d in hf and len(hf[d]) >= min_hist and drivers[d].get(pace_key) is not None]
            if len(elig) >= min_drv:
                if qualified_count >= 20:      # mirrors walkforward.run's `len(Xs) >= 20` gate
                    out.append((race['date'][:10], race['rid'], list(elig)))
                qualified_count += 1
        for d, v in drivers.items():
            hf.setdefault(d, []).append(v['finish'])
            if v.get(pace_key) is not None:
                hp.setdefault(d, []).append(v[pace_key])
    return out


def verify_elig_replay(preds_fpts, replay, races_by_rid):
    """Byte-for-byte proof the replica's driver_id ordering matches collect_preds' opaque u/actual
    arrays: same count, same date, same length, and the elig-derived finish vector equals `actual`
    exactly, for every one of the 128 races."""
    assert len(preds_fpts) == len(replay), (
        f'replay count mismatch: collect_preds={len(preds_fpts)} replay={len(replay)}')
    for i, ((u, actual, tt, date), (rdate, rid, elig)) in enumerate(zip(preds_fpts, replay)):
        assert date == rdate, f'race {i}: date mismatch {date} vs {rdate}'
        assert len(u) == len(elig), f'race {i} {date}: length mismatch {len(u)} vs {len(elig)}'
        race = races_by_rid[rid]
        real_finish = np.array([race['drivers'][d]['finish'] for d in elig], float)
        assert np.array_equal(real_finish, actual), f'race {i} {date} rid={rid}: finish order mismatch'


# ---------------------------------------------------------------------------
# step (b): as-of Bradley-Terry marginal baseline (spec section 3)
# ---------------------------------------------------------------------------
def build_bt_asof(races, typology):
    """s_d = as-of lifetime pairwise-win fraction over prior non-SS races; <5 prior non-SS races
    -> s_d = 0.5 (spec section 3). Returns (snapshots keyed by race rid -> {driver_id: s_d as of
    that race, i.e. using only races strictly before it}, final (races_count, wins, total) state
    for use as the forward race's prior history)."""
    races_count, wins, total = {}, {}, {}
    snapshots = {}
    for race in races:
        tt = typology.get(race['track'], 'UNIQ')
        drivers = race['drivers']
        ids = list(drivers.keys())
        snap = {d: s_d_of(d, races_count, wins, total) for d in ids}
        snapshots[race['rid']] = snap
        if tt != 'SS':
            finishes = {d: drivers[d]['finish'] for d in ids}
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    fa, fb = finishes[a], finishes[b]
                    if fa == fb:
                        continue                # finish tie -- no update, mirrors scoring doctrine
                    total[a] = total.get(a, 0) + 1
                    total[b] = total.get(b, 0) + 1
                    if fa < fb:
                        wins[a] = wins.get(a, 0) + 1
                    else:
                        wins[b] = wins.get(b, 0) + 1
            for d in ids:
                races_count[d] = races_count.get(d, 0) + 1
    return snapshots, (races_count, wins, total)


def s_d_of(d, races_count, wins, total):
    rc = races_count.get(d, 0)
    if rc < 5:
        return 0.5
    w, t = wins.get(d, 0), total.get(d, 0)
    return 0.5 if t == 0 else w / t


def p_base_h2h(s_lo, s_hi):
    return 0.5 if s_lo == s_hi else s_lo / (s_lo + s_hi)


# ---------------------------------------------------------------------------
# step (c)/(d): price + grade the walk-forward-derived races (IN-SAMPLE + 2026-OOS pool)
# ---------------------------------------------------------------------------
def price_and_grade_walkforward_races(preds_fpts, replay, bt_snapshots):
    """Returns a flat list of unit records (dicts), one per graded H2H pair / win / top10 slot,
    across every race in the combined 2022-2026 walk-forward pool (128 races). `stratum` is always
    'in_sample'; the 2026-OOS cut is derived later by filtering on year==2026 (spec section 2: 2026
    -OOS is an explicit SUBSET of the same sweep, not a separate run)."""
    records = []
    for (u_raw, actual, tt, date), (rdate, rid, elig) in zip(preds_fpts, replay):
        assert date == rdate
        n = len(elig)
        # walkforward.run()'s collect_preds u is fit on -X (see its own comment: "w fit on -X, so
        # u aligns with finish position") -- i.e. HIGHER u = WORSE finish, confirmed empirically
        # (spearmanr(u, actual) > 0, matching the positive rho_PL_fpts the engine itself reports).
        # pricing_layer/predict_next.py's convention is the opposite ("higher = better";
        # predict_next.py computes `util = -(X @ w)`), so u must be negated before pricing.
        u = -u_raw
        priced = pl.price_race(u, elig, tt, rid, topN=(3, 5, 10))
        idx_of = {d: i for i, d in enumerate(elig)}
        snap = bt_snapshots[rid]
        year = int(date[:4])

        # ---- h2h ----
        for i in range(n):
            for j in range(i + 1, n):
                a, b = elig[i], elig[j]
                lo, hi = (a, b) if a < b else (b, a)
                f_lo, f_hi = actual[idx_of[lo]], actual[idx_of[hi]]
                if f_lo == f_hi:
                    continue
                p_model = clip(priced['h2h'][lo][hi]['p'])
                p_base = clip(p_base_h2h(snap[lo], snap[hi]))
                outcome = 1.0 if f_lo < f_hi else 0.0
                records.append(dict(stratum='in_sample', market='h2h', ttype=tt, year=year,
                                     race_key=(date, rid), p_model=p_model, p_base=p_base,
                                     outcome=outcome))

        # ---- win ----
        for d in elig:
            p_model = clip(priced['win'][d]['p'])
            p_base = clip(1.0 / n)
            outcome = 1.0 if actual[idx_of[d]] == 1 else 0.0
            records.append(dict(stratum='in_sample', market='win', ttype=tt, year=year,
                                 race_key=(date, rid), p_model=p_model, p_base=p_base,
                                 outcome=outcome))

        # ---- top10 (MC; exclude tail_stand_down per pricing_layer section 5.3) ----
        for d in elig:
            entry = priced['topN_single'][10][d]
            if not entry['mc_reliability']['decision_grade']:
                continue
            p_model = entry['p']                       # MC add-half; already never 0/1
            p_base = clip(min(10, n) / n)
            outcome = 1.0 if actual[idx_of[d]] <= 10 else 0.0
            records.append(dict(stratum='in_sample', market='top10', ttype=tt, year=year,
                                 race_key=(date, rid), p_model=p_model, p_base=p_base,
                                 outcome=outcome))
    return records


# ---------------------------------------------------------------------------
# forward stream: sealed JSON + frozen snapshot, no re-pricing (docstring point above)
# ---------------------------------------------------------------------------
def load_forward_stream(bt_final_state):
    pred_path = os.path.join(sr.PREDICTIONS_DIR,
                              f'race_{FORWARD_RACE_ID}_{FORWARD_DATE}_prediction.json')
    d = json.load(open(pred_path))
    if not sr.verify_hash(d):
        sys.exit(f'[calibration_backtest] FORWARD STREAM hash verification FAILED for {pred_path} '
                  f'-- refusing to grade a possibly-tampered sealed record.')
    classified = mb.load_snapshot(FORWARD_YEAR, FORWARD_RACE_ID)
    if classified is None:
        sys.exit(f'[calibration_backtest] no frozen results snapshot for race {FORWARD_RACE_ID} '
                  f'-- forward stream has N=0 scored races today.')
    common = sr.common_set(d, classified)
    ids = common['common_ids']
    res_by_id = common['res_by_id']
    h2h_prob = d['h2h_prob']
    field_by_id = {f['driver_id']: f for f in d['field']}
    tt = d['track_type']
    n = len(ids)
    races_count, wins, total = bt_final_state

    records = []
    for i in range(n):
        for j in range(i + 1, n):
            lo, hi = ids[i], ids[j]
            f_lo = res_by_id[lo]['finishing_position']
            f_hi = res_by_id[hi]['finishing_position']
            if f_lo == f_hi:
                continue
            p_model = clip(h2h_prob[str(lo)][str(hi)])
            s_lo = s_d_of(lo, races_count, wins, total)
            s_hi = s_d_of(hi, races_count, wins, total)
            p_base = clip(p_base_h2h(s_lo, s_hi))
            outcome = 1.0 if f_lo < f_hi else 0.0
            records.append(dict(stratum='forward', market='h2h', ttype=tt, year=FORWARD_YEAR,
                                 race_key=(FORWARD_DATE, FORWARD_RACE_ID), p_model=p_model,
                                 p_base=p_base, outcome=outcome))

    for did in ids:
        f = field_by_id[did]
        p_model = clip(f['p_win'])
        p_base = clip(1.0 / n)
        outcome = 1.0 if res_by_id[did]['finishing_position'] == 1 else 0.0
        records.append(dict(stratum='forward', market='win', ttype=tt, year=FORWARD_YEAR,
                             race_key=(FORWARD_DATE, FORWARD_RACE_ID), p_model=p_model,
                             p_base=p_base, outcome=outcome))
        p10 = f['p_top10']
        rel = pl.mc_reliability(p10)
        if rel['decision_grade']:
            p_base10 = clip(min(10, n) / n)
            outcome10 = 1.0 if res_by_id[did]['finishing_position'] <= 10 else 0.0
            records.append(dict(stratum='forward', market='top10', ttype=tt, year=FORWARD_YEAR,
                                 race_key=(FORWARD_DATE, FORWARD_RACE_ID), p_model=p10,
                                 p_base=p_base10, outcome=outcome10))
    return records, dict(n=n, ttype=tt, unscored=common['unscored_ids'],
                          unpredicted=common['unpredicted_ids'])


# ---------------------------------------------------------------------------
# scoring primitives
# ---------------------------------------------------------------------------
def brier_of(records):
    if not records:
        return dict(b_model=float('nan'), b_base=float('nan'), bss=float('nan'), n=0)
    arr = np.array([(r['p_model'], r['p_base'], r['outcome']) for r in records], float)
    pm, pb, o = arr[:, 0], arr[:, 1], arr[:, 2]
    b_model = float(np.mean((pm - o) ** 2))
    b_base = float(np.mean((pb - o) ** 2))
    skill = 1 - b_model / b_base if b_base > 0 else float('nan')
    return dict(b_model=b_model, b_base=b_base, bss=skill, n=len(arr))


def logloss_of(records):
    if not records:
        return dict(ll_model=float('nan'), ll_base=float('nan'), ll_skill=float('nan'), n=0)
    arr = np.array([(r['p_model'], r['p_base'], r['outcome']) for r in records], float)
    pm, pb, o = arr[:, 0], arr[:, 1], arr[:, 2]
    ll_model = float(-np.mean(o * np.log(pm) + (1 - o) * np.log(1 - pm)))
    ll_base = float(-np.mean(o * np.log(pb) + (1 - o) * np.log(1 - pb)))
    skill = 1 - ll_model / ll_base if ll_base > 0 else float('nan')
    return dict(ll_model=ll_model, ll_base=ll_base, ll_skill=skill, n=len(arr))


def reliability_bins(records, n_bins=N_BINS):
    if not records:
        return dict(bins=[], reliability=float('nan'), resolution=float('nan'),
                     uncertainty=float('nan'))
    arr = np.array([(r['p_model'], r['outcome']) for r in records], float)
    order = np.argsort(arr[:, 0])
    arr = arr[order]
    n = len(arr)
    edges = np.linspace(0, n, n_bins + 1).astype(int)
    obar = float(arr[:, 1].mean())
    bins, reliability, resolution = [], 0.0, 0.0
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if hi <= lo:
            continue
        chunk = arr[lo:hi]
        mean_pred = float(chunk[:, 0].mean())
        obs_freq = float(chunk[:, 1].mean())
        cnt = len(chunk)
        bins.append(dict(n=cnt, mean_pred=mean_pred, obs_freq=obs_freq))
        reliability += cnt * (mean_pred - obs_freq) ** 2
        resolution += cnt * (obs_freq - obar) ** 2
    reliability /= n
    resolution /= n
    uncertainty = obar * (1 - obar)
    return dict(bins=bins, reliability=reliability, resolution=resolution,
                uncertainty=uncertainty, obar=obar)


# ---------------------------------------------------------------------------
# race-clustered bootstrap (spec section 3; mechanics ported "verbatim in form" from
# specs/market_benchmark_decision_rule.md's calibration-guards amendment)
# ---------------------------------------------------------------------------
def race_clustered_bootstrap_bss(records, seed=CALIB_SEED, b=B_CALIB):
    """Pools per-race SUMS of squared error (never a mean of per-race BSS's), sorted ascending by
    (race_date, race_id) before grouping -- same pooling convention market_benchmark.py's resampling
    uses. Returns point BSS, K (contributing races), N (graded units), and the one-sided 95% lower/
    upper bounds (index 500 / 9500 of B=10000 ascending order statistics, mirroring
    market_benchmark.py's own [9500] convention)."""
    by_race = defaultdict(lambda: [0.0, 0.0, 0])
    for r in records:
        acc = by_race[r['race_key']]
        acc[0] += (r['p_model'] - r['outcome']) ** 2
        acc[1] += (r['p_base'] - r['outcome']) ** 2
        acc[2] += 1
    races = sorted(by_race)                      # ascending (race_date, race_id)
    K = len(races)
    if K == 0:
        return dict(bss=float('nan'), lower=float('nan'), upper=float('nan'), K=0, N=0)
    arr = np.array([by_race[rk] for rk in races], float)
    sum_model, sum_base, counts = arr[:, 0], arr[:, 1], arr[:, 2]
    N = int(counts.sum())
    point_bss = 1 - sum_model.sum() / sum_base.sum() if sum_base.sum() > 0 else float('nan')

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, K, size=(b, K))
    rs_model = sum_model[idx].sum(axis=1)
    rs_base = sum_base[idx].sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        rep_bss = 1 - rs_model / rs_base
    rep_sorted = np.sort(rep_bss)
    lower = float(rep_sorted[int(0.05 * b)])
    upper = float(rep_sorted[min(int(0.95 * b), b - 1)])
    return dict(bss=point_bss, lower=lower, upper=upper, K=K, N=N)


def race_clustered_bootstrap_llskill(records, seed=CALIB_SEED, b=B_CALIB):
    by_race = defaultdict(lambda: [0.0, 0.0, 0])
    for r in records:
        pm, pb, o = r['p_model'], r['p_base'], r['outcome']
        acc = by_race[r['race_key']]
        acc[0] += -(o * np.log(pm) + (1 - o) * np.log(1 - pm))
        acc[1] += -(o * np.log(pb) + (1 - o) * np.log(1 - pb))
        acc[2] += 1
    races = sorted(by_race)
    K = len(races)
    if K == 0:
        return dict(ll_skill=float('nan'), lower=float('nan'), upper=float('nan'), K=0, N=0)
    arr = np.array([by_race[rk] for rk in races], float)
    sum_model, sum_base, counts = arr[:, 0], arr[:, 1], arr[:, 2]
    N = int(counts.sum())
    point = 1 - sum_model.sum() / sum_base.sum() if sum_base.sum() > 0 else float('nan')

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, K, size=(b, K))
    rs_model = sum_model[idx].sum(axis=1)
    rs_base = sum_base[idx].sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        rep = 1 - rs_model / rs_base
    rep_sorted = np.sort(rep)
    lower = float(rep_sorted[int(0.05 * b)])
    upper = float(rep_sorted[min(int(0.95 * b), b - 1)])
    return dict(ll_skill=point, lower=lower, upper=upper, K=K, N=N)


# ---------------------------------------------------------------------------
# verdict (spec section 3, terminal-only amendment)
# ---------------------------------------------------------------------------
def terminal_look_reached(k_forward_nonss):
    import datetime
    today = datetime.date.today().isoformat()
    if k_forward_nonss >= TERMINAL_K:
        return True, f'K={k_forward_nonss} >= {TERMINAL_K}'
    if today >= TERMINAL_CALENDAR:
        return True, f'calendar backstop {TERMINAL_CALENDAR} reached'
    return False, None


def evaluate_primary(boot):
    """Per the terminal-only amendment: every look before the terminal look is UNDERPOWERED BY
    DEFINITION, regardless of K/bounds -- no interim look may declare CALIBRATED-SKILL or NULL."""
    triggered, why = terminal_look_reached(boot['K'])
    if not triggered:
        return 'UNDERPOWERED', f'interim look (terminal-only amendment) -- {why or "K < " + str(TERMINAL_K) + " and calendar not reached"}'
    if boot['K'] < K_FLOOR:
        return 'UNDERPOWERED', f"terminal look but K={boot['K']} < floor {K_FLOOR}"
    if boot['lower'] > 0 and boot['bss'] >= DELTA_PRAC:
        return 'CALIBRATED-SKILL', f"terminal look ({why}): lower={boot['lower']:.4f} > 0 and BSS={boot['bss']:.4f} >= {DELTA_PRAC}"
    if boot['upper'] < DELTA_PRAC:
        return 'NULL', f"terminal look ({why}): upper={boot['upper']:.4f} < {DELTA_PRAC}"
    return 'UNDERPOWERED', f'terminal look ({why}) but neither CALIBRATED-SKILL nor NULL condition met'


# ---------------------------------------------------------------------------
# filtering + per-stratum aggregation helpers
# ---------------------------------------------------------------------------
def subset(records, market=None, ttype=None, year=None, nonss=False):
    out = records
    if market is not None:
        out = [r for r in out if r['market'] == market]
    if year is not None:
        out = [r for r in out if r['year'] == year]
    if nonss:
        out = [r for r in out if r['ttype'] != 'SS']
    if ttype is not None:
        out = [r for r in out if r['ttype'] == ttype]
    return out


def per_type_brier(records, market, types=ALL_TTYPES):
    return {tt: brier_of(subset(records, market=market, ttype=tt)) for tt in types
            if subset(records, market=market, ttype=tt)}


def fit_reliability_line(bins):
    """Weighted least squares of observed frequency on mean predicted probability across the
    N_BINS points (weights = bin counts). Descriptive only (S3) -- documents over/under-confidence
    direction, feeds specs/recalibration.md later; never drives a verdict."""
    if len(bins) < 2:
        return None
    x = np.array([b['mean_pred'] for b in bins])
    y = np.array([b['obs_freq'] for b in bins])
    w = np.array([b['n'] for b in bins], float)
    xbar = np.average(x, weights=w)
    ybar = np.average(y, weights=w)
    cov = np.average((x - xbar) * (y - ybar), weights=w)
    var = np.average((x - xbar) ** 2, weights=w)
    if var == 0:
        return None
    slope = cov / var
    intercept = ybar - slope * xbar
    return dict(slope=float(slope), intercept=float(intercept))


def stratum_report(records, label, n_races, types=ALL_TTYPES):
    """Common per-stratum bundle: pooled-non-SS + per-type BSS for h2h/win/top10, plus reliability
    curves (bins + Murphy decomposition + fitted line) for h2h (pooled + per-type, section 5's dual
    mandate) and pooled reliability for win/top10 (section 6: both explicitly scoped 'pooled
    non-SS' in their own table row, so no per-type cut is taken for them -- see module docstring
    reasoning applied inline at call sites)."""
    out = dict(label=label, n_races=n_races)
    for market in ('h2h', 'win', 'top10'):
        pooled = subset(records, market=market, nonss=True)
        out[market] = dict(pooled_nonss=brier_of(pooled), per_type=per_type_brier(records, market, types))
    out['reliability'] = dict(
        h2h_pooled_nonss=reliability_bins(subset(records, market='h2h', nonss=True)),
        h2h_per_type={tt: reliability_bins(subset(records, market='h2h', ttype=tt))
                      for tt in types if subset(records, market='h2h', ttype=tt)},
        win_pooled_nonss=reliability_bins(subset(records, market='win', nonss=True)),
        top10_pooled_nonss=reliability_bins(subset(records, market='top10', nonss=True)),
    )
    out['reliability']['h2h_pooled_nonss']['line'] = fit_reliability_line(
        out['reliability']['h2h_pooled_nonss']['bins'])
    for tt, rel in out['reliability']['h2h_per_type'].items():
        rel['line'] = fit_reliability_line(rel['bins'])
    return out


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------
def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 'n/a'
    return f'{x:.{nd}f}'


def render_brier_row(tt, b):
    return f'| {tt} | {b["n"]} | {fmt(b["b_model"])} | {fmt(b["b_base"])} | {fmt(b["bss"])} |'


def render_bins_table(rel):
    if not rel['bins']:
        return '_(no data)_\n'
    lines = ['| bin | n | mean predicted | observed freq |', '|---|---|---|---|']
    for i, b in enumerate(rel['bins']):
        lines.append(f"| {i+1} | {b['n']} | {fmt(b['mean_pred'])} | {fmt(b['obs_freq'])} |")
    lines.append('')
    lines.append(f"Brier decomposition: reliability={fmt(rel['reliability'])}  "
                 f"resolution={fmt(rel['resolution'])}  uncertainty={fmt(rel['uncertainty'])}")
    if rel.get('line'):
        slope = rel['line']['slope']
        if slope > 1.05:
            direction = ('steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than '
                         'stated), matching the audit\'s known finding (sec. 7)')
        elif slope < 0.95:
            direction = 'shallower-than-1:1 == OVERCONFIDENCE (true rates less extreme than stated)'
        else:
            direction = 'approximately 1:1 -- no strong over/under-confidence signal'
        lines.append(f"Fitted reliability line (weighted OLS, obs ~ a + b*pred): "
                     f"slope={fmt(rel['line']['slope'])}  intercept={fmt(rel['line']['intercept'])}"
                     f"  ({direction})")
    return '\n'.join(lines) + '\n'


def render_stratum_section(s, ss_note=''):
    lines = [f"**N races contributing = {s['n_races']}**{ss_note}", '']
    for market, mkt_label in (('h2h', 'H2H'), ('win', 'Win'), ('top10', 'Top-10')):
        lines.append(f'#### {mkt_label} -- BSS = 1 - B_model/B_base')
        lines.append('| stratum | n | B_model | B_base | BSS |')
        lines.append('|---|---|---|---|---|')
        pooled = s[market]['pooled_nonss']
        lines.append(f"| pooled non-SS | {pooled['n']} | {fmt(pooled['b_model'])} | "
                     f"{fmt(pooled['b_base'])} | {fmt(pooled['bss'])} |")
        for tt in ALL_TTYPES:
            if tt in s[market]['per_type']:
                b = s[market]['per_type'][tt]
                flag = '  SS STAND-DOWN -- not actionable' if tt == 'SS' else ''
                lines.append(f"| {tt}{flag} | {b['n']} | {fmt(b['b_model'])} | "
                             f"{fmt(b['b_base'])} | {fmt(b['bss'])} |")
        lines.append('')
    lines.append('#### H2H reliability (pooled non-SS, 10 equal-mass bins)')
    lines.append(render_bins_table(s['reliability']['h2h_pooled_nonss']))
    lines.append('#### H2H reliability by track type')
    for tt in ALL_TTYPES:
        if tt in s['reliability']['h2h_per_type']:
            flag = ' (SS STAND-DOWN)' if tt == 'SS' else ''
            lines.append(f'##### {tt}{flag}')
            lines.append(render_bins_table(s['reliability']['h2h_per_type'][tt]))
    lines.append('#### Win reliability (pooled non-SS)')
    lines.append(render_bins_table(s['reliability']['win_pooled_nonss']))
    lines.append('#### Top-10 reliability (pooled non-SS)')
    lines.append(render_bins_table(s['reliability']['top10_pooled_nonss']))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# power triage + section-9 C-trigger split (fixed prose, section 7 / section 9)
# ---------------------------------------------------------------------------
POWER_TRIAGE_TEXT = """\
- **Decision-grade scope = pooled non-SS two-outcome markets only** -- the primary H2H (section 3)
  and the action-eligible secondary top-10 (S2). These accrue roughly one forward season to a
  verdict (K>=20 non-SS forward races reachable in that window; K>=60 needed for the terminal
  look per the 2026-07-20 amendment).
- **Descriptive-only until a separately pre-registered horizon extension:** win/group markets
  (~1 winner-event per race -- never decision-grade on the forward stream in a realistic horizon);
  all SS markets (near-noise per the audit, sections 5/7 -- stand-down, never a verdict);
  per-track-type stratified cells (~5-15 forward races per type over a season -- underpowered
  per-type).
- **Today's actual state:** K_forward_nonss = {k} non-SS forward race(s) against the K>=20 interim
  floor and the K>=60 terminal floor. At K={k}, every look -- interim or (if it were reached)
  terminal -- returns UNDERPOWERED by construction; this is the correct, pre-registered outcome at
  N=1, not a shortfall.
"""

TRIGGER_SPLIT_TEXT = """\
- **Non-SS tail (S5, win; thin top-3) -> ARMS F7 formulation-C trigger T1 -- but only on a
  documented finding, which a single race cannot establish.** T1 requires "a documented finding of
  systematic miscalibration in the non-SS tail markets"; with N=1 forward race there is no
  statistical basis to call today's win-market Brier decomposition a "finding" rather than noise.
  **T1 status today: NOT ARMED** (insufficient evidence -- one race). The forward win-market
  numbers above are reported for monitoring; whether they eventually arm T1 is a question for a
  later, better-powered look, not this one. Even if/when T1 arms, C stays gated/unbuilt until the
  owner elects to pull it with its own pre-registration (section 9).
- **SS miscalibration -> CONFIRMS the stand-down; NEVER a C-trigger.** The forward stream has
  {ss_n} SS pairs graded to date (race 5618 was SHORT, not SS) -- no SS evidence exists yet in the
  forward stream. The in-sample/2026-peeked SS numbers above are historical/dev-only and, per
  section 9, would confirm the pre-registered stand-down even if poorly calibrated -- they are
  never routed to C regardless of what they show.
"""


def build_power_triage(k_forward_nonss):
    return POWER_TRIAGE_TEXT.format(k=k_forward_nonss)


def build_trigger_split(forward_ss_n):
    return TRIGGER_SPLIT_TEXT.format(ss_n=forward_ss_n)


def write_report(res):
    import datetime
    import platform
    today = datetime.date.today().isoformat()
    p = res['primary']
    sec = res['secondary']
    fm = res['forward_meta']

    lines = []
    lines.append(f'# Calibration backtest -- results ({today})')
    lines.append('')
    lines.append('Produced by `src/calibration_backtest.py` per `specs/calibration_backtest.md` '
                 'section 10\'s checklist (M3). Governs no frozen file; no change to '
                 '`predict_next.py` / `walkforward.py` / `scores_log.csv`.')
    lines.append('')
    lines.append('## Environment')
    lines.append(f'- interpreter: {platform.python_version()} ({sys.executable})')
    lines.append(f'- numpy {np.__version__}')
    lines.append(f'- anchor: `{res["anchor_path"]}`')
    lines.append('')
    lines.append('## Baseline replication (must pass before any calibration number, section 1)')
    lines.append(f'- backtest={res["trio"][0]:.3f}  non-SS={res["trio"][1]:.3f}  '
                 f'2026-OOS={res["trio"][2]:.3f}  (expected 0.413 / 0.476 / 0.447) -- **PASS**')
    lines.append('')

    lines.append('## SECTION 3 -- the ONE primary decision')
    lines.append('H2H Brier skill score vs the as-of Bradley-Terry marginal baseline, forward '
                 'stream, non-SS pairs, pooled. Race-clustered bootstrap '
                 f'(B_CALIB={B_CALIB}, CALIB_SEED={CALIB_SEED}).')
    lines.append('')
    lines.append(f"- K (non-SS forward races) = {p['boot']['K']}   N (graded pairs) = {p['boot']['N']}")
    lines.append(f"- point BSS = {fmt(p['boot']['bss'])}   95% one-sided lower = {fmt(p['boot']['lower'])}"
                 f"   upper = {fmt(p['boot']['upper'])}")
    lines.append(f"- terminal look reached: {p['terminal_triggered']} ({p['terminal_why'] or 'not yet'})")
    lines.append(f"- **VERDICT: {p['verdict']}**  -- {p['verdict_why']}")
    lines.append('')
    lines.append('Per the 2026-07-20 terminal-only amendment, this is an interim look (K << 60); '
                 'the primary verdict is computed and reported at every look but CALIBRATED-SKILL/'
                 'NULL may only be *declared* at the terminal look. UNDERPOWERED here is the '
                 'correct, pre-registered outcome at N=1 -- not a shortfall.')
    lines.append('')

    lines.append('## SECTION 6 -- sealed secondary family (non-citable, Bonferroni '
                 f'alpha={ALPHA_SEC:.4f}, at-most-one action -- gated on primary==CALIBRATED-SKILL '
                 'at a terminal look, not reached today)')
    lines.append('')
    lines.append('| cell | population | point | 95% lower | 95% upper | K | N |')
    lines.append('|---|---|---|---|---|---|---|')
    lines.append(f"| S1 log-loss skill | forward, H2H, non-SS pooled | {fmt(sec['s1']['ll_skill'])} | "
                 f"{fmt(sec['s1']['lower'])} | {fmt(sec['s1']['upper'])} | {sec['s1']['K']} | {sec['s1']['N']} |")
    lines.append(f"| S2 top-10 BSS (vs climatology min(10,n)/n) | forward, non-SS pooled | "
                 f"{fmt(sec['s2']['bss'])} | {fmt(sec['s2']['lower'])} | {fmt(sec['s2']['upper'])} | "
                 f"{sec['s2']['K']} | {sec['s2']['N']} |")
    line3 = sec['s3_line']
    s3_str = f"slope={fmt(line3['slope'])} intercept={fmt(line3['intercept'])}" if line3 else 'n/a (too few bins)'
    lines.append(f"| S3 H2H reliability slope+intercept (descriptive only) | forward, H2H, non-SS pooled | "
                 f"{s3_str} | -- | -- | -- | -- |")
    for tt in ALL_TTYPES:
        if tt in sec['s4']:
            b = sec['s4'][tt]
            note = ' (SS STAND-DOWN)' if tt == 'SS' else ''
            lines.append(f"| S4 per-type H2H BSS ({tt}){note} | forward | {fmt(b['bss'])} | -- | -- | -- | {b['n']} |")
    lines.append(f"| S5 win BSS (vs climatology 1/n, tail market, descriptive only) | forward, non-SS pooled | "
                 f"{fmt(sec['s5']['bss'])} | -- | -- | -- | {sec['s5']['n']} |")
    lines.append(f"| S6 H2H BSS, 2026-peeked cut | 2026-OOS, non-SS pooled | {fmt(sec['s6']['bss'])} | "
                 f"{fmt(sec['s6']['lower'])} | {fmt(sec['s6']['upper'])} | {sec['s6']['K']} | {sec['s6']['N']} |")
    lines.append('')
    lines.append('No action is taken from this family today: action-eligibility (S1, S2) requires '
                 'the section 3 primary to itself be CALIBRATED-SKILL at a terminal look, which has '
                 'not been reached (K << 60).')
    lines.append('')

    lines.append('## SECTION 7 -- power triage')
    lines.append('')
    lines.append(res['power_triage_text'])
    lines.append('')

    lines.append('## SECTION 9 -- C-trigger split')
    lines.append('')
    lines.append(res['trigger_split_text'])
    lines.append('')

    lines.append('## FORWARD stratum detail (race 5618, North Wilkesboro, SHORT, 2026-07-19)')
    lines.append(f"- common set n={fm['n']}, track_type={fm['ttype']}, "
                 f"unscored={fm['unscored']}, unpredicted={fm['unpredicted']}")
    lines.append(render_stratum_section(res['forward']))
    lines.append('')

    lines.append('## IN-SAMPLE stratum (dev smoke test, barred from decision & recal-fitting, '
                 f"{res['n_in_sample_races']} races, 2022-2026)")
    lines.append('')
    lines.append(render_stratum_section(res['in_sample']))
    lines.append('')

    lines.append(f"## 2026-OOS stratum (peeked secondary, non-citable except S6, "
                 f"{res['n_oos2026_races']} races)")
    lines.append('')
    lines.append(render_stratum_section(res['oos2026']))
    lines.append('')

    lines.append('## Resolved (not flagged) implementation notes')
    lines.append("""\
- Baseline replication runs against `data/anchors/races_parsed_anchor_20260719.pkl` (the same
  frozen anchor `gate_gold.py`'s R0 uses; its functions are reused verbatim) rather than the live
  `races_parsed.pkl`, which now includes race 5618 itself and would no longer reproduce 0.447
  exactly. The spec's own phrase ("the frozen anchor") names this artifact directly.
- `walkforward.run`'s `collect_preds` hook returns `(u, actual, track_type, date)` with no
  `driver_id`. `replay_elig_sequence` reproduces only the eligibility/history bookkeeping (never
  the PL fit) against the same RACES object to recover driver identity, verified byte-for-byte
  (same count, same date, same length, elig-derived finish vector == `actual`) against all 128
  collected races before use -- the same "faithful side-channel replay" pattern `gate_gold.py`'s
  own R2/R3 already use for this engine.
- The FORWARD stream's H2H/win/top10 probabilities are read directly from the sealed prediction
  JSON (`h2h_prob`, `p_win`, `p_top10`) rather than re-priced via `pricing_layer.price_race` --
  `specs/pricing_layer.md` section 2 point 1 and this spec's own section 1 forward-stream
  definition both pin this ("the sealed h2h_prob... from the JSON"; "adding no new numbers to the
  sealed forward record"). `price_race` is used only for IN-SAMPLE/2026-OOS, which have no
  existing sealed JSON.
- H2H pairs are graded whenever `h2h_prob` is defined and finishes differ -- `p == 0.5` is NOT
  skipped (unlike the pick-accuracy rule in `specs/scoring_methodology.md` section 4, which skips
  it because a discrete pick needs a side to take). A proper score handles `p=0.5` natively (it
  simply contributes 0.25 to the Brier sum); the "skip p=0.5" rule exists only for a discrete pick,
  which this spec's population definition never asks for.
- S5 (win market) and S2 (top-10) both need a baseline; S2's is given explicitly
  (`min(10,n)/n`, a climatology base rate). S5's is not stated, so it is taken as the same
  climatology form generalized to N=1: `min(1,n)/n = 1/n` -- "each driver equally likely to win,"
  the direct analogue of S2's own formula, not an invented statistic.
- `pricing_layer.score_floor` (eps=1.25e-5) is applied to every analytic probability (H2H, win,
  and the as-of BT baseline) before it enters any Brier or log-loss computation, extending
  `specs/pricing_layer.md` section 5.2's stated log-loss floor to the BT baseline symmetrically
  (the baseline can equal exactly 0.0 for a driver with a lifetime of losses, which would blow up
  a log-loss term if left unfloored) and to Brier for uniformity; MC-derived values (top-10) need
  no floor, already add-half smoothed.
- Real `race_id` (the anchor pkl's own `rid` field) and real `driver_id`s (recovered via the elig
  replay) are used for `price_race`'s seed and identifiers on IN-SAMPLE/2026-OOS races -- no
  synthetic ids were needed.
""")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print('=' * 78)
    print('calibration_backtest -- specs/calibration_backtest.md section 10')
    print('=' * 78)

    anchor_path, anchor_races, preds_oos, trio = assert_baseline_replication()
    anchor_sorted = sorted(anchor_races, key=lambda r: r['date'])
    races_by_rid = {r['rid']: r for r in anchor_races}

    print('\n[calibration_backtest] building as-of Bradley-Terry marginal baseline (non-SS history)...')
    bt_snapshots, bt_final_state = build_bt_asof(anchor_sorted, MY_TYPE)

    print('[calibration_backtest] replaying eligibility sequence to recover driver_id per scored race...')
    replay = replay_elig_sequence(anchor_sorted, gg.OOS_YEARS)
    verify_elig_replay(preds_oos['fpts'], replay, races_by_rid)
    print(f'[calibration_backtest] elig replay verified byte-identical for all {len(replay)} races.')

    print('[calibration_backtest] pricing + grading IN-SAMPLE / 2026-OOS pool via pricing_layer...')
    wf_records = price_and_grade_walkforward_races(preds_oos['fpts'], replay, bt_snapshots)
    in_sample_races = {r['race_key'] for r in wf_records}
    oos2026_records = [r for r in wf_records if r['year'] == FORWARD_YEAR]
    oos2026_races = {r['race_key'] for r in oos2026_records}
    print(f'[calibration_backtest]   IN-SAMPLE: {len(in_sample_races)} races, {len(wf_records)} unit records')
    print(f'[calibration_backtest]   2026-OOS (subset): {len(oos2026_races)} races, {len(oos2026_records)} unit records')

    print('[calibration_backtest] loading FORWARD stream (race 5618 sealed JSON + frozen snapshot)...')
    forward_records, forward_meta = load_forward_stream(bt_final_state)
    print(f"[calibration_backtest]   FORWARD: 1 race (id={FORWARD_RACE_ID}), n_common={forward_meta['n']}, "
          f"ttype={forward_meta['ttype']}, {len(forward_records)} unit records")

    # ---- per-stratum descriptive bundles ----
    in_sample = stratum_report(wf_records, 'IN-SAMPLE (dev, barred from decision & recal-fitting)',
                                len(in_sample_races))
    oos2026 = stratum_report(oos2026_records, '2026-OOS (peeked secondary, non-citable except S6)',
                              len(oos2026_races))
    forward = stratum_report(forward_records, 'FORWARD (decision-grade)', 1)

    # ---- section 3: the ONE primary decision ----
    primary_pop = subset(forward_records, market='h2h', nonss=True)
    primary_boot = race_clustered_bootstrap_bss(primary_pop)
    verdict, verdict_why = evaluate_primary(primary_boot)
    terminal_triggered, terminal_why = terminal_look_reached(primary_boot['K'])

    print('\n' + '=' * 78)
    print('SECTION 3 -- the ONE primary decision (H2H BSS vs as-of BT baseline, forward, non-SS, pooled)')
    print('=' * 78)
    print(f"K={primary_boot['K']} (non-SS forward races)  N={primary_boot['N']} (graded pairs)")
    print(f"point BSS={fmt(primary_boot['bss'])}  95% one-sided lower={fmt(primary_boot['lower'])}  "
          f"upper={fmt(primary_boot['upper'])}")
    print(f'terminal look reached: {terminal_triggered} ({terminal_why or "not yet"})')
    print(f'VERDICT: {verdict}  ({verdict_why})')

    # ---- section 6: sealed secondary family (forward, except S6 = 2026-peeked) ----
    s1 = race_clustered_bootstrap_llskill(subset(forward_records, market='h2h', nonss=True))
    s2 = race_clustered_bootstrap_bss(subset(forward_records, market='top10', nonss=True))
    s3_rel = forward['reliability']['h2h_pooled_nonss']
    s4_per_type = forward['h2h']['per_type']
    s5 = brier_of(subset(forward_records, market='win', nonss=True))
    s5_rel = forward['reliability']['win_pooled_nonss']
    s6 = race_clustered_bootstrap_bss(subset(oos2026_records, market='h2h', nonss=True))

    forward_ss_n = len(subset(forward_records, market='h2h', ttype='SS'))
    power_triage_text = build_power_triage(primary_boot['K'])
    trigger_split_text = build_trigger_split(forward_ss_n)

    print('\n' + '=' * 78)
    print(f'SECTION 6 -- sealed secondary family (Bonferroni alpha={ALPHA_SEC:.4f}, non-citable, '
          f'at-most-one action -- gated on primary==CALIBRATED-SKILL at a terminal look, not reached)')
    print('=' * 78)
    print(f"S1 log-loss skill (forward, non-SS pooled): point={fmt(s1['ll_skill'])} "
          f"lower={fmt(s1['lower'])} upper={fmt(s1['upper'])} K={s1['K']} N={s1['N']}")
    print(f"S2 top-10 BSS (forward, non-SS pooled, vs climatology min(10,n)/n): "
          f"point={fmt(s2['bss'])} lower={fmt(s2['lower'])} upper={fmt(s2['upper'])} K={s2['K']} N={s2['N']}")
    print(f"S3 H2H reliability line (forward, non-SS pooled): "
          f"{s3_rel.get('line')}")
    print('S4 per-track-type H2H BSS (forward):')
    for tt in ALL_TTYPES:
        if tt in s4_per_type:
            b = s4_per_type[tt]
            print(f"    {tt}: n={b['n']} BSS={fmt(b['bss'])}" + ('  SS STAND-DOWN' if tt == 'SS' else ''))
    print(f"S5 win BSS (forward, non-SS pooled, tail market, vs climatology 1/n): "
          f"n={s5['n']} BSS={fmt(s5['bss'])}")
    print(f"S6 H2H BSS on 2026-peeked cut: point={fmt(s6['bss'])} lower={fmt(s6['lower'])} "
          f"upper={fmt(s6['upper'])} K={s6['K']} N={s6['N']}")

    print('\n' + '=' * 78)
    print('SECTION 7 -- power triage')
    print('=' * 78)
    print(power_triage_text)

    print('=' * 78)
    print('SECTION 9 -- C-trigger split')
    print('=' * 78)
    print(trigger_split_text)

    results = dict(
        anchor_path=anchor_path, trio=trio,
        in_sample=in_sample, oos2026=oos2026, forward=forward,
        primary=dict(boot=primary_boot, verdict=verdict, verdict_why=verdict_why,
                     terminal_triggered=terminal_triggered, terminal_why=terminal_why),
        secondary=dict(s1=s1, s2=s2, s3_line=s3_rel.get('line'), s4=s4_per_type, s5=s5,
                       s5_rel=s5_rel, s6=s6),
        power_triage_text=power_triage_text, trigger_split_text=trigger_split_text,
        forward_meta=forward_meta, forward_ss_n=forward_ss_n,
        n_in_sample_races=len(in_sample_races), n_oos2026_races=len(oos2026_races),
    )
    write_report(results)
    print(f'\n[calibration_backtest] wrote {REPORT_PATH}')
    return results


if __name__ == '__main__':
    main()
