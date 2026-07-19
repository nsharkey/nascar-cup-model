#!/usr/bin/env python3
import numpy as np, pickle
from walkforward import run, MY_TYPE, THEIR_TYPE, summarize, by_type
from scipy.stats import wilcoxon

np.random.seed(13)

def d(rows, a, b):
    x = np.array([r[a] for r in rows]); y = np.array([r[b] for r in rows])
    m = ~np.isnan(x) & ~np.isnan(y); dd = x[m] - y[m]
    return dd.mean(), (wilcoxon(dd)[1] if np.any(dd != 0) else 1.0)

print("=" * 78)
print("STEP 3 - TYPOLOGY AUDIT (pace=med85, hl=8, burn=15 held fixed)")
print("=" * 78)

print("\n[A] their typology as written (Roval/Chicago/Indy-RC/Dover -> silently UNIQ)")
rows_a = run(typology=THEIR_TYPE)
print("    typed-vs-finish lift: %+0.3f (p=%.5f)" % d(rows_a, 'rho_combined_typed', 'rho_finish'))

print("\n[B] my corrected typology (roads complete; Dover->SHORT; Darlington/Pocono/")
print("    Indy-oval/WWTR->INT; NH->SHORT; Bristol Dirt->OTHER), their fallback rule")
rows_b = run(typology=MY_TYPE)
print("    typed-vs-finish lift: %+0.3f (p=%.5f)" % d(rows_b, 'rho_combined_typed', 'rho_finish'))

print("\n[C] my typology + shrinkage typed-history (partial pooling, k=3)")
rows_c = run(typology=MY_TYPE, typed_mode='shrinkage')
print("    typed-vs-finish lift: %+0.3f (p=%.5f)" % d(rows_c, 'rho_combined_typed', 'rho_finish'))

print("\nC3 per-type predictability under MY corrected typology (combined_typed):")
by_type(rows_b, 'rho_combined_typed')
print("\n  ...and for the naive finish baseline (same races):")
by_type(rows_b, 'rho_finish')

# where does the typed model's lift come from, by type?
print("\nModel-vs-baseline lift BY TRACK TYPE (my typology, [B]):")
from collections import defaultdict
g = defaultdict(list)
for r in rows_b:
    if not np.isnan(r['rho_combined_typed']) and not np.isnan(r['rho_finish']):
        g[r['ttype']].append(r['rho_combined_typed'] - r['rho_finish'])
for t, arr in sorted(g.items(), key=lambda x: -np.mean(x[1])):
    a = np.array(arr)
    print(f"  {t:<8} n={len(a):>3}  mean lift={a.mean():>+0.3f}")

pickle.dump({'their': rows_a, 'mine': rows_b, 'mine_shrunk': rows_c}, open('rows_typology.pkl', 'wb'))
