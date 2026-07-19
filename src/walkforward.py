#!/usr/bin/env python3
"""Zero-trust audit engine. All code independent of the prior session's scripts."""
import pickle
import numpy as np
from scipy.stats import spearmanr, kendalltau, wilcoxon
from scipy.optimize import minimize

RACES = sorted(pickle.load(open('races_parsed.pkl', 'rb')), key=lambda r: r['date'])

# ---- typologies -------------------------------------------------------------
THEIR_TYPE = {  # exactly as written in boost_analysis.py (missing names -> UNIQ)
 'Daytona International Speedway':'SS','Talladega Superspeedway':'SS','Atlanta Motor Speedway':'SS',
 'Las Vegas Motor Speedway':'INT','Kansas Speedway':'INT','Texas Motor Speedway':'INT',
 'Homestead-Miami Speedway':'INT','Michigan International Speedway':'INT','Charlotte Motor Speedway':'INT',
 'Nashville Superspeedway':'INT','Chicagoland Speedway':'INT','Auto Club Speedway':'INT',
 'Martinsville Speedway':'SHORT','Richmond Raceway':'SHORT','Bristol Motor Speedway':'SHORT',
 'North Wilkesboro Speedway':'SHORT','Phoenix Raceway':'SHORT','Iowa Speedway':'SHORT',
 'Circuit of The Americas':'ROAD','Watkins Glen International':'ROAD','Sonoma Raceway':'ROAD',
 'Chicago Street Course':'ROAD','San Diego Street Course':'ROAD',
 'Darlington Raceway':'UNIQ','Pocono Raceway':'UNIQ','Indianapolis Motor Speedway':'UNIQ',
 'New Hampshire Motor Speedway':'UNIQ','World Wide Technology Raceway':'UNIQ',
}
MY_TYPE = {}
for t in ['Daytona International Speedway','Talladega Superspeedway','Atlanta Motor Speedway']:
    MY_TYPE[t]='SS'
for t in ['Las Vegas Motor Speedway','Kansas Speedway','Texas Motor Speedway','Homestead-Miami Speedway',
          'Michigan International Speedway','Charlotte Motor Speedway','Chicagoland Speedway',
          'Auto Club Speedway','Nashville Superspeedway','Darlington Raceway',
          'World Wide Technology Raceway','Pocono Raceway','Indianapolis Motor Speedway']:
    MY_TYPE[t]='INT'
for t in ['Martinsville Speedway','Richmond Raceway','Bristol Motor Speedway','North Wilkesboro Speedway',
          'Iowa Speedway','Phoenix Raceway','New Hampshire Motor Speedway','Dover Motor Speedway']:
    MY_TYPE[t]='SHORT'
for t in ['Circuit of The Americas','Watkins Glen International','Sonoma Raceway','Chicago Street Race',
          'San Diego Street Course','Charlotte Motor Speedway Road Course',
          'Indianapolis Motor Speedway Road Course','Road America','Autódromo Hermanos Rodríguez']:
    MY_TYPE[t]='ROAD'
MY_TYPE['Bristol Motor Speedway Dirt']='OTHER'

# ---- helpers ----------------------------------------------------------------
def wmean(xs, hl):
    if not xs: return None
    if hl is None: return float(np.mean(xs))
    w = 0.5 ** (np.arange(len(xs)-1, -1, -1) / hl)
    return float(np.average(xs, weights=w))

def z(a):
    a = np.asarray(a, float)
    s = a.std()
    return (a - a.mean()) / (s + 1e-9)

def znan(vals):
    """z-score with NaN -> 0 after standardizing over non-NaN."""
    a = np.asarray(vals, float)
    m = ~np.isnan(a)
    if m.sum() < 3: return np.zeros(len(a))
    mu, sd = a[m].mean(), a[m].std() + 1e-9
    out = (a - mu) / sd
    out[~m] = 0.0
    return out

# ---- Plackett-Luce with linear features, walk-forward -----------------------
def pl_fit(X_list, ord_list, lam=0.5, w0=None):
    k = X_list[0].shape[1]
    def nll_grad(w):
        nll = lam * w @ w
        grad = 2 * lam * w
        for X, order in zip(X_list, ord_list):
            u = X @ w
            uo, Xo = u[order], X[order]
            m = uo.max()
            e = np.exp(uo - m)
            S = np.cumsum(e[::-1])[::-1]                    # suffix sums
            nll += float(np.sum(np.log(S) + m - uo))
            inv = np.cumsum(1.0 / S)                        # prefix of 1/S_i
            q = e * inv                                     # weight per j
            grad += q @ Xo - Xo.sum(axis=0)
        return nll, grad
    w0 = np.zeros(k) if w0 is None else w0
    r = minimize(nll_grad, w0, jac=True, method='L-BFGS-B')
    return r.x

# ---- main walk-forward ------------------------------------------------------
def run(pace_key='pace_med85', hl=8, burn=15, min_hist=5, min_drv=20,
        typology=THEIR_TYPE, years=(2022, 2023, 2024, 2025), typed_mode='their_fallback',
        pl_specs=None, pl_refit_every=1, out_w=None, collect_preds=None, verbose=False):
    """pl_specs: dict name -> list of feature keys among
       ['pace','fin','typed','start','fepace','practice']"""
    sample = [r for r in RACES if r['year'] in years]
    hf, hp, hfe, ht = {}, {}, {}, {}
    rows = []                       # per scored race: dict of rho per predictor + meta
    pl_train = {name: ([], []) for name in (pl_specs or {})}
    pl_w = {name: None for name in (pl_specs or {})}
    since_fit = {name: 0 for name in (pl_specs or {})}

    for idx, race in enumerate(sample):
        tt = typology.get(race['track'], 'UNIQ')
        drivers = race['drivers']
        if idx >= burn:
            elig = [d for d in drivers
                    if d in hf and len(hf[d]) >= min_hist and drivers[d].get(pace_key) is not None]
            if len(elig) >= min_drv:
                actual = np.array([drivers[d]['finish'] for d in elig], float)
                start = np.array([drivers[d]['start'] if drivers[d]['start'] else 20 for d in elig], float)
                fin_h = np.array([wmean(hf[d], hl) for d in elig])
                pace_h = np.array([wmean(hp[d], hl) for d in elig])
                if typed_mode == 'their_fallback':
                    typ_h = np.array([wmean(ht[(d, tt)], hl) if ht.get((d, tt))
                                      else float(np.mean(hf[d])) for d in elig])
                else:  # shrinkage toward overall recency-weighted finish
                    typ_h = []
                    for d in elig:
                        th = ht.get((d, tt), [])
                        base = wmean(hf[d], hl)
                        if th:
                            n = len(th)
                            typ_h.append((n * wmean(th, hl) + 3 * base) / (n + 3))
                        else:
                            typ_h.append(base)
                    typ_h = np.array(typ_h)
                fe_h = np.array([wmean(hfe[d], hl) if hfe.get(d) else np.nan for d in elig])
                prac = np.array([drivers[d].get('practice') or np.nan for d in elig], float)

                comb = z(pace_h) + z(fin_h)
                comb_t = z(pace_h) + 0.5 * z(fin_h) + 0.5 * z(typ_h)

                row = dict(date=race['date'][:10], year=race['year'], track=race['track'],
                           ttype=tt, n=len(elig))
                preds = dict(start=start, finish=fin_h, pace=pace_h,
                             combined=comb, combined_typed=comb_t,
                             fepace=np.where(np.isnan(fe_h), np.nanmean(fe_h), fe_h),
                             practice=np.where(np.isnan(prac), np.nanmean(prac), prac))
                for k_, v in preds.items():
                    if np.all(np.isnan(v)):
                        row['rho_' + k_] = np.nan
                    else:
                        row['rho_' + k_] = spearmanr(v, actual)[0]
                row['tau_finish'] = kendalltau(fin_h, actual)[0]
                row['tau_combined_typed'] = kendalltau(comb_t, actual)[0]

                # ---- PL models -------------------------------------------------
                feat_bank = dict(pace=znan(pace_h), fin=znan(fin_h), typed=znan(typ_h),
                                 start=znan(start), fepace=znan(fe_h), practice=znan(prac))
                for name, keys in (pl_specs or {}).items():
                    X = np.column_stack([feat_bank[k_] for k_ in keys])
                    Xs, Os = pl_train[name]
                    if len(Xs) >= 20:
                        if pl_w[name] is None or since_fit[name] >= pl_refit_every:
                            pl_w[name] = pl_fit(Xs, Os, w0=pl_w[name])
                            since_fit[name] = 0
                        since_fit[name] += 1
                        u = X @ pl_w[name]   # w fit on -X, so u aligns with finish position
                        row['rho_PL_' + name] = spearmanr(u, actual)[0]
                        row['tau_PL_' + name] = kendalltau(u, actual)[0]
                        if collect_preds is not None:
                            collect_preds.setdefault(name, []).append(
                                (u.copy(), actual.copy(), tt, race['date'][:10]))
                    else:
                        row['rho_PL_' + name] = np.nan
                    order = np.argsort(actual)     # best finisher first
                    Xs.append(-X)                  # negate: higher utility = better
                    Os.append(order)
                    if out_w is not None and pl_w[name] is not None:
                        out_w[name] = pl_w[name].copy()
                rows.append(row)
        # update histories
        for d, v in drivers.items():
            hf.setdefault(d, []).append(v['finish'])
            if v.get(pace_key) is not None:
                hp.setdefault(d, []).append(v[pace_key])
            if v.get('fepace') is not None:
                hfe.setdefault(d, []).append(v['fepace'])
            ht.setdefault((d, tt), []).append(v['finish'])
    return rows

# ---- reporting helpers ------------------------------------------------------
def summarize(rows, keys, base='rho_finish'):
    print(f"  scored races: {len(rows)}")
    b = np.array([r[base] for r in rows])
    print(f"  {'predictor':<24}{'mean rho':>9}{'sd':>7}{'vs base':>9}{'Wilcoxon p':>12}{'95% CI of diff':>20}")
    out = {}
    for k_ in keys:
        a = np.array([r.get(k_, np.nan) for r in rows], float)
        m = ~np.isnan(a) & ~np.isnan(b)
        d = a[m] - b[m]
        try:
            p = wilcoxon(d)[1] if np.any(d != 0) else 1.0
        except Exception:
            p = np.nan
        boots = np.array([np.mean(np.random.choice(d, len(d))) for _ in range(4000)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        print(f"  {k_:<24}{np.nanmean(a):>9.3f}{np.nanstd(a):>7.3f}{d.mean():>+9.3f}"
              f"{p:>12.4f}{'':>6}[{lo:+.3f},{hi:+.3f}]")
        out[k_] = (np.nanmean(a), d.mean(), p, lo, hi)
    return out

def by_type(rows, key):
    from collections import defaultdict
    g = defaultdict(list)
    for r in rows:
        if not np.isnan(r.get(key, np.nan)):
            g[r['ttype']].append(r[key])
    print(f"  {'type':<8}{'n':>4}{'mean rho':>10}{'95% CI':>18}")
    for t, arr in sorted(g.items(), key=lambda x: -np.mean(x[1])):
        a = np.array(arr)
        boots = np.array([np.mean(np.random.choice(a, len(a))) for _ in range(4000)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        print(f"  {t:<8}{len(a):>4}{a.mean():>10.3f}{'':>6}[{lo:.3f},{hi:.3f}]")

if __name__ == '__main__':
    np.random.seed(7)
    print("=" * 78)
    print("STEP 1 - REPLICATION RUN (their config, my code): pace=med85 hl=8 burn=15")
    print("        their typology as written (incl. its silent-UNIQ bugs), 2022-2025")
    print("=" * 78)
    rows = run()
    summarize(rows, ['rho_start', 'rho_finish', 'rho_pace', 'rho_combined', 'rho_combined_typed'])
    print("\n  C3 per-type, their model (combined_typed), their typology:")
    by_type(rows, 'rho_combined_typed')
    print("\n  Same per-type breakdown for the NAIVE baseline (past finish) --")
    print("  tests whether superspeedway unpredictability is model-independent:")
    by_type(rows, 'rho_finish')
    pickle.dump(rows, open('rows_replication.pkl', 'wb'))
