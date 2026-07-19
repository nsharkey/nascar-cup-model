#!/usr/bin/env python3
import numpy as np, pickle
from walkforward import run
from scipy.stats import wilcoxon

np.random.seed(11)

def diffstats(rows, a, b):
    x = np.array([r[a] for r in rows]); y = np.array([r[b] for r in rows])
    m = ~np.isnan(x) & ~np.isnan(y); d = x[m] - y[m]
    p = wilcoxon(d)[1] if np.any(d != 0) else 1.0
    return d.mean(), p, len(d)

print("=" * 88)
print("STEP 2A - C1 SENSITIVITY: pace-vs-finish edge across pace definitions x half-life")
print("        (their choice = med85 / hl=8; everything else my alternatives)")
print("=" * 88)
print(f"{'pace definition':<14}{'half-life':<10}{'races':>6}{'pace-finish':>13}{'p':>9}"
      f"{'comb-finish':>13}{'p':>9}{'typed-finish':>14}{'p':>9}")
results = []
for pk, label in [('pace_med85', 'med85'), ('pace_mean70', 'mean70'),
                  ('pace_p20', 'p20'), ('pace_best', 'best20')]:
    for hl in [4, 8, 16, None]:
        rows = run(pace_key=pk, hl=hl)
        d1, p1, n = diffstats(rows, 'rho_pace', 'rho_finish')
        d2, p2, _ = diffstats(rows, 'rho_combined', 'rho_finish')
        d3, p3, _ = diffstats(rows, 'rho_combined_typed', 'rho_finish')
        hls = 'flat' if hl is None else str(hl)
        print(f"{label:<14}{hls:<10}{n:>6}{d1:>+13.3f}{p1:>9.3f}{d2:>+13.3f}{p2:>9.4f}{d3:>+14.3f}{p3:>9.5f}")
        results.append((label, hls, d1, p1, d2, p2, d3, p3))

print()
print("STEP 2B - burn-in / eligibility sensitivity (pace=med85, hl=8)")
print(f"{'burn':>5}{'min_hist':>9}{'races':>7}{'pace-finish':>13}{'p':>8}{'typed-finish':>14}{'p':>9}")
for burn, mh in [(10, 3), (15, 5), (25, 5), (25, 8)]:
    rows = run(burn=burn, min_hist=mh)
    d1, p1, n = diffstats(rows, 'rho_pace', 'rho_finish')
    d3, p3, _ = diffstats(rows, 'rho_combined_typed', 'rho_finish')
    print(f"{burn:>5}{mh:>9}{n:>7}{d1:>+13.3f}{p1:>8.3f}{d3:>+14.3f}{p3:>9.5f}")

pickle.dump(results, open('sensitivity.pkl', 'wb'))
