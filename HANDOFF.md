# HANDOFF — NASCAR Cup Model (read this first in a new session)

## Prompt to paste into a new session

> I'm continuing an ongoing NASCAR Cup Series modeling project. Attached is
> `nascar-handoff.zip`. Unzip it to /home/claude, read `HANDOFF.md` at the repo
> root, and follow its bootstrap steps. Then check "Current status" and do the
> single next step listed there — one step at a time, nothing speculative.
> Honor the doctrine section (superspeedway stand-down, no post-hoc
> predictions, validated config stays frozen). Today's task: [fill in — e.g.
> "score last week's race", "generate this week's prediction after
> qualifying", or a specific question].

If the zip isn't attached but the repo is on GitHub, replace the first two
sentences with: clone `https://github.com/<user>/nascar-cup-model`, read
`HANDOFF.md`, then run the full pipeline (`download.py` then `parse.py`,
~10 min) since the parsed dataset isn't committed.

## What this project is

A walk-forward Plackett–Luce model predicting Cup Series finishing order from
public cf.nascar.com feeds, produced by a zero-trust audit of an earlier
modeling effort (full report: `report/NASCAR_AUDIT_REPORT.md`). Audit verdicts
on the prior effort's five claims: C2, C3 reproduced (C3 strengthened);
C1 partial (real but fragile, not significant); C4 method dispute (grid is a
feature, not a rival); C5 failed (their ~0.38 ceiling broken at 0.413 with
their own ingredients properly fitted). Backtest 0.413 Spearman, 0.476
non-superspeedway, 0.449 on 2026 out-of-sample.

**Production config (FROZEN — do not change without a validated reason):**
pace = `pace_med85`, half-life 8, corrected typology (`MY_TYPE` in
`src/walkforward.py`), shrinkage typed history, PL features
`[fin, pace, typed, start]`, ridge λ=0.5, burn 15, min_hist 5, min_drv 20.

## Bootstrap (new session, zip attached)

```bash
cd /home/claude && unzip -q /mnt/user-data/uploads/nascar-handoff.zip
cd nascar-cup-model && pip install -r requirements.txt --break-system-packages -q
cd src && python3 update_data.py    # fetches only races completed since handoff
```

`src/races_parsed.pkl` ships inside the zip (808 KB), so no full re-download
is needed. `update_data.py` appends any newly completed races in seconds.

## Weekly protocol (the forward test — the project's main activity)

1. After qualifying posts (usually Sat): `python3 update_data.py` then
   `python3 predict_next.py`. Writes prediction to `predictions/`.
2. `git add -A && git commit -m "pre-race: <track>" && git push` — **before
   the green flag.** The public timestamp is the point.
3. Record book head-to-head matchup prices at close into the JSON's
   `book_prices` block (manual, or paste them in chat).
4. After the race: run `update_data.py` again, then score — Spearman of
   predicted vs. actual order; H2H pick accuracy from the JSON's `h2h_prob`
   matrix; vs. book picks where prices were recorded. Append results to
   `predictions/scores_log.csv`. **The scoring procedure, edge cases, and
   the exact CSV contract are frozen in `specs/scoring_methodology.md` —
   follow it exactly** (it adds a `book_n` column to the list originally
   sketched here). Commit.

## Doctrine (non-negotiable)

- **Superspeedways (Daytona, Talladega, Atlanta) are stand-downs.** Confident
  picks there scored worse than coin flips (Brier 0.2514). Predictions are
  logged for completeness, never actionable. The harness flags these.
- **No post-hoc predictions.** `predict_next.py` refuses to run once results
  exist. Never hand-construct a "prediction" for a completed race.
- **One step at a time.** Resources are limited. Finish and commit the current
  step before proposing the next.
- **Frozen config.** Model changes require walk-forward validation evidence,
  not intuition. The audit exists because the last effort skipped this.
- Nothing here is betting advice; the forward test decides whether an edge
  over the closing line exists at all. ~52–53% pairwise accuracy against the
  book's orderings is break-even after hold. A negative result is a valid
  outcome.

## Current status (update this section every session)

- **2026-07-18:** Forward test LIVE. Prediction #1 committed pre-race:
  race 5618, North Wilkesboro (SHORT), 2026-07-19. Top-5 picked: Blaney,
  Bell, Hamlin, Gibbs, Reddick. Trained on 148 races through Atlanta 7/12.
- **2026-07-18 (planning session):** `specs/` pre-registered before any race
  was scored: scoring methodology, market-benchmark decision rule (gates
  roadmap #5), and the two roadmap-#4 A/B protocols (DNF/status, pooling).
  Frozen sections are immutable per `specs/README.md`. Also
  `planning/aws_solutions.md`: plan-only AWS/infra roadmap (odds capture,
  live-feed poller, mirroring, automation) — nothing implemented; each item
  needs its own go.
- **2026-07-19 (direction set):** foundation-first **medallion rebuild**
  (bronze/silver/gold) adopted — clean, local, embedded (DuckDB engine +
  parquet + gzipped raw-JSON bronze; no Spark/Databricks). Governance layer
  (audit + specs + review) is architecture-independent and preserved; the
  data/feature plumbing is rebuilt clean. Doctrine: **preserve the validated
  results and re-prove the model on the new foundation rather than re-choosing
  it**, and **never pause the perishable weekly odds capture**. The live
  sprint plan is `PLAN.md` (rendered from `plan/schedule.yml`) — it supersedes
  the prose roadmap below.
- **2026-07-19 (B1 done):** `specs/medallion_architecture.md` committed
  (4d3a415) — the execution contract for the whole rebuild. C-gate (silver
  field-for-field vs anchored pkl) and D-gate (reproduce 0.413/0.476/0.449
  via R0–R3 before gold replaces the pkl path) are FROZEN sections. Live
  probes verified all six feed URL patterns (3 series), confirmed the index
  floor is 2015, and found that missing objects 403 (not 404) — the spec's
  fetch protocol disambiguates absent-vs-throttled. Frozen scoring/market
  spec file paths are honored via a bronze-fed compatibility shim (no
  amendments needed).
- **2026-07-19 (track-audit package vendored):** owner-supplied external
  track/configuration research integrated at `research/track_audit/` — six
  immutable, SHA-256-manifest-verified files (43 physical configurations,
  2015–2026, points races only) + a derived `track_id`↔feed-name crosswalk,
  loader (`src/track_audit.py`) and validation gate
  (`src/test_track_audit.py`, PASS). Its 1–10 scores are analyst structural
  priors, NOT measurements; nothing feeds the frozen model. See
  `research/track_audit/INTEGRATION.md`. **Finding for B3:** the package's
  schedule audit exposes that `races_parsed.pkl` is missing the fall-2025
  Talladega playoff race (163 races where 164 completed 2022→cutoff) — the
  B3 bronze coverage superset check should confirm and close this gap.
- **2026-07-19 (B2 done, 7de2738):** full historical bronze pull —
  `src/bronze_fetch.py` / `src/warehouse.py` / `src/bronze_report.py`.
  4,222 files stored, 1,964 confirmed genuinely absent, 0 failed
  (~519 MB raw / ~63 MB gzipped). Detailed-feed floor discovered (later
  than the 2015 index floor, and feed-dependent): weekend-feed/live-feed
  2018, live-flag-data 2019, lap-times/live-pit-data/lap-notes 2020,
  uniform across all 3 series. Two live data-quality bugs found and fixed
  (`DATA_DICTIONARY.md` §8c/8d): `winner_driver_id` is unset for every
  2015–2019 race and 12/41 of 2022's (older index schema) —
  `race_has_run()` falls back to `average_speed`/`total_race_time`; the
  `year=2017` index URL 200s with 2018's season data instead of 403ing —
  `index_year_matches()` detects and treats it as absent. Owner-directed
  dated amendment to spec §2.4 mid-session (newest-year-first task order,
  shortened post-trip retry ladder, circuit-breaker recovery — none raise
  the request rate) cut the run from a projected 10–50+ hr to under 2 hr.
  **Known gap for C1:** the legacy `src/data/races/` raw-JSON cache (163
  races) that `races_parsed.pkl` was built from doesn't exist in this
  checkout (gitignored, never persisted outside the environment that
  built it) — only `race_list_2026.json` was importable via §2.6. §4.3's
  mismatch attribution has no legacy-import sha baseline for those races
  and needs owner escalation instead of the mechanical shas-differ check.
- **2026-07-19 (B3 done, ffc3ba8):** bronze verification. 4/5 of spec §2.9's
  terminal conditions PASS outright: terminal coverage (`failed`=0 across
  4,222 stored / 1,964 absent); spot-parse (120/120); hash-verify (100/100,
  `bronze_fetch.py --verify --sample 100`). Condition 3 (index reconciliation)
  PASS with the expected gap surfaced: bronze=164 vs `races_parsed.pkl`=163 vs
  track-audit-implied=164 completed Cup points races 2022→present; sole gap
  is race_id 5580 (fall-2025 Talladega) — root-caused this session by reading
  the stored payload directly: its `weekend-feed`'s `weekend_race` field is
  `null` (the only one of 164), an upstream NASCAR data gap, not a download or
  parse defect. Condition 2 (superset check) is **not** a clean pass: the
  "stored" half passes for all 163 anchor races, but the sha-comparison half
  cannot be computed at all — the legacy per-race cache (`src/data/races/`)
  `races_parsed.pkl` was built from doesn't exist in this checkout (only
  `race_list_2026.json` was ever legacy-imported; B2 finding, not new).
  Documented as an **open owner-escalation item carried into C1**: §4.3's
  mismatch attribution has no legacy-import sha baseline for any of the 163
  anchor races, and can only run mechanically if every anchor race turns out
  bit-identical. Full detail: `report/BRONZE_COVERAGE.md`,
  `## RESULT — B3` in the spec.
- **Next single step:** `C1` in the plan — silver driver-race parity (Sonnet
  build session; the frozen C-gate, gates D1/gold). Carries B3's condition-2
  escalation forward — see C1's `status_note` in `plan/schedule.yml`. C2
  (silver breadth) is equally unblocked and not picked only because the plan
  format allows one `next` at a time and D1's gate chain runs through C1.
  Scoring/benchmark are re-homed as Gold consumers in D2; prediction #1 is
  scored there.
- **2026-07-19 (G1 done):** `specs/clean_air_causal_pace.md` pre-registered
  (0c8e9fa) — the roadmap-#5 design, banked before any of its data exists.
  Two natural experiments (restart-reshuffle pit-box IV; pit-cycle offset
  windows) with FROZEN identification + feature-A/B gates and a
  fixed-effects prohibition list (report §7 stands). Execution (G2) remains
  doubly gated: market benchmark = EDGE, plus the C2/D1/D2 pipeline; if the
  benchmark never returns EDGE the spec is banked-never-executed, which is a
  valid outcome. Note: at the time of this session the working tree carried
  uncommitted mid-B2 work (bronze_fetch/warehouse/bronze_report + a dated
  mid-B2 fetch-protocol amendment in the medallion spec) from a separate B2
  session — left untouched and uncommitted by G1.
- **2026-07-19 (E2 done):** GitHub remote created and first push made —
  public repo `https://github.com/nsharkey/nascar-cup-model`. All commits
  through a50bc9c published ~16:45 UTC, ~6h15m before race 5618's 23:00 UTC
  green flag, so prediction #1's seal is publicly timestamped pre-race.
  H3 (weekly automation) is no longer remote-blocked.

## Roadmap (agreed order — do not skip ahead)

> **Superseded 2026-07-19 by the medallion plan in `PLAN.md`.** The items below
> are preserved as the original governance order; they now execute on the
> bronze/silver/gold foundation (features/scoring/benchmark are Gold consumers).
> Read `PLAN.md` (or run `python src/report_plan.py --open`) for the live schedule.


1. **Market benchmark (RUNNING).** Accumulate weekly predictions + book
   prices + scores. This gates everything below.
2. Config locked (done — see frozen config above).
3. Superspeedway stand-down codified (done — enforced in harness + doctrine).
4. When the log has ~8–10 scored races: DNF/status-aware history feature
   (`status` field already parsed), then teammate/manufacturer pooling. Each
   must beat the frozen config walk-forward before adoption.
5. Only if the market benchmark shows a live edge: clean-air pace via causal
   identification (restart reshuffles, pit-cycle natural experiments). The
   fixed-effects approach is a proven dead end (see report §7) — do not retry it.

## Repo map

```
HANDOFF.md          this file — the one-stop briefing
README.md           public-facing description
report/             full audit report
specs/              pre-registered, frozen design docs (scoring, market
                    gate, feature A/Bs) — read specs/README.md first
planning/           living plan docs (aws_solutions.md — plan-only infra
                    roadmap, nothing implemented)
research/           vendored external research (track_audit/ — immutable
                    hash-verified package + derived crosswalk; INTEGRATION.md)
plan/               sprint plan: schedule.yml (source of truth) + PLAN.html
PLAN.md             rendered sprint plan (source-of-record); do NOT hand-edit
PLAN_FORMAT.md      the plan mechanism + anti-drift gate
DATA_DICTIONARY.md  human-readable field reference (parsed store, prediction
                    JSON, CSV contracts, raw cf.nascar.com feeds)
src/                pipeline: download.py, parse_lib.py, parse.py,
                    update_data.py, predict_next.py, walkforward.py (engine),
                    report_plan.py (plan renderer), step2/3/4/6 (audit analyses)
                    -- medallion rebuild (B2): bronze_fetch.py (ingestion,
                    --full/--update/--verify), warehouse.py (duckdb catalog),
                    bronze_report.py (coverage matrix)
predictions/        forward-test log: per-race prediction files,
                    predictions_log.csv, scores_log.csv (once scoring starts)
data/               gitignored medallion foundation (bronze/silver/gold +
                    nascar.duckdb); see specs/medallion_architecture.md
                    section 1.1 and DATA_DICTIONARY.md section 8
```

## Sprint-plan display (read before touching the plan)

The sprint plan is **structured data + a deterministic renderer + a drift
gate**, not a hand-maintained doc. Edit `plan/schedule.yml` and run
`python src/report_plan.py` to regenerate `PLAN.md` and `plan/PLAN.html` —
**never hand-edit a rendered file** (`src/test_report_plan.py` fails CI if a
render diverges from the YAML).

**When the owner asks to see / look at the sprint plan, run
`python src/report_plan.py --open`** — it re-renders from the YAML and opens
`plan/PLAN.html` in the local browser (nothing is uploaded). Only publish the
claude.ai artifact form when the owner explicitly wants a shareable link. Full
spec: `PLAN_FORMAT.md`.
