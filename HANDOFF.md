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
- **Next single step:** after the North Wilkesboro race, score prediction #1
  per `specs/scoring_methodology.md` (build `score_race.py` + its fixture
  tests first — spec §10 checklist). Book prices for it: not yet recorded —
  grab them if still possible, else note absent.
- GitHub remote: not yet pushed (repo has local commits only). Pushing
  before green flag makes prediction #1 publicly timestamped.

## Roadmap (agreed order — do not skip ahead)

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
src/                pipeline: download.py, parse_lib.py, parse.py,
                    update_data.py, predict_next.py, walkforward.py (engine),
                    step2/3/4/6 (audit analyses)
predictions/        forward-test log: per-race prediction files,
                    predictions_log.csv, scores_log.csv (once scoring starts)
```
