# INCENTIVE_ANALYTICS.md -- F19 build report (research/domain_knowledge_scan.md sections 5/10.3)

Tier A analytics only: descriptive answers to standing playoff-desperation lore, built entirely
from `silver.results` (2017+, weekend-feed, results-grade) and `silver.stage_results` (2020+,
schema floor). No frozen surface touched -- `walkforward.py`, `predict_next.py`, and every gold
table are unmodified; nothing here joins a feature bank. Script: `src/incentive_analytics.py`
(read-only against `data/nascar.duckdb`). Any effect below strong enough to justify an M-tier A/B
needs its own later pre-registered spec, conditioned on surviving the 2026 format break -- not
built here.

## 0. Definitions (frozen elsewhere, reused verbatim; see the script's module docstring)

- **Crash-class / mech-class DNF**: `specs/dnf_status_feature.md` section 1 taxonomy, reused
  exactly -- `status in {'accident','dvp'}` = crash-class; DNF = `status != 'running'`. Verified
  against `silver.results.finishing_status` (lowercased/stripped) directly: the same values appear
  (`accident` 1,303, `dvp` 61, `running` 11,269, plus the same long mechanical-cause tail) as the
  spec's original `races_parsed.pkl`-sourced inventory, confirming the taxonomy transfers across
  the two different source paths (lap-times-derived `status` vs weekend-feed-derived
  `finishing_status`).
- **Cutline distance**: `|points_position_prior - 16|`, where `points_position_prior` is read from
  the driver's most recent **prior** in-season race (a `LAG` within `(year, driver_id)`, ordered by
  date) -- never the current race's own payload. Leak-free by construction (scan section 5.2). For
  the rare driver who sits out a race, this is their last known state, not necessarily race *t-1*
  exactly; noted, not silently assumed.
- **Ordinal-only caveat** (scan section 5.2/9.3, honored exactly as instructed): season point
  *totals* are not in-feed, only the official ordinal `points_position`. No points-distance metric
  was attempted anywhere in this analysis.
- **Regular season = the first 26 races of a season; playoffs = the last 10.** Verified, not
  assumed: `silver.races.playoff_round` for 2020-2025 confirms `36 - n_playoff == 26` in every
  season checked (10 playoff races 2020-2024, 9 in 2025 -- the already-documented race_id 5580
  `weekend_race`-null gap, not a new anomaly). Used instead of `playoff_round` directly because
  that field is a schema floor (0/absent 2017-2019, `DATA_DICTIONARY` 9g) and this 26/10 rule is
  not -- it is also externally confirmed by the 2026 rule announcement itself ("top 16 on points
  after 26 races qualify").
- **Late window** = the last 5 regular-season races (`season_race_num` 22-26); a 3-race window
  (24-26) is reported alongside as the robustness check the kickoff's "3-5" range asks for.
- **Bubble** := cutline distance <= 5 (ranks 11-21, the order of magnitude of the scan's own
  "~6-10 bubble drivers" estimate). **Locked-in** := `points_position_prior <= 10` (comfortably
  inside the cutline, scan section 5.1 claim (b)) -- deliberately one-sided (only the safely-in
  side), since "locked-in" in the lore means cushioned, not merely far from 16 in either direction
  (see the Q(a) confound below).

## 1. Q(a) -- does crash-class DNF rate rise with cutline proximity late in the season?

**Finding: no -- and the naive `|distance|` bucketing that would suggest otherwise is a confound.**

`|distance|`-bucketed, last-5-races window, 2017-2025 (n=1,710 driver-races):

| bucket | n | crash rate | DNF rate |
|---|---:|---:|---:|
| 0-2 (razor-edge) | 222 | 9.9% | 12.2% |
| 3-5 (bubble) | 268 | 8.2% | 10.8% |
| 6-10 (moderate) | 449 | 11.8% | 13.1% |
| 11+ (comfortable) | 771 | 12.2% | 18.7% |

Read naively, DNF rate *rises* with `|distance|` (Pearson r=+0.116, p<0.0001 on the DNF indicator;
crash-class alone: r=+0.014, p=0.56, not significant) -- the opposite direction the lore predicts,
and it looks like it discredits the desperation story outright. It doesn't: the "11+ comfortable"
bucket silently pools two very different populations under one `|distance|` value -- front-runners
safely inside the top 16 (rank 1-5) *and* backmarkers with no realistic transfer hope (rank 27+,
generally weaker equipment, structurally higher mechanical-DNF rates for reasons that have nothing
to do with playoff incentives). Disaggregating by rank instead of `|distance|` removes the
confound:

| rank bucket | n | crash rate | DNF rate |
|---|---:|---:|---:|
| 1-10 (safe) | 450 | 11.8% | 13.1% |
| 11-16 (protecting) | 270 | 9.3% | 11.5% |
| 17-21 (chasing) | 220 | 8.6% | 11.4% |
| 22+ (backmarker) | 770 | 12.2% | 18.7% |

The bubble itself (protecting + chasing, ranks 11-21) has the **lowest** crash and DNF rates of any
group in the last 5 regular-season races, 2017-2025 -- both extremes (safe top-10 and hopeless
backmarkers) run hotter. This holds in the 3-race window too (`last3`, n=1,042: bubble crash rates
9.9%/11.3% vs safe 13.7% and backmarker 15.5%) and is not a late-season-specific artifact --
`rest_of_season` (races 1-21, n=6,676) shows the same rank ordering, just compressed. **This is a
clean, well-powered null for the "bubble drivers crash more" claim** (a "well-run null retires a
garage trope" result, per project convention) -- if anything the bubble cohort races *cleaner*
than the rest of the field late in the year, plausibly because bubble drivers are disproportionately
full-season, well-resourced teams with something concrete to protect/chase, while the DNF-heavy
tail is backmarker equipment attrition unrelated to playoff position.

## 2. Q(b) -- do bubble drivers' stage points spike relative to their own season baseline?

**Finding: yes, and it is the strongest and cleanest of the three results.** 2020-2025 only
(`silver.stage_results` schema floor -- empty 2017-2019, not a bug). Baseline = each driver's own
mean stage points over regular-season races 1-21 that season; spike = late-window (22-26) race
stage points minus that baseline.

| cohort | n | mean spike | median spike | mean baseline | mean actual (late) | one-sample t (spike vs 0) |
|---|---:|---:|---:|---:|---:|---:|
| bubble (cutline dist <= 5) | 325 | **+0.86** | -1.29 | 2.88 | 3.74 | t=3.03, p=0.0026 |
| locked-in (rank <= 10) | 300 | **-1.28** | -2.05 | 6.90 | 5.62 | t=-3.94, p=0.0001 |
| all late-window rows | 1,128 | -0.02 | -0.29 | 2.93 | 2.91 | t=-0.17, p=0.87 (no pooled effect) |

Bubble drivers gain stage points relative to their own baseline late in the year (significant,
p=0.003); locked-in drivers lose stage points relative to their own baseline over the same window
(significant, p=0.0001) -- and the difference between the two cohorts is highly significant
(Mann-Whitney U, p=1.4e-7). The mean/median divergence for bubble drivers (positive mean, negative
median) says the effect is driven by a subset of strong stage results rather than a uniform shift
-- consistent with "occasionally gambling for stage points," not "always racing harder for them."
Both halves of the lore -- (a) bubble drivers chase stage points, (b) locked-in drivers ease off --
measure true in this data, 2020-2025.

## 3. Q(c) -- does the locked-in cohort's expected-vs-actual finish correlation degrade late?

**Finding: no significant effect -- a noisy null.** Proxy for "expected finish" (deliberately NOT
the frozen PL model's own walk-forward rho: that model's pace features have a lap-times data floor
of 2020, and gold scopes the production model to `year >= 2022` -- reproducing its rho back to
2017 would mean extending gated model machinery across years it has never been proven on, out of
scope for a Tier A session). Instead: each driver's own season-to-date mean finishing position
(strictly prior races, same season), Spearman-correlated against actual finish, computed per race,
restricted to the locked-in cohort (rank <= 10) present in that race.

| window | mean rho | n races |
|---|---:|---:|
| early season (races 1-21) | 0.0295 | 180 |
| late window (races 22-26) | 0.0211 | 45 |

Both correlations are weak-positive (as expected -- recent form does mildly predict finish) and
the late-window value is lower, in the lore-predicted direction, but the per-season paired
comparison is noisy and not significant (Wilcoxon signed-rank on the 9 season pairs, p=1.0):

| year | early rho | late rho |
|---|---:|---:|
| 2017 | 0.010 | 0.051 |
| 2018 | 0.141 | -0.052 |
| 2019 | 0.180 | 0.061 |
| 2020 | 0.119 | 0.172 |
| 2021 | -0.044 | 0.029 |
| 2022 | -0.042 | -0.037 |
| 2023 | -0.075 | 0.191 |
| 2024 | -0.126 | -0.027 |
| 2025 | 0.103 | -0.198 |

Five of nine seasons move in the lore-predicted direction (late < early), four don't. With only 9
season-level observations this comparison is honestly underpowered to detect anything short of a
large effect -- reported as a genuine null, not evidence of absence at high confidence.

## 4. The 2026 format break -- reported separately, not pooled

NASCAR abolished playoff points and win-and-you're-in for 2026 (announced 2026-01-12). Confirmed
independently in this session against our own feed (not just cited from the domain scan):
`playoff_points_earned = 0` across all 798 Cup driver-race rows through the 21 completed 2026
races, vs 65-85 rows/season > 0 in every season 2019-2025. **Every effect measured above in
sections 1-3 lived entirely in the old elimination format (win-and-in, playoff-point cushions,
must-win elimination races) and is not assumed to transfer to 2026's pure points-accumulation
format.** They are reported as historical (2017-2025 / 2020-2025) findings only.

**Live 2026 tracking:** 21 of 26 regular-season races completed as of this session (5 remain
before the playoff cutoff) -- too early for a 2026 late-window comparison; that window (races
22-26) hasn't happened yet and this analysis should be re-run once it has. Current cutline
standings (top 21 by points position, entering the next race):

| points position | cutline distance |
|---:|---:|
| 1-10 | 15 down to 6 |
| 11 | 5 |
| 12 | 4 |
| 13 | 3 |
| 14 | 2 |
| 15 | 1 |
| 16 (on the cutline) | 0 |
| 17-21 | 1 up to 5 |

(Full driver-level board is in the script's stdout; omitted here as PII-adjacent detail with no
descriptive value beyond the distance distribution shown.)

## 5. Explicitly out of scope

- **H5's championship-contender flag** (0.3% exposure) is not analyzed here -- routed to F3 as a
  pace-estimate sensitivity check (scan section 5.3), per the kickoff's instruction not to
  re-litigate it in this session.
- **No points-distance metric** was built or attempted (section 0's ordinal-only caveat).
- **No feature bank was touched.** These are descriptive findings only. Q(b)'s clean, significant,
  bidirectional result (section 2) is the strongest candidate for a future M-tier A/B, but any such
  A/B needs its own pre-registered spec explicitly conditioned on the 2026 format break (section 4)
  -- not decided or built here.

## 6. Reproduction

```
cd src && python incentive_analytics.py
```

Reads `data/nascar.duckdb` read-only via `warehouse.DB_PATH`; writes nothing. Anaconda `python`
(duckdb/numpy/scipy/pyarrow), same interpreter as the other 13 gates -- see `GATES.md`.
