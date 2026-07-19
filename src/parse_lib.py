#!/usr/bin/env python3
"""Per-race feed parsing, shared by parse.py (full rebuild) and update_data.py (incremental)."""
import json, statistics as st
import numpy as np

def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return None

def parse_race(dt, yr, rid, track, lt, wf):
    """Returns (race_dict, None) on success or (None, skip_reason)."""
    if not lt or not wf or not wf.get('weekend_race'):
        return None, 'no feed'
    wr = wf['weekend_race'][0]
    results = wr.get('results') or []
    if len(results) < 20:
        return None, f'results n={len(results)}'

    res = {}
    for r in results:
        fp = r.get('finishing_position')
        if not fp or fp <= 0: continue
        res[r['driver_id']] = dict(
            finish=fp, start=r.get('starting_position'),
            qspeed=r.get('qualifying_speed'), team=r.get('team_id'),
            make=r.get('car_make'), status=(r.get('finishing_status') or '').strip().lower(),
            laps_led=r.get('laps_led') or 0, laps_completed=r.get('laps_completed') or 0)
    if len(res) < 20:
        return None, 'few valid finishers'

    # green-flag lap set
    green = {f['LapsCompleted'] for f in (lt.get('flags') or []) if f.get('FlagState') == 1}
    per_lap, dlaps = {}, {}
    for drv in (lt.get('laps') or []):
        did = drv.get('NASCARDriverID')
        for lp in drv.get('Laps') or []:
            t, ln, rp = lp.get('LapTime'), lp.get('Lap'), lp.get('RunningPos')
            if t and t > 0 and ln in green:
                per_lap.setdefault(ln, []).append(t)
                dlaps.setdefault(did, []).append((ln, t, rp))
    med = {ln: st.median(v) for ln, v in per_lap.items() if len(v) >= 10}
    if len(med) < 30:
        return None, f'green laps with field={len(med)}'

    # ---------- per-driver simple pace variants (ratio to per-lap field median) ----------
    feats = {}
    for did, laps in dlaps.items():
        rr = sorted(t / med[ln] for ln, t, rp in laps if ln in med)
        if len(rr) < 15 or did not in res: continue
        n = len(rr)
        k85, k70, k20 = max(3, int(n*.85)), max(3, int(n*.70)), max(3, int(n*.20))
        feats[did] = dict(
            pace_med85=st.median(rr[:k85]),          # prior session's definition
            pace_mean70=float(np.mean(rr[:k70])),    # my variant: trimmed mean, tighter
            pace_p20=rr[max(0, int(n*.20)-1)],       # my variant: 20th pct (repr. good lap)
            pace_best=st.median(rr[:k20]),           # their clean-air proxy
            nlaps=n)

    # ---------- fixed-effects adjusted pace (my extension) ----------
    rows_y, rows_d, rows_x = [], [], []
    driver_ids = sorted(d for d in dlaps if d in feats)
    didx = {d: i for i, d in enumerate(driver_ids)}
    for did in driver_ids:
        laps = sorted((ln, t, rp) for ln, t, rp in dlaps[did] if ln in med)
        # segment into runs: consecutive green laps, no big-slow (pit) laps
        run = []
        def flush(run):
            if len(run) >= 6:
                for j, (ln, t, rp) in enumerate(run):
                    if j < 2: continue                     # drop restart/out laps
                    ratio = t / med[ln]
                    if ratio > 1.25: continue
                    age = min(j, 45)
                    pos = rp if rp else 20
                    rows_y.append(np.log(ratio))
                    rows_d.append(didx[did])
                    rows_x.append((age, age*age,
                                   1.0 if pos == 1 else 0.,
                                   1.0 if 2 <= pos <= 5 else 0.,
                                   1.0 if 6 <= pos <= 12 else 0.,
                                   1.0 if 13 <= pos <= 25 else 0.))
        for ln, t, rp in laps:
            if run and (ln != run[-1][0] + 1 or t / med[ln] > 1.20):
                flush(run); run = []
            run.append((ln, t, rp))
        flush(run)
    fe = {}
    if len(rows_y) > 200 and len(driver_ids) >= 15:
        nD = len(driver_ids)
        X = np.zeros((len(rows_y), nD + 6))
        for i, di in enumerate(rows_d): X[i, di] = 1.0
        X[:, nD:] = np.array(rows_x)
        # normalize tire-age columns for conditioning
        X[:, nD] /= 45.; X[:, nD+1] /= 2025.
        y = np.array(rows_y)
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        d_eff = coef[:nD]
        counts = np.bincount(rows_d, minlength=nD)
        ok = counts >= 25
        if ok.sum() >= 15:
            m = d_eff[ok].mean()
            for d_, i in didx.items():
                if ok[i]: fe[d_] = float(d_eff[i] - m)

    # ---------- practice + assemble ----------
    prac = {}
    for run in (wf.get('weekend_runs') or []):
        if run.get('run_type') == 1:
            for rr_ in (run.get('results') or []):
                blt = rr_.get('best_lap_time')
                if blt and blt > 0:
                    d_ = rr_.get('driver_id')
                    prac[d_] = min(prac.get(d_, 1e9), blt)

    table = {}
    for did, r in res.items():
        f = feats.get(did, {})
        table[did] = dict(r)
        table[did].update(f)
        table[did]['fepace'] = fe.get(did)
        table[did]['practice'] = prac.get(did)
    return dict(date=dt, year=yr, rid=rid, track=track, drivers=table,
                    n_green=len(med), n_fe=len(fe), n_prac=len(prac)), None


