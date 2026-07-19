#!/usr/bin/env python3
import numpy as np, pickle, time
from walkforward import run, MY_TYPE, by_type
from scipy.stats import wilcoxon

np.random.seed(17)
SPECS = dict(fp=['fin', 'pace'],
             fpt=['fin', 'pace', 'typed'],
             fpts=['fin', 'pace', 'typed', 'start'],
             prior_all=['fin', 'pace', 'typed', 'start', 'fepace'],
             sameday=['fin', 'pace', 'typed', 'start', 'fepace', 'practice'])

def table(rows, keys, base='rho_finish', label=''):
    b = np.array([r.get(base, np.nan) for r in rows], float)
    print(f"  {label}  ({len(rows)} scored races)")
    print(f"  {'model':<22}{'mean rho':>9}{'vs finish':>11}{'p':>9}{'pairwise acc':>14}")
    for k in keys:
        a = np.array([r.get(k, np.nan) for r in rows], float)
        m = ~np.isnan(a) & ~np.isnan(b)
        dd = a[m] - b[m]
        p = wilcoxon(dd)[1] if len(dd) > 5 and np.any(dd != 0) else np.nan
        tk = k.replace('rho_', 'tau_')
        taus = np.array([r.get(tk, np.nan) for r in rows], float)
        pa = (np.nanmean(taus) + 1) / 2 if not np.all(np.isnan(taus)) else np.nan
        pas = f"{pa:.3f}" if not np.isnan(pa) else "-"
        print(f"  {k:<22}{np.nanmean(a):>9.3f}{dd.mean():>+11.3f}{p:>9.4f}{pas:>14}")

t0 = time.time()
print("=" * 78)
print("STEP 4 - EXTENSIONS (my typology, shrinkage typed, pace=med85, hl=8)")
print("        PL = Plackett-Luce, weights refit walk-forward on past races only")
print("=" * 78)
W = {}
rows = run(typology=MY_TYPE, typed_mode='shrinkage', pl_specs=SPECS, pl_refit_every=1, out_w=W)
keys = (['rho_finish', 'rho_combined_typed', 'rho_fepace', 'rho_practice'] +
        ['rho_PL_' + s for s in SPECS])
table(rows, keys, label='2022-2025 held-out')

def paired(rows, a, b):
    x = np.array([r.get(a, np.nan) for r in rows], float)
    y = np.array([r.get(b, np.nan) for r in rows], float)
    m = ~np.isnan(x) & ~np.isnan(y); dd = x[m] - y[m]
    return dd.mean(), (wilcoxon(dd)[1] if np.any(dd != 0) else 1.0), len(dd)

for a, b in [('rho_PL_fpts', 'rho_combined_typed'), ('rho_PL_sameday', 'rho_PL_fpts'),
             ('rho_PL_prior_all', 'rho_PL_fpts')]:
    d_, p_, n_ = paired(rows, a, b)
    print(f"  paired {a} vs {b}: {d_:+.3f} (p={p_:.4f}, n={n_})")
fn = ['fin','pace','typed','start','fepace','practice']
for s in ['fpts','sameday']:
    if s in W:
        print(f"  final fitted PL weights [{s}]:",
              {k: round(float(v),3) for k, v in zip(SPECS[s], W[s])})

nonss = [r for r in rows if r['ttype'] in ('SHORT', 'INT', 'ROAD')]
print()
table(nonss, ['rho_finish', 'rho_combined_typed', 'rho_PL_prior_all', 'rho_PL_sameday'],
      label='non-superspeedway only (where strategy says to press)')

print(f"\n  [{time.time()-t0:.0f}s]")
print("=" * 78)
print("STEP 4B - same, with my preferred config (pace=p20, hl=4)")
print("=" * 78)
rows_p = run(pace_key='pace_p20', hl=4, typology=MY_TYPE, typed_mode='shrinkage',
             pl_specs=SPECS, pl_refit_every=1)
table(rows_p, keys, label='2022-2025 held-out')

print(f"\n  [{time.time()-t0:.0f}s]")
print("=" * 78)
print("STEP 5 - TRUE OUT-OF-SAMPLE: 2026 races (never seen by the prior session)")
print("=" * 78)
rows_26 = run(typology=MY_TYPE, typed_mode='shrinkage', years=(2022, 2023, 2024, 2025, 2026),
              pl_specs=SPECS, pl_refit_every=1)
only26 = [r for r in rows_26 if r['year'] == 2026]
table(only26, ['rho_start', 'rho_finish', 'rho_pace', 'rho_combined', 'rho_combined_typed',
               'rho_PL_prior_all', 'rho_PL_sameday'], label='2026 races only')
print("\n  2026 per-type (combined_typed):")
by_type(only26, 'rho_combined_typed')

pickle.dump({'main': rows, 'p20hl4': rows_p, 'r2026': only26}, open('rows_models.pkl', 'wb'))
print(f"\n  [{time.time()-t0:.0f}s total]")
