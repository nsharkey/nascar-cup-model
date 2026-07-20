#!/usr/bin/env python3
"""D-gate -- re-prove the validated model on gold (specs/medallion_architecture.md section 6,
FROZEN). Adjudicates: gold + re-pointed engine reproduce the validated results. Runs R0 -> R1 ->
R2 -> R3 in order, stopping at the first failure. Failure at any level stops the migration for
investigation -- tuning anything to "make it pass" is prohibited (section 6).

R0 -- environment/reference check (legacy path, anchor data): reproduce 0.413/0.476/0.449 at 3dp.
R1 -- silver replay (legacy engine, silver data): per-race rho_PL_fpts exactly equal to R0's,
      except section 4.4's PASS-with-note races (deltas reported individually).
R2 -- feature parity (gold SQL vs a Python replay of the same history mechanics): fin_h/pace_h/
      typ_h/start_feat within 1e-9 relative tolerance, identical NULL/eligibility membership,
      identical n_hist.
R3 -- decision parity (engine on gold): predicted-rank vector equals R1's per scored race
      (utility-pair near-ties < 1e-7 permitted, listed individually); |delta rho| <= 1e-6 outside
      listed races; trio equals R1's at 3dp.

walkforward.py is NOT edited (section 5.4) -- RACES is monkeypatched at call time, and R2/R3's
"replay" logic is a separate re-implementation in this file that mirrors walkforward.run()'s
history/eligibility mechanics line-for-line (using the same imported wmean/znan/pl_fit helpers)
so the raw feature values and utility vectors can be inspected, which run() itself does not
expose beyond aggregated rho (except via the sanctioned collect_preds hook, used for R1).

Run from src/.
"""
import glob
import os
import pickle
import sys

import duckdb
import numpy as np
from scipy.stats import spearmanr

import warehouse
import walkforward
from walkforward import MY_TYPE, pl_fit, wmean, znan
import gate_silver

REPO_ROOT = warehouse.REPO_ROOT
ANCHORS_DIR = os.path.join(REPO_ROOT, 'data', 'anchors')
REPORT_PATH = os.path.join(REPO_ROOT, 'report', 'GOLD_REPROOF.md')

SPEC = {'fpts': ['fin', 'pace', 'typed', 'start']}       # step4_models.py SPECS['fpts'], section 6
BACKTEST_YEARS = (2022, 2023, 2024, 2025)
OOS_YEARS = (2022, 2023, 2024, 2025, 2026)
NONSS_TTYPES = ('SHORT', 'INT', 'ROAD')                   # section 6: UNIQ/OTHER in neither bucket

HL = 8
BURN = 15
MIN_HIST = 5
MIN_DRV = 20
PACE_KEY = 'pace_med85'
PL_REFIT_EVERY = 1

EXPECTED_BACKTEST = 0.413
EXPECTED_NONSS = 0.476
# 2026-07-19 D1 amendment (spec section 6, AMENDMENT before `## RESULT -- D-gate`): the
# originally-published 0.449 was generated from the 5-feature `prior_all` spec (includes
# fepace, not a production feature), not the frozen 4-feature `fpts` model this gate actually
# reproves. 0.447 is what `fpts` (HANDOFF's frozen config) produces on the anchor -- confirmed
# via a direct diagnostic across all of step4_models.py's SPECS variants, owner-authorized.
EXPECTED_OOS = 0.447

NEAR_TIE_TOL = 1e-7
RHO_TOL = 1e-6
FEATURE_REL_TOL = 1e-9

DRIVER_FIELDS_ALWAYS = ['finish', 'start', 'qspeed', 'team', 'make', 'status',
                        'laps_led', 'laps_completed']
DRIVER_FIELDS_OMIT_IF_NULL = ['pace_med85', 'pace_mean70', 'pace_p20', 'pace_best', 'nlaps']
DRIVER_FIELDS_PRESENT_NONE = ['fepace', 'practice']


def _latest_anchor_path():
    paths = sorted(glob.glob(os.path.join(ANCHORS_DIR, 'races_parsed_anchor_*.pkl')))
    if not paths:
        sys.exit('[gate_gold] no anchor found under data/anchors/ -- section 4.1 must have run (C1)')
    return paths[-1]


def load_anchor():
    path = _latest_anchor_path()
    with open(path, 'rb') as f:
        races = pickle.load(f)
    races = sorted(races, key=lambda r: r['date'])
    return path, races


# ---------------------------------------------------------------------------
# section 5.4 -- silver_to_races_list(): reconstructs the pkl-shaped list-of-dicts from silver,
# reversing the section 3.3 null map. General (Cup, points, ok, ordered by (race_date, race_id));
# callers restrict to a specific race_id set (e.g. R1 restricts to the anchor's race set).
# Each race's `drivers` dict is built in ascending driver_id order (a deliberate, documented
# choice -- not specified by the pkl format, which never fixed an order -- so that
# walkforward.run()'s internal `elig` list order is deterministic and reproducible from outside
# the unedited engine; R3's gold-sourced replay reproduces the identical order for index-aligned
# comparison against R1's collect_preds output).
# ---------------------------------------------------------------------------
def _reconstruct_driver(rec):
    d = {f: rec[f] for f in DRIVER_FIELDS_ALWAYS}
    for f in DRIVER_FIELDS_OMIT_IF_NULL:
        v = rec[f]
        if v is not None:
            d[f] = v
    for f in DRIVER_FIELDS_PRESENT_NONE:
        d[f] = rec[f]
    return d


def silver_to_races_list(con, race_ids=None):
    q = "SELECT * FROM silver.driver_race WHERE series_id = 1"
    if race_ids is not None:
        ids = ','.join(str(int(r)) for r in sorted(set(race_ids)))
        q += f" AND race_id IN ({ids})"
    rows = con.sql(q).fetchall()
    cols = [c[0] for c in con.sql(q + ' LIMIT 0').description]
    by_race, meta = {}, {}
    for row in rows:
        rec = dict(zip(cols, row))
        rid = rec['race_id']
        meta[rid] = (rec['race_date'], rec['year'], rec['track'])
        by_race.setdefault(rid, {})[rec['driver_id']] = _reconstruct_driver(rec)

    races = []
    for rid in sorted(by_race, key=lambda rid: (meta[rid][0], rid)):
        date, year, track = meta[rid]
        drivers = {did: by_race[rid][did] for did in sorted(by_race[rid])}
        races.append(dict(date=date, year=year, rid=rid, track=track, drivers=drivers))
    return races


# ---------------------------------------------------------------------------
# R0 / R1 -- run the unedited walkforward.run() against a monkeypatched RACES global.
# ---------------------------------------------------------------------------
def run_reference(races, collect_preds_bt=None, collect_preds_oos=None):
    walkforward.RACES = races
    bt_rows = walkforward.run(typology=MY_TYPE, typed_mode='shrinkage', years=BACKTEST_YEARS,
                               pl_specs=SPEC, pl_refit_every=PL_REFIT_EVERY,
                               collect_preds=collect_preds_bt)
    oos_rows = walkforward.run(typology=MY_TYPE, typed_mode='shrinkage', years=OOS_YEARS,
                                pl_specs=SPEC, pl_refit_every=PL_REFIT_EVERY,
                                collect_preds=collect_preds_oos)
    return bt_rows, oos_rows


def headline_trio(bt_rows, oos_rows):
    bt = np.array([r['rho_PL_fpts'] for r in bt_rows], float)
    backtest_mean = float(np.nanmean(bt))
    nonss = np.array([r['rho_PL_fpts'] for r in bt_rows if r['ttype'] in NONSS_TTYPES], float)
    nonss_mean = float(np.nanmean(nonss))
    oos26 = np.array([r['rho_PL_fpts'] for r in oos_rows if r['year'] == 2026], float)
    oos_mean = float(np.nanmean(oos26))
    return backtest_mean, nonss_mean, oos_mean


def compare_rows(r0_rows, r1_rows, note_dates):
    """Per-race rho_PL_fpts: r0 vs r1, index-aligned (same race list, same years filter ->
    identical `sample` order and eligibility mask). note_dates = the C-gate's PASS-with-note
    race dates (section 4.4) -- deltas there are reported, not failed on."""
    assert len(r0_rows) == len(r1_rows), (
        f'scored-race count mismatch: r0={len(r0_rows)} r1={len(r1_rows)}')
    deltas, unexpected = [], []
    for i, (a, b) in enumerate(zip(r0_rows, r1_rows)):
        assert a['date'] == b['date'] and a['track'] == b['track'], (
            f"row {i} misaligned: r0=({a['date']},{a['track']}) r1=({b['date']},{b['track']})")
        av, bv = a['rho_PL_fpts'], b['rho_PL_fpts']
        same = (np.isnan(av) and np.isnan(bv)) or av == bv
        if not same:
            entry = {'date': a['date'], 'track': a['track'], 'r0': av, 'r1': bv,
                      'delta': None if (np.isnan(av) or np.isnan(bv)) else bv - av}
            deltas.append(entry)
            if a['date'] not in note_dates:
                unexpected.append(entry)
    return deltas, unexpected


# ---------------------------------------------------------------------------
# R2 -- "the replay": a faithful re-implementation of walkforward.run()'s history/eligibility
# mechanics (typed_mode='shrinkage') that records per-(race,driver) feature values instead of
# only aggregating them into rho. Same math as gold_build.py's SQL, independently written in
# Python against the R1 (silver-reconstructed, anchor-restricted) race list.
# ---------------------------------------------------------------------------
def replay_features(races, years, typology=MY_TYPE, hl=HL, burn=BURN, min_hist=MIN_HIST,
                     min_drv=MIN_DRV, pace_key=PACE_KEY):
    sample = [r for r in races if r['year'] in years]
    hf, hp, ht = {}, {}, {}
    out = []
    for idx, race in enumerate(sample):
        tt = typology.get(race['track'], 'UNIQ')
        drivers = race['drivers']
        if idx >= burn:
            elig = [d for d in drivers
                    if d in hf and len(hf[d]) >= min_hist and drivers[d].get(pace_key) is not None]
            if len(elig) >= min_drv:
                for d in elig:
                    fin_h = wmean(hf[d], hl)
                    pace_h = wmean(hp[d], hl) if hp.get(d) else None
                    th = ht.get((d, tt), [])
                    if th:
                        n = len(th)
                        typ_h = (n * wmean(th, hl) + 3 * fin_h) / (n + 3)
                    else:
                        typ_h = fin_h
                    start = drivers[d]['start']
                    out.append({
                        'race_id': race['rid'], 'driver_id': d, 'n_hist': len(hf[d]),
                        'fin_h': fin_h, 'pace_h': pace_h, 'typ_h': typ_h,
                        'start_feat': start if start else 20,
                        'has_pace': drivers[d].get(pace_key) is not None,
                        'finish': drivers[d]['finish'],
                    })
        for d, v in drivers.items():
            hf.setdefault(d, []).append(v['finish'])
            if v.get(pace_key) is not None:
                hp.setdefault(d, []).append(v[pace_key])
            ht.setdefault((d, tt), []).append(v['finish'])
    return out


def load_gold_features(con):
    cols = ['race_id', 'driver_id', 'n_hist', 'fin_h', 'pace_h', 'typ_h',
            'start_feat', 'has_pace', 'finish']
    q = f"SELECT {', '.join(cols)} FROM gold.wf_features"
    rows = con.sql(q).fetchall()
    return {(r[0], r[1]): dict(zip(cols, r)) for r in rows}


def run_r2(replay_rows, gold_by_key):
    mismatches = []
    for rr in replay_rows:
        key = (rr['race_id'], rr['driver_id'])
        g = gold_by_key.get(key)
        if g is None:
            mismatches.append({'key': key, 'field': 'membership',
                                 'detail': 'eligible in replay, missing from gold.wf_features'})
            continue
        if g['n_hist'] != rr['n_hist']:
            mismatches.append({'key': key, 'field': 'n_hist',
                                 'detail': f"gold={g['n_hist']} replay={rr['n_hist']}"})
        for field in ('fin_h', 'pace_h', 'typ_h'):
            gv, rv = g[field], rr[field]
            if gv is None and rv is None:
                continue
            if gv is None or rv is None:
                mismatches.append({'key': key, 'field': field,
                                     'detail': f'NULL membership differs: gold={gv} replay={rv}'})
                continue
            denom = max(1.0, abs(rv))
            rel = abs(gv - rv) / denom
            if rel > FEATURE_REL_TOL:
                mismatches.append({'key': key, 'field': field,
                                     'detail': f'gold={gv!r} replay={rv!r} rel_diff={rel:.3e}'})
        if g['start_feat'] != rr['start_feat']:
            mismatches.append({'key': key, 'field': 'start_feat',
                                 'detail': f"gold={g['start_feat']} replay={rr['start_feat']}"})
        if bool(g['has_pace']) != bool(rr['has_pace']):
            mismatches.append({'key': key, 'field': 'has_pace',
                                 'detail': f"gold={g['has_pace']} replay={rr['has_pace']}"})
        if g['finish'] != rr['finish']:
            mismatches.append({'key': key, 'field': 'finish',
                                 'detail': f"gold={g['finish']} replay={rr['finish']}"})
    return {'compared': len(replay_rows), 'mismatches': mismatches}


# ---------------------------------------------------------------------------
# R3 -- decision parity: same walk-forward PL loop as walkforward.run(), but pace_h/fin_h/typ_h/
# start_feat/finish are sourced from gold.wf_features instead of recomputed from raw history.
# Eligibility is gold's own n_hist/has_pace (validated equivalent to the legacy criteria by R2).
# ---------------------------------------------------------------------------
def gold_sourced_walk_forward(races, gold_by_key, years, typology=MY_TYPE, hl=HL, burn=BURN,
                               min_hist=MIN_HIST, min_drv=MIN_DRV, pl_specs=SPEC,
                               pl_refit_every=PL_REFIT_EVERY):
    sample = [r for r in races if r['year'] in years]
    pl_train = {name: ([], []) for name in pl_specs}
    pl_w = {name: None for name in pl_specs}
    since_fit = {name: 0 for name in pl_specs}
    rows = []
    preds = {name: [] for name in pl_specs}

    for idx, race in enumerate(sample):
        rid = race['rid']
        drivers = race['drivers']
        elig = [d for d in sorted(drivers)
                if (rid, d) in gold_by_key
                and gold_by_key[(rid, d)]['n_hist'] >= min_hist
                and gold_by_key[(rid, d)]['has_pace']]
        if idx >= burn and len(elig) >= min_drv:
            g = [gold_by_key[(rid, d)] for d in elig]
            actual = np.array([x['finish'] for x in g], float)
            start = np.array([x['start_feat'] for x in g], float)
            fin_h = np.array([x['fin_h'] for x in g], float)
            pace_h = np.array([x['pace_h'] for x in g], float)
            typ_h = np.array([x['typ_h'] for x in g], float)

            feat_bank = dict(pace=znan(pace_h), fin=znan(fin_h), typed=znan(typ_h), start=znan(start))
            row = dict(date=race['date'][:10], year=race['year'], track=race['track'],
                       ttype=typology.get(race['track'], 'UNIQ'), n=len(elig))
            for name, keys in pl_specs.items():
                X = np.column_stack([feat_bank[k] for k in keys])
                Xs, Os = pl_train[name]
                if len(Xs) >= 20:
                    if pl_w[name] is None or since_fit[name] >= pl_refit_every:
                        pl_w[name] = pl_fit(Xs, Os, w0=pl_w[name])
                        since_fit[name] = 0
                    since_fit[name] += 1
                    u = X @ pl_w[name]
                    row['rho_PL_' + name] = spearmanr(u, actual)[0]
                    preds[name].append((u.copy(), actual.copy(), race['date'][:10], rid))
                else:
                    row['rho_PL_' + name] = np.nan
                order = np.argsort(actual)
                Xs.append(-X)
                Os.append(order)
            rows.append(row)
    return rows, preds


def _pairwise_discordant(u1, u3, tol=NEAR_TIE_TOL):
    """All (i,j) pairs whose relative order differs between u1 and u3 -- i.e. genuine rank
    disagreements -- each flagged whether it falls within the section 6 near-tie exception
    (< tol in EITHER vector)."""
    n = len(u1)
    bad = []
    for i in range(n):
        for j in range(i + 1, n):
            s1 = np.sign(u1[i] - u1[j])
            s3 = np.sign(u3[i] - u3[j])
            if s1 != s3 and s1 != 0 and s3 != 0:
                gap = min(abs(u1[i] - u1[j]), abs(u3[i] - u3[j]))
                bad.append((i, j, float(gap), gap < tol))
    return bad


def compare_r1_r3(r1_preds, r3_preds):
    assert len(r1_preds) == len(r3_preds), (
        f'predicted-race count mismatch: r1={len(r1_preds)} r3={len(r3_preds)}')
    near_tie_races, rank_fail_races, rho_deltas = [], [], []
    for i, ((u1, a1, _tt1, date1), (u3, a3, date3, rid3)) in enumerate(zip(r1_preds, r3_preds)):
        assert len(u1) == len(u3) == len(a1) == len(a3), f'race {i} ({date1}): field-size mismatch'
        assert date1 == date3, f'race {i}: date mismatch r1={date1} r3={date3}'
        bad = _pairwise_discordant(u1, u3)
        rho1 = float(spearmanr(u1, a1)[0])
        rho3 = float(spearmanr(u3, a3)[0])
        delta = abs(rho3 - rho1)
        is_exception = False
        if bad:
            if all(entry[3] for entry in bad):
                near_tie_races.append({'race_id': rid3, 'date': date1,
                                         'pairs': [(i_, j_, gap) for i_, j_, gap, _ in bad]})
                is_exception = True
            else:
                rank_fail_races.append({'race_id': rid3, 'date': date1,
                                          'pairs': [(i_, j_, gap, ok) for i_, j_, gap, ok in bad]})
        if not is_exception and delta > RHO_TOL:
            rho_deltas.append({'race_id': rid3, 'date': date1, 'rho1': rho1, 'rho3': rho3,
                                 'delta': delta})
    return near_tie_races, rank_fail_races, rho_deltas


def r3_trio(bt_rows, oos_rows):
    return headline_trio(bt_rows, oos_rows)


# ---------------------------------------------------------------------------
def main():
    result = {}

    print('=' * 78)
    print('R0 -- environment/reference check (legacy path, anchor data)')
    print('=' * 78)
    anchor_path, anchor_races = load_anchor()
    print(f'[gate_gold] anchor: {anchor_path}  ({len(anchor_races)} races)')
    r0_bt, r0_oos = run_reference(anchor_races)
    r0_trio = headline_trio(r0_bt, r0_oos)
    print(f'[gate_gold] R0 trio: backtest={r0_trio[0]:.3f} non-SS={r0_trio[1]:.3f} '
          f'2026-OOS={r0_trio[2]:.3f}')
    r0_ok = (round(r0_trio[0], 3) == EXPECTED_BACKTEST and round(r0_trio[1], 3) == EXPECTED_NONSS
             and round(r0_trio[2], 3) == EXPECTED_OOS)
    result['r0'] = {'trio': r0_trio, 'pass': r0_ok}
    if not r0_ok:
        print(f'\n[gate_gold] R0 FAIL -- expected ({EXPECTED_BACKTEST}, {EXPECTED_NONSS}, '
              f'{EXPECTED_OOS}), got {tuple(round(x, 3) for x in r0_trio)}. STOP: environment or '
              f'data-integrity problem, not a modeling question. Not proceeding to R1-R3.')
        result['verdict'] = 'FAIL_R0'
        return result

    print('\n' + '=' * 78)
    print('C-gate re-check (needed for R1\'s PASS-with-note list, section 4.4)')
    print('=' * 78)
    c_result = gate_silver.run_gate()
    if c_result['verdict'] != 'PASS':
        print(f"\n[gate_gold] STOP -- C-gate is not PASS ({c_result['verdict']}); D-gate depends "
              f"on it (section 4). Not proceeding.")
        result['verdict'] = 'FAIL_CGATE'
        return result
    note_race_ids = set(c_result['race_pass_note'])
    note_dates = {r['date'] for r in anchor_races if r['rid'] in note_race_ids}
    print(f'[gate_gold] C-gate PASS-with-note races: {len(note_race_ids)} (all fepace-only per C1)')

    print('\n' + '=' * 78)
    print('R1 -- silver replay (legacy engine, silver data)')
    print('=' * 78)
    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    anchor_ids = {r['rid'] for r in anchor_races}
    r1_races = silver_to_races_list(con, race_ids=anchor_ids)
    preds_bt, preds_oos = {}, {}
    r1_bt, r1_oos = run_reference(r1_races, collect_preds_bt=preds_bt, collect_preds_oos=preds_oos)
    r1_trio = headline_trio(r1_bt, r1_oos)
    print(f'[gate_gold] R1 trio: backtest={r1_trio[0]:.3f} non-SS={r1_trio[1]:.3f} '
          f'2026-OOS={r1_trio[2]:.3f}')

    bt_deltas, bt_unexpected = compare_rows(r0_bt, r1_bt, note_dates)
    oos_deltas, oos_unexpected = compare_rows(r0_oos, r1_oos, note_dates)
    print(f'[gate_gold] R1 vs R0 rho_PL_fpts deltas: backtest={len(bt_deltas)} '
          f'(unexpected={len(bt_unexpected)}), OOS={len(oos_deltas)} (unexpected={len(oos_unexpected)})')
    result['r1'] = {'trio': r1_trio, 'bt_deltas': bt_deltas, 'oos_deltas': oos_deltas,
                     'bt_unexpected': bt_unexpected, 'oos_unexpected': oos_unexpected}
    r1_ok = not bt_unexpected and not oos_unexpected
    if not r1_ok:
        print(f'\n[gate_gold] R1 FAIL -- {len(bt_unexpected)+len(oos_unexpected)} race(s) with a '
              f'rho_PL_fpts delta NOT on the C-gate PASS-with-note list. STOP.')
        for e in (bt_unexpected + oos_unexpected)[:10]:
            print(f"  {e['date']} {e['track']}: r0={e['r0']} r1={e['r1']} delta={e['delta']}")
        result['verdict'] = 'FAIL_R1'
        return result

    print('\n' + '=' * 78)
    print('R2 -- feature parity (gold SQL vs replay)')
    print('=' * 78)
    replay_rows = replay_features(r1_races, OOS_YEARS)
    gold_by_key = load_gold_features(con)
    con.close()
    r2 = run_r2(replay_rows, gold_by_key)
    print(f"[gate_gold] R2: {r2['compared']} eligible (race,driver) pairs compared, "
          f"{len(r2['mismatches'])} mismatches")
    result['r2'] = r2
    if r2['mismatches']:
        print(f'\n[gate_gold] R2 FAIL -- {len(r2["mismatches"])} mismatch(es). STOP.')
        for m in r2['mismatches'][:15]:
            print(f"  {m['key']} {m['field']}: {m['detail']}")
        result['verdict'] = 'FAIL_R2'
        return result

    print('\n' + '=' * 78)
    print('R3 -- decision parity (engine on gold)')
    print('=' * 78)
    r3_bt, preds3_bt = gold_sourced_walk_forward(r1_races, gold_by_key, BACKTEST_YEARS)
    r3_oos, preds3_oos = gold_sourced_walk_forward(r1_races, gold_by_key, OOS_YEARS)
    r3_trio_val = r3_trio(r3_bt, r3_oos)
    print(f'[gate_gold] R3 trio: backtest={r3_trio_val[0]:.3f} non-SS={r3_trio_val[1]:.3f} '
          f'2026-OOS={r3_trio_val[2]:.3f}')

    nt_bt, rf_bt, rd_bt = compare_r1_r3(preds_bt['fpts'], preds3_bt['fpts'])
    nt_oos, rf_oos, rd_oos = compare_r1_r3(preds_oos['fpts'], preds3_oos['fpts'])
    near_tie = nt_bt + nt_oos
    rank_fail = rf_bt + rf_oos
    rho_deltas = rd_bt + rd_oos
    print(f'[gate_gold] R3: near-tie exceptions={len(near_tie)}, rank FAILs={len(rank_fail)}, '
          f'rho deltas>{RHO_TOL}={len(rho_deltas)}')
    trio_ok = (round(r3_trio_val[0], 3) == round(r1_trio[0], 3)
               and round(r3_trio_val[1], 3) == round(r1_trio[1], 3)
               and round(r3_trio_val[2], 3) == round(r1_trio[2], 3))
    result['r3'] = {'trio': r3_trio_val, 'near_tie': near_tie, 'rank_fail': rank_fail,
                     'rho_deltas': rho_deltas, 'trio_ok': trio_ok}
    r3_ok = not rank_fail and not rho_deltas and trio_ok
    if not r3_ok:
        print(f'\n[gate_gold] R3 FAIL.')
        if rank_fail:
            print(f'  {len(rank_fail)} race(s) with a genuine (non-near-tie) rank disagreement:')
            for e in rank_fail[:5]:
                print(f"    race {e['race_id']} {e['date']}: {e['pairs'][:3]}")
        if rho_deltas:
            print(f'  {len(rho_deltas)} race(s) with |delta rho| > {RHO_TOL}:')
            for e in rho_deltas[:5]:
                print(f"    race {e['race_id']} {e['date']}: rho1={e['rho1']:.6f} "
                      f"rho3={e['rho3']:.6f} delta={e['delta']:.2e}")
        if not trio_ok:
            print(f'  trio mismatch: r1={tuple(round(x,3) for x in r1_trio)} '
                  f'r3={tuple(round(x,3) for x in r3_trio_val)}')
        result['verdict'] = 'FAIL_R3'
        return result

    print('\n' + '=' * 78)
    print('D-GATE PASS')
    print('=' * 78)
    result['verdict'] = 'PASS'
    result['anchor_path'] = anchor_path
    result['anchor_count'] = len(anchor_races)
    result['note_race_ids'] = note_race_ids
    return result


if __name__ == '__main__':
    result = main()
    sys.exit(0 if result.get('verdict') == 'PASS' else 1)
