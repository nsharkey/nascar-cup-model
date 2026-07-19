# NASCAR Cup Model — sprint plan

*As of 2026-07-19 · format v1 · source `plan/schedule.yml`, rendered by `src/report_plan.py` — do not hand-edit.*

The single living plan for the walk-forward Plackett-Luce Cup Series model: a completed foundation (audit, frozen config, pre-registered and adversarially reviewed specs) now feeding the weekly forward test, with the feature and causal-pace tracks gated behind it. Rendered from data, kept here and nowhere else.

## Phase A — Foundation & pre-registration

*Fable 5 · thinking on* — Judgment-shaped work: audit, frozen config, and immutable rulebooks written before any result exists. Complete. Model attribution on these rows reflects the judgment tier; detail lives in the technical column.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| A1 | Zero-trust audit | ✅ done | Fable 5 · thinking on | — | Re-checked the previous modeling effort's claims from scratch — most held, two were overstated, and the supposed accuracy ceiling was beaten. | 163 races parsed from cf.nascar.com; walk-forward Spearman. C2/C3 confirmed and strengthened, C1/C4 shown noise-level, C5 broken at 0.413 with a fitted Plackett-Luce model. report/NASCAR_AUDIT_REPORT.md. |
| A2 | Frozen config + walk-forward engine | ✅ done | Fable 5 · thinking on | — | Locked the production model settings so nothing changes without walk-forward validation evidence. | PL features [fin, pace, typed, start], pace_med85, half-life 8, ridge lambda 0.5, MY_TYPE typology, burn 15, min_hist 5, min_drv 20; src/walkforward.py is the frozen engine. |
| A3 | Forward-test harness + prediction #1 | ✅ done | Fable 5 · thinking on | — | Built the weekly prediction tool and logged the first public pre-race pick. | predict_next.py refuses post-hoc runs; race 5618 (North Wilkesboro) prediction sealed with a sha256 payload hash. |
| A4 | Pre-registration specs | ✅ done | Fable 5 · thinking on | — | Wrote the rulebooks for how everything is judged — before any result exists — so outcomes cannot be cherry-picked later. | specs/: scoring methodology, market-benchmark decision rule (gates roadmap #5), DNF and pooling A/B protocols. Frozen per specs/README.md. |
| A5 | Adversarial review + amendments | ✅ done | Fable 5 / Opus 4.8 · thinking on | ~1 day | Had fresh reviewers attack all four rulebooks and fixed every hole before it mattered, including one serious statistical flaw. | 26 findings (1 CRITICAL, 6 MAJOR), all accepted; amendments applied pre-data; review/ ledger + 3 findings files. CRITICAL: interim bootstrap edge boundary was uncalibrated at small race counts. |

## Phase B — Market-benchmark accrual (RUNNING)

*Sonnet 5 · thinking on · high* — The running spine: the weekly predict-then-score loop that accumulates scored races and closing prices to answer the project's central question (is there a live edge over the closing line?). Gates Phases C and D.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| B0 | Build score_race.py + score prediction #1 | ⬅ next | Sonnet 5 · thinking on · high | ~2-4 hr (first build; then a few min/week) | Turn the first race into the first scored data point — the tool that grades every weekly prediction from here on. | Implement to the AMENDED scoring spec (section 10 checklist + all AMENDMENT blocks: completeness gate, frozen results snapshot, pipeline order, provenance); pass the section 9 fixtures before touching real data. |
| B1 | Weekly pre-race: predict + commit + push + record odds | pending | Sonnet 5 · thinking on · high | ~15-30 min + human odds step (recurring) | Log each pick publicly before the green flag, and record the closing betting prices the whole benchmark depends on. | update_data.py then predict_next.py; commit + push before green flag; record ALL primary-book matchups per the market-spec full-board amendment. |
| B2 | Weekly post-race: score | pending | Sonnet 5 · thinking on · high | ~10-20 min (recurring, once B0 exists) | Add each completed race to the scored log. | score_race.py writes the frozen results snapshot and appends scores_log.csv; commit per the spec message format. |
| B3 | Create GitHub remote + first push | pending | Sonnet 5 · thinking on · high | ~30 min | Make the pre-race timestamps publicly verifiable and unblock later automation. | Create remote, push all local commits (publishes prediction #1's seal); prerequisite for E3. |
| B4 | Build market_benchmark.py + first look | pending | Sonnet 5 · thinking on · high | ~2-3 hr (first meaningful look needs enough priced races) | Compute the running edge verdict from the sealed inputs. | Amended section 6: race-clustered bootstrap with K>=20 floor and pinned mechanics; sequential Haybittle-Peto looks; reads sealed JSONs + frozen snapshots only. |

## Phase C — Feature experiments (gated: >=8 scored races)

*Sonnet 5 · thinking on · xhigh* — Walk-forward A/B tests that adopt a feature only if it beats the frozen config by a pre-registered margin. Hard-gated on >=8 scored forward races; C2 is serial after C1's decision.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| C1 | DNF/status A/B (roadmap #4a) | ⛔ blocked | Sonnet 5 · thinking on · xhigh | ~3-6 hr incl. discards | Test whether accounting for HOW a driver dropped out improves predictions; adopt only if it clears a pre-set bar. | 3 variants; adopt iff one-sided Wilcoxon p<=0.0167 AND mean delta-rho >=+0.005; per amended spec (V2 column namespacing, hardened baseline gate via explicit run() arg assertions). |
| C2 | Team/manufacturer pooling A/B (roadmap #4b) | ⛔ blocked | Sonnet 5 · thinking on · xhigh | reparse ~10 min + ~3-6 hr | Test whether teammate and manufacturer form add signal, after the DNF decision is settled. | Reparse for the team_name org key (regression-gated) then 3 exclude-self pooled variants; multiplicity 0.05/6 if C1 adopted nothing. |

## Phase D — Causal clean-air pace (gated: market EDGE)

*Fable 5 · thinking on* — The hardest feature, attempted only if the market benchmark returns EDGE. The design spec can be written now; execution stays gated. The fixed-effects approach is a proven dead end (audit report section 7).

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| D0 | Pre-register the roadmap-#5 design spec | pending | Fable 5 · thinking on | ~2-4 hr | Bank the research design for the highest-leverage feature now, while execution stays gated on a proven edge. | Causal identification via restart reshuffles and pit-cycle natural experiments; pre-registered kill/keep gate. Fixed-effects is a dead end (report section 7). |
| D1 | Implement roadmap #5 | ⛔ blocked | Sonnet 5 · thinking on · xhigh | TBD | Build the causal-pace feature only if the market says it is worth it. | Per the D0 spec's pre-registered kill/keep gate. |

## Phase E — AWS / infra (optional, per-item go)

*Sonnet 5 · thinking on · high* — Independent of C and D. Capture-side infrastructure to protect the benchmark's sample size and preserve irreplaceable race-day data at a few dollars a month. Plan-only today; each item needs its own go.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| E1 | S1 closing-odds capture | pending | Sonnet 5 · thinking on · high | ~1-2 hr | Stop losing the closing betting prices the whole benchmark depends on; a scheduled job records them every race morning. | EventBridge -> Lambda -> licensed odds API -> S3; formatter emits book_prices.entries per scoring spec section 5.1; human still commits. See planning/aws_solutions.md. |
| E2 | S2 live-feed poller + S3 archive mirror | pending | Sonnet 5 · thinking on · high | ~1-2 hr | Record the one race-day data stream that is otherwise lost forever, and back up all source feeds for pennies. | Race-window Lambda polling live-feed.json; one-time backfill of all consumed cf.nascar.com endpoints + weekly increment. |
| E3 | S4 weekly automation | ⛔ blocked | Sonnet 5 · thinking on · high | ~2-4 hr | Make the weekly public prediction post automatic so a busy Saturday cannot break the experiment. | Qualifying-detection off the weekend feed -> predict -> commit/push with cloud-held credentials; NOT GitHub Actions (quota trap). |

## Handoff — next session (B0)

**Model & settings:** Sonnet 5, thinking on, effort high.

B0 is a Sonnet 5 build against a zero-judgment spec — run it fresh on Sonnet 5, thinking on, effort high (this Fable session exceeds that tier). It is gated only on the North Wilkesboro race actually running; the prediction refuses to be scored before results exist.

```
Continuing the NASCAR Cup model project (repo at ~/Downloads/nascar-cup-model).
Read HANDOFF.md first. Today's task: score prediction #1 (race 5618, North
Wilkesboro, 2026-07-19) per protocol step 4.

Follow specs/scoring_methodology.md EXACTLY — INCLUDING every dated AMENDMENT
block at the bottom of the file (a red-team pass amended it pre-race: results
completeness gate on winner_driver_id, frozen _wf_scored.json snapshot with
defined read precedence, section 5 book-pipeline order, recorded_utc
provenance, n<3 handling, note-clause ordering). In order:
1. Implement src/score_race.py + src/test_score_race.py per spec section 10 and
   all amendments; the section 9 fixtures plus amendment rules must all pass
   before real data.
2. If closing book prices for 5618 were captured, record them per section 5.1
   BEFORE scoring; else proceed and let the scorer note their absence.
3. Run update_data.py, then score_race.py 5618. Hash verification must pass;
   the first scoring writes the frozen results snapshot.
4. Update HANDOFF status; commit per the spec's message format; tree clean.
Doctrine: frozen config, no post-hoc anything, one step at a time.
```

**Bottom line:** Foundation and pre-registration are complete and adversarially reviewed (26 findings, all fixed pre-data). The project is now in weekly accrual (Phase B), whose only near-term build is **B0 — build `score_race.py` and score prediction #1**. Phases C and D stay behind their gates; the two items you can independently pull forward are the Fable-written roadmap-#5 design spec (D0) and AWS closing-odds capture (E1).
