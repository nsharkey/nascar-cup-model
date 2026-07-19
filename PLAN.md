# NASCAR Cup Model — sprint plan

*As of 2026-07-19 · format v1 · source `plan/schedule.yml`, rendered by `src/report_plan.py` — do not hand-edit.*

The single living plan for the walk-forward Plackett-Luce Cup Series model, now on a foundation-first medallion (bronze/silver/gold) rebuild. Governance (audit, pre-registered specs, adversarial review) is complete and architecture-independent; the data foundation is being rebuilt clean, with the perishable weekly market capture running throughout. Rendered from data, kept here and nowhere else.

## Phase A — Foundation & pre-registration (governance)

*Fable 5 · thinking on · xhigh* — Judgment-shaped work done before any result existed — audit, frozen config VALUES, immutable rulebooks, adversarial review. Complete and architecture-independent: it survives the rebuild unchanged and is the equity the rebuild must preserve, not re-choose.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| A1 | Zero-trust audit | ✅ done | Fable 5 · thinking on · xhigh | — | Re-checked the previous modeling effort's claims from scratch — most held, two were overstated, and the supposed accuracy ceiling was beaten. | 163 races parsed from cf.nascar.com; walk-forward Spearman. C2/C3 confirmed and strengthened, C1/C4 shown noise-level, C5 broken at 0.413 with a fitted Plackett-Luce model. report/NASCAR_AUDIT_REPORT.md. |
| A2 | Frozen config + walk-forward engine | ✅ done | Fable 5 · thinking on · xhigh | — | Locked the production model settings so nothing changes without walk-forward validation evidence. | PL features [fin, pace, typed, start], pace_med85, half-life 8, ridge lambda 0.5, MY_TYPE typology. The config VALUES carry into gold; the engine code is re-pointed to gold and re-proven in Phase D. |
| A3 | Forward-test harness + prediction #1 | ✅ done | Fable 5 · thinking on · high | — | Built the weekly prediction tool and logged the first public pre-race pick. | predict_next.py refuses post-hoc runs; race 5618 (North Wilkesboro) prediction sealed with a sha256 payload hash. The sealed file is architecture-independent and survives the rebuild. |
| A4 | Pre-registration specs | ✅ done | Fable 5 · thinking on · xhigh | — | Wrote the rulebooks for how everything is judged — before any result exists — so outcomes cannot be cherry-picked later. | specs/: scoring methodology, market-benchmark decision rule, DNF and pooling A/B protocols. Frozen; govern the gold consumers regardless of pipeline. |
| A5 | Adversarial review + amendments | ✅ done | Fable 5 / Opus 4.8 · thinking on · xhigh | ~1 day | Had fresh reviewers attack all four rulebooks and fixed every hole before it mattered, including one serious statistical flaw. | 26 findings (1 CRITICAL, 6 MAJOR), all accepted; amendments applied pre-data; review/ ledger + 3 findings files. |

## Phase B — Bronze — immutable raw archive

*Sonnet 5 · thinking on · high* — The medallion rebuild starts here. Design the architecture first (Fable), then pull EVERY available feed for every series back to the real detailed-feed floor into an unchanged, hashed local store. Purely additive, low-risk, and preserves data that lives only on NASCAR's servers.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| B1 | Design the medallion architecture (spec) | ✅ done | Fable 5 · thinking on · xhigh | ~2 hr | Designed the clean bronze/silver/gold rebuild on paper before building any of it — schemas, storage, fetch protocol, and the frozen rule that the model's proven accuracy must be reproduced, not re-chosen. | specs/medallion_architecture.md committed: DuckDB + parquet + versioned json.gz bronze w/ sha256 manifest; silver parity via parse_lib reuse (C-gate frozen, field-for-field vs anchored pkl w/ upstream-revision attribution); gold features in SQL (D-gate frozen, R0-R3 reproduce 0.413/0.476/0.449); frozen-spec paths honored via bronze-fed shim. URL patterns + 403-absent semantics live-verified; index floor = 2015. |
| B2 | Bronze ingestion — full historical pull | ⬅ next | Sonnet 5 · thinking on · high | ~1-2 hr (mostly polite fetching) | Download every available NASCAR feed — all series, back as far as the data goes — into a permanent, unchanged local archive with a fingerprint per file. | Execute spec section-10 B2 checklist: src/bronze_fetch.py per the frozen-ish section-2 protocol (concurrency 4, 5 req/s cap, retry ladder, 403 two-pass absent rule, atomic versioned json.gz, append-only manifest), warehouse catalog views, legacy import, then the full 2015->present pull (6 feeds x 3 series, ~8k requests) + tentative-absent sweep + interim coverage report. |
| B3 | Bronze verification & coverage | pending | Sonnet 5 · thinking on · high | ~30-60 min | Confirm the archive is complete and every file is intact before anything is built on it. | Coverage manifest terminal (ok/absent/failed=0); superset check that the existing 163 races' consumed feeds are present; spot-parse sample files; hashes recorded. |

## Phase C — Silver — cleaned & conformed

*Sonnet 5 · thinking on · high* — Parse, clean, dedupe, conform bronze into DuckDB/parquet tables. The driver-race table must reproduce today's parsed fields EXACTLY (regression-gated), so the validated model is untouched; new lap/pit/flag tables unlock the feeds we've never used.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| C1 | Silver driver-race table (behavior-preserving) | pending | Sonnet 5 · thinking on · high | ~3-5 hr | Rebuild the cleaned per-driver-per-race table the model uses — proven to match today's numbers exactly, so nothing about the validated model changes. | Silver driver-race table in DuckDB/parquet from bronze; field-for-field regression vs races_parsed.pkl (163/163) covering finish/start/status/pace_med85/etc.; dedupe + type conform. |
| C2 | Silver lap / pit / flag tables | pending | Sonnet 5 · thinking on · high | ~2-4 hr | Build cleaned tables for the richer data we've never used — lap-by-lap, pit stops, and cautions — so it's ready when the model wants it. | Lap-level (times/positions), pit-level (stop timing/tires/positions gained), flag-level (caution/stage transitions) silver tables from the newly-archived feeds; keyed to race+driver. Feeds roadmap-#5 pace work. |

## Phase D — Gold — model & analytics surface

*Sonnet 5 · thinking on · xhigh* — Model-ready feature tables + scoring + benchmark as consumers, built in SQL on silver. The frozen config VALUES carry over; the engine is re-pointed to gold and must RE-PROVE 0.413 / 0.476 non-SS before gold replaces the old pickle path. Effort xhigh — the numbers must match.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| D1 | Gold features + re-point engine + re-prove 0.413 | pending | Sonnet 5 · thinking on · xhigh | ~4-6 hr (incl. re-validation) | Rebuild the model's inputs on the new foundation and re-confirm it still hits the validated accuracy — the checkpoint that lets us keep standing on the 0.413 result. | Walk-forward feature banks (recency-weighted finish/pace/typed histories, grid) as gold tables in SQL; re-point the engine to gold; hard gate: reproduce 0.413 / 0.476 non-SS / 0.449 2026 before gold replaces the pkl path. |
| D2 | Gold scoring + benchmark consumers (scores race #1) | pending | Sonnet 5 · thinking on · xhigh | ~3-5 hr | Move scoring and the market-edge test onto the new foundation and finally score the first race. | Scoring (specs/scoring_methodology.md + amendments) and market_benchmark (amended spec) as gold consumers reading bronze results + sealed predictions; scores prediction #1 (race 5618); absorbs retired R1/R2/R3. |

## Phase E — Forward test (RUNNING — perishable capture)

*Sonnet 5 · thinking on · high* — Closing-line data exists only in the minutes before each green flag and can never be backfilled, so this loop runs every race weekend regardless of rebuild progress. Scoring/benchmark themselves are re-homed to Gold; what stays here is the capture that must not be starved.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| E1 | Weekly pre-race: predict + commit + push + record odds | pending | Sonnet 5 · thinking on · high | ~15-30 min (recurring) | Every race weekend, log the public prediction and record closing prices BEFORE the green flag — the one thing that can never be recovered later, so it runs no matter what else is in progress. | predict_next -> commit -> push -> record ALL primary-book matchups per the market-spec full-board amendment. Perishable; never paused for the rebuild. |
| E2 | Create GitHub remote + first push | pending | Sonnet 5 · thinking on · high | ~30 min | Publish the repo so the pre-race prediction timestamps are independently verifiable. | Create remote, push all local commits (publishes prediction #1's seal); prerequisite for H automation. Architecture-independent. |

## Phase F — Feature experiments (gated: >=8 scored, on gold)

*Sonnet 5 · thinking on · xhigh* — The pre-registered roadmap-#4 A/Bs, now executed against the gold feature layer. Specs are frozen and carry over; hard-gated on >=8 scored races, and F2 is serial after F1's decision.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| F1 | DNF/status A/B (roadmap #4a, on gold) | ⛔ blocked | Sonnet 5 · thinking on · xhigh | ~3-6 hr incl. discards | Test whether accounting for HOW a driver dropped out improves predictions — now run on the new foundation. | specs/dnf_status_feature.md (amended) executed against the gold feature layer; adopt iff Wilcoxon p<=0.0167 AND mean delta-rho>=+0.005; gated on >=8 scored races. |
| F2 | Team/manufacturer pooling A/B (roadmap #4b, on gold) | ⛔ blocked | Sonnet 5 · thinking on · xhigh | ~3-6 hr | Test teammate and manufacturer form, after the DNF decision — on the new foundation. | specs/team_mfr_pooling.md (amended) on gold; the team_name org key is already clean in silver (no reparse needed); 0.05/6 multiplicity if F1 adopted nothing. |

## Phase G — Causal clean-air pace (gated: market EDGE)

*Fable 5 · thinking on · xhigh* — The hardest feature, attempted only if the market benchmark returns EDGE. The design spec can be written now; its raw material (restart reshuffles, pit cycles) comes from the new silver pit/flag tables.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| G1 | Pre-register the roadmap-#5 design spec | pending | Fable 5 · thinking on · xhigh | ~2-4 hr | Bank the design for the hardest feature (clean-air pace) while execution stays gated on a proven market edge. | Pre-register specs/clean_air_causal_pace.md: restart/pit-cycle natural experiments sourced from the new silver pit/flag tables; kill/keep gate. Fixed-effects is a dead end (report section 7). |
| G2 | Implement roadmap #5 | ⛔ blocked | Sonnet 5 · thinking on · xhigh | TBD | Build clean-air pace only if the market says it is worth it. | Per G1's pre-registered gate; consumes silver pit/flag tables + gold features. |

## Phase H — Infra (AWS, optional, per-item go)

*Sonnet 5 · thinking on · high* — Capture-side infrastructure at a few dollars a month. Odds capture protects the perishable data; the live poller + S3 mirror back up the ephemeral stream and the bronze archive. Plan-only; each needs its own go.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| H1 | S1 closing-odds capture | pending | Sonnet 5 · thinking on · high | ~1-2 hr | Automate recording the closing prices the benchmark depends on, so a busy weekend cannot lose them. | EventBridge -> Lambda -> licensed odds API -> S3; emits book_prices.entries per scoring spec 5.1. planning/aws_solutions.md S1. |
| H2 | S2 live-feed poller + S3 bronze mirror | pending | Sonnet 5 · thinking on · high | ~1-2 hr | Record the one race-day stream that is otherwise lost, and back up the permanent archive off-machine. | Race-window Lambda polling live-feed.json; S3 mirror of data/bronze/. planning/aws_solutions.md S2/S3. |
| H3 | S4 weekly automation | ⛔ blocked | Sonnet 5 · thinking on · high | ~2-4 hr | Make the weekly public prediction post automatic so a busy Saturday cannot break the experiment. | Qualifying-detection off the weekend feed -> predict -> commit/push; NOT GitHub Actions (quota trap). |

## Phase R — Retired — superseded by the medallion rebuild

*Sonnet 5 · thinking on · high* — Sessions overtaken by the 2026-07-19 foundation-rebuild decision, kept as record. Their intent survives — folded into the Gold consumers — but the standalone-script-against-the-old-pipeline approach is retired.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---------|--------|------------------|------------|-------------------|-------------------|
| R1 | Standalone score_race.py (old pipeline) | ⊘ retired | Sonnet 5 · thinking on · high | — | Superseded — a standalone scorer against the old pickle pipeline. Scoring is now built on the new foundation instead. | Retired 2026-07-19 under the medallion pivot; folded into Gold consumer D2. The frozen scoring-methodology spec carries over unchanged. |
| R2 | Standalone market_benchmark.py (old pipeline) | ⊘ retired | Sonnet 5 · thinking on · high | — | Superseded — a standalone market-benchmark script. The edge test is now built on the new foundation instead. | Retired 2026-07-19; folded into Gold consumer D2. The amended market-benchmark spec carries over unchanged. |
| R3 | Standalone weekly scoring step | ⊘ retired | Sonnet 5 · thinking on · high | — | Superseded — the standalone weekly scoring step, now part of the new foundation's scoring and the running loop. | Retired 2026-07-19; scoring runs as a Gold consumer (D2) reading bronze results. The perishable capture that remains is E1 (predict + odds). |

## Handoff — next session (B2)

**Model & settings:** Sonnet 5, thinking on, effort high.

B2 is a Sonnet build session executing the spec's section-10 B2 checklist with zero design judgment calls (every choice is pre-resolved in the spec; genuine ambiguity means stop and flag, not choose). Doctrine for the whole rebuild: preserve the validated results and pre-registered decisions, RE-PROVE the model on the new foundation rather than re-choosing it, and never pause the perishable weekly odds capture.

```
Continuing the NASCAR Cup model project (repo at ~/Downloads/nascar-cup-model).
Read HANDOFF.md, then specs/medallion_architecture.md IN FULL — it is the
execution contract for this session and pre-resolves every design choice.

BUILD session B2 — bronze ingestion, per the spec's section-10 B2 checklist:
1. Add duckdb+pyarrow to requirements.txt (record versions); add data/ to
   .gitignore.
2. Build src/bronze_fetch.py exactly per spec section 2: layout/versioning
   section 1.1 + 2.5, manifest section 2.3, fetch protocol section 2.4
   (default concurrency 4, aggregate 5 req/s, retry ladder 2/4/8/16/32s,
   circuit breaker, the 403 two-pass tentative-absent rule, atomic writes,
   sha256 of uncompressed payload), modes --full/--update/--verify.
3. Build src/warehouse.py (bronze.manifest/files/coverage views).
4. Run the legacy import (spec section 2.6) of src/data/.
5. Run the full pull: index years 2015->present (+2014 floor re-check),
   all 3 series, all 6 feeds, every index race; then the end-of-run
   tentative-absent sweep. Expect ~8k requests, 30-60 min, ~<=1 GB gzipped.
6. Build src/bronze_report.py and emit the interim coverage matrix;
   re-run --update until failed count is ~0 (leave B3's terminal
   verification for B3).
Zero design judgment calls: if the spec is genuinely ambiguous anywhere,
STOP and flag it rather than choosing. If today is a race weekend, E1
duties (prediction + odds capture) come first. Commit code + interim
coverage summary; leave the tree clean.
```

**Bottom line:** B1 is done (2026-07-19): specs/medallion_architecture.md is committed (4d3a415) — the execution contract for the whole rebuild, with the silver regression gate (C) and the 0.413/0.476/0.449 re-prove gate (D) frozen. Next is **B2 — bronze ingestion** (Sonnet): the full historical pull of all 6 feeds x 3 series from the 2015 index floor into an immutable, hashed, versioned archive. The perishable weekly predict+odds capture (E1) never pauses for the rebuild; scoring and the market benchmark are re-homed as Gold consumers. Feature and causal-pace work run on Gold, still gated.
