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
