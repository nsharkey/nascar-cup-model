# SILVER_BREADTH.md -- C2 build report (specs/medallion_architecture.md section 3.4)

Eight new silver tables built by `src/silver_build.py`'s `build_silver_breadth()`, in DuckDB SQL
directly over bronze `json.gz` files (section 3.1's "no parity obligation" path -- distinct from
`silver.driver_race`'s frozen Python-parser reuse). No parity gate applies to these tables; the
existing C-gate (section 4) was re-run after this build and remains **PASS** (1 clean, 162
pass-with-note, 0 fail -- identical to C1's result), confirming `silver.driver_race` was not
touched or regressed.

## Race coverage

- 1,166 races enumerated (`bronze.races_index`, all series/years/`race_type_id`).
- 934 have at least one of the six section-3.4 feeds stored and were built fresh (`--full`, so
  0 reused from prior build state -- this is the first C2 build).
- 232 have none of the six feeds stored (pre-floor years, or genuinely never fetched) and
  contribute zero rows to every breadth table, per the spec's "race simply absent" rule.

## Per-table row counts and dedupe/conflict counts

| table | rows | dedup dropped (exact dup) | conflicts (same key, different value; kept first) |
|---|---:|---:|---:|
| `silver.results` | 34,816 | 2 | 7 |
| `silver.laps` | 4,223,220 | 0 | 0 |
| `silver.lap_flags` | 122,807 | 0 | 0 |
| `silver.flag_events` | 6,494 | 0 | 0 |
| `silver.pit_stops` | 113,423 | 64 | 0 |
| `silver.lap_notes` | 32,311 | 0 | 0 |
| `silver.practice_runs` | 71,913 | 0 | 5 |
| `silver.live_final` | 33,694 | 0 | 10 |

Dedupe/conflict key per table (section 3.4's grain column, used as the "same-key" definition):
`results` = `(series_id, race_id, driver_id)`; `laps` = `(series_id, race_id, driver_id, lap)`;
`lap_flags` = `(series_id, race_id, laps_completed)`; `lap_notes` = `(series_id, race_id,
note_id)`; `practice_runs` = `(series_id, race_id, weekend_run_id, driver_id)`; `live_final` =
`(series_id, race_id, driver_id)`. `flag_events` and `pit_stops` are ordered "event" tables with
no smaller natural business key than their full raw content, so their key is every source field;
under that key a "conflict" is structurally impossible (a differing row is a different key by
construction), and dedupe there reduces to exact-row-content matching (`pit_stops`' 64 dropped
rows are exact repeats of a stop record; `flag_events` had none).

**Conflict root cause, spot-checked**: all 7 `results` conflicts and both spot-checked
`practice_runs`/`live_final` conflict groups are the same real-world pattern -- a driver entered
in two different cars for one event (e.g. race (series 2, race_id 4825): driver_id 4213/Josh
Bilicki appears once as car #17's actual finisher and once as car #93 with 0 laps, an
entered-but-did-not-race second entry). This is genuine upstream data, not a parse defect; the
dedupe rule's "keep first, count the conflict" behavior handles it as designed.

## `pit_stops.driver_id` resolution (section 3.4)

- Resolved by `vehicle_number` = `silver.results.car_number` (trimmed, within race): **112,596**
- Resolved by fallback exact `driver_name` = `driver_fullname` match: **2**
- Unresolved (`NULL`): **825** (0.7% of 113,423 rows)

Of the 825 unresolved, 327 (40%) are a single already-documented race: (series 1, race_id 5580),
the fall-2025 Talladega race whose `weekend-feed.weekend_race` field is `null` (B3 finding,
`DATA_DICTIONARY.md` §8; root-caused as an upstream NASCAR data gap, not a fetch/parse defect) --
`silver.results` has zero rows for that race, so there is no join target at all and every one of
its pit stops is correctly unresolved.

The remaining ~498 unresolved rows, spot-checked across (series 2, race_id 5100) and similar,
are **Cup Series crossover drivers appearing in a lower-series race's `live-pit-data` feed**
(e.g. Ross Chastain, Austin Dillon, Ryan Blaney, William Byron pit-stop records inside an Xfinity
race's feed) whose car numbers do not appear anywhere in that race's own `weekend-feed` results.
NASCAR races at the same track/weekend share a physical pit road, and the live pit-data feed
appears to capture all cars present rather than filtering to the race's own entry list -- a real
upstream feed characteristic, not a resolution-logic bug. Falling through to `NULL` (rather than
misassigning to a same-named or same-numbered driver from the wrong race) is the correct,
designed outcome.

## Environment

- python: 3.14.6
- duckdb: 1.5.4
- pyarrow: 25.0.0
- Wall clock: `silver_build.py --full` (parity path + all 8 breadth tables) ran in ~83s.

---

## C4 addendum (2026-07-20) -- silver breadth extension #2

Three new breadth tables (`silver.caution_segments`, `silver.stage_results`,
`silver.race_leaders`) plus two new columns on `silver.races`
(`playoff_round`, `stage_4_laps`), per `research/domain_knowledge_scan.md`
sections 3.2/10.1. Same no-parity-obligation DuckDB-SQL-over-bronze path as
C2, extending `build_silver_breadth()` (`BREADTH_VERSION` bumped 1→2, which
forced a one-time full rebuild of all eight C2 tables too — their row
counts below differ trivially from the original C2 report because bronze
has accrued a few weeks of routine capture since then, not because of any
C4 logic change). `playoff_round`/`stage_4_laps` are sourced from
weekend-feed `weekend_race[0]` (like every other C4/C2 object) rather than
the `race_list` index — the index carries `playoff_round` but only
carries `stage_4_laps` inconsistently across seasons, so reading both from
the same feed avoids a coverage gap. The C-gate re-ran **PASS** after this
build (identical to C1/C2's result — `silver.driver_race` untouched); all
14 gates green before and after.

### Race coverage (all series/years; `bronze.races_index` = 1,166 races)

- 935 races have at least one of the six section-3.4 feeds stored and were
  built fresh (`--full`, so 0 reused — this is the first C4 build); 231
  have none and contribute zero rows to every breadth table, unchanged
  from C2.

### New table row counts

| table | grain | rows | dedup dropped | conflicts |
|---|---|---:|---:|---:|
| `silver.caution_segments` | event (ordered) | 6,428 | 0 | 0 |
| `silver.stage_results` | driver-stage | 12,209 | 0 | 0 |
| `silver.race_leaders` | leader segment (ordered) | 14,232 | 0 | 0 |

Dedupe/conflict key: `caution_segments` and `race_leaders` are ordered
"event" tables with no smaller natural business key than their full raw
content (same treatment as `flag_events`/`pit_stops` — key =
`(series_id, race_id)` + every source field, `event_seq`/`leader_seq`
assigned after dedup); `stage_results`' natural key is
`(series_id, race_id, stage_number, driver_id)` (a driver finishes each
stage at most once). Zero conflicts and zero exact-duplicates in all three
— cleaner than the original C2 batch, plausibly because these three
objects have simpler internal structure (no dual-entry-per-driver pattern
like `results`/`practice_runs`/`live_final` saw).

### `silver.races.playoff_round` / `silver.races.stage_4_laps`

935 of 1,166 races patched from weekend-feed (the same coverage set as the
other C4/C2 weekend-feed objects — races without a stored weekend-feed get
`NULL`, not an error, same absence convention as everywhere else in
section 3.4). Cup (`series_id=1`, `race_type_id=1`) verified directly
against the spec's coverage claims:

- `caution_segments`: 2017+, 323/324 Cup points races 2017–2025 covered
  (99.7%, matching/exceeding the scan's "~98%" estimate); 2026 partial
  (21/36, season in progress).
- `stage_results`: **empty 2017–2019 as expected — a schema floor, not a
  bug** (98 of those 108 races have nonzero `stage_1_laps`, i.e. stages
  existed, but the structured `stage_results` field wasn't populated
  upstream); 2020+ covers 214/216 Cup points races through 2025.
- `race_leaders`: 2017+, same 323/324 (99.7%) coverage as `caution_segments`.
- `playoff_round`: 2020+, 59 Cup playoff races 2020–2025 (10/season
  2020–2024, 9 in 2025 — see anomaly note below); correctly 0 so far in
  2026 (playoffs haven't started) and 0 in 2017–2019 (playoffs existed but
  the field wasn't populated upstream, same schema-floor pattern as
  `stage_results`).
- `stage_4_laps`: nonzero only for the Coca-Cola 600 (the one Cup points
  race with a 4th stage), 2020–2026 — see anomaly note below.

**Parse anomalies (both genuine upstream data, not pipeline defects):**

1. **2025's playoff-race count is 9, not 10.** The missing race is
   race_id 5580 (fall-2025 Talladega, `YellaWood 500`) — the same,
   already-documented gap from B3/C1: its stored weekend-feed's
   `weekend_race` field is `null` (upstream NASCAR data gap), so
   `silver.results` has zero rows for it and none of the four C4 objects
   have any data for it either. `playoff_round` is correctly `NULL`
   there, not `0` — absence propagating exactly as designed, not a new
   finding.
2. **`stage_4_laps` is negative (`-51`) for the 2024 Coca-Cola 600**
   (race_id 5406). Verified directly against the raw stored bytes (both
   the `race_list` index and `weekend-feed` agree on `-51`): that race was
   rain-shortened to 249 actual laps against 300 scheduled laps across
   stages 1–3 (100 each), so a stage-4 remaining-laps figure computed
   upstream as `actual_laps - (stage_1+2+3)` goes negative. Recorded
   verbatim per the section-3.4 no-invented-validation convention — not
   clamped, not treated as missing.

### `src/warehouse.py` extension (C4)

`build_warehouse()`'s breadth-table view loop extended with
`caution_segments`, `stage_results`, `race_leaders` — same
rebuildable-from-disk `CREATE OR REPLACE VIEW ... SELECT * FROM
read_parquet(...)` pattern as every other silver table. `silver.races`
needed no view-definition change (`SELECT *` already picks up the two new
columns).

### Environment (C4 build)

- python: 3.13.5 (Anaconda), duckdb 1.5.4, pyarrow (Anaconda stack)
- Wall clock: `silver_build.py --full` (parity path + all 11 breadth
  objects) ran in well under 2 minutes.
