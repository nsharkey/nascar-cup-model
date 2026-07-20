# Calibration backtest -- results (2026-07-20)

Produced by `src/calibration_backtest.py` per `specs/calibration_backtest.md` section 10's checklist (M3). Governs no frozen file; no change to `predict_next.py` / `walkforward.py` / `scores_log.csv`.

## Environment
- interpreter: 3.13.5 (/opt/anaconda3/bin/python)
- numpy 2.1.3
- anchor: `/Users/nicholassharkey/Downloads/nascar-cup-model/data/anchors/races_parsed_anchor_20260719.pkl`

## Baseline replication (must pass before any calibration number, section 1)
- backtest=0.413  non-SS=0.476  2026-OOS=0.447  (expected 0.413 / 0.476 / 0.447) -- **PASS**

## SECTION 3 -- the ONE primary decision
H2H Brier skill score vs the as-of Bradley-Terry marginal baseline, forward stream, non-SS pairs, pooled. Race-clustered bootstrap (B_CALIB=10000, CALIB_SEED=20260720).

- K (non-SS forward races) = 1   N (graded pairs) = 666
- point BSS = 0.0010   95% one-sided lower = 0.0010   upper = 0.0010
- terminal look reached: False (not yet)
- **VERDICT: UNDERPOWERED**  -- interim look (terminal-only amendment) -- K < 60 and calendar not reached

Per the 2026-07-20 terminal-only amendment, this is an interim look (K << 60); the primary verdict is computed and reported at every look but CALIBRATED-SKILL/NULL may only be *declared* at the terminal look. UNDERPOWERED here is the correct, pre-registered outcome at N=1 -- not a shortfall.

## SECTION 6 -- sealed secondary family (non-citable, Bonferroni alpha=0.0083, at-most-one action -- gated on primary==CALIBRATED-SKILL at a terminal look, not reached today)

| cell | population | point | 95% lower | 95% upper | K | N |
|---|---|---|---|---|---|---|
| S1 log-loss skill | forward, H2H, non-SS pooled | -0.0021 | -0.0021 | -0.0021 | 1 | 666 |
| S2 top-10 BSS (vs climatology min(10,n)/n) | forward, non-SS pooled | 0.0420 | 0.0420 | 0.0420 | 1 | 37 |
| S3 H2H reliability slope+intercept (descriptive only) | forward, H2H, non-SS pooled | slope=2.3005 intercept=-0.7218 | -- | -- | -- | -- |
| S4 per-type H2H BSS (SHORT) | forward | 0.0010 | -- | -- | -- | 666 |
| S5 win BSS (vs climatology 1/n, tail market, descriptive only) | forward, non-SS pooled | 0.0120 | -- | -- | -- | 37 |
| S6 H2H BSS, 2026-peeked cut | 2026-OOS, non-SS pooled | 0.0528 | 0.0357 | 0.0703 | 16 | 10697 |

No action is taken from this family today: action-eligibility (S1, S2) requires the section 3 primary to itself be CALIBRATED-SKILL at a terminal look, which has not been reached (K << 60).

## SECTION 7 -- power triage

- **Decision-grade scope = pooled non-SS two-outcome markets only** -- the primary H2H (section 3)
  and the action-eligible secondary top-10 (S2). These accrue roughly one forward season to a
  verdict (K>=20 non-SS forward races reachable in that window; K>=60 needed for the terminal
  look per the 2026-07-20 amendment).
- **Descriptive-only until a separately pre-registered horizon extension:** win/group markets
  (~1 winner-event per race -- never decision-grade on the forward stream in a realistic horizon);
  all SS markets (near-noise per the audit, sections 5/7 -- stand-down, never a verdict);
  per-track-type stratified cells (~5-15 forward races per type over a season -- underpowered
  per-type).
- **Today's actual state:** K_forward_nonss = 1 non-SS forward race(s) against the K>=20 interim
  floor and the K>=60 terminal floor. At K=1, every look -- interim or (if it were reached)
  terminal -- returns UNDERPOWERED by construction; this is the correct, pre-registered outcome at
  N=1, not a shortfall.


## SECTION 9 -- C-trigger split

- **Non-SS tail (S5, win; thin top-3) -> ARMS F7 formulation-C trigger T1 -- but only on a
  documented finding, which a single race cannot establish.** T1 requires "a documented finding of
  systematic miscalibration in the non-SS tail markets"; with N=1 forward race there is no
  statistical basis to call today's win-market Brier decomposition a "finding" rather than noise.
  **T1 status today: NOT ARMED** (insufficient evidence -- one race). The forward win-market
  numbers above are reported for monitoring; whether they eventually arm T1 is a question for a
  later, better-powered look, not this one. Even if/when T1 arms, C stays gated/unbuilt until the
  owner elects to pull it with its own pre-registration (section 9).
- **SS miscalibration -> CONFIRMS the stand-down; NEVER a C-trigger.** The forward stream has
  0 SS pairs graded to date (race 5618 was SHORT, not SS) -- no SS evidence exists yet in the
  forward stream. The in-sample/2026-peeked SS numbers above are historical/dev-only and, per
  section 9, would confirm the pre-registered stand-down even if poorly calibrated -- they are
  never routed to C regardless of what they show.


## FORWARD stratum detail (race 5618, North Wilkesboro, SHORT, 2026-07-19)
- common set n=37, track_type=SHORT, unscored=[], unpredicted=[]
**N races contributing = 1**

#### H2H -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 666 | 0.2112 | 0.2114 | 0.0010 |
| SHORT | 666 | 0.2112 | 0.2114 | 0.0010 |

#### Win -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 37 | 0.0260 | 0.0263 | 0.0120 |
| SHORT | 37 | 0.0260 | 0.0263 | 0.0120 |

#### Top-10 -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 37 | 0.1889 | 0.1972 | 0.0420 |
| SHORT | 37 | 0.1889 | 0.1972 | 0.0420 |

#### H2H reliability (pooled non-SS, 10 equal-mass bins)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 66 | 0.3421 | 0.0909 |
| 2 | 67 | 0.4152 | 0.2388 |
| 3 | 66 | 0.4523 | 0.3333 |
| 4 | 67 | 0.4825 | 0.3433 |
| 5 | 67 | 0.5124 | 0.4179 |
| 6 | 66 | 0.5406 | 0.4545 |
| 7 | 67 | 0.5683 | 0.6119 |
| 8 | 66 | 0.5956 | 0.7273 |
| 9 | 67 | 0.6349 | 0.7612 |
| 10 | 67 | 0.7189 | 0.9104 |

Brier decomposition: reliability=0.0216  resolution=0.0596  uncertainty=0.2499
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=2.3005  intercept=-0.7218  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

#### H2H reliability by track type
##### SHORT
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 66 | 0.3421 | 0.0909 |
| 2 | 67 | 0.4152 | 0.2388 |
| 3 | 66 | 0.4523 | 0.3333 |
| 4 | 67 | 0.4825 | 0.3433 |
| 5 | 67 | 0.5124 | 0.4179 |
| 6 | 66 | 0.5406 | 0.4545 |
| 7 | 67 | 0.5683 | 0.6119 |
| 8 | 66 | 0.5956 | 0.7273 |
| 9 | 67 | 0.6349 | 0.7612 |
| 10 | 67 | 0.7189 | 0.9104 |

Brier decomposition: reliability=0.0216  resolution=0.0596  uncertainty=0.2499
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=2.3005  intercept=-0.7218  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

#### Win reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 3 | 0.0133 | 0.0000 |
| 2 | 4 | 0.0186 | 0.0000 |
| 3 | 4 | 0.0204 | 0.0000 |
| 4 | 3 | 0.0232 | 0.0000 |
| 5 | 4 | 0.0251 | 0.0000 |
| 6 | 4 | 0.0277 | 0.0000 |
| 7 | 3 | 0.0289 | 0.0000 |
| 8 | 4 | 0.0329 | 0.0000 |
| 9 | 4 | 0.0350 | 0.2500 |
| 10 | 4 | 0.0413 | 0.0000 |

Brier decomposition: reliability=0.0057  resolution=0.0060  uncertainty=0.0263

#### Top-10 reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 3 | 0.1448 | 0.0000 |
| 2 | 4 | 0.1980 | 0.0000 |
| 3 | 4 | 0.2141 | 0.0000 |
| 4 | 3 | 0.2410 | 0.3333 |
| 5 | 4 | 0.2573 | 0.7500 |
| 6 | 4 | 0.2815 | 0.5000 |
| 7 | 3 | 0.2895 | 0.3333 |
| 8 | 4 | 0.3170 | 0.0000 |
| 9 | 4 | 0.3378 | 0.2500 |
| 10 | 4 | 0.3879 | 0.5000 |

Brier decomposition: reliability=0.0562  resolution=0.0666  uncertainty=0.1972


## IN-SAMPLE stratum (dev smoke test, barred from decision & recal-fitting, 128 races, 2022-2026)

**N races contributing = 128**

#### H2H -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 67458 | 0.2178 | 0.2247 | 0.0307 |
| SS  SS STAND-DOWN -- not actionable | 13807 | 0.2495 | 0.2463 | -0.0131 |
| INT | 32461 | 0.2211 | 0.2258 | 0.0207 |
| SHORT | 21443 | 0.2112 | 0.2188 | 0.0347 |
| ROAD | 12993 | 0.2189 | 0.2307 | 0.0511 |
| OTHER | 561 | 0.2523 | 0.2491 | -0.0130 |

#### Win -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 3850 | 0.0262 | 0.0268 | 0.0202 |
| SS  SS STAND-DOWN -- not actionable | 771 | 0.0263 | 0.0265 | 0.0078 |
| INT | 1844 | 0.0264 | 0.0269 | 0.0186 |
| SHORT | 1224 | 0.0264 | 0.0270 | 0.0220 |
| ROAD | 748 | 0.0255 | 0.0260 | 0.0205 |
| OTHER | 34 | 0.0277 | 0.0285 | 0.0304 |

#### Top-10 -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 3850 | 0.1762 | 0.2001 | 0.1193 |
| SS  SS STAND-DOWN -- not actionable | 771 | 0.1897 | 0.1946 | 0.0247 |
| INT | 1844 | 0.1772 | 0.2000 | 0.1139 |
| SHORT | 1224 | 0.1740 | 0.1999 | 0.1297 |
| ROAD | 748 | 0.1763 | 0.2006 | 0.1213 |
| OTHER | 34 | 0.2068 | 0.2076 | 0.0038 |

#### H2H reliability (pooled non-SS, 10 equal-mass bins)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 6745 | 0.3268 | 0.1914 |
| 2 | 6746 | 0.4030 | 0.2941 |
| 3 | 6746 | 0.4444 | 0.3798 |
| 4 | 6746 | 0.4772 | 0.4481 |
| 5 | 6746 | 0.5074 | 0.5187 |
| 6 | 6745 | 0.5363 | 0.5967 |
| 7 | 6746 | 0.5660 | 0.6598 |
| 8 | 6746 | 0.5980 | 0.7216 |
| 9 | 6746 | 0.6358 | 0.7630 |
| 10 | 6746 | 0.7017 | 0.8245 |

Brier decomposition: reliability=0.0094  resolution=0.0398  uncertainty=0.2484
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.8534  intercept=-0.4234  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

#### H2H reliability by track type
##### SS (SS STAND-DOWN)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 1380 | 0.3324 | 0.4210 |
| 2 | 1381 | 0.4153 | 0.4497 |
| 3 | 1381 | 0.4554 | 0.4591 |
| 4 | 1380 | 0.4838 | 0.5239 |
| 5 | 1381 | 0.5084 | 0.5069 |
| 6 | 1381 | 0.5321 | 0.5301 |
| 7 | 1380 | 0.5560 | 0.5196 |
| 8 | 1381 | 0.5824 | 0.5612 |
| 9 | 1381 | 0.6147 | 0.5467 |
| 10 | 1381 | 0.6776 | 0.5952 |

Brier decomposition: reliability=0.0024  resolution=0.0026  uncertainty=0.2499
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=0.5132  intercept=0.2466  (shallower-than-1:1 == OVERCONFIDENCE (true rates less extreme than stated))

##### INT
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 3246 | 0.3237 | 0.2144 |
| 2 | 3246 | 0.4032 | 0.3189 |
| 3 | 3246 | 0.4450 | 0.3937 |
| 4 | 3246 | 0.4784 | 0.4677 |
| 5 | 3246 | 0.5091 | 0.5209 |
| 6 | 3246 | 0.5380 | 0.5887 |
| 7 | 3246 | 0.5672 | 0.6494 |
| 8 | 3246 | 0.5988 | 0.6975 |
| 9 | 3246 | 0.6371 | 0.7366 |
| 10 | 3247 | 0.7030 | 0.8078 |

Brier decomposition: reliability=0.0062  resolution=0.0331  uncertainty=0.2484
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.6815  intercept=-0.3354  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

##### SHORT
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 2144 | 0.3299 | 0.1525 |
| 2 | 2144 | 0.4049 | 0.2701 |
| 3 | 2144 | 0.4462 | 0.3708 |
| 4 | 2145 | 0.4797 | 0.4559 |
| 5 | 2144 | 0.5098 | 0.5373 |
| 6 | 2144 | 0.5382 | 0.6315 |
| 7 | 2145 | 0.5674 | 0.6960 |
| 8 | 2144 | 0.5992 | 0.7696 |
| 9 | 2144 | 0.6366 | 0.8223 |
| 10 | 2145 | 0.7031 | 0.8587 |

Brier decomposition: reliability=0.0170  resolution=0.0523  uncertainty=0.2468
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=2.1233  intercept=-0.5508  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

##### ROAD
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 1299 | 0.3300 | 0.1855 |
| 2 | 1299 | 0.4003 | 0.2794 |
| 3 | 1299 | 0.4409 | 0.3487 |
| 4 | 1300 | 0.4717 | 0.3923 |
| 5 | 1299 | 0.5004 | 0.5127 |
| 6 | 1299 | 0.5297 | 0.5535 |
| 7 | 1300 | 0.5613 | 0.6300 |
| 8 | 1299 | 0.5954 | 0.7136 |
| 9 | 1299 | 0.6326 | 0.7444 |
| 10 | 1300 | 0.6967 | 0.8115 |

Brier decomposition: reliability=0.0095  resolution=0.0401  uncertainty=0.2497
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.8830  intercept=-0.4543  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

##### OTHER
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 56 | 0.3180 | 0.3393 |
| 2 | 56 | 0.3923 | 0.4286 |
| 3 | 56 | 0.4318 | 0.4107 |
| 4 | 56 | 0.4614 | 0.4643 |
| 5 | 56 | 0.4863 | 0.4107 |
| 6 | 56 | 0.5083 | 0.3214 |
| 7 | 56 | 0.5335 | 0.5357 |
| 8 | 56 | 0.5628 | 0.5536 |
| 9 | 56 | 0.6003 | 0.4286 |
| 10 | 57 | 0.6680 | 0.4561 |

Brier decomposition: reliability=0.0118  resolution=0.0049  uncertainty=0.2458
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=0.3354  intercept=0.2684  (shallower-than-1:1 == OVERCONFIDENCE (true rates less extreme than stated))

#### Win reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 385 | 0.0145 | 0.0000 |
| 2 | 385 | 0.0190 | 0.0000 |
| 3 | 385 | 0.0212 | 0.0000 |
| 4 | 385 | 0.0235 | 0.0026 |
| 5 | 385 | 0.0256 | 0.0104 |
| 6 | 385 | 0.0282 | 0.0208 |
| 7 | 385 | 0.0311 | 0.0130 |
| 8 | 385 | 0.0341 | 0.0442 |
| 9 | 385 | 0.0375 | 0.0390 |
| 10 | 385 | 0.0432 | 0.1455 |

Brier decomposition: reliability=0.0013  resolution=0.0018  uncertainty=0.0268

#### Top-10 reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 385 | 0.1566 | 0.0208 |
| 2 | 385 | 0.2010 | 0.0519 |
| 3 | 385 | 0.2221 | 0.0805 |
| 4 | 385 | 0.2433 | 0.1273 |
| 5 | 385 | 0.2625 | 0.2052 |
| 6 | 385 | 0.2844 | 0.2857 |
| 7 | 385 | 0.3094 | 0.3506 |
| 8 | 385 | 0.3344 | 0.4857 |
| 9 | 385 | 0.3614 | 0.5403 |
| 10 | 385 | 0.4042 | 0.6208 |

Brier decomposition: reliability=0.0181  resolution=0.0419  uncertainty=0.2002


## 2026-OOS stratum (peeked secondary, non-citable except S6, 20 races)

**N races contributing = 20**

#### H2H -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 10697 | 0.2138 | 0.2257 | 0.0528 |
| SS  SS STAND-DOWN -- not actionable | 2738 | 0.2416 | 0.2371 | -0.0193 |
| INT | 5997 | 0.2153 | 0.2276 | 0.0541 |
| SHORT | 1998 | 0.2035 | 0.2138 | 0.0483 |
| ROAD | 2702 | 0.2180 | 0.2302 | 0.0530 |

#### Win -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 593 | 0.0256 | 0.0263 | 0.0259 |
| SS  SS STAND-DOWN -- not actionable | 150 | 0.0255 | 0.0260 | 0.0165 |
| INT | 333 | 0.0255 | 0.0263 | 0.0291 |
| SHORT | 111 | 0.0257 | 0.0263 | 0.0232 |
| ROAD | 149 | 0.0256 | 0.0261 | 0.0207 |

#### Top-10 -- BSS = 1 - B_model/B_base
| stratum | n | B_model | B_base | BSS |
|---|---|---|---|---|
| pooled non-SS | 593 | 0.1680 | 0.1970 | 0.1473 |
| SS  SS STAND-DOWN -- not actionable | 150 | 0.1912 | 0.1955 | 0.0220 |
| INT | 333 | 0.1676 | 0.1972 | 0.1502 |
| SHORT | 111 | 0.1629 | 0.1972 | 0.1743 |
| ROAD | 149 | 0.1727 | 0.1964 | 0.1204 |

#### H2H reliability (pooled non-SS, 10 equal-mass bins)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 1069 | 0.3200 | 0.1862 |
| 2 | 1070 | 0.3922 | 0.2374 |
| 3 | 1070 | 0.4334 | 0.3262 |
| 4 | 1069 | 0.4678 | 0.3863 |
| 5 | 1070 | 0.4994 | 0.4935 |
| 6 | 1070 | 0.5289 | 0.5421 |
| 7 | 1069 | 0.5601 | 0.6445 |
| 8 | 1070 | 0.5934 | 0.7393 |
| 9 | 1070 | 0.6338 | 0.7822 |
| 10 | 1070 | 0.7040 | 0.8495 |

Brier decomposition: reliability=0.0132  resolution=0.0489  uncertainty=0.2496
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.9838  intercept=-0.4996  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

#### H2H reliability by track type
##### SS (SS STAND-DOWN)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 273 | 0.3362 | 0.3333 |
| 2 | 274 | 0.4137 | 0.4453 |
| 3 | 274 | 0.4507 | 0.4307 |
| 4 | 274 | 0.4792 | 0.5146 |
| 5 | 274 | 0.5057 | 0.5146 |
| 6 | 273 | 0.5322 | 0.5092 |
| 7 | 274 | 0.5564 | 0.5073 |
| 8 | 274 | 0.5829 | 0.6277 |
| 9 | 274 | 0.6183 | 0.5803 |
| 10 | 274 | 0.6995 | 0.6679 |

Brier decomposition: reliability=0.0010  resolution=0.0085  uncertainty=0.2498
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=0.8809  intercept=0.0572  (shallower-than-1:1 == OVERCONFIDENCE (true rates less extreme than stated))

##### INT
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 599 | 0.3212 | 0.1970 |
| 2 | 600 | 0.3942 | 0.2167 |
| 3 | 600 | 0.4358 | 0.3283 |
| 4 | 599 | 0.4712 | 0.3873 |
| 5 | 600 | 0.5028 | 0.4700 |
| 6 | 600 | 0.5317 | 0.5267 |
| 7 | 599 | 0.5627 | 0.6210 |
| 8 | 600 | 0.5955 | 0.7300 |
| 9 | 600 | 0.6369 | 0.7667 |
| 10 | 600 | 0.7067 | 0.8383 |

Brier decomposition: reliability=0.0122  resolution=0.0468  uncertainty=0.2499
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.9310  intercept=-0.4879  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

##### SHORT
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 199 | 0.3272 | 0.1005 |
| 2 | 200 | 0.3966 | 0.2650 |
| 3 | 200 | 0.4352 | 0.2850 |
| 4 | 200 | 0.4680 | 0.3850 |
| 5 | 200 | 0.5003 | 0.5350 |
| 6 | 199 | 0.5309 | 0.6432 |
| 7 | 200 | 0.5608 | 0.7200 |
| 8 | 200 | 0.5942 | 0.8250 |
| 9 | 200 | 0.6334 | 0.8450 |
| 10 | 200 | 0.7102 | 0.9050 |

Brier decomposition: reliability=0.0273  resolution=0.0707  uncertainty=0.2474
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=2.3779  intercept=-0.6753  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

##### ROAD
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 270 | 0.3134 | 0.1963 |
| 2 | 270 | 0.3832 | 0.2963 |
| 3 | 270 | 0.4271 | 0.3333 |
| 4 | 270 | 0.4606 | 0.4037 |
| 5 | 271 | 0.4909 | 0.4871 |
| 6 | 270 | 0.5212 | 0.5481 |
| 7 | 270 | 0.5529 | 0.6259 |
| 8 | 270 | 0.5878 | 0.6778 |
| 9 | 270 | 0.6276 | 0.7815 |
| 10 | 271 | 0.6921 | 0.8303 |

Brier decomposition: reliability=0.0090  resolution=0.0406  uncertainty=0.2497
Fitted reliability line (weighted OLS, obs ~ a + b*pred): slope=1.8295  intercept=-0.4071  (steeper-than-1:1 == UNDERCONFIDENCE (true rates more extreme than stated), matching the audit's known finding (sec. 7))

#### Win reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 59 | 0.0142 | 0.0000 |
| 2 | 59 | 0.0184 | 0.0000 |
| 3 | 59 | 0.0205 | 0.0000 |
| 4 | 60 | 0.0223 | 0.0000 |
| 5 | 59 | 0.0244 | 0.0169 |
| 6 | 59 | 0.0268 | 0.0169 |
| 7 | 60 | 0.0298 | 0.0000 |
| 8 | 59 | 0.0333 | 0.0339 |
| 9 | 59 | 0.0368 | 0.0339 |
| 10 | 60 | 0.0429 | 0.1667 |

Brier decomposition: reliability=0.0018  resolution=0.0024  uncertainty=0.0263

#### Top-10 reliability (pooled non-SS)
| bin | n | mean predicted | observed freq |
|---|---|---|---|
| 1 | 59 | 0.1536 | 0.0000 |
| 2 | 59 | 0.1954 | 0.0169 |
| 3 | 59 | 0.2146 | 0.0847 |
| 4 | 60 | 0.2321 | 0.0667 |
| 5 | 59 | 0.2511 | 0.1356 |
| 6 | 59 | 0.2712 | 0.2712 |
| 7 | 60 | 0.2975 | 0.3500 |
| 8 | 59 | 0.3260 | 0.4746 |
| 9 | 59 | 0.3541 | 0.5932 |
| 10 | 60 | 0.4008 | 0.7000 |

Brier decomposition: reliability=0.0285  resolution=0.0569  uncertainty=0.1970


## Resolved (not flagged) implementation notes
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

