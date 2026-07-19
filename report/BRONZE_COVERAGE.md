# Bronze Coverage — B3 Verification Report

*Session: B3 (bronze verification), 2026-07-19. Drives `specs/medallion_architecture.md`
section 2.9's five terminal conditions. Environment: Anaconda `python` 3.13.5,
`duckdb` 1.4.0, `pyarrow` 19.0.0 (per `requirements.txt` pins `duckdb>=1.0`,
`pyarrow>=15`).*

---

## Verdict

**4 of 5 conditions PASS outright. Condition 2 (superset check) is PASS-with-gap:
its "stored" half passes for all 163 anchor races, but its sha-comparison half
cannot be computed at all — the legacy per-race raw-JSON cache
(`src/data/races/`) that `races_parsed.pkl` was built from does not exist in
this checkout. This is not a new finding: B2 (7de2738) already discovered and
documented it, and `bronze_fetch.py::import_legacy_cache` prints the same
warning on every run. B3 is not silently passing it — see §2 below for the
full accounting and the escalation this needs from the owner before C1.**

---

## 1. Terminal coverage (condition 1)

Re-ran `bronze_fetch.py --update` at session start (run_id
`20260719T200935Z`) to catch any drift since B2's commit (7de2738): 36 feed
tasks queued (revision-window re-checks + retries), all processed, 1
tentative-absent swept to terminal. No new `failed` entries.

Coverage grid = every completed race (index race with a truthy completion
signal, `race_has_run()`) × 3 series × 6 feeds, 2015→present:

| state | n |
|---|---|
| stored | 4,222 |
| absent | 1,964 |
| **failed** | **0** |

1,031 distinct completed races × 6 feeds = 6,186 = 4,222 + 1,964. Terminal
coverage is complete — every cell is `stored` or `absent`, none `pending` or
`failed`. **Condition 1: PASS.**

(228 additional grid rows exist for index races without a completion signal
yet — e.g. today's race 5618 — correctly excluded from the terminal-coverage
universe per spec §2.2's "not yet run" carve-out.)

### Terminal state by feed (completed races only)

| feed | stored | absent |
|---|---|---|
| weekend-feed | 837 | 194 |
| lap-times | 641 | 390 |
| live-pit-data | 598 | 433 |
| live-flag-data | 672 | 359 |
| lap-notes | 638 | 393 |
| live-feed | 836 | 195 |

### Terminal state by series

| series_id | stored | absent |
|---|---|---|
| 1 (Cup) | 1,783 | 821 |
| 2 (Xfinity) | 1,444 | 662 |
| 3 (Trucks) | 995 | 481 |

### Per-feed × per-series first-year-with-data (discovered floor)

Uniform across all three series — confirms B2's finding that the detailed-feed
floor is later than the 2015 index floor and feed-dependent, not series-dependent:

| feed | series 1 | series 2 | series 3 |
|---|---|---|---|
| weekend-feed | 2018 | 2018 | 2018 |
| live-feed | 2018 | 2018 | 2018 |
| live-flag-data | 2019 | 2019 | 2019 |
| lap-times | 2020 | 2020 | 2020 |
| live-pit-data | 2020 | 2020 | 2020 |
| lap-notes | 2020 | 2020 | 2020 |

---

## 2. Superset check (condition 2)

Spec §2.9.2: *"for every race in `races_parsed.pkl`, `lap-times` and
`weekend-feed` are `stored`, and the latest bronze payload sha equals the
legacy import's sha."*

**"Stored" half — PASS.** All 163 races in `races_parsed.pkl` (series 1,
years 2022–2026, `rid` 5146–5605) have both `lap-times` and `weekend-feed` in
`stored` state: 326/326 (163 races × 2 feeds) rows checked, 0 not-stored.

**Sha-comparison half — CANNOT BE COMPUTED. Documented gap, not a pass.**
The legacy import (spec §2.6) is meant to import `src/data/races/*.json`
(163 races × lap-times/weekend-feed = up to 326 files) plus
`race_list_2026.json` into `data/bronze/legacy_import/` as the comparison
anchor. In this checkout, `src/data/races/` is **empty** — the per-race raw
cache that `races_parsed.pkl` was originally built from was never persisted
outside the environment that built it (it's gitignored and B2 confirms it
doesn't exist here). Only `race_list_2026.json` was importable:

```
$ grep '"outcome": "imported"' data/bronze/manifest.jsonl
{"...","feed": "legacy_import", ..., "outcome": "imported", ...,
 "path": "data/bronze/legacy_import/race_list_2026.json.gz", ...}
```

One imported file, not 326. There is **no legacy-import sha to compare
against** for any of the 163 anchor races — not "0 mismatches found" but
"0 comparisons possible." Reporting this as a pass would be wrong; it is a
gap with a known, already-diagnosed cause (this is the same gap B2's
`import_legacy_cache()` flags in its own end-of-run message and the same one
`plan/schedule.yml`'s B2 `status_note` records).

**Downstream consequence, flagged per the kickoff instructions and B2's own
note (not resolved here — no workaround was invented):** `specs/
medallion_architecture.md` §4.3's mismatch-attribution mechanism (used by
C1's gate) is defined as "compare bronze payload sha vs. legacy-import sha";
with no legacy-import sha for these 163 races, C1 cannot run that mechanical
step for any mismatch it finds and will need an owner-directed fallback
(re-derive from a fresh legacy-cache export, or another attribution method) —
this is an **owner escalation item**, not a B3 decision.

**Condition 2 verdict: PASS (stored) / GAP-DOCUMENTED, NOT PASS (sha
comparison) — carried forward to C1 as an open item, per the owner's
mid-session instruction not to silently skip or invent a workaround.**

---

## 3. Race-index reconciliation (condition 3)

Reconciled three independent sources for Cup (series 1) points races
(`race_type_id == 1`), completed, 2022→present:

| source | count |
|---|---|
| bronze race index (`bronze.races_index`, `has_winner`) | **164** |
| `races_parsed.pkl` | **163** |
| vendored track-audit package (implied; `research/track_audit/INTEGRATION.md`) | **164** |

Bronze and the track-audit package agree exactly (164); `races_parsed.pkl` is
short by one. Per-year bronze breakdown: 2022–2025 = 36/36 each (full
seasons), 2026 = 20 (through the 2026-07-12 Atlanta cutoff, matching
INTEGRATION.md's independently-stated "20 of 36 2026 races completed through
2026-07-12"). Total 4×36+20 = 164.

**Set difference — bronze `race_id`s not in `races_parsed.pkl`:**

| race_id | year | race_date | track |
|---|---|---|---|
| 5580 | 2025 | 2025-11-17 | Talladega Superspeedway |

**Set difference the other direction (pkl race_ids not in the bronze
index) — empty.** No races exist in the legacy parsed set that bronze
doesn't independently confirm.

This is exactly the known fall-2025 Talladega playoff race flagged in
`research/track_audit/INTEGRATION.md` and `HANDOFF.md`'s B2 entry — confirmed
present in the bronze archive, absent from the legacy pipeline's output.

**Root cause, established directly from the stored bronze payload (not
present in prior sessions' notes — new for B3):** race 5580's `weekend-feed`
is `stored` and parses as valid JSON, but its `weekend_race` field is `null`
(only `weekend_runs` is populated); its `lap-times` file is present and
non-empty (40 lap entries). This matches the original audit report's
independent observation of the same race
(`report/NASCAR_AUDIT_REPORT.md` §1: *"its `weekend-feed.json` returns a
null `weekend_race` block — lap times exist, results don't"*). A scan of
all 164 bronze-completed Cup points races' `weekend-feed` payloads confirms
**race 5580 is the only one with a null `weekend_race`** — this is an
upstream NASCAR data-completeness gap for this one race, not a download or
parse defect in bronze, and not a broader pattern.

**No other gaps found.** The `race_id`-set reconciliation and the
independent null-content scan agree on exactly one anomaly.

**Condition 3: PASS** (reconciliation ran against both `races_parsed.pkl`
and the track-audit package; the known gap is surfaced; no additional gap
exists).

---

## 4. Spot-parse (condition 4)

20 random `stored` files per feed type (seeded, `random.seed(20260719)`),
parsed as JSON and checked for the expected top-level structure:

| feed | sampled | structurally OK | failed |
|---|---|---|---|
| weekend-feed | 20 | 20 | 0 |
| lap-times | 20 | 20 | 0 |
| live-pit-data | 20 | 20 | 0 |
| live-flag-data | 20 | 20 | 0 |
| lap-notes | 20 | 20 | 0 |
| live-feed | 20 | 20 | 0 |

120/120 files parsed as valid JSON with the expected top-level shape
(`laps`/`flags` present for lap-times; `weekend_race` key present — note this
checks *key presence*, not non-null value, consistent with spec wording — for
weekend-feed; list for pit/flag feeds; `laps` dict for lap-notes; `vehicles`
for live-feed). **Condition 4: PASS.**

---

## 5. Hash verify (condition 5)

Reused `bronze_fetch.py --verify --sample 100` (no reimplementation, per the
kickoff instruction):

```
$ python bronze_fetch.py --verify --sample 100
[bronze_fetch] verify: checking 100 file(s)
[bronze_fetch] verify complete: 100 ok, 0 missing, 0 mismatched
```

100/100 randomly sampled stored/imported files re-hash (gunzip → sha256) to
their manifest-recorded sha256. **Condition 5: PASS.**

---

## Totals and environment

- Total stored files on disk: 4,238 (includes race-list index snapshots and
  the one legacy import, in addition to the 4,222 feed-grid `stored` cells).
- Total bytes: 518.7 MB raw / 62.9 MB gzipped.
- `data/bronze/manifest.jsonl`: 6,641 lines, sha256
  `a583023f58fc60d172d696ca4b8e6c1e173c185940e332dbc2f7b5199a8f9f3f`
  (2,969,677 bytes).
- Library versions: `duckdb` 1.4.0, `pyarrow` 19.0.0 (Anaconda `python` 3.13.5).

## Mismatch list (consolidated)

1. **§2.9.2 (superset sha comparison), all 163 anchor races:** no
   legacy-import sha baseline exists — gap, not a mismatch per se (see §2).
   Owner escalation needed before C1 can run §4.3's mechanical
   shas-differ check.
2. **§2.9.3 (index reconciliation):** race_id 5580 (2025-11-17, Talladega
   Superspeedway) present in bronze and the track-audit package's implied
   schedule, absent from `races_parsed.pkl`. Root cause: upstream
   `weekend_race` is null for this one race in NASCAR's own feed (confirmed
   directly from the stored payload). No other gaps found by either the
   race_id-set diff or an exhaustive null-content scan of all 164 races.
