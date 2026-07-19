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
- **Next single step:** `B2` in the plan — bronze ingestion (Sonnet build
  session; kickoff prompt in `plan/schedule.yml`). Scoring/benchmark are
  re-homed as Gold consumers in D2; prediction #1 is scored there.
- GitHub remote: not yet pushed (repo has local commits only). Pushing
  before green flag makes prediction #1 publicly timestamped.

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
predictions/        forward-test log: per-race prediction files,
                    predictions_log.csv, scores_log.csv (once scoring starts)
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
