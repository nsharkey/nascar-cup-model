# Next Gen equipment-share decomposition (F14)

Built per `specs/equipment_share_decomposition.md`. Tier A / analytics — descriptive only, never
joined to `gold.wf_features`, never changes the frozen model. Source: hierarchical driver/team/make
variance decomposition of Cup finishing order, 2022–2026 (Next Gen era), ported from van Kesteren &
Bergkamp (*JQAS* 2023)'s rank-ordered-logit template (`research/external_knowledge_scan.md` §3.6).

## Headline: the F11 trigger verdict

**NOT ARMED.** Primary variant (DNF included, this project's own `finish` convention) team
variance share = **21.4%**, below the pre-registered 25% bar (spec §5.1). NASCAR's Next Gen
parity rules produce a driver/team/make split of **71.4% / 21.4% / 7.1%** — team/equipment
matters, and is far from negligible, but does not clear the bar this session pre-registered for
spec'ing F11 (the banked hierarchical-Bayesian-PL lane). This is a **clean, well-reasoned null**,
exactly the kind of documented negative this project's doctrine treats as a success, not a
disappointment: it permanently answers "how much does Next Gen equipment matter, relative to
driver skill, under this era's parity rules" without needing F11's much heavier machinery.

Compare to the source paper's own hybrid-era F1 finding: constructor ≈ 88% of variance (their
cross-method range 64–88%). NASCAR's Next Gen team share (21.4%) sits roughly a third to a
quarter of F1's low end — a large, plausible gap, consistent with what the Next Gen parity rules
(spec-package chassis, single-source parts, tightly controlled aero) are specifically designed to
produce, and with this session's own pre-registered expectation ("expected well below F1's ~88%
given the parity rules").

## Fitted variance shares (both variants)

| variant | lam (driver, team, make) | SD (driver, team, make) | var share (driver / team / make) | trigger |
|---|---|---|---|---|
| **primary** (DNF included) | 3.0, 10.0, 30.0 | 0.408, 0.224, 0.129 | **71.4% / 21.4% / 7.1%** | NOT ARMED (team share 21.4% < 25%) |
| dnf_excluded (sensitivity) | 3.0, 30.0, 30.0 | 0.408, 0.129, 0.129 | 83.3% / 8.3% / 8.3% | n/a (decision keys off primary only) |

`SD_X = sqrt(1/(2*lam_X))` is the prior-implied (headline) standard deviation selected by
leave-one-season-out cross-validated log-likelihood, per spec §4.1/§5 — the de-shrunk estimate of
each factor's true between-entity spread. The raw empirical population SD of the fitted
(ridge-shrunk) point estimates themselves is smaller in every case, as expected (spec §5, shrinkage
attenuates point estimates toward zero):

| variant | SD empirical (driver, team, make) |
|---|---|
| primary | 0.231, 0.177, 0.057 |
| dnf_excluded | 0.335, 0.111, 0.082 |

## DNF-exclusion sensitivity check (van Kesteren & Bergkamp's own check, imported verbatim)

Consistent with the source paper's own finding (scan §3.7, E6: "DNF handling materially reorders
skill estimates"), excluding DNF drivers from each race's order **does** materially move the
shares here too — but in the opposite direction from a naive guess: dropping DNFs pushes *more*
weight onto driver (71.4% → 83.3%) and *less* onto team and make (21.4%→8.3%, 7.1%→8.3%). Read
plainly: a meaningful share of what looks like "team effect" in the primary variant is carried by
DNF-heavy or DNF-light patterns correlated with team/equipment (mechanical failures cluster by
team in ways finishing-position-among-classified-finishers does not capture) — removing DNFs from
the likelihood removes exactly that channel, leaving relatively more of the remaining variance
attributable to driver skill among classified finishers. This is reported for transparency per the
imported sensitivity check; it does not change the §5.1 decision, which keys off the primary
(DNF-included) variant only, per this project's own established `finish` convention.

## Connectivity diagnostic (standing requirement, `external_knowledge_scan.md` §3.2)

Per-season + pooled strong-connectivity check on the driver-level "finished-ahead-of" digraph
(`scipy.sparse.csgraph.connected_components`, primary variant):

| window | n drivers | components | strongly connected? | offending driver |
|---|---:|---:|---|---|
| pooled 2022–2026 | 101 | 1 | **yes** | — |
| 2022 | 62 | **2** | **no** | `driver_id` 3816 — Andy Lally (1 race, finished 39/39, `status='suspension'`) |
| 2023 | 64 | 1 | yes | — |
| 2024 | 62 | **2** | **no** | `driver_id` 3170 — David Starr (1 race, finished 37/37, `status='steering'`) |
| 2025 | 60 | 1 | yes | — |
| 2026 (partial) | 52 | 1 | yes | — |

Team and make factors are strongly connected in every window (31 teams / 3 makes, densely
inter-raced — trivially satisfied, checked generically rather than assumed).

This is a **real, concrete confirmation** of the standing requirement's own text ("NASCAR data
genuinely fails this on some real windows"), not a hypothetical: two of five season windows fail
Hunter's Assumption 1, and both failures have the identical, textbook Hunter signature (his own
example: "always-last drivers") — a single driver who ran exactly one race that season, finished
dead last, and DNF'd, so they were beaten by the whole field but beat no one, leaving them
unreachable *from* the rest of the graph. This does not block the headline (pooled 2022–2026)
fit — already strongly connected on its own — nor any fit here, since the block-ridge penalty
(spec §4) guarantees a finite, unique estimate regardless of connectivity. It **would** bind if this
model were ever re-run as a rolling per-season walk-forward, which is exactly F11's territory, not
this session's.

## Part-timer shrinkage (standing requirement, part-timer behavior stated up front)

Spot check, primary variant, driver factor — every driver with exactly one race in scope clusters
tightly near zero (range **−0.15 to +0.08**) regardless of that single race's raw outcome, while
164-race full-time drivers range far more widely (**−0.04 to +0.42**):

| driver | n_races | fitted worth |
|---|---:|---:|
| Burt Myers | 1 | −0.148 |
| Juan Pablo Montoya | 1 | −0.088 |
| Matt Crafton | 1 | −0.069 |
| Parker Kligerman | 1 | −0.031 |
| Ryan Truex | 1 | −0.014 |
| Boris Said | 1 | +0.014 |
| Grant Enfinger | 1 | +0.025 |
| Jacques Villeneuve | 1 | +0.081 |
| Austin Cindric | 164 | +0.042 |
| Chase Briscoe | 164 | +0.156 |
| Todd Gilliland | 164 | +0.179 |
| Christopher Bell | 164 | +0.288 |
| Tyler Reddick | 164 | +0.337 |
| William Byron | 164 | +0.342 |
| Ryan Blaney | 164 | +0.350 |
| Daniel Suárez | 164 | +0.416 |

This is the exact ridge/partial-pooling behavior spec §5.3 pre-registered: entities with little
data contribute little log-likelihood pull against the fixed quadratic penalty, so they are shrunk
hardest toward the common baseline. No separate minimum-sample floor is applied — the
regularization *is* the floor, continuously, by construction.

## Named worths, primary variant (top/bottom 5)

| factor | top 5 (worth, n_races) | bottom 5 (worth, n_races) |
|---|---|---|
| driver | Ross Chastain +0.620 (164), Chase Elliott +0.532 (157), Chris Buescher +0.434 (163), Kevin Harvick +0.429 (72), Daniel Suárez +0.416 (164) | Daniil Kvyat −0.439 (3), BJ McLeod −0.410 (66), Jimmie Johnson −0.399 (16), Brennan Poole −0.398 (8), Chad Finchum −0.387 (12) |
| team | RFK Racing +0.383 (142), Hendrick Motorsports +0.351 (164), Joe Gibbs Racing +0.254 (164), Team Penske +0.206 (164), Stewart-Haas Racing +0.181 (108) | Power Source −0.339 (13), NY Racing Team −0.303 (32), Garage 66 −0.252 (26), Rick Ware Racing −0.239 (164), Team Hezeberg −0.218 (6) |
| make | Toyota +0.081, Ford −0.040, Chevrolet −0.041 | (same 3 — only 3 makes exist) |

Sign sanity confirmed mechanically (`gate_equip_share.py` check 6, not just eyeballed here): for
every factor, the single highest-worth entity has a better (numerically lower) mean actual
`finish` over its own scope races than the single lowest-worth entity — the fitted direction is
right-way-round, not inverted (the exact class of bug `report/CALIBRATION_BACKTEST.md`/M3 already
found once elsewhere in this codebase).

## Team-key canonicalization (spec §1.2)

32 raw `team_name` strings → 31 canonical entities: exactly one pair merged
(`'TrackHouse Racing'`/`'Trackhouse Racing'`, a mid-window capitalization artifact, verified same
`owner_id`), while every genuine rename remains distinct — `Stewart-Haas Racing` / `Haas Factory
Team` (real 2024→2025 ownership change), `Roush Fenway Keselowski Racing` / `RFK Racing`, `Petty
GMS` / `Petty GMS Motorsports` — per `team_mfr_pooling.md` §1's already-adopted policy, imported
verbatim rather than re-litigated. `gate_equip_share.py` check 5 asserts both halves of this
mechanically (the merge happened; the renames did not get over-merged), not just narratively.

## Build-graph isolation

`gold.equip_share_worths` / `gold.equip_share_summary` / `gold.equip_share_connectivity` appear
zero times in `gold_build.py`, `walkforward.py`, or `predict_next.py` (`gate_equip_share.py` check
2, source-text scan). Nothing here is ever joined into `gold.wf_features`.

## Gate result

`gate_equip_share.py` — **PASS**. Full re-derivation (both variants' entire leave-one-season-out
CV + coordinate-descent λ-selection + final refit, re-run from `silver.driver_race`/
`silver.results`) reproduces every stored λ, worth, and summary/variance-share number within
`math.isclose(rel_tol=1e-6)`; connectivity table reproduces exactly (integer/boolean/string
fields, no tolerance needed); team-key canonicalization and sign-direction checks both pass.
18/18 gates green (17 inherited + this session's new gate). Full detail:
`specs/equipment_share_decomposition.md` `## RESULT — F14`.
