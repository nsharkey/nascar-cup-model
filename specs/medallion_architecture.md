# SPEC: Medallion architecture — the bronze/silver/gold foundation rebuild

**Status:** pre-registered design, written 2026-07-19 in plan session B1
(Fable 5, spec-only, no production code). Governs build sessions B2, B3, C1,
C2, D1, D2 in `plan/schedule.yml`.

**Freeze map.** Per `specs/README.md` discipline:

- **FROZEN on commit:** §4 (silver regression gate), §6 (gold re-prove gate),
  §3.3 (the driver-race parity contract), and §7.1–§7.3 (path-of-record,
  continuity, and cutover rules). These are decision rules; they may not be
  edited once committed except by the dated-amendment mechanism, and never
  after the data they adjudicate exists.
- **Stable design (amendable by dated note until the relevant build session
  starts):** everything else — layouts, protocol constants, table columns for
  the *new* (non-parity) tables, checklists.
- `## RESULT` blocks at the end are the designated write-points for B3, C1,
  D1, D2 outcomes.

**Doctrine this spec serves** (from HANDOFF and the 2026-07-19 direction):
the project's equity is its **validated results and pre-registered
decisions** — the audit conclusions, the frozen config VALUES, `specs/`, the
sealed predictions. Plumbing is rebuilt freely; the model is **re-proven on
the new foundation, never re-chosen**. The perishable weekly odds capture
(E1) never pauses for any of this.

---

## 0. Scope and invariants

### 0.1 What this spec builds

A local, embedded medallion data foundation:

- **Bronze** — an immutable, hashed archive of raw JSON from every public
  `cf.nascar.com` feed the project knows about, all three national series,
  back to the real per-feed floor.
- **Silver** — cleaned, conformed, deduplicated tables (parquet, queried via
  DuckDB), one of which reproduces today's `races_parsed.pkl` exactly.
- **Gold** — the frozen walk-forward features as SQL-built tables, plus
  scoring and the market benchmark re-homed as consumers.

Stack: **DuckDB** (engine) + **parquet** (silver/gold storage) + **gzipped
raw JSON** (bronze storage). Deliberately no Spark, no Databricks, no cloud
dependency — this is a <5 GB project on one machine. (The owner's NFL
project is the Databricks one; this repo is intentionally the lightweight
counterpart.)

### 0.2 What this spec does NOT change (invariants)

1. **Frozen config VALUES:** `pace_med85`, half-life 8, `MY_TYPE` typology,
   shrinkage typed history, PL features `[fin, pace, typed, start]`, ridge
   λ=0.5, burn 15, min_hist 5, min_drv 20. They carry over verbatim.
2. **The frozen specs** (`scoring_methodology.md`,
   `market_benchmark_decision_rule.md`, the two A/B protocols) — their rules,
   thresholds, schemas, and **file-path mechanics** are honored verbatim.
   Where a frozen spec names a concrete path (e.g. scoring §1.2's
   `src/data/races/{year}_{race_id}_wf.json`, or the market spec's
   `_wf_scored.json` snapshots), the medallion **feeds that path** rather
   than amending the spec (§5.5).
3. **Sealed artifacts:** everything in `predictions/` (JSONs, `.md`s,
   `predictions_log.csv`, future `scores_log.csv`), `report/`, `review/`,
   `specs/`. Architecture-independent; never migrated, never rewritten.
4. **Doctrine:** SS stand-down, no post-hoc predictions, one step at a time,
   frozen config, negative results are valid outcomes.
5. **The weekly protocol (E1):** runs on the legacy pkl path until §6's gate
   passes and §7.3's cutover completes. On a race weekend the prediction
   commit always precedes any rebuild work.

### 0.3 New dependencies

Add to `requirements.txt` in B2: `duckdb>=1.0`, `pyarrow>=15`. Record the
exact installed versions in the B3 coverage report and the D1 gate report.
(`numpy`/`scipy` pins unchanged — the D-gate reference runs must use the
same venv as the audit did.)

---

## 1. Repo layout, naming, git policy

### 1.1 Directory layout (all new data under repo-root `data/`)

```
data/                                  # gitignored in full (see §1.3)
  bronze/
    manifest.jsonl                     # append-only fetch ledger (§2.3)
    .tmp/                              # in-flight downloads (atomic-rename source)
    race_list/{year}/race_list_basic.{fetch_ts}.json.gz
    series_{sid}/{year}/{race_id}/{feed}.{fetch_ts}.json.gz
    legacy_import/{original_filename}.json.gz   # §2.6
  silver/
    races.parquet
    driver_race.parquet
    results.parquet
    laps.parquet
    lap_flags.parquet
    flag_events.parquet
    pit_stops.parquet
    lap_notes.parquet
    practice_runs.parquet
    live_final.parquet
    _build_state.parquet               # per-race input fingerprints (§3.5)
  gold/
    wf_features.parquet
    track_typology.parquet
  anchors/
    races_parsed_anchor_{YYYYMMDD}.pkl # §4.1 (sha256 recorded in committed report)
  nascar.duckdb                        # derived warehouse — always rebuildable (§1.2)
```

- `{sid}` = series_id: 1 Cup, 2 Xfinity, 3 Trucks.
- `{feed}` = the exact remote basename without extension: `weekend-feed`,
  `lap-times`, `live-pit-data`, `live-flag-data`, `lap-notes`, `live-feed`.
- `{fetch_ts}` = UTC fetch time, compact form `YYYYMMDDTHHMMSSZ`. Multiple
  versions of one feed coexist; **latest = lexicographic max on disk** (disk
  is truth for content; the manifest is provenance).

### 1.2 The warehouse file is derived, never authoritative

`data/nascar.duckdb` holds schemas `bronze` (catalog views), `silver`, and
`gold` (views over the parquet files plus the SQL that builds gold).
`src/warehouse.py` recreates it from scratch at any time. Durable state
lives ONLY in: bronze files + `manifest.jsonl`, silver/gold parquet, and the
committed repo. Deleting `nascar.duckdb` must never lose information.

### 1.3 Git policy

- Append `data/` to `.gitignore` (existing entries stay).
- Committed instead of data: the coverage/gate **reports** (`report/`
  additions named in §10 checklists), each containing the relevant sha256
  anchors (manifest digest, anchor-pkl hash, parquet content hashes where a
  gate depends on them).
- Commit cadence per global preference: batch locally at working
  checkpoints; no remote exists yet (E2 pending), so sessions end with a
  clean, fully committed tree.

### 1.4 New source modules (flat in `src/`, matching repo style)

| file | role | built in |
|---|---|---|
| `src/bronze_fetch.py` | discovery, full pull, weekly increment, verify (`--full` / `--update` / `--verify`) | B2 |
| `src/bronze_report.py` | coverage matrix + terminal-state report | B2/B3 |
| `src/silver_build.py` | bronze → silver (parity path + new tables; `--full` / incremental) | C1/C2 |
| `src/gate_silver.py` | §4 regression gate | C1 |
| `src/gold_build.py` | silver → gold SQL feature build | D1 |
| `src/gate_gold.py` | §6 re-prove gate (R0–R3) | D1 |
| `src/warehouse.py` | (re)build `nascar.duckdb` schemas/views | B2, extended C/D |
| `src/score_race.py` + `src/test_score_race.py` | per frozen scoring spec, verbatim | D2 |
| `src/market_benchmark.py` | per frozen market spec + amendments, verbatim | D2 |

Scripts run from `src/` like the existing pipeline; each resolves the repo
root as `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` and
data paths from there.

---

## 2. Bronze — immutable raw archive

### 2.1 Feed inventory and verified URL patterns

Live-probed 2026-07-19 (this session; ~20 polite GETs). All patterns
verified working unless noted:

| feed | URL pattern | verified on |
|---|---|---|
| index | `https://cf.nascar.com/cacher/{year}/race_list_basic.json` | 2015, 2018, 2024, 2026 → 200; **2013, 2014 → 403** |
| weekend-feed | `https://cf.nascar.com/cacher/{year}/{sid}/{race_id}/weekend-feed.json` | sid 1 (163 races, existing pipeline), sid 2 (2024/5443) |
| lap-times | same shape, `lap-times.json` | sid 1, 2, 3 (2024) |
| live-pit-data | same shape, `live-pit-data.json` | sid 1, 2 (2024) |
| lap-notes | same shape, `lap-notes.json` | sid 1 (2024) |
| live-flag-data | `https://cf.nascar.com/cacher/live/series_{sid}/{race_id}/live-flag-data.json` — **no year segment** | sid 1, 2 (2024) |
| live-feed | `https://cf.nascar.com/cacher/live/series_{sid}/{race_id}/live-feed.json` — no year segment; post-race only the final frame survives | sid 1 (2024) |

Facts that shape the protocol, observed 2026-07-19:

- **The index floor is 2015.** 2013/2014 return HTTP 403 with an S3
  `AccessDenied` XML body. **Missing objects 403 — they do not 404.** The
  same 403 code is also the feeds' under-load throttle response, so a 403 is
  ambiguous between "absent" and "backed off"; §2.4 disambiguates.
- The detailed feeds' floor is **later than 2015 and per-feed**: a real 2015
  Cup race (race_id 4383) 403s for both `lap-times` and `weekend-feed`. The
  floor is not guessed — the B2 pull attempts everything from 2015 forward
  and the coverage map (§2.9) IS the floor discovery.
- One index file covers all three series (`series_1/2/3` keys, verified
  2015 and 2024). Index race entries are rich (`series_id`, `track_id`,
  `race_type_id`, stage lengths, `schedule[]` with `start_time_utc` per
  event, `winner_driver_id`, …) — the index snapshot is itself data.
- `live-pit-data` records carry `vehicle_number`/`driver_name` but **no
  driver_id** (§3.4 resolves). `lap-notes` is `{"laps": {lap_number_str:
  [{DriverIDs, FlagState, Note, NoteID}]}}` (lap `"0"` = pre-race).
  `live-flag-data` is a list of flag-transition events
  (`flag_state, lap_number, elapsed_time, time_of_day, comment,
  beneficiary`); one 2024 Cup race returned a single-element stub — tiny or
  near-empty responses are valid data, not errors. `live-feed`'s final frame
  has race-state fields plus `vehicles[]` with per-driver season-style
  summary stats (avg running position, quality passes, pit_stops, …).
- `weekend-feed.results[]` includes `car_number`, `team_name`,
  `owner_fullname`, `crew_chief_*`, qualifying fields, `points_*`,
  `winnings`, `disqualified` — the F2 pooling org key (`team_name`) is here.

### 2.2 What gets archived

For every year from **2015** through the current year, for every series
1/2/3, for **every race in the index regardless of `race_type_id`**
(exhibitions included — bronze archives raw truth; scope filters live in
silver/gold): all six feeds are attempted. Plus one index snapshot per year
per run when changed. Races without a truthy `winner_driver_id` (not yet
run) are skipped by `--full` and picked up by later `--update` runs.

Volume expectation (recorded so nobody panics): ≈ 8,000 requests on the
first full pull, ≈ 0.6–1 MB raw per fully-covered race, order **1–3 GB raw /
well under 1 GB gzipped**. Wall clock ≈ 30–60 min at the §2.4 rate cap.

### 2.3 Manifest and catalog

`data/bronze/manifest.jsonl` — append-only; one JSON object per terminal
fetch outcome:

```json
{"run_id": "20260726T140000Z", "fetch_utc": "2026-07-26T14:03:11+00:00",
 "url": "...", "feed": "lap-times", "series_id": 1, "year": 2024,
 "race_id": 5409, "outcome": "stored", "http_status": 200,
 "sha256": "<hex of UNCOMPRESSED payload bytes>", "bytes_raw": 474897,
 "bytes_gz": 61234, "path": "data/bronze/series_1/2024/5409/lap-times.20260726T140311Z.json.gz",
 "attempts": 1, "error": null}
```

- `outcome` ∈ `stored` | `unchanged` (payload sha equals latest on disk —
  no new file) | `absent` (§2.4 two-pass rule) | `failed` (retry ladder
  exhausted on a non-absent signal — retried next run) | `imported` (§2.6).
- `feed` = `race_list` for index fetches (`race_id`/`series_id` null).
- **sha256 is over the uncompressed payload bytes exactly as received** —
  never over the gzip container (gzip output is not canonical).

DuckDB catalog (schema `bronze` in the warehouse, built by
`src/warehouse.py`):

- `bronze.manifest` — `read_json_auto('data/bronze/manifest.jsonl')`.
- `bronze.files` — one row per stored file **from a disk glob** (path,
  feed, series_id, year, race_id, fetch_ts, sha256, bytes), joined to
  manifest provenance; "latest version" = max `fetch_ts` per
  (feed, series_id, year, race_id).
- `bronze.coverage` — expected grid (every index race × 6 feeds) with
  terminal state `stored | absent | failed | pending`.

### 2.4 Fetch protocol (politeness, 403 disambiguation, atomicity)

Constants (defaults; amendable pre-B2 by dated note):

- User-Agent `nascar-cup-model/1.0 (personal research archive)`; timeout
  30 s connect / 60 s total.
- Concurrency: default 4 workers, **hard max 6**; aggregate rate cap
  **5 requests/second** with 0–250 ms uniform jitter per request.
- Retry ladder: 5 attempts, sleeps 2/4/8/16/32 s + 0–1 s jitter, on HTTP
  403/429/5xx, timeouts, connection errors, and 200-with-unparseable-JSON
  (error pages must never be stored).
- Circuit breaker: if ≥8 of the last 30 completed requests returned 403,
  pause 120 s and drop to 1 worker for the remainder of the run (the feeds
  403 under load — this is the documented failure mode).
- **Absent vs throttled (the 403 ambiguity):** a URL still 403/404 after
  the full ladder is marked *tentative-absent* in memory. At end of run, a
  verification sweep re-attempts every tentative-absent once, single
  worker, 2 s spacing. Still 403/404 → `absent` (terminal). Success →
  stored. Anything else → `failed` (retried next run). A 404, if ever seen,
  is treated identically to 403 here.
- **Atomic writes:** download to `data/bronze/.tmp/`, `json.loads` to
  validate, hash the raw bytes, gzip with `mtime=0`, `os.replace` into the
  final path, then append the manifest line. Orphans in `.tmp/` are deleted
  on startup. A crash between rename and manifest append is self-healing:
  the next attempt sees the file on disk, compares payload sha, and records
  `unchanged`.
- **Resumability:** before fetching any (feed, series, year, race), check
  disk for a stored version and the manifest for a terminal `absent`. Skip
  terminal states; `--full` therefore resumes mid-pull for free. `failed`
  is always re-attempted.

**2026-07-19 dated amendment (owner-directed, mid-B2).** B2's first live `--full`
run measured that 2015-2019 (and part of 2022) are structurally, not just
transiently, absent for the detailed feeds — the circuit breaker tripped
almost immediately, and under the literal constants above ("drop to 1
worker for the remainder of the run", full 5-attempt ladder on every
request) that projected to 10-50+ hours of wall clock, because every
confirmed-absent request still paid the full ladder, permanently
serialized. Owner asked for a way to speed this up "without overwhelming
the endpoints"; three changes shipped, none of which raise the request
rate against cf.nascar.com (the 5 req/s aggregate cap and per-URL backoff
shape are untouched):
1. **Task order is newest-year-first**, not ascending. Recent years are
   far likelier to have real data; processing them first banks that data
   at full concurrency before any trip, instead of hitting the
   absence-heavy years immediately and staying throttled for the healthy
   years too.
2. **Once tripped, the ladder shortens** to 2 attempts / 2s (from 5
   attempts / 2-4-8-16-32s) for the duration of the trip. This resolves
   confirmed-absent URLs faster *and* sends fewer total requests at an
   endpoint already showing sustained 403s — strictly more polite, not
   less. Pre-trip behavior is unchanged.
3. **The circuit breaker now recovers**: once the trailing 30-request
   window drops to ≤1/30 403s, concurrency and the full ladder are
   restored (it can trip again later if another absence-heavy stretch
   follows). Previously the drop to 1 worker was permanent for the rest
   of the run even after returning to healthy years.

### 2.5 Immutability and versioning rules

1. Nothing under `data/bronze/` (except `.tmp/`) is ever modified or
   deleted by any tool. No exceptions; there is no `--force`.
2. A re-fetch whose payload sha differs from the latest stored version
   writes a **new version** (new `fetch_ts` filename). Upstream revisions
   (post-race penalties, corrections) thus become visible history, never
   silent overwrites. NASCAR does revise results (DQs exist); the evidence
   trail is the point.
3. Silver always reads the **latest** version of each feed. The version
   history exists for attribution (§4.3) and audit.

### 2.6 Legacy-cache import (one-time, in B2)

The current pipeline's raw cache — `src/data/races/*.json` (163 races ×
lt/wf) and `src/data/race_list_2026.json` — is the exact evidence the
validated model was built from. B2 imports each file into
`data/bronze/legacy_import/{original_filename}.json.gz` with manifest
outcome `imported` (sha256 of the uncompressed bytes, `url` null, `path`
recorded, `fetch_utc` = import time). `src/data/` itself is left untouched
(it stays the live pipeline's working cache until cutover). These imports
are the comparison anchors for §4.3's upstream-revision attribution.

### 2.7 Weekly increment (`--update`; folded into weekly ops after B2)

1. Fetch the current year's index (and next year's once it 200s); snapshot
   as a new version if the payload sha changed.
2. For every race in all three series with truthy `winner_driver_id` and
   either (a) no stored `weekend-feed`, or (b) `race_date` within the last
   **21 days** (revision window — penalties land within days; 21 is
   generous; owner may trim by dated note): attempt all six feeds,
   version-if-changed.
3. Re-attempt every `failed` terminal from prior runs.
4. **Never blocks E1.** On race weekends the prediction commit happens
   first; `--update` runs after, and its failure defers to next run without
   ceremony.

### 2.8 Series/coverage scope decisions (recorded)

- All three national series are archived even though the model is Cup-only:
  the marginal cost is small, the data is deletable-by-NASCAR, and future
  work (pooling priors, driver crossover history) plausibly wants it.
- Exhibition races (`race_type_id != 1`) are archived in bronze, ignored by
  silver's parity scope and gold. Recorded as a decision, not an oversight.
- The ephemeral in-race `live-feed` snapshot **stream** is out of scope
  here (that is AWS item S2 / plan H2); bronze archives only the surviving
  final frame.

### 2.9 B3 — verification terminal conditions (gate for building silver)

B3 passes when ALL of:

1. **Terminal coverage:** every (index race 2015–present × 3 series × 6
   feeds) is `stored` or `absent`; `failed` count = 0 (re-run `--update`
   until so or document a persistent upstream outage).
2. **Superset check:** for every race in `races_parsed.pkl`, `lap-times`
   and `weekend-feed` are `stored`, and the latest bronze payload sha
   equals the legacy import's sha — every mismatch is listed in the report
   (it means NASCAR revised the feed since the original download; §4.3
   consumes this list).
3. **Spot-parse:** 20 random stored files per feed type parse as JSON and
   contain the expected top-level structure (`laps`/`flags` for lap-times,
   `weekend_race` for weekend-feed, list for pit/flag feeds, `laps` dict
   for lap-notes, `vehicles` for live-feed).
4. **Hash verify:** 100 random stored files re-hash to their recorded
   sha256 (gunzip → sha256 → compare).
5. **Coverage report committed:** `report/BRONZE_COVERAGE.md` — per-feed ×
   per-series first-year-with-data table (the discovered floors), counts by
   terminal state, total bytes, the §2.9.2 mismatch list, installed
   duckdb/pyarrow versions, and the sha256 of `manifest.jsonl` at report
   time.

## RESULT — B3 (to be filled by the B3 session)

*(pending)*

---

## 3. Silver — cleaned and conformed

### 3.1 Build strategy (the one big recorded decision)

**The parity table is built by the existing Python parser, not by a SQL
rewrite.** `silver_build.py` feeds each race's latest bronze `lap-times` +
`weekend-feed` payloads through `parse_lib.parse_race()` — imported,
unmodified — and writes the result to parquet. Rationale: §4's gate demands
*exact* field-for-field equality with `races_parsed.pkl`; the only way to
guarantee that without re-validating 127 lines of subtle, audit-era logic
(median-of-best-85%, fixed-effects `lstsq`, run segmentation) is to run the
same code on the same bytes. Rewriting the parser in SQL would be
re-choosing, not preserving. The **new** tables (§3.4), which have no parity
obligation, are built in DuckDB SQL directly over the bronze `json.gz`
files (DuckDB reads gzipped JSON natively). Gold (§5) is SQL, per the plan.

### 3.2 `silver.races` — one row per (series_id, race_id)

From the latest index snapshot(s), all years/series, all `race_type_id`:

`series_id, race_id, year (=race_season), race_type_id, race_date (as text,
verbatim), race_name, track_id, track_name (stripped), scheduled_laps,
actual_laps, stage_1_laps, stage_2_laps, stage_3_laps, winner_driver_id,
green_flag_utc (schedule[] entry with event_name=='Race' → start_time_utc;
null if missing), number_of_cautions, number_of_caution_laps,
number_of_lead_changes` — plus build fields:

- `parse_status`: `'ok'` | `'skipped: <reason>'` (the exact `parse_race`
  skip string: `no feed`, `results n=<k>`, `few valid finishers`,
  `green laps with field=<k>`) | `'not_attempted'` (no bronze lap-times or
  weekend-feed stored, or exhibition).
- `n_green, n_fe, n_prac` (parse diagnostics; null unless `ok`).

`parse_race` is attempted for every race (any series/year, `race_type_id`
== 1) whose two input feeds are `stored`. Its Cup-field-size gates (≥20
results etc.) are part of frozen behavior and apply to all series
unchanged — a Trucks race that fails them is `skipped`, correctly.

### 3.3 `silver.driver_race` — the parity table (FROZEN contract)

Grain: one row per (series_id, race_id, driver_id) for every race with
`parse_status = 'ok'`. Columns and types:

| column | parquet type | source (pkl field) | null semantics |
|---|---|---|---|
| series_id | INT32 | — (1 for all pkl rows) | never |
| race_id | INT32 | race `rid` | never |
| year | INT32 | race `year` | never |
| race_date | STRING | race `date` (verbatim ISO text) | never |
| track | STRING | race `track` | never |
| driver_id | INT32 | drivers key | never |
| finish | INT32 | `finish` | never |
| start | INT32 | `start` | nullable (source may omit) |
| qspeed | DOUBLE | `qspeed` | NULL ⇔ pkl `None` |
| status | STRING | `status` | never (may be `''`) |
| team | INT32 | `team` | nullable |
| make | STRING | `make` | nullable |
| laps_led | INT32 | `laps_led` | never (parser zero-fills) |
| laps_completed | INT32 | `laps_completed` | never (parser zero-fills) |
| pace_med85 | DOUBLE | `pace_med85` | **NULL ⇔ key absent in pkl** |
| pace_mean70 | DOUBLE | `pace_mean70` | same |
| pace_p20 | DOUBLE | `pace_p20` | same |
| pace_best | DOUBLE | `pace_best` | same |
| nlaps | INT32 | `nlaps` | same |
| fepace | DOUBLE | `fepace` | NULL ⇔ pkl `None` |
| practice | DOUBLE | `practice` | NULL ⇔ pkl `None` |

Recorded pkl facts this contract encodes (measured 2026-07-19 on the
163-race / 6,083-row pkl, sha256 `b41e697d2c0f…`): the five pace columns are
*absent keys* (not `None`) for 40 rows (drivers with <15 usable green
laps); `fepace` is present-`None` for 135 rows, `practice` for 1,006;
`qspeed`/`practice` mix int and float Python values (parquet stores DOUBLE;
equality in §4 is by numeric value, not Python type). Extra columns beyond
the pkl's fields are **permitted** (additive); the listed columns' values
are the frozen parity surface.

### 3.4 New silver tables (no parity obligation; SQL over bronze)

Common rules: snake_case names; CamelCase source keys mapped
(`NASCARDriverID→driver_id`, `LapTime→lap_time`, `Lap→lap`,
`RunningPos→running_pos`, `FlagState→flag_state`,
`LapsCompleted→laps_completed`); every table carries `series_id, race_id`;
**dedupe** = drop exact-duplicate rows silently, keep-first + count in the
build report for same-key-different-value conflicts; unparseable/missing
feed → race simply absent from that table (coverage is queryable via
`bronze.coverage`). Empty or stub feed responses (observed in the wild for
`live-flag-data`) produce zero rows, not errors.

| table | grain | columns (beyond series_id, race_id) |
|---|---|---|
| `silver.results` | driver-race, every race with a stored weekend-feed (incl. races silver.driver_race skips) | all `weekend_race[0].results[]` fields flattened verbatim: driver_id, driver_fullname, finishing_position, starting_position, finishing_status, qualifying_position, qualifying_speed, qualifying_order, car_number, official_car_number, team_id, **team_name**, owner_id, **owner_fullname**, crew_chief_id, crew_chief_fullname, car_make, car_model, sponsor, laps_completed, laps_led, times_led, points_earned, points_position, points_delta, playoff_points_earned, winnings, diff_laps, diff_time, disqualified, result_id |
| `silver.laps` | driver-lap | driver_id, lap, lap_time, running_pos (from lap-times `laps[].Laps[]`) |
| `silver.lap_flags` | lap | flag_state, laps_completed (from lap-times `flags[]`) |
| `silver.flag_events` | event (ordered) | event_seq (file order), flag_state, lap_number, elapsed_time, time_of_day, time_of_day_os, comment, beneficiary (from live-flag-data) |
| `silver.pit_stops` | stop (ordered) | stop_seq (file order), vehicle_number, driver_name, **driver_id** (resolved: join `vehicle_number` to `silver.results.car_number` as trimmed strings within the race; if no unique match, exact `driver_name` = `driver_fullname` match; else NULL — unresolved count in build report), lap_count, leader_lap, pit_in_race_time, pit_out_race_time, box_stop_race_time, box_leave_race_time, pit_stop_duration, total_duration, in_travel_duration, out_travel_duration, pit_in_flag_status, pit_out_flag_status, pit_in_rank, pit_out_rank, positions_gained_lost, pit_stop_type, left_front_tire_changed, left_rear_tire_changed, right_front_tire_changed, right_rear_tire_changed, previous_lap_time, next_lap_time, vehicle_manufacturer |
| `silver.lap_notes` | note | lap_number (INT from the dict key; `"0"` = pre-race), note_id, note, flag_state, driver_ids (LIST\<INT\>) |
| `silver.practice_runs` | driver-run | run_type, run_name (if present), driver_id, best_lap_time, and other per-result fields present in `weekend_runs[].results[]` |
| `silver.live_final` | driver-race | from live-feed final frame `vehicles[]`: vehicle_number, driver name (nested `driver` object flattened), starting_position, running_position (final), laps_completed, laps_led, best_lap_time, last_lap_time, average_running_position, average_speed, passes_made, times_passed, quality_passes, fastest_laps_run, position_differential_last_10_percent, is_on_dvp, status — plus race-frame fields lap_number, laps_in_race, flag_state as of frame |

C2 may add columns it finds in the feeds (additive, verbatim-flattened);
it may not drop or rename the ones listed.

### 3.5 Incremental build

`silver_build.py` computes, per (series_id, race_id), an input fingerprint:
`sha256("parser_v{N}|" + "|".join(sorted(f"{feed}:{sha256}" for latest
stored versions of that race's feeds)))`, stored in
`silver._build_state.parquet`. A race is (re)built iff its fingerprint
changed. `parser_v{N}` is a module constant bumped on any parse-logic
change (bumping forces full rebuild). `--full` ignores state and rebuilds
everything; **§4's gate always runs against a `--full` build.**

---

## 4. C-gate — the silver regression protocol (FROZEN)

Adjudicates: *silver.driver_race reproduces `races_parsed.pkl`
field-for-field.* Runs in C1. Gold may not be built on silver (D1 may not
start) until this gate is recorded as PASS.

### 4.1 Anchor

At C1 start, before anything else: copy the current `src/races_parsed.pkl`
to `data/anchors/races_parsed_anchor_{YYYYMMDD}.pkl`; record its sha256 and
race count in the gate report. The anchor's race set is the gate universe —
"163/163" as of 2026-07-19; if E1 has appended races by then, the universe
grows with it and ALL races must pass. The anchor never changes afterward;
it is also §6's R0 input.

### 4.2 Comparison

`gate_silver.py`, on a `--full` silver build, for every race in the anchor:

1. **Race present:** a (series_id=1, race_id) exists in silver.driver_race
   output with `parse_status='ok'`.
2. **Race-level fields equal:** `date/race_date` (string-equal), `year`,
   `rid/race_id`, `track`, `n_green`, `n_fe`, `n_prac`.
3. **Driver set equal:** identical driver_id sets.
4. **Every driver field equal**, per the §3.3 table: ints/strings by `==`;
   floats by **exact** `==` (same code path on same bytes ⇒ bit-identical;
   no epsilon is granted); null-semantics per the §3.3 null map
   (pkl-absent ⇔ NULL, pkl-`None` ⇔ NULL); int-vs-float Python type
   differences compare by numeric value.
5. Additionally: no race in silver's Cup/points/`ok` set for the anchor's
   date range is *missing* from the anchor (else the parser's skip behavior
   drifted) — and every anchor-era skip recorded in `silver.races` matches
   `parse_race`'s reason string for that race.

### 4.3 Mismatch attribution (mechanical, no judgment)

For each race with any inequality:

1. Compare the latest bronze payload shas for `lap-times`/`weekend-feed`
   against the legacy-import shas (§2.6) for that race.
2. **Shas equal → the parser or plumbing broke. Gate FAILS.** Fix, rebuild,
   re-run the whole gate.
3. **Shas differ → candidate upstream revision.** Re-run
   `parse_lib.parse_race` directly on the legacy-import payloads. If that
   output matches the anchor exactly, the mismatch is attributed to a
   NASCAR-side data revision: record the race, the differing fields, both
   values, and the differing feed(s) in the report. Counts as
   **PASS-with-note** (the parser is proven equivalent; the data changed
   upstream). If it does not match the anchor either → gate FAILS.

### 4.4 Verdict

PASS ⇔ every anchor race is PASS or PASS-with-note. The report
(`report/SILVER_REGRESSION.md`, committed) records: anchor sha256 + race
count, rows compared, field-comparison counts, every PASS-with-note in
full, and the environment (python/numpy/duckdb/pyarrow versions). The
PASS-with-note list feeds §6's R1 expectations verbatim.

## RESULT — C-gate (to be filled by C1)

*(pending)*

---

## 5. Gold — features in SQL, consumers re-homed

### 5.1 `gold.track_typology` (seed table, frozen values)

The `MY_TYPE` dict from `src/walkforward.py` materialized as
(track_name, ttype) rows, verbatim, plus the rule: unmapped → `'UNIQ'`.
The typology VALUES are frozen config; the table is their storage. Any
future track addition is a config change requiring validation evidence
(doctrine), not a data-engineering edit.

### 5.2 `gold.wf_features` — the walk-forward feature bank (SQL)

Scope for D1: series_id 1, `race_type_id` 1, every `parse_status='ok'`
race. Grain: (race_id, driver_id) — one row per driver **per parsed race
they appear in**. Definitions (must implement exactly; these transcribe
`walkforward.run`'s history mechanics):

- **Ordering.** Races ordered by (`race_date`, `race_id`) ascending —
  verified 2026-07-19: no duplicate race datetimes exist in the current
  data; `gate_gold.py` asserts this on every run and fails loudly if a tie
  ever appears (a tie would make Python-replay order authoritative).
- **race_seq** — the race's 1-based index in that ordering (the walk-forward
  clock).
- For driver d at target race t (typology `tt` = target race's ttype):
  - **n_hist** = count of d's parsed races strictly before t.
  - **fin_h** = weighted mean of d's prior `finish` values f_1…f_k (oldest
    first) with weights `0.5^((k−j)/8)` for j = 1…k (most recent weight 1).
    NULL if k = 0.
  - **pace_h** = same weighting over the subsequence of prior races where
    `pace_med85` is non-NULL — **the exponent indexes within that
    subsequence**, not within all prior races (this mirrors `hp` only
    appending non-null pace; it is the classic transcription bug — don't
    make it). NULL if that subsequence is empty.
  - **typ_h** = let T = d's prior races whose ttype equals tt (ttype of
    each prior race per §5.1 applied to ITS track), m = |T|, and
    `typed_wmean` = the same half-life-8 weighted mean over T's finishes
    (subsequence-indexed). Then `typ_h = (m·typed_wmean + 3·fin_h)/(m+3)`
    if m > 0 else `fin_h`. NULL if k = 0. (Shrinkage form per
    `predict_next.py`; base is the hl-weighted fin_h.)
  - **start_feat** = the target race's `start`, with falsy (NULL or 0) → 20.
  - **has_pace** = target race `pace_med85` IS NOT NULL (backtest
    eligibility input).
  - **finish** = target race finish (backtest label, convenience).
- Half-life 8 and shrinkage constant 3 are frozen config values.

z-scoring (`znan`), eligibility filtering (burn 15 on race_seq of *scored*
sample, n_hist ≥ 5, has_pace, ≥20 eligible), PL fitting, and sampling stay
in the **engine** — they depend on the per-race eligible set and are
already-validated Python. Gold stores pre-race feature values; the engine
consumes them.

### 5.3 Current-form views (for the weekly prediction)

`gold.driver_form` — per driver, as of the latest parsed race: n_hist,
fin_h, pace_h (same definitions, evaluated "after all races"). 
`gold.driver_type_form` — per (driver, ttype): m and typed_wmean as above.
`predict_next` (post-cutover) computes `typ_h` from these plus the target
race's ttype, and grid from the live weekend feed exactly as today.

### 5.4 Engine re-point mechanics

- `walkforward.py` is **not edited** for gating (it is audit record; its
  module-level `RACES` load stays). Gate runs monkeypatch
  `walkforward.RACES` after import — `run()` reads the global at call time.
- D1 adds a thin adapter in `gate_gold.py`/`gold_build.py`:
  `silver_to_races_list()` reconstructs the pkl-shaped list-of-dicts from
  silver (Cup, points, `ok`, ordered by (race_date, race_id)), reproducing
  the §3.3 null map in reverse — NULL pace columns become *absent keys*;
  NULL fepace/practice/qspeed become present-`None`.
- The production re-point (cutover, §7.3) modifies `predict_next.py` to
  read §5.3 views instead of replaying the pkl; payload format, config
  block, seeds (Gumbel rng seed 5618 per race id convention), rounding —
  all unchanged.

### 5.5 Scoring and market benchmark as gold consumers (D2)

Both are implemented to their frozen specs **verbatim** — this spec adds
only where their inputs come from:

- `src/score_race.py` + `src/test_score_race.py`: exactly per
  `scoring_methodology.md` (with its amendments), including §1.2's read
  path `src/data/races/{year}_{race_id}_wf.json` and the `_wf_scored.json`
  first-scoring snapshot. **The compatibility shim:** before scoring, the
  weekly flow extracts the latest bronze `weekend-feed` payload for the
  race to that exact path (byte-identical uncompressed payload). The frozen
  procedure ("if the file exists on disk, read it") is thereby satisfied
  without amendment; bronze is simply the upstream that populates the
  cache. The scorer itself is not modified to know about bronze.
- `src/market_benchmark.py`: exactly per the amended market spec — inputs
  are the sealed prediction JSONs and the `_wf_scored.json` snapshots, and
  nothing else; seed 20260718; the full amended look/boundary machinery.
- Gold-side additions are read-only conveniences: `gold.scores` (view over
  `predictions/scores_log.csv`) and `gold.predictions` (view over the
  sealed JSONs) for analytics. The CSVs/JSONs remain the artifacts of
  record; views never write.
- The bronze race_list version history additionally preserves, for every
  race, the `schedule[]`/`start_time_utc` as-of-pre-race — strengthening
  the market spec's green-flag admissibility evidence at no protocol
  change.

---

## 6. D-gate — re-prove the validated model on gold (FROZEN)

Adjudicates: *gold + re-pointed engine reproduce the validated results.*
The frozen config VALUES carry over; what is re-proven is that the new
plumbing computes the same model. **Failure at any level stops the
migration for investigation — tuning anything to "make it pass" is
prohibited** (that would be re-choosing). Gold does not replace the pkl
path until R0–R3 pass and §7.3's cutover condition is met.

Reference runs (transcribing `step4_models.py`; `SPEC = {'fpts': ['fin',
'pace', 'typed', 'start']}`):

- **Backtest run:** `run(typology=MY_TYPE, typed_mode='shrinkage',
  pl_specs=SPEC, pl_refit_every=1)` (defaults: pace_med85, hl 8, burn 15,
  min_hist 5, min_drv 20, years (2022, 2023, 2024, 2025)).
  Headline = `nanmean(rho_PL_fpts)` over its rows; non-SS headline = same
  over rows with `ttype ∈ {SHORT, INT, ROAD}` (note: UNIQ/OTHER rows are in
  neither bucket — this is the audit's definition, kept).
- **OOS run:** same with `years=(2022, 2023, 2024, 2025, 2026)`; headline =
  `nanmean(rho_PL_fpts)` over rows with `year == 2026`.

**R0 — environment/reference check (legacy path, anchor data).**
`walkforward.RACES` ← the §4.1 anchor pkl; run both reference runs.
Expected, at 3 decimal places: backtest **0.413**, non-SS **0.476**, 2026
OOS **0.449**. The published trio is the record; the audit prose attributes
all three to the four-feature model, and R0 verifies that from the code
rather than trusting recollection of which step-4 column printed what. If
R0 does not reproduce the trio, STOP — nothing downstream is meaningful;
report to the owner (this would mean an environment or data-integrity
problem, not a modeling question).

**R1 — silver replay (legacy engine, silver data).** `walkforward.RACES` ←
`silver_to_races_list()` restricted to the anchor's race set; same runs.
Expected: per-race `rho_PL_fpts` **exactly equal** to R0's (float `==`)
for every row — except races on §4.4's PASS-with-note list, whose deltas
are reported individually. If the note list was empty, R1 must equal R0
exactly and print the same trio.

**R2 — feature parity (gold SQL vs replay).** For every (race, driver) in
R1's scored-race eligible sets: gold's `fin_h, pace_h, typ_h, start_feat`
vs the replay's values — relative tolerance ≤ 1e-9 (denominator
`max(1,|ref|)`), identical NULL/eligibility membership, identical
`n_hist`. Any set-membership difference is a FAIL regardless of magnitude.

**R3 — decision parity (engine on gold).** Run the walk-forward with
feature vectors sourced from `gold.wf_features` (znan/PL/eligibility in the
engine as always): per scored race, the predicted-rank vector must equal
R1's. Permitted exception: races where some utility pair differs by
< 1e-7 (a near-tie under float drift) — each such race is listed with the
pair and gap. Per-race `|Δrho| ≤ 1e-6` outside listed races; the trio must
equal R1's at 3 decimal places.

All four are recorded in the RESULT block with the environment versions.
The gate PASSES ⇔ R0 reproduces the trio, R1 matches per §4.4's note list,
and R2/R3 pass as stated.

## RESULT — D-gate (to be filled by D1)

*(pending)*

---

## 7. Migration and continuity

### 7.1 Path of record (FROZEN rule)

At every moment exactly one path is the **path of record** for the weekly
protocol: the legacy pkl path (`update_data.py` → `predict_next.py`) until
cutover completes, the gold path after. Predictions are only ever published
from the path of record. Rebuild work never delays a pre-race commit: on a
race weekend, E1's steps run first on the path of record, rebuild sessions
after.

### 7.2 Continuity guarantees (FROZEN)

- **The perishable capture never pauses.** Odds recording and pre-race
  prediction commits proceed through every phase of the rebuild. A rebuild
  session that would collide with a race weekend yields.
- Sealed predictions, `specs/`, `report/`, `review/`, the scores/market
  CSV-and-snapshot contracts: untouched by every session of this rebuild.
- The legacy path stays fully functional (code + pkl + `src/data/` cache)
  until cutover, and remains present-but-retired afterward as the rollback
  path through at least the end of the 2026 season.

### 7.3 Cutover checklist (FROZEN; executed in/after D2)

1. §4 gate PASS recorded; §6 gate PASS recorded.
2. **Dual-run check on one real weekend:** generate the weekly prediction
   via BOTH paths (gold path unpublished); after removing `generated_utc`
   and `sha256_of_payload`, the two JSON payloads must be **identical**.
   Any difference → no cutover; publish legacy; investigate; try next
   weekend. (Given R2/R3, a difference is overwhelmingly likely a wiring
   bug, not float drift.)
3. Score-race shim (§5.5) wired and `score_race.py` + tests green;
   prediction #1 (race 5618) and any backlog scored per the frozen spec.
4. Cutover commit: `predict_next.py` re-pointed; weekly ops become
   `bronze_fetch --update` → `silver_build` → `gold_build` → predict;
   HANDOFF weekly protocol + repo map updated; `races_parsed.pkl` final
   state archived to `data/anchors/` with sha256 recorded in the commit
   message; legacy scripts marked LEGACY in their docstrings (not
   deleted).
5. Rollback rule: any weekly-flow failure on the gold path before two
   consecutive clean weekly cycles → revert to the legacy path (still
   functional by 7.2), fix, re-attempt cutover. After two clean cycles the
   gold path is simply the path of record.

### 7.4 DATA_DICTIONARY and docs

Each build session extends `DATA_DICTIONARY.md` with the tables it creates
(same style: field, type, meaning) and updates HANDOFF's repo map. The
medallion spec (this file) remains the design authority; the dictionary
remains the field reference.

---

## 8. Retirement list

Superseded by this rebuild (sessions retired; files kept as audit record —
nothing is deleted):

| item | disposition |
|---|---|
| Plan sessions R1/R2/R3 (standalone `score_race.py` / `market_benchmark.py` / weekly-scoring against the old pipeline) | already retired in `plan/schedule.yml` 2026-07-19; their INTENT lands as D2's gold consumers; the frozen specs they implement carry over unchanged |
| `src/download.py` (2022+ Cup-only bulk fetch) | superseded by `bronze_fetch.py` at B2; marked LEGACY at cutover |
| `src/parse.py` (pkl full rebuild) | superseded by `silver_build.py` at C1; marked LEGACY at cutover |
| `src/update_data.py` (weekly pkl increment) | path of record until cutover; retained afterward as the rollback entry point |
| `src/races_parsed.pkl` | frozen at cutover as the final anchor artifact (hashed, archived) |
| `src/walkforward.py` | **retained** — audit record and gate reference engine; not edited by this rebuild |
| `src/predict_next.py` | retained and re-pointed at cutover (§5.4) |
| `src/step2/3/4/6_*.py` | frozen audit artifacts; `step4_models.py`'s invocations live on as §6's reference definitions |
| `src/data/` | becomes a bronze-fed compatibility cache (§5.5 shim); original contents preserved in bronze `legacy_import` |
| `planning/aws_solutions.md` S3 item | scope note (living doc, no freeze): the mirror target becomes `data/bronze/` |

---

## 9. Recorded decisions and flagged ambiguities

Decisions made here so builders make none (each with the reason):

1. **Parity table via `parse_lib`, not SQL** (§3.1) — exact-equality gate
   demands the same code path; SQL rewrite = re-choosing.
2. **403 is ambiguous** (absent vs throttled — discovered 2026-07-19, the
   feeds 403 for BOTH missing objects and load-shedding): resolved by the
   two-pass tentative-absent rule (§2.4), never by guessing.
3. **Frozen-spec path mechanics honored via the shim** (§5.5), not
   amendments: scoring's §1.2 read-path and the `_wf_scored.json` snapshot
   contract predate this spec and adjudicate data that begins existing
   today (race 5618); amending them now would skirt the
   amendment-after-data rule. The shim satisfies them byte-for-byte.
4. **Versioned bronze, never overwrite** (§2.5) — NASCAR revises results
   (penalties/DQs); the archive must show what was true when.
5. **Manifest not committed to git** — it grows unbounded and the repo
   should stay lean pre-E2; integrity anchors (manifest sha256, per-gate
   file hashes) go in committed reports instead. Owner may reverse by
   dated note.
6. **Exhibitions archived, excluded from silver parity/gold** (§2.8) —
   bronze is raw truth; the model's race_type_id==1 scope is preserved.
7. **All-series archive** (§2.8) — small cost, irreversible upstream
   deletion risk, plausible future use.
8. **21-day revision re-fetch window** (§2.7) — generous vs the observed
   days-scale penalty timeline; owner-tunable pre-B2.
9. **Silver/gold rebuilds are fingerprint-incremental with `--full` for
   gates** (§3.5) — deterministic, and gates never trust incremental state.
10. **Non-SS defined as ttype ∈ {SHORT, INT, ROAD}** (§6) — the audit code's
    definition (UNIQ/OTHER excluded), kept verbatim rather than
    "everything except SS".

Genuine ambiguities flagged (none block execution; defaults chosen):

- **A1.** The audit report's prose attributes 0.476/0.449 to the
  four-feature model, but `step4_models.py`'s printed non-SS/2026 tables
  listed the `prior_all`/`sameday` columns (which differed from `fpts` by
  ≤0.001 overall). §6 R0 resolves this mechanically — the trio is verified
  against a fresh legacy run before gold is judged — but if R0 disagrees
  with the published trio at 3dp, that is an owner-visible finding, not a
  thing to paper over.
- **A2.** If NASCAR revised any 2022–2026 feed since the original
  download, C1 will surface it as PASS-with-note (§4.3) and R1 inherits
  the delta. Expected count: zero (2022–2025 results are long-settled);
  any nonzero count is reported per-race.
- **A3.** The detailed-feed floor per feed/series is unknown until B2's
  pull maps it (2015 index floor confirmed; 2015 detailed feeds 403 on the
  probed race). No downstream design depends on where the floor lands;
  `BRONZE_COVERAGE.md` records it.
- **A4.** `silver.pit_stops.driver_id` resolution can fail for oddball
  entries (name mismatches, ownership swaps mid-season). Unresolved rows
  keep NULL driver_id and are counted; no fuzzy matching is attempted
  (deterministic > clever).

---

## 10. Per-session implementation checklists

Every session: honor §7.1/§7.2 first (race weekend ⇒ E1 duties precede
rebuild work); finish with a clean committed tree; update the plan YAML
status and re-render.

### B2 — bronze ingestion (Sonnet 5, thinking on, high)

1. Add `duckdb`, `pyarrow` to `requirements.txt`; install; record versions.
2. Add `data/` to `.gitignore`.
3. Build `src/bronze_fetch.py` per §2 (protocol constants §2.4, layout
   §1.1, manifest §2.3, `--full`/`--update`/`--verify`).
4. Build `src/warehouse.py` (bronze schema: manifest/files/coverage views).
5. Legacy import (§2.6).
6. Probe index years 2015→present (plus 2014 to confirm the floor stands);
   run the full pull (§2.2); run the tentative-absent sweep.
7. `src/bronze_report.py`: emit the coverage matrix; iterate `--update`
   until `failed` is small/zero; leave the rest for B3.
8. Commit code + an interim coverage summary.

### B3 — verification (Sonnet 5, thinking on, high)

1. Drive §2.9's five conditions to terminal; commit
   `report/BRONZE_COVERAGE.md`.
2. Fill `## RESULT — B3` in this spec (dated).
3. Update plan YAML; commit.

### C1 — silver parity (Sonnet 5, thinking on, high)

1. Take the §4.1 anchor FIRST (before any silver code runs).
2. Build `src/silver_build.py` parity path (§3.1–§3.3) + `silver.races`;
   extend `warehouse.py`.
3. `--full` build; run `src/gate_silver.py` (§4.2–§4.4); attribution loop
   until PASS.
4. Commit `report/SILVER_REGRESSION.md`; fill `## RESULT — C-gate`;
   extend DATA_DICTIONARY; update plan YAML; commit.

### C2 — silver breadth (Sonnet 5, thinking on, high)

1. Build the §3.4 tables in SQL over bronze; dedupe/conflict counts to a
   build report section; pit-stop driver_id resolution stats.
2. Extend warehouse views + DATA_DICTIONARY; update plan YAML; commit.

### D1 — gold + re-prove (Sonnet 5, thinking on, xhigh)

1. Build `gold.track_typology` (§5.1), `gold.wf_features` (§5.2), form
   views (§5.3) in `src/gold_build.py`.
2. Build `src/gate_gold.py`: the adapter (§5.4), then R0 → R1 → R2 → R3 in
   order, stopping at first failure.
3. On PASS: commit `report/GOLD_REPROOF.md` + fill `## RESULT — D-gate`.
   On FAIL: report, do not tune (§6).
4. Update plan YAML; commit.

### D2 — consumers + cutover (Sonnet 5, thinking on, xhigh)

1. `src/score_race.py` + `src/test_score_race.py` per the frozen scoring
   spec, verbatim; §5.5 shim wired into weekly ops.
2. Score race 5618 and any backlog; `scores_log.csv` born per contract.
3. `src/market_benchmark.py` per the amended market spec (it has inputs
   once a priced race is scored).
4. Gold convenience views (`gold.scores`, `gold.predictions`).
5. Execute §7.3 cutover steps in order (the dual-run check spans a real
   race weekend — cutover may therefore complete a week after D2's code).
6. Fill `## RESULT — D2`; update HANDOFF (weekly protocol + repo map +
   current status); update plan YAML; commit.

## RESULT — D2 / cutover (to be filled)

*(pending)*
