# DATA_DICTIONARY.md — human-readable field reference

Every dataset the project reads or writes, with exact field names, types, and
meanings. Grounded in the code and live data as of 2026-07-19 (`src/parse_lib.py`
for parsed fields; `predictions/` for the prediction/log schemas;
`specs/scoring_methodology.md` for the scoring contracts; the live cf.nascar.com
feeds for raw inputs). When code and this doc disagree, the code
(`src/parse_lib.py`) is authoritative — fix this file.

Units: pace features are **ratios to the per-lap field median** (≈1.0; lower =
faster). Times are UTC. "Driver-row" = one driver's record within one race.

---

## 1. Parsed dataset — `src/races_parsed.pkl`

A pickled `list` of race dicts, sorted by `date`. Built by `parse_lib.parse_race()`;
kept current by `update_data.py`. **Not committed** (in `.gitignore`); ships in the
handoff zip and is rebuilt by `download.py` + `parse.py`.

### 1a. Race-level dict

| field | type | meaning |
|-------|------|---------|
| `date` | str | Race datetime, ISO `YYYY-MM-DDThh:mm:ss` (sort key). |
| `year` | int | Season year. |
| `rid` | int | NASCAR `race_id`. |
| `track` | str | Track name, verbatim from the feed (e.g. `Atlanta Motor Speedway`). |
| `drivers` | dict | `driver_id (int) → driver-row` (§1b). |
| `n_green` | int | Count of green-flag laps with a full-field median (diagnostic). |
| `n_fe` | int | Drivers with a fixed-effects pace estimate (diagnostic). |
| `n_prac` | int | Drivers with a practice lap (diagnostic). |

### 1b. Driver-row dict (`drivers[driver_id]`)

| field | type | meaning |
|-------|------|---------|
| `finish` | int | Official finishing position (1 = win). **The model's target.** DNFs are ranked here by laps completed. |
| `start` | int | Starting position (grid). `predict_next`/`walkforward` substitute 20 if falsy. |
| `qspeed` | float | Qualifying speed (mph); `None` if not posted. |
| `status` | str | Finishing status, lowercased: `running`, `accident`, `dvp`, `engine`, … (31 values seen). DNF = anything ≠ `running`. Drives the roadmap-#4a DNF feature. |
| `team` | int | **Per-car** `team_id` — NOT per-organization (Penske's #12 and #22 differ). Do not pool teammates on this; the pooling spec uses `team_name` instead (see §5, `team_mfr_pooling.md`). |
| `make` | str | Manufacturer: `Chevrolet` / `Ford` / `Toyota`. |
| `laps_led` | int | Laps led. |
| `laps_completed` | int | Laps completed (ranks DNFs). |
| `pace_med85` | float | **Production pace feature.** Median of the driver's best 85% of green-flap lap-time ratios. |
| `pace_mean70` | float | Trimmed mean of best 70% of ratios (audit variant, unused in prod). |
| `pace_p20` | float | 20th-percentile lap ratio (audit variant). |
| `pace_best` | float | Median of best 20% ("clean-air proxy", audit variant). |
| `nlaps` | int | Green-flap laps used to compute the pace ratios. |
| `fepace` | float | Fixed-effects adjusted pace (audit extension); `None` if unestimable. **Proven dead end — not in prod** (report §7). |
| `practice` | float | Best practice lap time; `None` if none. Added nothing in the audit. |

---

## 2. Prediction file — `predictions/race_{rid}_{date}_prediction.json`

Written by `predict_next.py`; one per forecast race. Sealed: `sha256_of_payload`
is the sha256 of `json.dumps(payload, sort_keys=True)` over the payload with a
**pristine** `book_prices` block (see `scoring_methodology.md §1.3`).

| field | type | meaning |
|-------|------|---------|
| `sha256_of_payload` | str | Tamper-evidence hash (excludes itself; computed pre-book-prices). |
| `generated_utc` | str | Generation timestamp (ISO, UTC). |
| `race_id` | int | NASCAR race id. |
| `track` | str | Track name. |
| `track_type` | str | `SS` / `INT` / `SHORT` / `ROAD` / `OTHER` / `UNIQ` (MY_TYPE typology). `SS` ⇒ stand-down. |
| `race_date` | str | `YYYY-MM-DD`. |
| `config` | obj | Frozen config: `pace`, `hl`, `feats[]`, `typology`, `typed`, `lam`. |
| `trained_through` | str | Date of the last race in the training set. |
| `n_train_races` | int | Number of races the PL model was fit on. |
| `weights` | obj | Fitted PL feature weights: `fin`, `pace`, `typed`, `start`. |
| `field[]` | list | One object per entered driver (§2a). |
| `h2h_prob` | obj | `str(id_a) → { str(id_b) → P(a beats b) }`, 4-dp. Both orientations stored; rounding can make `p[a][b]+p[b][a] ≠ 1`. Scoring uses the lower-id canonical entry. |
| `book_prices` | obj | `{note, entries[]}` — filled at close (§4). |
| `stand_down` | bool | `true` iff `track_type == "SS"` — logged, never actionable. |

### 2a. `field[]` element

| field | type | meaning |
|-------|------|---------|
| `driver_id` | int | NASCAR driver id (join key). |
| `name` | str | Driver full name. |
| `grid` | int | Starting position. |
| `n_hist` | int | Career races in the dataset; `< 5` ⇒ feature-fallback, treat with caution. |
| `utility` | float | PL linear utility (higher = predicted better). |
| `pred_rank` | int | Predicted finishing rank (1 = best; no ties). **Scoring's rho input.** |
| `p_win` / `p_top5` / `p_top10` | float | PL-sampled probabilities (40k Gumbel draws). |

---

## 3. `predictions/predictions_log.csv`

One row per committed prediction (append-only), written by `predict_next.py`.

`generated_utc, race_id, race_date, track, track_type, sha256, stand_down`

All verbatim from the JSON of the same run; `sha256` = `sha256_of_payload`.

---

## 4. `book_prices.entries[]` (inside the prediction JSON)

Recorded manually at close per protocol step 3; schema frozen in
`scoring_methodology.md §5.1`.

| field | type | meaning |
|-------|------|---------|
| `book` | str | Sportsbook id (the designated primary book binds at first recorded price). |
| `recorded_utc` | str | **Observation** time at the book (not transcription time). |
| `closing` | bool | `true` if captured at/near close (target ≤ ~30 min pre-green). |
| `driver_id_a` / `driver_id_b` | int | The matchup's two drivers. |
| `price_a` / `price_b` | int | American odds for "a ahead of b" / the other side. Nonzero. |
| `void` | bool | Set post-race iff the book voided the matchup. |
| `note` | str | Free text. |

Admissibility for the market benchmark: the commit first containing the entry
must predate the race's scheduled green flag (`market_benchmark_decision_rule.md`).

---

## 5. `predictions/scores_log.csv`

Written by the (to-be-built) `score_race.py`; contract frozen in
`scoring_methodology.md §6` (incl. its amendments). One row per scored race,
idempotent upsert, sorted by `(date, race_id)`.

`race_id, date, track, ttype, n, rho, h2h_acc, h2h_n, book_n, book_agree_n, model_beats_book_n, notes`

| column | type | meaning |
|--------|------|---------|
| `race_id` | int | From the prediction JSON. |
| `date` | str | **Race** date `YYYY-MM-DD` (not scoring date). |
| `track` / `ttype` | str | Track name / track type. |
| `n` | int | Common-set size (drivers in both the prediction and official results). |
| `rho` | 4-dp | **Primary metric.** Spearman of `pred_rank` vs official finish; blank if `n < 3`. |
| `h2h_acc` | 4-dp | Pairwise concordance of the published ranking; blank if `h2h_n = 0`. |
| `h2h_n` | int | Graded H2H pairs. |
| `book_n` | int | Graded book matchups (deduped, non-void, well-formed, strict favorite). |
| `book_agree_n` | int | Of `book_n`, where model pick = book pick. |
| `model_beats_book_n` | int | Of the disagreements, where the model's pick finished ahead. |
| `notes` | str | Semicolon-separated flags (`SS STAND-DOWN`, `no book prices`, …); ordered per the spec. |

---

## 6. Raw feeds consumed — `cf.nascar.com`

Public, unauthenticated (CloudFront/AWS). Fetched by `download.py` /
`update_data.py` / `predict_next.py`. Only fields the pipeline reads are listed.

**`.../race_list_basic.json`** (`series_1[]`): `race_id`, `race_type_id`
(1 = points), `race_date`, `track_name`, `winner_driver_id` (truthy ⇒ complete),
and each race's `schedule[]` (the `event_name == "Race"` entry's `start_time_utc`
= green-flag instant, used for benchmark admissibility).

**`.../{yr}/1/{rid}/weekend-feed.json`** → `weekend_race[0].results[]`:
`driver_id`, `driver_fullname`, `finishing_position`, `starting_position`,
`finishing_status`, `qualifying_speed`, `team_id`, `team_name` / `owner_fullname`
(the org key for pooling), `car_make`, `disqualified`, `laps_led`,
`laps_completed`. Also `weekend_runs[]` (practice): `run_type == 1`,
`results[].best_lap_time`, `driver_id`.

**`.../{yr}/1/{rid}/lap-times.json`**: `laps[]` (`NASCARDriverID`, `Laps[]` with
`LapTime`, `Lap`, `RunningPos`) and `flags[]` (`FlagState` — 1 = green —,
`LapsCompleted`).

Additional archived feeds exist but are **not** consumed today (pit-stop, flag,
lap-notes, live-feed) — see `planning/aws_solutions.md`.

---

## 7. Track-audit reference package — `research/track_audit/`

Vendored external research (integrated 2026-07-19; provenance, evidence
model, and update procedure in `research/track_audit/INTEGRATION.md`).
Immutable source files — `src/test_track_audit.py` re-verifies the package
manifest's SHA-256 hashes plus all schemas below. Loader:
`src/track_audit.py` (stdlib only). **The ten `*_prior` fields are analyst
structural priors (Working Hypotheses), NOT measured statistics; future 2026
races are NOT completed observations.** Nothing here feeds the frozen
production model.

### 7a. `nascar_cup_track_configurations.csv` (= `tracks[]` in the JSON bundle)

One row per **physical configuration** (43 rows) — era splits, not
facilities (`atlanta_pre_2022` ≠ `atlanta_post_2022`, etc.).

| field | type | meaning |
|-------|------|---------|
| `track_id` | str | Stable configuration key. **Join key for every package file.** |
| `facility` / `configuration` / `location` | str | Venue name, layout label, city/state. |
| `length_mi` / `shape` / `surface` / `turns` / `banking` | mixed | Physical spec (Verified Fact tier). |
| `road_course` | bool | `True`/`False` in the CSV. |
| `primary_family` / `secondary_family` | str | Package taxonomy (12 primary families). Coexists with the frozen `MY_TYPE`; see §7d. |
| `*_prior` ×10 | int 1–10 | **Analyst structural priors** (tire deg., track position, passing, attrition, restarts, pit road, qualifying, strategy, DFS dominator, finish variance). Uncalibrated. |
| `key_comparables` / `key_change_notes` / `racing_analysis` / `dfs_betting_implications` | str | Narrative analysis (Strong Inference tier); DFS/betting guidance lives here. |
| `source_ids` | str | Semicolon-separated refs into the S001–S041 ledger. |
| `confidence` / `evidence_class` / `score_type` | str | Preserve verbatim — the zero-trust labeling. |
| `completed_points_races_2015_2025` | int | Completed observations. |
| `completed_points_races_2026_through_cutoff` | int | Completed 2026 races at the 2026-07-19 cutoff. |
| `future_scheduled_points_races_2026` | int | **Scheduled, not observed.** Never train on these. |
| `scheduled_points_races_2026_total` / `scope_event_count_including_2026_schedule` | int | Identities: completed-2026 + future = 2026 total; 2015-25 + 2026 total = scope count (gate-enforced). |
| `first_year_in_scope` / `last_year_in_scope_or_schedule` | int | Era bounds. |
| `structural_nearest_neighbors` | str | Mirror of §7b (gate-checked for agreement). |

### 7b. `nascar_track_similarity_edges.csv`

`source_track_id, neighbor_rank (1–5), target_track_id,
structural_similarity_score (0–100], distance (≥0), method`. Analyst-prior
feature distances within structural supergroups — **not historical outcome
correlations** (the `method` string says so and the gate keeps it that way).

### 7c. `nascar_track_sources.csv`

`source_id (S001–S041), title, publisher, url, source_type, reliability,
coverage`. Also embedded in the JSON bundle; the gate requires the two
ledgers to agree field-for-field.

### 7d. `crosswalk_track_ids.csv` (DERIVED, repo-authored)

Maps package `track_id` ↔ the feed `track` strings in `races_parsed.pkl`
(§1a), era-aware. `track_id, feed_track_name, season_start, season_end,
date_note, mapping (one_to_one|era_split|unmapped), in_repo_scope,
my_type (frozen walkforward.MY_TYPE class), package_primary_family, notes`.
One row per era-range (`sonoma_short` has two). Phoenix 2018 needs a race
month, not just a season (`date_note`); helper:
`track_audit.track_id_for(name, season, month=None)`. Both ID systems are
preserved — neither replaces the other.
