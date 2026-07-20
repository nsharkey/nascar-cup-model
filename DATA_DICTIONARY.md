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

Written by `score_race.py` (built in D2 — see §11); contract frozen in
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
`_load_races_index_from_weekend_feed()` (renamed/generalized to
`_load_race_records_from_weekend_feed()` at C1 -- §9b): for any year with no
usable `race_list` index but with stored `weekend-feed` files (currently
just 2017), it synthesizes the same row shape per-race directly from each
race's own `weekend-feed` payload instead of a year-level index snapshot.
General on purpose, not hardcoded to 2017. `bronze.races_index` now carries 1,166 rows
(was 1,069), `bronze.coverage`'s totals moved from 4,222/1,964 to 4,416/2,352
(+194 stored = 97 `weekend-feed` + 97 `live-feed`; +388 absent = 4 feeds ×
97 races) — exactly the expected 2017 addition, verified via `bronze_report.py`
with zero regression to 2015-2026.

2017 Cup/Xfinity/Truck data is now on par with 2018+ in every bronze/warehouse
respect. Whether to pull 2017 into silver/gold scope (C1 onward) remains a
separate decision for whoever scopes those sessions — bronze/warehouse
availability and silver/gold inclusion are not the same question.

---

## 9. Silver layer — `data/silver/` (medallion rebuild, C1)

Cleaned/conformed tables built by `src/silver_build.py` from bronze. Design:
`specs/medallion_architecture.md` section 3. `silver.driver_race` is the
FROZEN parity table (section 3.3) — reproduces `races_parsed.pkl`
field-for-field via the C-gate (section 4); see `## RESULT — C-gate` in the
spec and `report/SILVER_REGRESSION.md` for the full C1 outcome.

### 9a. `silver.races` — `data/silver/races.parquet`

One row per `(series_id, race_id)`, every year/series/`race_type_id` present
in bronze (1,166 races as of C1: 601 Cup/Xfinity/Truck `race_type_id=1`
points races, plus exhibitions and other race types). Source: the latest
`race_list_basic` index entry for that race (or, for years with no usable
index — 2017 — the race's own `weekend-feed` `weekend_race[0]` object,
which carries the identical field vocabulary; `DATA_DICTIONARY` §8f).

| field | type | meaning |
|-------|------|---------|
| `series_id` | int | 1 Cup / 2 Xfinity / 3 Trucks. |
| `race_id` | int | NASCAR `race_id`. |
| `year` | int | Season year (index snapshot directory year). |
| `race_type_id` | int | 1 = points race; other values = exhibitions etc. |
| `race_date` | str | Verbatim ISO race datetime from the index entry. |
| `race_name` | str | Verbatim race name. |
| `track_id` | int | NASCAR track id. |
| `track_name` | str | Stripped track name. |
| `scheduled_laps` / `actual_laps` | int | Race distance. |
| `stage_1_laps` / `stage_2_laps` / `stage_3_laps` | int | Stage lengths (0 if unstaged). |
| `winner_driver_id` | int \| null | Unset for pre-2020-ish index rows (§8c) and some exhibitions. |
| `green_flag_utc` | str \| null | `schedule[]` entry with `event_name=='Race'` → `start_time_utc`; `null` if no such entry. |
| `number_of_cautions` / `number_of_caution_laps` / `number_of_lead_changes` | int | Race summary stats. |
| `parse_status` | str | `ok` \| `skipped: <reason>` (verbatim `parse_race` skip string) \| `not_attempted` (missing lap-times/weekend-feed, or non-points race type). |
| `n_green` / `n_fe` / `n_prac` | int \| null | Parse diagnostics from `parse_race`; `null` unless `parse_status='ok'`. |

### 9b. `silver.driver_race` — `data/silver/driver_race.parquet` (FROZEN parity contract)

One row per `(series_id, race_id, driver_id)` for every race with
`parse_status='ok'` (22,463 rows as of C1, 6,083 of them the 163-race Cup
2022–2026 anchor subset). Produced by feeding each race's latest bronze
`lap-times` + `weekend-feed` through `parse_lib.parse_race()` **unmodified**
— same code path, same bytes, so parity with `races_parsed.pkl` (§1) is
mechanical rather than re-derived. Columns: `series_id, race_id, year,
race_date, track, driver_id`, then the 15 driver fields of §1b verbatim
(`finish, start, qspeed, status, team, make, laps_led, laps_completed,
pace_med85, pace_mean70, pace_p20, pace_best, nlaps, fepace, practice`) —
same types and null semantics as §1b (a plain `dict.get()` on the same
`parse_race()` output dict reproduces the pkl's absent-key-vs-`None`
distinction automatically).

Attempted for **any series**, not just Cup — the spec's frozen behavior
(field-size gates etc.) applies unchanged to Xfinity/Trucks; a race that
fails them is `skipped`, correctly. This means `silver.driver_race` has
substantially more races than the 163-race Cup anchor (2020–2026 Cup, plus
Xfinity/Trucks) — additive, not a parity violation (section 4.1: "the
universe grows with it").

### 9c. `src/warehouse.py` extension (C1)

`load_race_records()` (public): full raw per-race record (every
`race_list_basic`/`weekend_race` field, not the 7-column trim) per
`(series_id, race_id)`, used by `silver_build.py` to populate `silver.races`.
`_load_races_index()` (bronze layer) is now a thin trim of
`load_race_records()`'s output — same `bronze.races_index` columns/behavior
as before, zero regression. `build_warehouse()` additionally registers
`silver.races` / `silver.driver_race` as DuckDB views over the parquet files
in `data/silver/` when present (same rebuildable-from-disk pattern as the
bronze views — deleting `nascar.duckdb` never loses information).

### 9d. C1 finding — `fepace` cross-environment BLAS/LAPACK non-reproducibility (2026-07-19)

The C-gate (section 4) as originally FROZEN demands bit-identical floats,
"no epsilon granted," on the theory that the same code on the same bytes is
deterministic. For 162/163 anchor races this held for every field **except**
`fepace` — the one §1b/§3.3 column computed via `np.linalg.lstsq` (an SVD
solve). Diffs were ULP-scale (~1e-15 relative) and stable across repeated
runs in this session, the signature of a numpy/BLAS/LAPACK implementation
difference between this environment (numpy 2.1.3, OpenBLAS 0.3.21, macOS
arm64) and whatever built `races_parsed.pkl`, not a code or data
difference. Owner-authorized dated amendment (spec section 4, `## AMENDMENT
(2026-07-19...)`) relaxed `fepace`'s equality check to
`math.isclose(rel_tol=1e-9, abs_tol=1e-12)`; every other column is
unaffected and still compares by exact `==`. `fepace` is not used by the
production model (`walkforward.py`'s frozen feature set is `[fin, pace,
typed, start]`, `pace=pace_med85`) — see report §7's "proven dead end."
Full per-race, per-driver diff detail: `report/SILVER_REGRESSION.md`.

### 9e. C2 breadth tables — `data/silver/*.parquet` (medallion rebuild, C2)

Eight tables built by `silver_build.py`'s `build_silver_breadth()` (section 3.4 of the medallion
spec) — no parity obligation, built in DuckDB SQL directly over bronze `json.gz` files (one file
per query, explicit `columns=` schema, to avoid cross-season type-drift in DuckDB's JSON
auto-detection). Every table carries `series_id, race_id`. Common key map applied at extraction:
`NASCARDriverID→driver_id`, `LapTime→lap_time`, `Lap→lap`, `RunningPos→running_pos`,
`FlagState→flag_state`, `LapsCompleted→laps_completed`. Dedupe rule: exact-duplicate rows dropped
silently; same-key-different-value conflicts keep the first row and are counted. Full build
report (row counts, dedupe/conflict counts, pit-stop resolution stats): `report/SILVER_BREADTH.md`.

| table | grain | source | key columns |
|---|---|---|---|
| `silver.results` | driver-race | `weekend-feed` `weekend_race[0].results[]`, flattened verbatim | `(series_id, race_id, driver_id)` |
| `silver.laps` | driver-lap | `lap-times` `laps[].Laps[]` | `(series_id, race_id, driver_id, lap)` |
| `silver.lap_flags` | lap | `lap-times` `flags[]` | `(series_id, race_id, laps_completed)` |
| `silver.flag_events` | event (ordered) | `live-flag-data` (root-level array) | `event_seq` (file order); no smaller natural key than full row content |
| `silver.pit_stops` | stop (ordered) | `live-pit-data` (root-level array) | `stop_seq` (file order); `driver_id` resolved (see below) |
| `silver.lap_notes` | note | `lap-notes` (`{"laps": {lap_str: [...]}}`, a map keyed by lap number) | `(series_id, race_id, note_id)` |
| `silver.practice_runs` | driver-run | `weekend-feed` `weekend_runs[].results[]` | `(series_id, race_id, weekend_run_id, driver_id)` |
| `silver.live_final` | driver-race (final frame) | `live-feed` `vehicles[]` (latest stored snapshot = the post-race final frame) | `(series_id, race_id, driver_id)` |

Notes:

- `silver.results` is built for **every** race with a stored `weekend-feed`, including races
  `silver.driver_race` skips (non-Cup, non-points, or parse-failed) — it is a superset by design.
- `silver.live_final.driver` is a nested object (`driver_id, full_name, first_name, last_name,
  is_in_chase`) flattened to `driver_id, driver_full_name, driver_first_name, driver_last_name,
  driver_is_in_chase`. `laps_led` there is a `LIST<STRUCT(start_lap, end_lap)>` (lap ranges led),
  distinct from `silver.results.laps_led` (an integer count) — same field name, different feed,
  different shape; not to be confused.
- `silver.pit_stops.driver_id` resolution (section 3.4): join `vehicle_number` to
  `silver.results.car_number` (trimmed strings, within race, only if the match is unique); else
  exact `driver_name == driver_fullname` (within race, only if unique); else `NULL`. 112,596 of
  113,423 rows (99.3%) resolved by car number, 2 by name, 825 unresolved — see
  `report/SILVER_BREADTH.md` for the two known unresolved patterns (the race-5580 `weekend_race`
  null gap, and Cup-crossover drivers appearing in a lower-series race's shared pit-road feed).
- `src/warehouse.py`'s `build_warehouse()` registers all eight as DuckDB views over their parquet
  files when present, same rebuildable-from-disk pattern as `silver.races`/`silver.driver_race`.
- Incremental build state: `data/silver/_breadth_build_state.parquet`, keyed by
  `(series_id, race_id)`, fingerprint = `sha256("breadth_v{N}|" + joined shas of whichever of the
  six section-3.4 feeds are currently stored for that race)`. `N` (`BREADTH_VERSION` in
  `silver_build.py`) is bumped on any section-3.4 transform change, forcing a full rebuild —
  independent of `silver.driver_race`'s own `PARSER_VERSION`/build state, so a breadth-only logic
  change never forces an unnecessary re-parse of the frozen parity path (and vice versa).

### 9f. Track reference tables — `data/silver/*.parquet` (medallion rebuild, C3)

Seven tables built by `src/track_reference_build.py` from the vendored `research/track_audit/`
package (loader: `src/track_audit.py`; section 7 above) plus `silver.races`. Design:
`research/track_audit_derivation.md` section 2. No parity obligation, no incremental build state
(cheap to fully rebuild every time from the immutable package). Package files untouched —
`src/test_track_audit.py` and the frozen C-gate (`src/gate_silver.py`) both re-run clean after
this build. New sibling gate: `src/gate_track_reference.py` (re-derivation checks: row counts,
banking parse, dim↔xwalk join integrity, race_track/race_track_features consistency). Full build
report, including two findings from this session (a crosswalk row-count prose correction and a
real join bug caught and fixed): `report/TRACK_REFERENCE.md`.

| table | rows | grain | notes |
|---|---:|---|---|
| `silver.track_dim` | 43 | one per `track_id` | T1 physical facts (`length_mi, shape, surface, road_course, turns, banking_text` verbatim + parsed `banking_max_deg`/`banking_secondary_deg`), T2 taxonomy (`primary_family, secondary_family`), era bounds + Cup-points-race counts, `hp750_2026` BOOL (`road_course OR length_mi < 1.5`, VF S039), provenance (`source_ids, confidence, evidence_class, package_version, source_sha256, built_at`). **The ten `*_prior` fields, `key_comparables`, `structural_nearest_neighbors`, and all narrative fields are deliberately excluded** — a fact table nobody can mistake for a Working Hypothesis (section 2.2's design decision). |
| `silver.track_xwalk` | 44 | one per era-range (`sonoma_short` has two) | Crosswalk verbatim + provenance. **44, not the "45" some prose says** — see the build report's row-count correction. |
| `silver.track_priors` | 430 | `(track_id, prior_name)` | Long-form quarantine table: `track_id, prior_name, score (1-10), score_type` (verbatim "not an empirical measurement" warning), `evidence_class='Working Hypothesis'`, `package_version`. Every row labeled — nothing here can be silently read as a measurement. |
| `silver.track_similarity_prior` | 193 | edge | The 193 structural-similarity edges verbatim, same quarantine treatment (`evidence_class='Working Hypothesis'`). |
| `silver.rules_era` | 6 | one per era | `era_key, season_start, season_end, description, source_ids`, transcribed from the narrative report's "Recommended era keys" table (`track_audit.RULES_ERA`). Contiguous, `season_end=9999` for the open 2026 era. |
| `silver.race_track` | 966 | `(series_id, race_id)` | `series_id, race_id, track_id`. **All three series**, points races only (`race_type_id=1`) — join of `silver.races` to the crosswalk on `(track_name=feed_track_name, season_start<=year<=season_end)`, with the Phoenix-2018 month-split tiebreak implemented for parity with `track_id_for()` (verified unreachable against real data — 2018 Phoenix races carry the track_name `"ISM Raceway"`, outside the crosswalk's vocabulary). Unresolved races (historical facility-name variants) are simply absent, the standard silver coverage-by-absence convention. |
| `silver.race_track_features` | 404 | `(series_id, race_id)`, **Cup only** | The section-2.3 leakage-free derived features: `config_age_years, config_race_number, return_gap_years, era_key, era_race_number, hp750_2026`. Restricted to `series_id=1` because the source counts (`schedule_by_year`) are Cup-points-race counts by the package's own stated scope. `config_race_number`/`return_gap_years` computed walk-forward: full prior seasons from the package's own `schedule_by_year` (safe for any completed season), within-season order from the repo's actual `race_date` sequence. None of these are model features until they win their own pre-registered A/B (research/track_audit_derivation.md section 7, catalog items 6/7). |

`src/warehouse.py`'s `build_warehouse()` registers all seven as DuckDB views over their parquet
files, same rebuildable-from-disk pattern as every other silver table.

## 10. Gold layer — `data/gold/` (medallion rebuild, D1)

Feature-bank tables built by `src/gold_build.py` in DuckDB SQL over `silver.driver_race` /
`silver.races` — no parity obligation of their own, but `gold.wf_features` transcribes
`walkforward.run()`'s history mechanics exactly and is re-proven bit-for-bit against a Python
replay by the D-gate (section 6 of the spec; see `## RESULT — D-gate` and
`report/GOLD_REPROOF.md` for the full R0–R3 outcome — PASS, zero mismatches).

**Scope amendment (2026-07-19, D1):** `gold.wf_features` and the current-form views are bounded
to `series_id=1, race_type_id=1, parse_status='ok', year >= 2022` — matching exactly what
`races_parsed.pkl` ever contained, even though silver itself covers back to 2020. See the spec's
`## AMENDMENT` block before section 5.3 for the full rationale (unbounded history would give 2022
drivers real 2020–2021 history the legacy engine never had).

### 10a. `gold.track_typology` — `data/gold/track_typology.parquet`

34 rows, one per track name in `walkforward.MY_TYPE` (imported directly from `src/walkforward.py`
at build time, not hand-transcribed — the strongest available guarantee of "verbatim", spec
section 5.1). Columns: `track_name, ttype` (`SS` / `INT` / `SHORT` / `ROAD` / `OTHER`). Any track
name not present in this table maps to `'UNIQ'` by convention wherever it's joined (never stored
as a row — the fallback is applied at query time, matching `MY_TYPE.get(track, 'UNIQ')`).

### 10b. `gold.wf_features` — `data/gold/wf_features.parquet`

6,083 rows — one per `(race_id, driver_id)` for every driver in every scope-qualifying race
(2022–2026, 163 races; row count matches the C-gate anchor's driver-race row count exactly, since
the scope amendment lines gold up with the anchor's own universe).

| field | type | meaning |
|---|---|---|
| `race_id` | int | NASCAR race id (target race). |
| `driver_id` | int | Driver. |
| `race_seq` | int | 1-based index of the target race in `(race_date, race_id)` order — the walk-forward clock. |
| `n_hist` | int | Count of this driver's scope races strictly before `race_seq`. |
| `fin_h` | double \| null | Half-life-8 recency-weighted mean of prior finishes. `null` iff `n_hist=0`. |
| `pace_h` | double \| null | Same, over the subsequence of prior races with non-null `pace_med85` — the recency exponent ranks WITHIN that subsequence, not within all prior races (the transcription trap section 5.2 calls out explicitly). `null` if the subsequence is empty. |
| `typ_h` | double \| null | Shrinkage blend of the typed (same-`ttype`-as-target) weighted mean and `fin_h`: `(m·typed_wmean + 3·fin_h)/(m+3)` if `m>0` else `fin_h`; `null` iff `fin_h` is `null`. `ttype` for both the target and every prior race is each race's OWN track mapped through `gold.track_typology`. |
| `start_feat` | int | Target race's `start`, falsy (`null` or `0`) mapped to `20`. |
| `has_pace` | bool | Target race's `pace_med85 IS NOT NULL`. |
| `finish` | int | Target race's `finish` (backtest label, convenience). |

Half-life 8 and shrinkage constant 3 are frozen config values (`HALF_LIFE`/`SHRINK_K` in
`gold_build.py`), not derived. Eligibility filtering (burn 15, `n_hist>=5`, `has_pace`, `>=20`
eligible per race), z-scoring, and PL fitting are NOT computed here — they depend on the per-race
eligible set and stay in the engine (`walkforward.py`, unedited), per spec section 5.2.

### 10c. Current-form views — `data/gold/driver_form.parquet`, `data/gold/driver_type_form.parquet`

For the weekly prediction (post-cutover, section 5.3) — same weighting, evaluated "as of the
latest scope race" rather than relative to a specific target race (i.e. every scope race counts
as history, ranked purely by recency).

| table | rows | grain | columns |
|---|---:|---|---|
| `gold.driver_form` | 101 | one per `driver_id` | `n_hist, fin_h, pace_h` — same definitions as `gold.wf_features`, evaluated over ALL of that driver's scope races. |
| `gold.driver_type_form` | 325 | `(driver_id, ttype)` | `m, typed_wmean` — the building blocks `predict_next.py` combines with the target race's own `ttype` (via `gold.track_typology`) to compute `typ_h` at prediction time. |

### 10d. `src/warehouse.py` extension (D1)

`build_warehouse()` registers all four gold tables as DuckDB views over their parquet files in
`data/gold/` when present, same rebuildable-from-disk pattern as bronze/silver — deleting
`nascar.duckdb` never loses information. `gold_build.py` calls `build_warehouse()` twice: once
before computing (so `silver.*` views are fresh) and once after (so `gold.*` views pick up the
parquet files just written).

### 10e. D1 finding — the R0 trio's published 2026-OOS figure (2026-07-19)

R0 (section 6) initially reproduced backtest (0.413) and non-SS (0.476) exactly but not 2026-OOS
(0.447 vs the published 0.449). Root cause, confirmed by re-running the anchor through all five of
`step4_models.py`'s `SPECS` variants: the published 0.449 was generated from `prior_all` (a
5-feature spec that includes `fepace`), not `fpts` (the actually-frozen 4-feature production
model, `[fin, pace, typed, start]`) — exactly the mechanism spec section 9's pre-flagged ambiguity
A1 anticipated. `fpts` and `prior_all` agree to 3dp on the 143-race backtest and ~90-race non-SS
slices (large samples wash out `fepace`'s marginal effect) but diverge on the small 20-race
2026-OOS slice, crossing a rounding boundary. Owner-authorized resolution: `fpts` stays the
D-gate's reference model (matches HANDOFF's frozen config; `fepace` is confirmed unused in
production, §9d above); the D-gate's expected 2026-OOS figure is corrected to 0.447. Full detail:
spec section 6's `## AMENDMENT` block (before `## RESULT — D-gate`) and `report/GOLD_REPROOF.md`.
Note: HANDOFF.md/README.md's own headline "0.449" citations describe the mixed-provenance figure
and are unchanged by this finding (a documentation cleanup out of D1's scope, not a gate blocker)
— new citations of the 2026-OOS figure for the model actually in production should use 0.447.

---

## 11. Scoring and market-benchmark consumers — `src/score_race.py`, `src/market_benchmark.py` (medallion rebuild, D2)

Implement `scoring_methodology.md` and `market_benchmark_decision_rule.md` verbatim (incl. every
amendment). Output contracts (`predictions/scores_log.csv`, `book_prices.entries[]`) are already
documented in sections 3–5 above and unchanged by this build — this section covers only the new
code and its gold-side plumbing.

### 11a. `src/score_race.py`

Pure functions per the spec's implementation checklist: `verify_hash`, `load_results`,
`common_set`, `score_rho`, `score_h2h`, `grade_books` (built on a shared
`malformed_dedup_void()` — see 11b), `compose_row`, `upsert_row`; `main()` wires them per section 8.
Does not import anything from bronze — section 5.5's compatibility shim (11c) is a separate,
upstream step. `src/test_score_race.py` implements all 10 frozen fixtures (F1–F10), plain stdlib
asserts, no pytest.

Two behaviors worth flagging explicitly since they're easy to miss reading the frozen spec alone:

- **Completeness gate + snapshot freeze** (results-finality amendment): before loading results,
  confirms `race_list_basic.json`'s `winner_driver_id` is truthy (same signal `update_data.py`
  uses); on first successful scoring, copies the exact results bytes used to
  `src/data/races/{year}_{race_id}_wf_scored.json`, which then takes precedence over `_wf.json` and
  the network on every later run for that race and is never overwritten.
- **`post-race price entry` note** (provenance amendment): for each `book_prices` entry, walks
  `git log --follow` on the prediction JSON to find the first commit whose content contains that
  exact entry (matched on unordered driver pair + book + `recorded_utc`), and compares that
  commit's committer timestamp against the race's *scheduled* green-flag `start_time_utc`
  (`race_list_basic.json`'s `schedule[]`, `event_name == "Race"`). Best-effort by design: any git
  failure silently yields no note rather than crashing a real scoring run; the "ref pushed before
  the scheduled start" refinement the amendment adds once a remote exists is approximated by the
  local committer timestamp alone (git has no native push-time record) — see spec section
  `## RESULT — D2` item 8 for the full reasoning.

### 11b. Shared entry pipeline — `score_race.malformed_dedup_void(entries)`

Factored out of `grade_books` because the market spec's own resolved-ambiguity register says it
imports exactly this: "the entry schema (scoring 5.1) and the malformed→dedup→void pipeline
(scoring 5.2 and its pipeline-order amendment)" — but NOT section 5.3's strict-book-favorite
filter, which stays local to `score_race.grade_books`. `market_benchmark.py` imports this function
directly rather than duplicating the pipeline.

### 11c. `src/bronze_fetch.py --sync-legacy-cache RACE_ID` — section 5.5 compatibility shim

`sync_legacy_wf_cache(race_id, series_id=1, year=None)`: finds the latest bronze-stored
weekend-feed for a Cup race (globbing `data/bronze/series_1/*/​{race_id}/` for the year if not
given), gunzips it, and writes the raw bytes — byte-identical, no `json.dump` re-serialization — to
`src/data/races/{year}_{race_id}_wf.json`, the exact path `scoring_methodology.md` section 1.2
names. `score_race.py` itself has no knowledge of bronze; this is a separate step that runs first
in the weekly flow (`bronze_fetch.py --update` → `--sync-legacy-cache RACE_ID` → `score_race.py
RACE_ID`).

### 11d. `src/market_benchmark.py`

Recomputes every graded pick from scratch on each run (idempotent). A race counts for this script's
statistic exactly when its `_wf_scored.json` snapshot exists — never `_wf.json`, never the network,
never `scores_log.csv` (section 6 inputs-pinned amendment). `find_primary_book()` walks commit
history across all of `predictions/` oldest-first and binds to the book named in the first commit
that ever added a non-empty `book_prices.entries` anywhere — currently `draftkings`, bound at
commit `5af852c`. Resampling mechanics are pinned exactly: `numpy.random.default_rng(20260718)`
constructed fresh per look, `B=10000`, add-one bootstrap p, futility bound = the 9,501st ascending
order statistic of the resampled mean-profit-per-pick values, dual interim boundary (bootstrap p
AND a one-sided t-test on per-race profit totals both ≤ 0.001), and the K≥20 race-count floor
gating every decision arm — including final-look NO-EDGE, not just EDGE (the amendment's "a final
look with K < 20 returns UNDERPOWERED" is unconditional).

### 11e. `gold.scores`, `gold.predictions` — read-only conveniences (`src/warehouse.py`)

Views only, created when their source exists; never written to. `gold.scores` = `read_csv_auto`
over `predictions/scores_log.csv`. `gold.predictions` = `read_json_auto` over
`predictions/race_*_prediction.json` (`union_by_name=true`, since not every field is present in
every prediction — e.g. `book_prices.entries` shape varies). The CSV and sealed JSONs remain the
artifacts of record; rebuilding `nascar.duckdb` never touches them.

### 11f. `src/gold_predict_dryrun.py` — dry-run only, section 7.3 step 2 verification

Not part of the weekly protocol and not the cutover. Reproduces `predict_next.py`'s exact
training/current-form/sampling logic sourced from `gold.wf_features` (training — a single final
`pl_fit` over the full accumulated eligible-race set, not gate_gold.py's incremental walk-forward
refit) and `gold.driver_form` / `gold.driver_type_form` (current form, section 5.3) instead of the
pkl replay, and returns the payload in-memory without writing to `predictions/`. Used once, live,
to prove the section 7.3 dual-run identity check for race 5618 (PASS — see spec `## RESULT — D2`).
Kept committed because its logic is what actual cutover folds into `predict_next.py` in place;
`predict_next.py` itself is untouched and remains the path of record.

### 11g. D2 finding — race 5618's book prices are provenance-inadmissible (2026-07-19)

All 3 of race 5618's recorded `book_prices` entries first appear in commit `5af852c`
(`2026-07-19T23:26:57Z`), 26m57s after the race's *scheduled* green flag (`2026-07-19T23:00:00Z`
per `race_list_basic.json`). Per the admissibility amendment this makes them inadmissible for
`market_benchmark.py`'s statistic (they still count fully toward `score_race.py`'s descriptive
`book_n`, carrying the `post-race price entry` note). Not a bug and not corrected — the race's
actual green flag was delayed well past its scheduled time (results still weren't posted ~3h
later), which is exactly the real-world edge the frozen rule's scheduled-time basis anticipates
rather than tries to detect after the fact.
