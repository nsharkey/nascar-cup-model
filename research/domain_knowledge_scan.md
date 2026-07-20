# NASCAR domain-knowledge scan — what the sport knows that our feature set ignores (F16)

**Session:** F16 research spike · Fable 5 · 2026-07-19
**Status:** research report — **proposes only.** Nothing here builds anything,
changes any frozen spec, or touches the production model. Doctrine, verbatim
(INTEGRATION.md / plan): **nothing enters the frozen PL prediction model
without its own pre-registered, walk-forward-gated A/B.**
**Deliverable:** the complement to F6 (`external_knowledge_scan.md`). F6 asked
"how does everyone else model NASCAR" and structurally filtered out domain
lore that lacked rigorous external verification. This spike asks "what does
the sport ITSELF know that our feature set ignores" — crew chief changes,
playoff incentives, tire allocation, draft alliances — admitting
practitioner/domain knowledge as **hypothesis generators with explicit
credibility discounting**. An idea qualifies only if it also has a
measurable, walk-forward-safe proxy in data this project already holds.
The rigor lands at the A/B gate, not at source verification.

---

## 0. Executive summary

Five findings, in decreasing order of consequence:

1. **The feed knows far more than the model reads — and this session
   measured exactly what.** The weekend-feed result row carries 39 fields;
   the frozen model consumes 9 of them. Verified directly against
   bronze/silver (§3): `crew_chief_id`/`crew_chief_fullname` are 100%
   populated for 2022+ (exactly the model's era), `points_position` is
   populated 2017+ and confirmed to be *post-race official standings*
   (`points_delta` reconciles 96% of transitions), and `owner_id` carries
   organizational continuity across at least one team rename that the
   pooling spec's `team_name` key breaks. Against that: `pit_box` is dead
   (populated in 13 of 392 Cup races — a 13-race 2023 block), `winnings`,
   `race_purse`, and `attendance` are all-zero, `points_delta` died after
   2022, and the structured `infractions`/`pit_reports` race-level lists
   are populated **2020–2022 only**. The kickoff's assumed field list was
   right about presence but wrong about live coverage in three places —
   the verified coverage map is §3's table.
2. **The strongest new model hypothesis is personnel change (crew chief +
   ride), and its event frequency is now measured.** Cup points races
   2022–2025: 185 within-season crew-chief changes — 75 of which revert
   within 8 races (the suspension/interim signature; the 2022 wheel-loss
   rule's 4-race crew-chief suspensions explain the 2022 peak of 70, and
   its 2023 repeal [V-web] explains the decline to 13 by 2025) — plus
   21–30 offseason changes/season and 5–17 within-season ride changes.
   A low-tenure/recent-change feature would be active in roughly 10% of
   eligible driver-races — the same order as the DNF feature's 13.9% base
   rate, i.e. plausibly powered for the +0.005 bar without being likely to
   clear it. → candidate session **F18** (§4).
3. **The incentive-state hypothesis is measurable but was just structurally
   broken by NASCAR — in our favor as forecasters, against us as testers.**
   The bubble-desperation mechanism everyone in the garage asserts is
   testable from `points_position` (as-of, official, leak-free) plus
   `playoff_round`/`driver_is_in_chase` (2020+/2017+). But NASCAR's
   announced 2026 return to a Chase format [V-web, confirmed against our
   own feed data: `playoff_points_earned` = 0 across all 880 result rows
   of 2026 while 2019–2025 average ~76/season] eliminates playoff points
   AND win-and-you're-in — the exact mechanisms a 2022–2025 backtest would
   validate a feature against. A backtest-won bubble feature could be
   adopted precisely when its mechanism stopped existing. Incentive work
   is therefore proposed as **analytics first** (F19), with any model A/B
   explicitly conditioned on the descriptive effect surviving the format
   break. The track-audit's H5 (championship-race contender flag) reduces
   to 1 race × 4 drivers/season — hopeless for the ρ gate; routed to F3 as
   a covariate note instead (§5).
4. **Tires: the allocation data this project doesn't hold isn't worth
   chasing; the tire behavior it does hold is already spoken for.**
   Goodyear per-race allocations/compounds live in nascar.com editorial
   "tire setup" articles [V-web] — an NDM-covered, bot-blocked property
   (F6 §6.5), so systematic collection is ToS-out under the A6 posture;
   and sets-per-weekend is largely deterministic by track type anyway.
   The in-feed proxies (per-stop tires-changed flags, 2020+) already
   belong to F3's SFS/PIS scope. `pit_box` — the field the track-audit's
   H7 hoped would expose pit-road geometry — is confirmed dead in-feed.
   Recorded as a documented null; no session (§6).
5. **The cheapest concrete win is a small silver extension, not a model
   idea.** Four structured race-level objects the weekend-feed has carried
   for years are in bronze but absent from silver: `caution_segments`
   (2017+ — **two years below the live-flag-data floor**, with a clean
   caution-*reason* taxonomy and the lucky-dog beneficiary),
   `stage_results` (2020+, per-stage finishing order + stage points),
   `race_leaders` (2017+, leader segments), and `playoff_round` +
   `stage_4_laps` onto `silver.races`. One low-effort session (**C4**)
   materializes all of them and directly widens F3's and F19's data floor
   (§3.3, §8).

Verdict on the kickoff's prior: confirmed. Expected payoff is **MED for
model features** (low-frequency events fight the +0.005 practical floor),
**HIGH for analytics/DFS and for replacing pundit lore with measured
answers** — and the single highest-value output of the sweep is the
verified inventory itself.

---

## 1. Method and evidence standard

This spike deliberately inverts F6's posture. F6 admitted only claims that
survived adversarial multi-agent verification against fetched primary
sources; domain lore without published evidence was structurally excluded.
Here, practitioner/garage knowledge is admitted **as hypotheses**, each
carrying an explicit credibility label, and the bar an idea must clear is
different: (mechanism stated) + (measurable, walk-forward-safe proxy in
data we already hold) + (non-duplication against every existing plan row).
Adoption rigor is unchanged and lives where it always lives — the
pre-registered, walk-forward-gated A/B.

Evidence labels used throughout:

| Label | Meaning |
|---|---|
| **[DATA]** | Verified this session directly against the project's own bronze/silver archive (DuckDB queries over `data/nascar.duckdb`; raw `json.gz` payload scans). The strongest class in this report. |
| **[V-web]** | Verified against a fetched/quoted external source this session — single-verifier grade, NOT F6's triple-verification. |
| **[LORE]** | Practitioner/domain assertion admitted as a hypothesis generator. Credibility-discounted by construction; never adoption evidence. |
| **[U]** | Unverifiable this session; stated as such. |

Governance tiers are F5/F6's (M = model-facing, A/B-gated; A = analytics/
reference; D = data/infrastructure; G = governance).

All [DATA] claims were computed against the archive as of 2026-07-19:
bronze holds 392 Cup weekend-feeds 2017–2026 (24 completed 2026 races;
race 5618's results were not yet posted), `silver.results` holds 33
columns × all stored races, and `gold.wf_features` holds 6,083 rows of
which 5,650 are model-eligible (`n_hist ≥ 5 AND has_pace`).

---

## 2. What already exists (the overlap baseline)

Pinned so every overlap statement below is exact:

- **Frozen engine:** walk-forward covariate-PL, features
  `[fin, pace, typed, start]`, `pace_med85`, half-life 8, `MY_TYPE`,
  ridge λ=0.5. Consumes 9 result-row fields (via `parse_lib`): `finish`,
  `start`, `qspeed`, `status`, `team_id`, `car_make`, `laps_led`,
  `laps_completed`, `disqualified` — plus lap-times for pace.
- **Pre-registered feature A/Bs:** DNF/status (F1, V1–V3), team/mfr
  pooling (F2, W1–W3, org key = `team_name`, renames-as-new-entities
  recorded as a known limitation with a future alias-table variant
  explicitly requiring its own spec).
- **Track work:** F3 (ten empirical track metrics incl. ARS attrition
  decomposition, PIS pit importance, SFS strategy entropy), F4 (empirical
  similarity), C3 done (track_dim/xwalk/priors/rules_era + leakage-free
  config-novelty features). Track-audit novel hypotheses H1–H8 live in the
  bundle; H5 = championship-incentive flag, H7 = pit-road geometry.
- **Era work:** F9 (era-reset A/B: `era_key`/`era_race_number`/
  `hp750_2026`) owns rules/format-era features.
- **Likelihood/dynamics lanes:** F10 (Kalman recency), F11 (hierarchical,
  conditional), F12 (attrition likelihood).
- **Loop data:** F13 owns driver loop-metric histories from `silver.laps`;
  `silver.live_final` already carries the official per-race loop numbers
  (ARP, quality passes, fastest laps, closers) back to 2017.
- **Causal clean-air:** G1's spec owns everything causal about track
  position; F3's TPP is descriptive-only by explicit exclusion.
- **F6 §4.2 residue this spike picks up:** the practitioner signals F6
  verified as credentialed-but-evidence-free included two "genuinely not
  in our feature set" items — pit-crew quality (routed to F3 PIS
  secondaries) and **points-position motivation, which F6 left out as
  unmeasured**. §5 below is the measured version. F6 §10's open questions
  are unaffected by this report except where noted.

---

## 3. The in-feed inventory [DATA] — every unconsumed field, verified

The kickoff supplied a 12-field list "verified present in bronze
2026-07-19" and asked that it be re-verified rather than trusted. Result:
all 12 exist as keys; **three are effectively dead or era-limited in ways
the list didn't capture** (`pit_box`, `points_delta`, `race_purse` — plus
`infractions`/`pit_reports` are 2020–2022 relics). Full verified map:

### 3.1 Result-row fields (39 keys; `weekend_race[0].results[]`)

Consumed = read by `parse_lib` into the frozen model path. In silver =
present in `silver.results` (C2 flattens the row verbatim minus six keys).

| Field | Live coverage (Cup) [DATA] | In silver? | Candidate use |
|---|---|---|---|
| `crew_chief_id`, `crew_chief_fullname` | 0% ≤2020; 59% of 2021; **100% 2022+** | yes | **Personnel-change features (§4, F18)** — coverage floor aligns exactly with the model's 2022+ era |
| `points_position` | 2017+ (~93–96% of rows; 0 = points-ineligible entries) | yes | **Incentive states (§5, F19)**. Confirmed post-race standings: `points_delta = prev_pos − pos` reconciles 1,211/1,261 (96%) of 2022 transitions; as-of use = read from the driver's *previous* race ⇒ leak-free |
| `points_delta` | 2017–2022 only; **all-zero 2023+** | yes | Dead in the current era; derivable from `points_position` anyway. No use |
| `playoff_points_earned` | 2019–2025 (65–85 rows/season > 0); **all-zero in 2026** — real, not a feed bug: the 2026 Chase format abolished playoff points [V-web, §7] | yes | Incentive states, 2019–2025 backtest window only |
| `owner_id`, `owner_fullname` | 2017+ (~100%) | yes | **Org-key sharpener for F2** (finding below); 42 distinct owner_ids vs 32 team_names 2022+ |
| `sponsor` | 2017+ (~99%) | yes | No clear use (funding-level proxy is hopelessly confounded and unquantified). Recorded and closed |
| `winnings` | **all-zero every year** | yes | Dead |
| `pit_box` | **13 of 392 races** (a contiguous 2023 block: race_ids 5275–5295, Apr–Aug 2023) | **no** | Dead for any feature. Does NOT answer track-audit H7 (§6.2) |
| `times_led` | 2017+ | yes | F13 loop-history adjacency (laps_led already parsed) |
| `points_earned` | 2017+ | yes | Incentive accounting (per-race points incl. stage points); cumulative-sum caveat in §5.3 |
| `qualifying_position`, `qualifying_order` | 2017+ (spotty 2019) | yes | `start ≠ qualifying_position` flags post-qualifying to-the-rear penalties — weak, unproposed |
| `car_number`, `official_car_number` | 2017+ | yes | Already consumed by C2's pit-stop driver resolution |
| `car_model` | 2017+ | yes | Constant within make-era; no use |
| `diff_laps`, `diff_time` | 2017+ | yes | Margin-aware finish history is a conceivable feature but overlaps `pace_med85`'s job; recorded, unproposed |
| `disqualified` | consumed | yes | already in model path |
| `driver_hometown`, `hometown_city/state/country` | 2017+ | **no** | No use (demographics) |
| `race_season`, `race_id`, `series_id`, `result_id` | keys | partial | plumbing |

**Finding — `owner_id` survives a rename that `team_name` doesn't
[DATA]:** Stewart-Haas Racing (2024) ran cars under owner_ids {3193,
4084}; Haas Factory Team (2025) continues as owner_id **4084**. The
pooling spec (F2) chose `team_name` and pre-registered
renames-as-new-entities, explicitly noting an alias-table variant would
need its own spec — this is the first concrete evidence that a cheaper
alternative exists in-feed (an `owner_id`-keyed pool preserves SHR→HFT
continuity mechanically). Not a change request: owner_id is also *finer*
than team_name (42 vs 32 distinct 2022+, roughly per charter/entity), so
it is not a drop-in superior key. Routed to F2's future-variant option as
an input, nothing more.

### 3.2 Race-level fields (47 keys; `weekend_race[0]`)

`silver.races` is built from the index feed with the same vocabulary, so
most scalars are covered. Unconsumed and alive:

| Field | Coverage (Cup) [DATA] | Candidate use |
|---|---|---|
| `caution_segments[]` | **2017+, ~98% of races** (start/end lap, `reason` — Debris/Accident/…, `comment`, `beneficiary_car_number` = lucky dog, flag_state) | **The best unconsumed race-level object.** Extends caution-event detail 2 years below live-flag-data's 2019 floor; adds a structured caution-cause taxonomy `silver.flag_events` lacks (it has only free-text `comment`); beneficiary tracking feeds wave-around analysis. → C4 + F3 tightening (§8) |
| `stage_results[]` | 2020+ (36/41 races = the staged points races; empty 2017–2019 despite stages existing — schema floor) | Per-stage finishing order + stage points: incentive accounting (§5), stage-aggression histories (F13-adjacent). → C4 |
| `race_leaders[]` | 2017+, 100% | Leader segments (start/end lap per car): *when* led, not just how much — DCI/F13 detail. → C4 |
| `playoff_round` | 2020+ (10 races/season = the playoff races; 0 in 2017–2019 despite playoffs existing; 0 so far in 2026 — playoffs not started) | Incentive states: marks playoff races + round. → C4 (onto silver.races) |
| `stage_4_laps` | rare (Coca-Cola 600) | silver.races carries stages 1–3 only; trivial completeness fix. → C4 |
| `infractions[]` | **2020–2022 only** (34/41, 41/41, 41/41; empty 2023+) | Structured penalty ledger (driver, lap, infraction, penalty) — a 3-season research asset for pit-penalty rates (F3 PIS secondary), not a live feature. Historical-only |
| `pit_reports[]` | **2020–2022 only** | Near-duplicate of live-pit-data, which silver.pit_stops already covers 2020+ with the same fields. Redundant; no use |
| `race_comments` | 2017+ | Free text; reliably carries pre-race to-the-rear penalty notes (the structured `infractions` version died after 2022). Text-mining is possible but unproposed |
| `margin_of_victory`, `pole_winner_driver_id/speed`, `number_of_leaders`, `number_of_cars_in_field`, `average_speed`, `total_race_time`, distances | 2017+ | Descriptive; `race_has_run()` already uses two of them. No feature use |
| `inspection_complete` | constant `true` 2019+ | No signal. Dead |
| `attendance`, `race_purse` | all-zero | Dead |
| `restrictor_plate` | bool, 2017+ | Superseded by C3's era machinery (plates ended 2019) |
| broadcasters ×3, `tunein_date`, `qualifying_date`, `date_scheduled`, `master_race_id`, `timing_run_id` | — | Plumbing/no use |
| `schedule[]` | consumed for green-flag time only | Weekend-format features (practice length, qualifying format) conceivable; weak, unproposed |

`weekend_runs[]` (practice + qualifying sessions) is fully consumed as
`silver.practice_runs` (run_type 1 = practice, 2 = qualifying [DATA]).

### 3.3 What this buys, concretely

The unconsumed-fields story splits cleanly: (a) three genuinely dead ends
verified dead (`pit_box`, money fields, `points_delta`-era); (b) a
personnel/incentive family fully alive in silver already (§4–§5); and
(c) four structured race-level objects alive in bronze but invisible to
silver — the **C4** proposal (§8), effort LOW, which is also the
prerequisite that widens F3's caution work to 2017+ results-grade depth.

---

## 4. Sweep 1 — people/org changes (crew chiefs, rides)

### 4.1 K1 — Crew-chief tenure / change features [DATA + LORE] — the headline model candidate

- **Domain claim [LORE]:** the crew chief is the team's race-day
  strategist and setup owner; pairings take time to gel ("chemistry"), and
  a swap — especially an interim substitution during a suspension —
  degrades performance in the short run. Ubiquitous garage/media
  assertion; zero public effect-size estimates found (consistent with F6's
  finding that practitioner claims carry no backtests).
- **Measured event base [DATA]:** Cup points races 2022–2025, drivers with
  `crew_chief_id > 0`: **185 within-season crew-chief changes** (70 / 61 /
  41 / 13 by year) + 21–30 offseason changes per season boundary. Of the
  185, **75 revert to the prior crew chief within 8 races** — the
  suspension/interim signature — and 110 are durable. The 2022 peak and
  monotone decline match the penalty-rule history [V-web]: 2022's
  wheel-loss rule suspended the crew chief 4 races per lost wheel; the
  2023 revision removed crew-chief suspensions for loose wheels entirely
  (two pit-crew members, 2 races, instead).
- **Mechanism (two distinct sub-hypotheses):** (i) *interim weeks* — a
  stand-in crew chief calls the race: strategy quality drops for exactly
  the weeks the swap-and-revert pattern marks; (ii) *durable changes* — a
  performance discontinuity (in either direction: teams change crew chiefs
  *because* results are bad — see the leakage note below) followed by a
  gel-in period.
- **Proxy fields (all in `silver.results` today):** per driver as-of
  histories over `crew_chief_id`: `cc_tenure` (consecutive prior races
  with the current-as-of-last-race crew chief), `cc_changed_recent`
  (change within last k races), optionally `cc_is_interim` proxied as
  "current cc differs from the cc of both 1 and ~5 races ago" (real-time
  knowable; the revert itself is not).
- **Leakage check:** clean if features are computed strictly from races
  *before* t (the tenure/change state as of the driver's previous race).
  Using the *current* race's crew chief pre-race needs the same
  feasibility check + fallback the pooling spec §3 pre-registered for
  `team_name` (pre-race payload population is untestable from bronze —
  bronze only stores completed races; flagged, not assumed). Second,
  subtler leak: crew-chief changes are *caused by* bad form — a change
  flag partially re-encodes recent results the `fin` history already
  carries. The A/B's exclude-nothing paired design handles this honestly
  (the question is marginal value over `fin`, which is exactly what the
  gate measures).
- **Power check:** ~110 durable changes + 75 interim windows over 4
  seasons; a k=5-race post-change window marks ≈ 900–1,000 driver-races ≈
  **10% of the 5,650 eligible driver-races** — the same order as the DNF
  feature's 13.9% base rate, which the frozen program already deemed
  power-worthy. Expectation honestly stated: like V1-dnf, the +0.005
  practical floor is the binding constraint, and a well-run null is the
  likely outcome.
- **Credibility discount:** mechanism is plausible and the event base is
  real, but the direction/size is pure lore. No external evidence exists
  either way — which is precisely the kind of question this project
  answers by A/B rather than by belief.
- **Tier: M** (via its own pre-registered spec; feature-lever, disjoint
  from F1's status lever, F2's pooling lever, F10's recency lever).
  **Overlap:** F2 pools *current org form*; this is *personnel
  discontinuity* — different mechanism, different fields. No existing row
  covers it. → **Candidate session F18** (§8).

### 4.2 K2 — Ride changes (driver–team discontinuity) [DATA + LORE]

- **Domain claim [LORE]:** a driver changing teams (offseason or
  mid-season) resets car quality, pit crew, and communication; history
  from the old ride mispredicts the new one.
- **Measured base [DATA]:** within-season `team_name` changes are rare
  (15/17/11/5 for 2022–2025, 3 in 2026 — mostly part-timers and
  substitutions); offseason moves are the real mass (silly season,
  ~5–10 full-time moves/yr [LORE, uncounted here]).
- **Proxy:** `team_tenure` / `team_changed_offseason` from
  `silver.results.team_name` (or `owner_id`, §3.1) — same as-of
  construction as K1.
- **Overlap — material:** F2's W1/W3 already inject the *new* team's
  current form for a moved driver (the pool follows this race's org), and
  the driver's own `fin`/`typed` histories carry the old-ride information
  the hypothesis says to discount. The genuinely new increment — history
  *down-weighting* after a move — is an engine-mechanics change (per-driver
  history reweighting), which is F10's machinery lane, not a feature
  column. Also partially covered: the audit's `n_hist< 5` fallback already
  handles series rookies.
- **Power:** offseason moves affect ~8 drivers × ~36 races in their first
  season ≈ 5% of rows at full strength only early-season.
- **Verdict:** admitted, but **folded into F18 as a secondary variant**
  (a `team_tenure` feature) rather than its own session; the
  history-reweighting version is explicitly deferred to F10's lane with a
  cross-reference, not proposed here. **Tier M** (within F18's spec).

### 4.3 K3 — Interim-substitute drivers / driver changes [DATA]

For completeness: the same `silver.results` machinery detects mid-season
*driver* substitutions in a car (injury/suspension). The model is
driver-keyed, so a substitute simply appears with his own (thin) history —
already handled by the `n_hist` fallback. Nothing to build. Recorded so
the idea isn't re-proposed.

---

## 5. Sweep 2 — incentive states (playoffs, bubble, desperation)

### 5.1 The domain claims [LORE], and what F6 left unmeasured

Garage/media lore asserts at least four incentive effects: (a) bubble
drivers near the playoff cutline drive desperate in the closing
regular-season races (more aggression → more crashes, more strategy
gambles); (b) locked-in drivers coast or test race-strategy variants;
(c) playoff drivers in elimination races take must-win risks;
(d) championship-race contenders (H5's four) race a different race than
the other 32 cars. F6 §4.2 verified the *assertion* exists among
credentialed practitioners ("points-position motivation as an H2H
handicap") and correctly recorded it as unmeasured. The track-audit's H5
[Working Hypothesis, Medium-High confidence] is claim (d) plus the
methodological warning that contenders shouldn't contaminate track pace
estimates.

### 5.2 What is measurable in-feed [DATA]

- `points_position` (2017+): official post-race standings, confirmed
  semantics (§3.1). As-of cutline distance = |rank − 16| entering race t,
  from the previous race's payload. Leak-free by construction.
- `playoff_round` (2020+): marks the 10 playoff races/season and their
  round. `driver_is_in_chase` (`silver.live_final`, 2017+): per-driver
  playoff-field membership in exactly those races.
- `playoff_points_earned` (2019–2025): banked playoff points — cushion
  size above the cutline, elimination-round math.
- `stage_results` (2020+, after C4): stage-point accounting per race.
- Season race index (from `silver.races` dates): races-remaining-to-cutoff.
- **Caveat [DATA]:** season *point totals* are not carried in-feed — only
  ordinal position. A points-distance-to-cutline (rather than rank
  distance) needs a cumulative sum of `points_earned`, which drifts from
  official standings wherever NASCAR assessed post-race point *deductions*
  (L1/L2 penalties, not in any feed). Ordinal `points_position` is exact;
  derived point gaps are approximate. A spec must choose ordinal (exact,
  coarser) and say so.

### 5.3 K4 — Bubble/playoff-pressure features — measurable, but the regime just broke [DATA + V-web]

- **The 2026 format break (the decisive fact):** NASCAR announced
  2026-01-12 a return to "The Chase": top 16 on points after 26 races
  qualify — **win-and-you're-in eliminated**; **playoff points
  eliminated**; win value raised 40→55 points; staggered reset
  (~2,100/2,075/2,065, −5 per seed; regular-season champion +25); stage
  points unchanged [V-web — ESPN fetched directly; nascar.com + Red Bull
  explainer corroborate via search; nascar.com itself 403s, consistent
  with F6 §6.5]. **Confirmed against our own archive:**
  `playoff_points_earned` = 0 on all 880 Cup result rows of 2026 through
  24 races, vs 65–85 rows/season > 0 in 2019–2025, while stage racing
  demonstrably continues (`stage_results` populated, stage_points 10-9-8…
  [DATA]).
- **Why that matters for testing:** every desperation mechanism a
  2022–2025 backtest can validate lived in the elimination format
  (win-and-in ⇒ a longshot's rational play is maximum variance;
  elimination races ⇒ must-win). In 2026 none of that exists — bubble
  pressure is pure points accumulation near P16, wins are worth more but
  guarantee nothing. A walk-forward A/B whose training window is 88%
  old-format races would adopt or kill the feature on evidence from a
  dead regime, then apply it to a live one. This is the same class of
  problem F9 (era-reset) exists for — and F9's era machinery
  (`silver.rules_era`) currently encodes *car/package* eras only, not
  format eras (flagged to F9 in §8).
- **Power check (honest, and poor for the model path):** peak-pressure
  exposure ≈ the last 3–5 regular-season races × ~6–10 bubble drivers +
  10 playoff races × the contender subsets ≈ **3–5% of eligible
  driver-races** at full mechanism strength — half to a third of K1's
  exposure, on a mechanism that just changed shape. Clearing mean
  Δρ ≥ +0.005 program-wide from a 4% exposure requires an implausibly
  large per-affected effect (~+0.12 ρ-equivalent concentrated in those
  races).
- **H5 sharpening specifically:** the championship-contender flag = 1
  race/season × 4 drivers ≈ 0.3% exposure. As a *model feature*: hopeless,
  and this report says so terminally. As *methodology* — H5's actual
  content (don't let the four contenders' strategy-distorted laps
  contaminate Phoenix pace estimates) — it is cheap and right: F3's
  per-track metrics should carry a contender-exclusion sensitivity check
  at championship races. Routed to F3 (§8), consistent with H5's own
  wording ("physical pace estimates should use the full field and avoid
  assuming contenders are representative").
- **What survives as a session:** the *descriptive* questions, which are
  format-robust in construction and genuinely unanswered: does crash-class
  DNF rate rise with cutline proximity in late-regular-season races
  (2017–2025, 9 seasons of results-grade data)? Do bubble drivers' stage
  points spike (stage-strategy aggression, 2020+)? Does the locked-in
  cohort's ρ-residual degrade in the last regular-season races? Each is a
  measured answer to standing pundit lore, feeds the sim's incentive knob
  someday, and doubles as the effect-size evidence any future model A/B
  would be conditioned on. → **Candidate session F19, Tier A**
  (analytics-first; an M-tier A/B only if F19's measured effect under the
  *new* format's logic justifies one — pre-registered then, not now)
  (§8).
- **Leakage check:** all inputs as-of from prior-race payloads (§5.2);
  descriptive outputs are Tier A and never join feature banks (F5 §6.4's
  build-graph rule applies).

---

## 6. Sweep 3 — equipment and tires

### 6.1 K5 — Goodyear allocation/compound data: not in-feed, not worth chasing [DATA + V-web]

- **Verified in-feed answer [DATA]:** no feed carries allocation or
  compound identity. Tire-adjacent in-feed data = per-stop
  `*_tire_changed` flags + `pit_stop_type` (silver.pit_stops, 2020+;
  duplicated by weekend-feed `pit_reports` 2020–2022 only).
- **External source [V-web]:** per-race "tire setup" articles on
  nascar.com (sets per weekend by series/track, compound codes, e.g. Cup
  intermediates ≈ 10 sets, superspeedways 7, road courses 7 dry + wets) —
  an NDM-covered, bot-blocked property (F6 §6.5): systematic collection is
  ToS-out under the A6 posture; manual per-week transcription is possible
  but buys little (below).
- **Why it buys little even if held:** sets-per-weekend is largely
  deterministic by track type and season policy — nearly collinear with
  the track dimension C3 already carries; the strategy-relevant quantity
  (tire-set scarcity binding late-race decisions) expresses itself in the
  *behavior* silver.pit_stops already records, which is F3-SFS/PIS scope.
  Year-over-year compound changes (the "Goodyear brought a softer tire"
  storyline [LORE]) are real but arrive as unstructured press prose, and
  their measurable consequence — degradation-slope shifts — is exactly
  F3's TDS computed per era.
- **Verdict: documented null, no session.** The tire lane is already
  owned: TDS (F3) measures what tires *did*; allocation adds nothing
  in-feed, and the external source is governance-blocked. Tier G note
  only.

### 6.2 K6 — `pit_box` / pit-road geometry (track-audit H7): dead in-feed [DATA]

The one field that could have carried stall assignments is populated in
**13 of 392** Cup weekend-feeds (a contiguous Apr–Aug 2023 block:
Martinsville→Indy road course, race_ids 5275–5295) and zero elsewhere —
a transient upstream experiment, unusable. `silver.pit_stops` has no
stall field. H7 therefore remains **unanswered by held data**: pit-entry/
exit time-loss *by track* is measurable (F3's PIS secondaries — in/out
travel durations), but stall-position effects within a race are not.
Recorded as a terminal in-feed null so H7 isn't re-proposed against this
archive; G1's S1 IV design (pit-box-time shocks) is unaffected — it uses
realized stop durations, not stall numbers. **Tier G (null).**

### 6.3 K7 — Manufacturer draft alliances at superspeedways [DATA + LORE]

- **Domain claim [LORE]:** manufacturers coordinate drafting at
  Daytona/Talladega/Atlanta — same-make lines, spotter agreements,
  pushing partners — well-attested in broadcast/practitioner discourse,
  never quantified publicly.
- **Proxy [DATA]:** fully held — `silver.laps` running positions × 28 SS
  races 2022–2026 (6/season, all with lap data) joined to `car_make`.
  Metric: same-make running-order adjacency rate vs a
  random-permutation baseline, green-flag laps, per race; driver-level
  cooperation scores as-of.
- **Leakage/power check:** as-of histories are constructible, but the
  model-payoff arithmetic is stacked against it: SS races are ~15% of
  the schedule, are the *least* predictable regime (ρ≈0.16), and are
  doctrine-level stand-downs (output never actionable). Clearing +0.005
  program-wide needs ≈+0.033 mean Δρ concentrated at SS — conceivable
  arithmetic, implausible signal-to-noise, and the payoff would land in
  races the project refuses to act on.
- **Real value:** analytics/sim — SS finish outcomes are *correlated
  within make* if alliances are real, which changes multi-entry DFS/beting
  exposure math and the sim's crash/finish covariance structure. That is
  F3's ARS-b lane (common-cause wreck decomposition, correlated outcomes
  at drafting tracks) extended with a make-clustering component.
- **Verdict:** **Tier A, folded into F3's scope as an ARS-b extension**
  (§8) — no standalone session, no model path proposed. A measured
  alliance-adjacency table replaces a broadcast trope with a number,
  which is this spike's definition of success.

---

## 7. Sweep 4 — rules/format eras (inventory only; F9 owns this)

Per the kickoff, inventory without development. Verified this session and
handed to F9:

1. **The 2026 Chase format break [V-web + DATA]** (§5.3): playoff points
   gone, win-and-in gone, win = 55 pts, staggered reset. This is a
   *format/incentive* era boundary, not a car-package one —
   `silver.rules_era`'s six keys (aero/package eras, C3) do not encode it.
   F9's spec should decide whether format eras become a second era key or
   an explicit non-goal; this report only flags that the distinction now
   exists in the live forward test.
2. **Stage racing schema floors [DATA]:** stages exist 2017+ (26/36 races
   in 2017, all 36 from 2018), but `stage_results` populates 2020+ only.
3. **Wheel-penalty regime [V-web]:** 2022 = 4-race crew-chief suspension
   per lost wheel; 2023+ = no crew-chief suspension (two crew, 2 races) —
   directly visible in K1's swap counts; any K1 feature spanning 2022
   should know its interim-swap base rate is regime-inflated.
4. **`restrictor_plate` flag [DATA]:** in-feed 2017+; superseded by C3's
   era machinery. No action.

Nothing else new. F9 remains the owning session for all era-reset feature
work; this report adds input #1 as its most material new fact.

---

## 8. Sweep 5 — race-craft meta (inventory only; F3/G1/F13 own this)

Per the kickoff, inventory and defer — nothing new proposed:

| Race-craft item [LORE] | Measurable proxy [DATA] | Owner |
|---|---|---|
| Late-race restart chaos / closers | `silver.live_final.position_differential_last_10_percent` (official closers, 2017+); restart windows from flag_events | F3 (RVS), F13 (closers history) |
| Fuel-mileage gambles / off-sequence strategy | `silver.pit_stops` stop-lap paths vs stage boundaries; SFS entropy | F3 (SFS) |
| Lucky dog / wave-arounds | `caution_segments.beneficiary_car_number` (2017+, after C4) + `flag_events.beneficiary` (2019+) | F3; G1's S2 already screens pit-cycle cautions |
| Pit-crew execution spread | `pit_stop_duration` distributions | F3 (PIS secondaries; F6 §4.2 routed it there already) |
| Restart lane choice (choose rule) | **not in-feed** (row/parity proxy only, already noted in F5 §3.5) | F3 (RVS, labeled approximate) |
| Dominator timing (when led, not just how much) | `race_leaders[]` segments (2017+, after C4) | F13/F3 (DCI) |

The only addition this sweep makes is data plumbing: two of the six rows
above get their 2017+ depth from **C4**'s materialization of
`caution_segments`/`race_leaders` (§3.2).

---

## 9. Leakage / trap notes specific to this report's ideas

1. **Post-race standings masquerading as pre-race state.**
   `points_position` in race t's payload is post-race-t [DATA-confirmed].
   Every incentive feature must read the *previous* race's payload. An
   as-of join keyed on race t would silently leak the target race's
   outcome into its own predictor.
2. **Personnel changes are outcome-caused.** Crew-chief and ride changes
   follow bad results; a change flag correlates with (already-modeled)
   recent form by construction. The paired A/B design measures marginal
   value correctly — but any *descriptive* K1 analysis must not read a
   post-change dip as causal without a pre-trend control.
3. **Cumulative points drift.** Feed-derived season point totals omit
   post-race penalty deductions (not in any feed); only ordinal
   `points_position` is official. Specs must pick ordinal or accept
   documented drift.
4. **Format-regime transfer (the 2026 break).** A 2022–2025-validated
   incentive feature encodes elimination-format behavior; adopting it for
   2026+ on that evidence is a category error unless the mechanism is
   argued format-robust pre-data (§5.3). This is the incentive-lane
   version of F5 §6's hindsight rule: the walk-forward gate cannot fix a
   *mechanism* that no longer exists.
5. **Pre-race field-population assumptions.** Bronze stores only completed
   races, so no pre-race payload exists to verify that `crew_chief_id`
   (or `team_name`) is populated before the green flag. Any feature
   needing the *current* race's value must pre-register the
   most-recent-prior-value fallback (pooling spec §3's pattern) — or use
   strictly-prior-race constructions that need no current-race read at
   all (K1's tenure features are deliberately shaped this way).
6. **Interim-vs-durable confusion.** "Crew chief changed" conflates
   4-race suspensions (2022-heavy, rule-driven, reverting) with genuine
   reorganizations. A spec must either model them separately or justify
   pooling; the revert-within-8 signature is measurable as-of only up to
   the revert itself (you know it *was* interim only after the return).

---

## 10. Candidate plan sessions (ranked: payoff band, then effort)

| # | Candidate | Band | Effort | Depends on | Gate | Overlap guard |
|---|---|---|---|---|---|---|
| 10.1 | **C4 — silver breadth extension #2:** materialize `caution_segments` (2017+), `stage_results` (2020+), `race_leaders` (2017+); add `playoff_round` + `stage_4_laps` to `silver.races` | **HIGH** (unlocks F3's 2017+ caution depth + F19's inputs; pure reference) | **LOW** (~1–2 h) | none (bronze already holds everything) | none — silver reference tables, C2's conventions; C-gate must stay green | additive-only; no overlap — these objects are consumed nowhere today [DATA §3.2] |
| 10.2 | **F18 — personnel-change features A/B** (crew-chief tenure/interim + team-tenure secondary; §4) | **MED** (honest: DNF-class frequency, lore-only direction) | MED (~1 h spec + ~3–5 h run) | D1/D2 + ≥8 scored races (program discipline) + own pre-registered spec | adopt iff Wilcoxon p ≤ α_adj (extending the roadmap-#4 multiplicity convention) AND mean Δρ ≥ +0.005 | personnel discontinuity ≠ F2's org-form pooling (different mechanism/fields); history-reweighting variant explicitly deferred to F10's lane; interim/durable split per §9.6 |
| 10.3 | **F19 — incentive-state analytics** (crash-rate × cutline proximity, stage-aggression, locked-in residuals, 2017–2025 + live 2026 tracking; §5) | **MED** (measured answers to standing lore; sim/DFS inputs; A/B trigger evidence) | LOW-MED (~2–4 h) | C2 (done); C4 preferred for stage_results/playoff_round | Tier A — analytics only; any M-tier A/B needs its own later spec conditioned on F19's measured effects under 2026-format logic (§5.3) | the measured version of F6 §4.2's unmeasured "motivation" signal; H5 itself routed to F3, not here; era semantics deferred to F9 |
| 10.4 | **F3 tightenings** (no new session): caution-cause taxonomy from `caution_segments` (2017+ depth), make-clustering ARS-b extension (K7), H5 contender-exclusion sensitivity at championship races | MED | folds into F3 | C4 | F3's existing pre-registration discipline | uses C4 outputs; K7 stays Tier A inside ARS-b |
| 10.5 | **F9 addendum** (no new session): the 2026 Chase-format break as a format-era input (§7.1); wheel-rule regime note for any 2022-spanning personnel feature | MED | folds into F9 | — | F9's own spec | format eras vs package eras distinction recorded there |
| 10.6 | **F2 input** (no new session): `owner_id` rename-continuity finding (§3.1) as evidence for the spec's own future alias-table variant | LOW-MED | note only | — | F2's spec owns it | not a change request |

**Explicitly NOT proposed,** with reasons on record: tire
allocation/compound acquisition (ToS-blocked source, near-collinear with
track dimension, behavioral signal already owned by F3 — §6.1); anything
`pit_box`/stall-geometry (field dead in-feed — §6.2); a draft-alliance
model feature (stand-down actionability + SS noise floor — §6.3); a
championship-contender model feature (0.3% exposure — §5.3); sponsor/
winnings/purse/attendance/hometown features (dead or useless fields —
§3); driver-substitution handling (already covered by `n_hist` fallback —
§4.3); margin-aware finish history via `diff_time` (overlaps pace;
recorded unproposed — §3.1); weekend-format features from `schedule[]`
(weak — §3.2).

Sequencing/independence: 10.1 is runnable now and independent of
everything (it is also 10.3's and 10.4's preferred prerequisite). 10.2
waits on the standard model-A/B gates. 10.3 could run on current silver
minus stage/playoff columns, but is better after C4.

---

## 11. Proposed plan edits (for the owner to fold in)

Following the F5/F6/F7 precedent (proposals folded as rows in the same
close-out), this session's close-out adds:

- **C4** (Phase C, pending): silver breadth extension #2 per §10.1.
- **F18** (Phase F, blocked): personnel-change A/B per §10.2, gated like
  F8/F9 (D1/D2 + ≥8 scored + own spec).
- **F19** (Phase F, pending): incentive-state analytics per §10.3,
  Tier A, dependent on C2 (met) with C4 preferred.
- One-line tightenings recorded in the F3 and F9 rows' technical
  summaries per §10.4/§10.5 (caution taxonomy + ARS-b make-clustering +
  H5 contender sensitivity → F3; 2026 format-era input → F9).

No change to any frozen spec; no change to the single 'next' (E1).

---

## 12. Open questions (honest residue)

1. **Pre-race population of `crew_chief_id`/`team_name` in the live
   weekend feed** — unverifiable from bronze (completed races only);
   testable only against a live upcoming race, exactly like the pooling
   spec's standing §3 flag. F18's spec must inherit that check + fallback.
2. **Whether 2026's `playoff_round` will populate under the new Chase**
   (first observable September 2026). If it stays 0, the playoff-race
   marker for 2026+ becomes date-derived rather than in-feed.
3. **Offseason ride-change counts** were asserted from domain knowledge
   ([LORE], ~5–10 full-time moves/yr), not measured here — measurable
   from silver in F18's spec session with one query; within-season counts
   are measured (§4.2).
4. **Why `infractions`/`pit_reports`/`points_delta`/`pit_box` died
   upstream after 2022–2023** — unknowable from our side; recorded so
   nobody assumes a fetch bug. If NASCAR ever revives them, C4's
   machinery picks them up unchanged.
5. **The exact shape of 2026 Chase seeding** (2,100/2,075/2,065…, −5
   steps) rests on a single fetched source plus search corroboration
   [V-web] — sufficient for this report's purpose (the *existence* of the
   break is confirmed in our own data); F9's spec session should
   re-verify the numbers if it encodes them.

---

## Appendix A — source ledger

**Project-internal [DATA] (primary evidence class of this report):**
`data/nascar.duckdb` (silver.results/races/laps/live_final/pit_stops/
flag_events/practice_runs, gold.wf_features) and raw
`data/bronze/series_1/{2017–2026}/*/weekend-feed.*.json.gz` payload scans
— all queries run 2026-07-19 against the archive state after D2
(392 Cup weekend-feeds; race 5618 results not yet posted).

**External [V-web] (single-verifier grade):**

| Source | Used for |
|---|---|
| espn.com/racing/nascar/story/_/id/47592082 (fetched, quoted) | 2026 Chase format: win-and-in eliminated, top-16 on points, 55-pt win, +25 reg-season champ cushion, stage points unchanged; announced 2026-01-12 |
| nascar.com/news-media/2026/01/12/nascar-returns-to-chase-championship-format-for-2026 (403 to fetchers — consistent with F6 §6.5; content via search corroboration) + redbull.com Chase explainer + Wikipedia 2026 Cup page | corroboration: playoff points no longer awarded; staggered reset values |
| racer.com/2023/01/31/nascar-easing-back-on-wheel-nut-penalties + nascar.com 2022-01-24 penalty-structure article + nbcsports.com 2023 rule changes (search-verified) | 2022 wheel-loss = 4-race crew-chief suspension; 2023 revision removed crew-chief suspension (two crew members, 2 races) |
| nascar.com Goodyear "tire setup" per-race articles (Pocono/Nashville/Texas/Bristol/Kansas/Talladega/Sonoma 2026; search-verified) | tire allocation publication channel + per-track-type set counts; not in cf feeds |

**Domain lore [LORE] admitted as hypotheses (no citable evidence, by
design):** crew-chief chemistry/gel-in; bubble desperation; locked-in
coasting; manufacturer draft alliances; Goodyear compound storylines.
Each appears only with a credibility discount and a [DATA] proxy.

---

*Report ends. Nothing was built, no frozen spec was edited, no model code
was touched. Every idea that could ever reach the production model is
routed through its own future pre-registered, walk-forward-gated A/B
(§10's gate column); everything else is labeled analytics, data plumbing,
or governance. The likeliest outcome of F18/F19 — well-run nulls that
permanently retire pieces of garage lore — is a success by project
doctrine.*
