#!/usr/bin/env python3
"""Is the PL model's implied H2H probability calibrated out of sample? (PL: P(i beats j)=sigmoid(u_j-u_i))"""
import numpy as np, pickle
from walkforward import run, MY_TYPE

np.random.seed(23)
preds = {}
rows = run(typology=MY_TYPE, typed_mode='shrinkage',
           pl_specs={'fpts': ['fin','pace','typed','start']}, collect_preds=preds)

ps, ys, types = [], [], []
for u, actual, tt, dt in preds['fpts']:
    n = len(u)
    for i in range(n):
        for j in range(i+1, n):
            p = 1.0/(1.0+np.exp(-(u[j]-u[i])))   # P(i finishes ahead of j)
            ps.append(p); ys.append(1.0 if actual[i] < actual[j] else 0.0); types.append(tt)
ps, ys = np.array(ps), np.array(ys); types = np.array(types)
print(f"H2H pairs evaluated (walk-forward, out-of-sample): {len(ps):,}")
print(f"overall Brier: {np.mean((ps-ys)**2):.4f}   (coin-flip baseline: 0.2500)")
print(f"log-loss: {-np.mean(ys*np.log(ps)+(1-ys)*np.log(1-ps)):.4f}   (coin-flip: 0.6931)")
print(f"\n{'pred prob bin':<16}{'n pairs':>9}{'mean pred':>11}{'empirical':>11}{'gap':>8}")
bins = np.array([0,.2,.3,.4,.45,.5,.55,.6,.7,.8,1.0])
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (ps >= lo) & (ps < hi)
    if m.sum() > 100:
        print(f"[{lo:.2f},{hi:.2f})     {m.sum():>9,}{ps[m].mean():>11.3f}{ys[m].mean():>11.3f}{ys[m].mean()-ps[m].mean():>+8.3f}")
print("\nBy track type (confidence available vs realized):")
print(f"{'type':<8}{'n pairs':>9}{'acc @ p>0.6':>13}{'Brier':>9}")
for t in ['SHORT','INT','ROAD','SS']:
    m = types == t
    conf = m & ((ps > 0.6) | (ps < 0.4))
    pc, yc = ps[conf], ys[conf]
    acc = np.mean((pc > 0.5) == (yc > 0.5)) if conf.sum() else np.nan
    frac_conf = conf.sum()/m.sum()
    print(f"{t:<8}{m.sum():>9,}{acc:>13.3f}{np.mean((ps[m]-ys[m])**2):>9.4f}   (share of pairs with conf>60%: {frac_conf:.0%})")
