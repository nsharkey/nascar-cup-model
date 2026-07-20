# TRACK_REFERENCE.md -- C3 build report (research/track_audit_derivation.md section 2)

Seven new silver tables materialized by `src/track_reference_build.py` from the vendored,
immutable, hash-gated `research/track_audit/` package (loader: `src/track_audit.py`) plus
`silver.races` (C1/C2). Package files untouched throughout -- `src/test_track_audit.py` re-run
after this build and still **PASS**. `src/gate_silver.py` (the frozen C-gate) also re-run and
still **PASS** (1 clean, 162 pass-with-note, 0 fail, identical to C1/C2) -- `silver.driver_race`
untouched. New re-derivation gate: `src/gate_track_reference.py`, **PASS**.

## Row counts

| table | rows | expected |
|---|---:|---:|
| `silver.track_dim` | 43 | 43 (one per package `track_id`) |
| `silver.track_xwalk` | 44 | see "row-count correction" below |
| `silver.track_priors` | 430 | 43 x 10 (one row per track_id x prior) |
| `silver.track_similarity_prior` | 193 | 193 (edge file, verbatim) |
| `silver.rules_era` | 6 | 6 (narrative era table) |
| `silver.race_track` | 966 | (series 1: 404, series 2: 337, series 3: 225) |
| `silver.race_track_features` | 404 | Cup-only (series_id=1) by design -- see scope note |

## Row-count correction: crosswalk is 44 rows, not 45

`research/track_audit_derivation.md` (section 1.4, section 2.2) and this session's own kickoff
prompt both say `crosswalk_track_ids.csv` is "45 rows." The committed file actually has **44**
data rows: 43 track_ids, with exactly one track_id (`sonoma_short`) getting two rows for its two
disjoint in-scope windows (2015-2018 and 2022-9999) -- 43 + 1 = 44. Verified this session by
direct `csv.DictReader` count and by checking `src/test_track_audit.py`: no check there asserts
45 anywhere, and every identity/coverage check in that gate (43 track_ids covered exactly,
`sonoma_short` the only duplicate) is consistent with 44, not 45. Treated as a prose miscount in
the two documents (not a data problem) and corrected here and in `gate_track_reference.py`
(`EXPECTED_XWALK_ROWS = 44`) rather than silently building to a number the file doesn't have.

## Banking parse

`track_reference_build.parse_banking()`: splits the verbatim `banking` text on `;`, extracts a
`<N> deg` or `<N>-<M> deg` pattern per segment (range -> upper bound), and treats a segment as
the **secondary** value only if it explicitly says "tri-oval" or "frontstretch" (section 2.2's
literal instruction) -- every other multi-segment pattern (asymmetric turns 1-2 vs 3-4,
`turns`/`straights`, T1/T2/T3) folds into `banking_max_deg` only, `banking_secondary_deg` stays
NULL.

- 29/43 tracks got a numeric `banking_max_deg`; 14/43 got NULL (11 road/street courses with
  descriptive-only banking text, e.g. "significant elevation change," "mostly flat," plus
  `bristol_dirt`'s "variable after dirt installation" -- none of these have a `deg` number in the
  source text at all, so NULL is correct, not a parse failure).
- 2/43 (`daytona_oval`, `talladega_oval`) got a `banking_secondary_deg` -- the only two tracks
  whose banking text names a tri-oval banking distinct from the turns banking.
- 0 anomalies (no track had digits in its banking text with no parsed `deg` value).
- `gate_track_reference.py` re-derives every row from the bundle's own banking text fresh and
  diffs against the stored parquet value (exact match required), plus 7 hand-checked known values
  (`daytona_oval`, `talladega_oval`, `bristol_dirt`, `homestead`, `new_hampshire`, `wwt_gateway`,
  `watkins_glen`).

## `silver.race_track` -- scope and the Phoenix-2018 finding

Implemented as a join of **every points race** (`race_type_id=1`, any series) to the crosswalk on
`(track_name = feed_track_name, season_start <= year <= season_end)` -- not restricted to Cup,
matching the spec's literal `silver.race_track = silver.races JOIN xwalk -> (series_id, race_id,
track_id)` (which keeps `series_id` as an output column, implying the view is meant to span all
three series -- physical facts like banking/length are series-agnostic; a Xfinity or Truck race
at Kansas Speedway really did happen at the `kansas` `track_id`). Restricted to points races only,
matching the package's own stated scope (bundle `metadata.scope`: "Points-paying Cup races").
Unresolved races (historical facility-name variants not in the crosswalk's vocabulary, e.g.
`Dover International Speedway`, `Richmond International Raceway`, `ISM Raceway`) are simply absent
from the table -- the standard silver "coverage by absence" convention (section 3.4), not an
error.

**Empirically verified this session, not previously known:** the crosswalk's Phoenix-2018 month
split (`phoenix_pre_2018f` through the spring 2018 race, `phoenix_post_2018f` from the November
2018 race onward, both keyed to `feed_track_name = 'Phoenix Raceway'`) is unreachable **for any
repo year**, not just 2022+ as the spec noted -- because the real feed's `track_name` for both
2018 Phoenix races is `"ISM Raceway"`, a string the crosswalk's vocabulary doesn't cover at all
(it only has `"Phoenix Raceway"`). So the month rule never actually fires against real data. It is
still implemented in `build_race_track()` (per the kickoff's explicit instruction to mirror
`track_id_for()`), as a group-level tiebreak that only activates when a race genuinely matches
*two* crosswalk rows -- verified against the full 966-row join (0 multi-matches after the fix
below).

**Bug found and fixed during this build:** the first implementation applied the month rule
*unconditionally per matched row* instead of only within groups that actually had two competing
matches. That silently dropped 21 legitimate, unambiguous Phoenix races (every spring "post-2018"
race 2020-2026, which only ever matches one crosswalk row) because a bare `month < 11` test fired
on rows that had no competing row to break a tie with. Caught by comparing the join's raw
966-row/404-Cup-row count against an independent ad hoc re-derivation of the same join before
trusting the output; fixed by grouping on `(series_id, race_id)` first and only invoking the
Phoenix tiebreak inside groups of size 2. Also caught and fixed a column-aliasing bug in the same
query (`r.track_id AS xwalk_track_id` instead of `x.track_id AS xwalk_track_id` --
`silver.races.track_id` is NASCAR's own numeric track id, a completely different key from the
package's string `track_id`; the two collide by name only).

## `silver.race_track_features` -- scope decision and spot checks

Restricted to `series_id=1` (Cup) by design, distinct from `race_track`'s broader scope: these
derived features (`config_race_number`, `return_gap_years`, `era_race_number`) are computed from
`schedule_by_year`, which counts **Cup points races only** (bundle `metadata.scope`, again) --
attaching a "count of prior Cup races" to a Xfinity/Truck row would misrepresent what the number
means, so this table stays Cup-only rather than inheriting `race_track`'s all-series scope.

Derivation (section 2.3, walk-forward by construction): for a race in season *Y* at `track_id`
*T*, `config_race_number` = (sum of `schedule_by_year[y][T]` for every *y* < *Y*, using the
package's own per-season counts -- safe for any fully-completed prior season, no repo-string
trust needed) + (count of this *T*'s races already run earlier in season *Y*, from the repo's own
chronological `race_date` order) + 1. `return_gap_years` = 0 if there was an earlier same-season
race, else *Y* minus the most recent earlier season with `schedule_by_year[y][T] > 0`, or NULL if
no such season exists (a true debut). `era_key`/`era_race_number` mirror the same logic scoped to
the enclosing rules era.

Spot-checked against the derivation doc's own worked examples:

- **Chicagoland** (`chicagoland_oval`): raced 2015-2019, returns in `race_id 5616` (2026) with
  `return_gap_years = 7` (last raced 2019, 6 fully blank seasons 2020-2025, returns in the 7th) --
  matches the doc's "returns in 2026 after 6 blank years" narrative exactly.
- **North Wilkesboro, San Diego Street, Mexico City**: each shows `config_race_number = 1`,
  `return_gap_years = NULL` (true debuts within the repo's own 2015-2026 window, not returns).
- **Atlanta post-2022**: two races/season 2022-2026; `era_race_number` resets to 1 at each of the
  2023 and 2026 era boundaries while `config_race_number` keeps accumulating continuously (9, 10
  at the two 2026 races) -- exactly the "partial coefficient reset at era breaks" behavior the
  audit recommends.
- `config_race_number == 1` iff `return_gap_years IS NULL` holds for all 404 rows
  (`gate_track_reference.py` asserts this as an invariant).

## Priors quarantine

`silver.track_priors` (430 rows) and `silver.track_similarity_prior` (193 rows) carry
`evidence_class = 'Working Hypothesis'` on every row (gate-enforced) and are joined to nothing in
`gold.wf_features` or any production path -- section 2.2's design decision that a fact table
(`track_dim`) and a hypothesis table (`track_priors`) must never be the same table, so a
downstream consumer can't accidentally treat a 1-10 analyst score as a measurement.

## Scope: what this session did not do

No model feature was added, no A/B was run, and nothing here feeds `walkforward.py`'s frozen
`[fin, pace, typed, start]` feature set -- reference/analytics tables only, per the rebuild's
RE-PROVE-don't-re-choose doctrine. The catalog items 6/7 in `research/track_audit_derivation.md`
section 7 (config-novelty and era-reset features as future model A/B candidates) remain
unscheduled F-queue items.
