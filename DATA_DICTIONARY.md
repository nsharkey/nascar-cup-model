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

---

## 8. Bronze layer — `data/bronze/` (medallion rebuild, B2)

Immutable, versioned, hashed archive of raw cf.nascar.com JSON, gzipped.
Layout/protocol: `specs/medallion_architecture.md` sections 1.1/2. Built by
`src/bronze_fetch.py`; cataloged in DuckDB by `src/warehouse.py`
(`data/nascar.duckdb`, schema `bronze` — always rebuildable from disk, never
authoritative itself). Reported by `src/bronze_report.py`.

### 8a. `data/bronze/manifest.jsonl` — append-only fetch ledger

One JSON object per terminal fetch outcome (not one per file — `unchanged`/
`absent`/`failed` outcomes don't produce a new file).

| field | type | meaning |
|-------|------|---------|
| `run_id` | str | UTC compact timestamp (`YYYYMMDDTHHMMSSZ`) of the `bronze_fetch.py` invocation. |
| `fetch_utc` | str (ISO) | When this outcome was recorded. |
| `url` | str \| null | Full request URL (`null` for `legacy_import`). |
| `feed` | str | `weekend-feed` \| `lap-times` \| `live-pit-data` \| `live-flag-data` \| `lap-notes` \| `live-feed` \| `race_list` \| `legacy_import`. |
| `series_id` | int \| null | 1 Cup / 2 Xfinity / 3 Trucks; `null` for `race_list`/`legacy_import`. |
| `year` | int \| null | URL year segment; `null` for `legacy_import`. |
| `race_id` | int \| null | `null` for `race_list`/`legacy_import`. |
| `outcome` | str | `stored` (new version written) \| `unchanged` (payload sha matched the latest on disk) \| `absent` (terminal, two-pass confirmed) \| `failed` (retried next run) \| `imported` (legacy cache import). |
| `http_status` | int \| str \| null | Last HTTP status, or `unparseable` if 200 with invalid JSON. |
| `sha256` | str \| null | Of the **uncompressed** payload bytes; `null` on absent/failed. |
| `bytes_raw`, `bytes_gz` | int \| null | Uncompressed / gzipped size. |
| `path` | str \| null | Repo-root-relative path to the stored `.json.gz` (matches disk layout exactly); `null` on absent/failed. |
| `attempts` | int | Retry-ladder attempts used (shorter once the circuit breaker has tripped — 2026-07-19 amendment, spec 2.4). |
| `error` | str \| null | Last error/status text on failure. |

### 8b. Warehouse catalog (`data/nascar.duckdb`, schema `bronze`)

| object | kind | grain / definition |
|-------|------|---------------------|
| `bronze.manifest` | view | `manifest.jsonl` read directly (`read_json_auto`). |
| `bronze.files` | table | One row per file actually on disk (from a `glob()`, path/series_id/year/race_id/feed/fetch_ts parsed from the filename), left-joined to its latest manifest record for `sha256`/`bytes_raw`/`bytes_gz`. |
| `bronze.files_latest` | view | `bronze.files` deduped to the latest `fetch_ts` per `(feed, series_id, year, race_id)` — the version silver must read. |
| `bronze.manifest_latest` | view | `bronze.manifest` deduped to the latest `fetch_utc` per `(feed, series_id, year, race_id)` — used to resolve `absent`/`failed` when no file exists. |
| `bronze.races_index` | table | One row per `(series_id, year, race_id)`: `race_type_id`, `race_date`, `track_name`, `has_winner` (see §8c). Primarily from the latest on-disk `race_list` snapshot per year; a year whose index content doesn't match its own URL year (the 2017 aliasing quirk, §8d) is skipped there — never loaded from `race_list` even though the misfetched file stays on disk (bronze immutability forbids deleting it). For any such year that also has recovered `weekend-feed` files (2017, §8f), rows are synthesized per-race directly from those payloads instead. |
| `bronze.coverage` | view | Cross join of `bronze.races_index` × the 6 feeds, terminal state `stored \| absent \| failed \| pending` per the same precedence as `manifest_latest`. |

### 8c. `race_has_run(r)` — completion signal (2026-07-19 finding)

The index's own `winner_driver_id` field (spec 2.2's literal "not yet run"
gate) is **absent for every 2015-2019 race and 12/41 of 2022's** — an older
index-schema variant that never populated it, even for long-settled races.
`bronze_fetch.race_has_run()` (reused by `warehouse._load_races_index()`)
instead treats a race as run iff `winner_driver_id` is truthy **or**
`average_speed > 0` **or** `total_race_time` is non-empty — both populated
post-race and 0/empty pre-race in every observed year (verified against
2026 race 5618, not yet run as of this session).

### 8d. Index year-aliasing quirk (2017)

`https://cf.nascar.com/cacher/2017/race_list_basic.json` 200s with the
**exact 2018 season's races** (`race_season=2018` throughout) instead of
403ing like the genuinely-absent 2013/2014. Verified reproducible via a
fresh independent request, isolated to 2017 (every other year 2015-2026 is
self-consistent). `bronze_fetch.index_year_matches()` detects any
recurrence by majority vote on `race_season` vs. the requested URL year and
treats a mismatch as `absent`. The aliased file is a redundant copy of 2018
(which is itself fetched correctly under its own URL), so **no 2018 data is
affected** — but 2017's **own** races are consequently absent from bronze:
with no valid 2017 index there are no 2017 race_ids to enumerate. This is
neither disk loss (our copy is intact and quarantined) nor permanent at the
source — see §8f: a direct race_id probe recovered essentially the entire
2017 season across all three series, including full `weekend-feed` results,
not just index metadata. The B2-era assumption that 2017 was additionally
below the detailed-feed floor (superseded text: "2017 is below the
detailed-feed floor (§8e)... so the only unique gap is 2017's index
metadata") was wrong — it generalized from 2015-2016's genuinely-tried,
genuinely-403'd absence without ever actually testing 2017, which turned out
to behave completely differently once probed directly.

### 8e. Detailed-feed floor discovered by the B2 pull (2026-07-19)

Per §8c/8d fixes, all three series, all six feeds, 2015-2026 (minus the
aliased 2017) were attempted at B2 time. Result: 4,222 stored, 1,964
confirmed `absent`, 0 `failed`. The index floor (2015) and the detailed-feed
floor are **not the same** — at B2 time this looked like `weekend-feed`/
`live-feed` starting 2018, `live-flag-data` 2019, `lap-times`/`live-pit-data`/
`lap-notes` 2020, uniformly across all three series. 2015-2016 detailed feeds
are archived-absent, not missing — the pull attempted them and got a
two-pass-confirmed 403. 2017 detailed feeds were **not attempted at all** at
B2 time (no valid 2017 index ⇒ no 2017 race_ids to request; §8d) — the
manifest held zero 2017 detailed-feed rows, distinct from 2015-2016's
confirmed-`absent` rows. §8f's direct probe found the true 2017 floor differs
from what B2 assumed: `weekend-feed`/`live-feed` actually start **2017**, not
2018 — only `live-flag-data` (2019) and `lap-times`/`live-pit-data`/
`lap-notes` (2020) matched the B2-era assumption once actually tested.

### 8f. B4 — 2017 recovered via direct race_id probe (2026-07-19)

`src/bronze_probe_2017.py` (one-off, not part of `--full`/`--update`) bypassed
the broken 2017 index entirely: it derived each series' race_id gap between
its last 2016 race and its first 2018 race directly from `bronze.races_index`
(series 1: 4519-4672, series 2: 4552-4713, series 3: 4575-4746 — 488
candidates total) and probed `weekend-feed` for every candidate id in
year=2017, using the exact same fetch/retry/circuit-breaker/manifest
machinery as `bronze_fetch.py`.

Result: **97 stored, 391 confirmed-`absent` (two-pass), 0 failed** — series 1
(Cup): 41 stored/154 candidates, series 2 (Xfinity): 33/162, series 3
(Truck): 23/172. These recovered counts match the real 2017 schedules almost
exactly (2017 Cup ran 36 points races + Clash/Duels/All-Star; Xfinity 33
races; Trucks 23 races), and the recovered payloads carry full results (e.g.
race_id 4579 = the 2017 Daytona 500, 42 results rows; race_id 4576 = the
Advance Auto Parts Clash, `race_type_id=2`), `race_date` spanning
2017-02-19 through 2017-11-19 across all three series, and every other
`weekend-feed` field (`average_speed`, `total_race_time`, etc.) populated —
not partial or index-only data.

The bulk of the 391 `absent` results is not evidence of missing Cup/Xfinity/
Truck data — `race_id` is a single global counter shared across all three
series (and non-points events), so most of a series' full candidate range
was never that series' race_id to begin with; probing series 1 against an id
that was actually an Xfinity race legitimately 404s. The stored counts
landing right at each series' real season length confirms this rather than
suggesting further gaps.

**Consequence:** the §8d/§8e conclusion that 2017 contributes nothing beyond
index metadata was wrong. Full 2017 `weekend-feed` data (schedule, results,
stats) now exists in bronze for all three series, on par with 2018+.

**Follow-up (same day, owner-directed): the remaining 5 feeds.** Since the
2015-2016 floor generalization had just been shown wrong for `weekend-feed`,
the same untested-assumption risk applied to the other 5 feeds for 2017 —
they'd never actually been asked either. `src/bronze_probe_2017_remaining.py`
targeted the exact 97 `(series_id, race_id)` pairs `weekend-feed` had already
confirmed real (no need to re-probe the wide id range) against `lap-times`,
`live-pit-data`, `lap-notes`, `live-flag-data`, `live-feed`. Result: **`live-feed`
also exists for 2017 (97/97 stored)**; `lap-times`/`live-pit-data`/`lap-notes`/
`live-flag-data` are genuinely absent for 2017 (97/97 confirmed two-pass `absent`
each, 0 failed) — so the original floor generalization was right for those
four feeds specifically, just wrong for `weekend-feed` and `live-feed`. The
true per-feed 2017 floor: `weekend-feed`/`live-feed` = 2017, `live-flag-data`
= 2019, `lap-times`/`live-pit-data`/`lap-notes` = 2020 (all uniform across
series, matching every other year's pattern — 2017 just needed asking).

**Warehouse wiring:** `warehouse._load_races_index()` built `bronze.races_index`
exclusively from `race_list` snapshots, so the recovered 2017 rows were
invisible to `bronze.races_index`/`bronze.coverage` (and therefore to any
silver/gold consumer) despite being on disk. Added
`_load_races_index_from_weekend_feed()`: for any year with no usable
`race_list` index but with stored `weekend-feed` files (currently just 2017),
it synthesizes the same row shape per-race directly from each race's own
`weekend-feed` payload instead of a year-level index snapshot. General on
purpose, not hardcoded to 2017. `bronze.races_index` now carries 1,166 rows
(was 1,069), `bronze.coverage`'s totals moved from 4,222/1,964 to 4,416/2,352
(+194 stored = 97 `weekend-feed` + 97 `live-feed`; +388 absent = 4 feeds ×
97 races) — exactly the expected 2017 addition, verified via `bronze_report.py`
with zero regression to 2015-2026.

2017 Cup/Xfinity/Truck data is now on par with 2018+ in every bronze/warehouse
respect. Whether to pull 2017 into silver/gold scope (C1 onward) remains a
separate decision for whoever scopes those sessions — bronze/warehouse
availability and silver/gold inclusion are not the same question.
