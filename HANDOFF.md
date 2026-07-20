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
non-superspeedway, 0.447 on 2026 out-of-sample.

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
3. Record closing head-to-head matchup prices into the JSON's
   `book_prices.entries` block (manual read, or paste them in chat) — the **full
   board** of the chosen book's matchups, not a subset — then **commit AND push
   before the *scheduled* green flag.** The market spec's admissibility rule keys
   off the scheduled start (`start_time_utc` of the "Race" event); race 5618's
   prices were committed after the scheduled flag and were ruled inadmissible.
   Practically: capture ~45 min out, commit+push ~30 min out. No sportsbook
   scraping (DK/FanDuel ToS bar automated access); see
   `research/odds_source_evaluation.md`.
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
- **Calibration is model-quality, never edge, and never unlocks roadmap #5.**
  Calibration is model-vs-reality (free; a fair book breaks even by construction,
  so it yields zero profit signal and can never establish an edge); the
  closing-line benchmark is model-vs-market and remains the sole thing that can
  unlock roadmap #5. The market benchmark is **sovereign and gate-protected**:
  the model-book pivot (F20 — DEMOTE + tether) runs the diagnostic
  pricing/calibration thread as a **co-equal parallel thread**, never a
  replacement, and the benchmark's sovereignty is enforced mechanically, not by
  prose — three tether gates (`specs/tether_gates.md`, shipped M4, `GATES.md`
  gates 12–14) keep weekly odds capture alive, forbid any document from claiming
  calibration establishes an edge, and forbid roadmap #5 from ever being
  re-pointed at a calibration verdict. See `research/pivot_model_book_vetting.md`.

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
- **2026-07-19 (B4 done, a588563; 2017 confirmed in scope):** the 2017 index
  URL's aliasing quirk (§8d above) had been assumed to also mean 2017 was
  below the detailed-feed floor — untested, and wrong. A direct race_id probe
  recovered the real 2017 season for all 3 series: `weekend-feed`/`live-feed`
  exist (97/97 races each), `lap-times`/`live-pit-data`/`lap-notes`/
  `live-flag-data` genuinely don't (confirmed two-pass absent, matching the
  other years' pattern once actually tested). `warehouse.py` gained a general
  fallback (`_load_races_index_from_weekend_feed`) so `bronze.races_index`/
  `bronze.coverage` now carry 2017 like every other year — no separate
  code path, no special-casing needed downstream. Verified clean: full-archive
  `--verify` hash-checks pass (4,432/4,432), and all 97 recovered races were
  spot-checked structurally (non-empty results, parseable dates, exactly one
  finishing_position==1, no duplicate driver_ids) — 0 issues. The 41/33/23
  recovered races per series match the real 2017 schedule exactly (Clash,
  both Duels, All-Star Open + Race, Coca-Cola 600, etc., verified by name and
  date). **Owner decision (2026-07-19): 2017 is treated like any other bronze
  year going forward** — no exclusion, no special scope carve-out. `silver_build.py`
  (C1) needs no year-specific logic to pick this up: it already builds
  generically over `bronze.races_index`, which now includes 2017 natively.
  DATA_DICTIONARY §8b/8d/8e/8f, `plan/schedule.yml` updated.
- **(superseded below — see the later "Next single step") `C1` was next:**
  silver driver-race parity (Sonnet build session; the frozen C-gate, gates
  D1/gold). Carries B3's condition-2
  escalation forward — see C1's `status_note` in `plan/schedule.yml`. 2017 is
  in scope like every other year (see B4 above) and needs no special
  handling — `silver_build.py` reads `bronze.races_index` generically. C2
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
- **2026-07-19 (C1 done, PASS):** `silver_build.py` + `gate_silver.py` built;
  `warehouse.py` extended (`load_race_records()`, silver DuckDB views). Full
  build: 601 Cup/Xfinity/Truck races parsed `ok`, 22,463 driver_race rows.
  Gate vs. the 163-race anchor (`data/anchors/races_parsed_anchor_20260719.pkl`,
  sha `b41e697d2c0f…`): every field bit-identical except `fepace` (the sole
  `np.linalg.lstsq`-derived column), which differed at ULP scale on 162/163
  races — confirmed reproducible, confirmed isolated to `fepace`, confirmed a
  cross-environment numpy/BLAS/LAPACK artifact (not a parser bug, not a
  NASCAR data revision). Escalated mid-session; owner authorized a dated §4
  amendment exempting `fepace` via a documented tolerance (unused-in-
  production field; every other column unaffected). Gate: PASS (1 clean, 162
  PASS-with-note, 0 fail). `report/SILVER_REGRESSION.md` committed (full
  detail); `## RESULT — C-gate` + the AMENDMENT filled in the spec;
  `DATA_DICTIONARY.md` §9 added. Odds capture for race 5618 deferred to the
  owner (paste-when-ready, per HANDOFF's weekly protocol step 3) — prediction
  #1 itself was already sealed/pushed pre-race (E2).
- **2026-07-19 (D1 done, PASS):** `gold_build.py` + `gate_gold.py` built;
  `warehouse.py` extended with `gold.*` views. Gold feature bank
  (`gold.track_typology`, `gold.wf_features`, `gold.driver_form`,
  `gold.driver_type_form`) built per spec §5, scoped to `year >= 2022` per a
  dated amendment (silver covers 2020+, but `races_parsed.pkl` never did —
  confirmed 72 pre-2022 Cup/points/`ok` races with ~90–97% driver overlap
  into early 2022, which would have broken the D-gate's "identical `n_hist`"
  check for a data-window reason, not a plumbing one; flagged and
  owner-authorized *before* any gold code was written). D-gate (§6) ran
  R0→R1→R2→R3, all PASS with zero mismatches anywhere: R1 showed zero
  `rho_PL_fpts` deltas vs R0 across all 163 scored races (not just zero
  *unexpected* ones); R2 compared 5,316 eligible (race, driver) pairs with
  zero mismatches; R3 showed zero rank/near-tie/rho exceptions. R0's first
  run also surfaced a second dated finding: the published 2026-OOS figure
  (0.449) traces to a 5-feature model variant (`prior_all`, includes the
  non-production `fepace` column) rather than the frozen 4-feature `fpts`
  model — exactly the ambiguity spec §9's A1 had pre-flagged. Confirmed via
  a diagnostic across all of `step4_models.py`'s `SPECS` variants;
  owner-authorized correction to **0.447** for the actually-frozen model
  (HANDOFF's frozen config is unchanged — this corrects a mispublished
  number, not the model). Both findings are dated amendments in the spec
  (§5, before 5.3; §6, before `## RESULT — D-gate`), full detail in
  `report/GOLD_REPROOF.md` and `DATA_DICTIONARY.md` §10. **New citations of
  the 2026 out-of-sample figure for the model actually in production should
  use 0.447, not 0.449** (the header block above and README predated this
  finding; that documentation cleanup was completed in the 2026-07-19 overnight
  consolidation — it was never a gate blocker).
- **2026-07-19 (D2 done, code+dual-run PASS; race-5618 scoring pending on
  NASCAR):** `score_race.py`/`test_score_race.py` (all 10 frozen fixtures
  pass), `market_benchmark.py`, the §5.5 bronze→legacy-cache shim
  (`bronze_fetch.py --sync-legacy-cache`), and the `gold.scores`/
  `gold.predictions` read-only views are built exactly per the frozen specs.
  §7.3 step 2's dual-run identity check ran for real against race 5618 (via
  a new dry-run-only `gold_predict_dryrun.py`, `predict_next.py` untouched)
  and **PASSED**: the gold path's freshly generated payload is dict-identical
  to the legacy path's already-published one after stripping
  `generated_utc`/`sha256_of_payload`. Actually scoring race 5618 was
  attempted and correctly refused — as of this session NASCAR had not yet
  posted results, ~3h past the scheduled 23:00 UTC green flag; `score_race.py`
  exited nonzero per the frozen refusal rule, `scores_log.csv` untouched.
  **Finding:** race 5618's 3 recorded book prices were committed 27 min after
  the *scheduled* green flag (real green flag was delayed further), making
  them inadmissible for the market-benchmark statistic per the provenance
  amendment — not a bug, still fully valid for `score_race.py`'s descriptive
  counts. Full detail: `specs/medallion_architecture.md` `## RESULT — D2`,
  `DATA_DICTIONARY.md` §11. Cutover step 4 (re-pointing `predict_next.py`) is
  explicitly NOT done — owner-gated, needs two clean weekly cycles per §7.3
  step 5.
- **2026-07-19 (F16 done):** domain-knowledge scan committed
  (`research/domain_knowledge_scan.md`) — the complement to F6: what the
  sport itself knows that the feature set ignores, admitted as hypotheses
  with credibility discounting, kept only where a measurable
  walk-forward-safe proxy exists in held data. Verified the in-feed
  inventory directly against bronze/silver: crew_chief 100% populated
  2022+ (the model's exact era; 185 within-season changes 2022–2025, 75
  interim/suspension-pattern), points_position confirmed post-race
  official standings 2017+, owner_id survives the SHR→Haas Factory rename
  that team_name breaks (F2 input) — while pit_box (13/392 races),
  winnings/purse/attendance (all-zero), points_delta (dead 2023+), and
  infractions/pit_reports (2020–2022 relics) are verified dead or
  era-limited. Externally confirmed (and cross-checked in our own feed:
  playoff_points_earned = 0 all 2026) that NASCAR's 2026 Chase format
  abolished playoff points and win-and-in — a format-era break flagged to
  F9 that also breaks the backtest transfer of any bubble-desperation
  feature. Proposals folded into the plan: C4 (silver breadth extension
  #2: caution_segments 2017+/stage_results/race_leaders/playoff_round),
  F18 (personnel-change A/B, gated), F19 (incentive-state analytics,
  Tier A), plus F3/F9 tightenings. Proposes only — no model code, no
  frozen spec touched.
- **2026-07-20 (E1 / forward-test #1 SCORED — race 5618):** North Wilkesboro
  (SHORT, 2026-07-19) scored per the frozen `specs/scoring_methodology.md` via
  the D2 medallion path (`bronze_fetch.py --update` → `--sync-legacy-cache 5618`
  → `score_race.py 5618`). **rho=0.5458** (n=37 common set), h2h_acc=0.6877 over
  666 pairs, book_n=3 / book_agree_n=3 / model_beats_book_n=0 on the 3 recorded
  DraftKings matchups. Hash seal verified (pristine `book_prices` restore matched
  the sealed sha256); results snapshot frozen to `_wf_scored.json` per the
  results-finality amendment. The 3 book prices carry the `post-race price entry`
  note — first committed 23:26 UTC vs the 23:00 scheduled green flag — so they are
  **inadmissible for the market-benchmark statistic** (that spec's §2), though
  fully valid for `score_race.py`'s descriptive counts; the market benchmark
  therefore still has **0 admissible priced races**. `predictions/scores_log.csv`
  created with its first row. All 8 gates green before and after — scoring touches
  no gated surface (the anchor pkl and gold views are unchanged; bronze/silver are
  gitignored foundation).
- **2026-07-20 (L5 done — odds-source research + book decision):** produced
  `research/odds_source_evaluation.md` (evidence ledger + recommendation;
  propose-only, hit no odds endpoint, no spec/model touched). **Reframing:** race
  5618's inadmissibility was a **workflow** failure (book prices committed 26 min
  after the *scheduled* green), not a source failure — any source is admissible if
  the entry is committed **and pushed before the scheduled green flag**. **ToS:**
  DraftKings/FanDuel terms **explicitly** bar automated scraping "for any purpose"
  (cease-and-desist + account termination) — so the DK unofficial JSON and any
  Apify DK scraper both violate them; the conservative posture (mirroring A6)
  resolves the odds side by *not scraping*. Clean, non-scrape licensed routes exist
  for NASCAR H2H (SportsDataIO — matchups + closing lines sourced from FanDuel;
  SportsGameOdds — free tier / $99, H2H depth to confirm on trial); The Odds API
  still has **no** NASCAR. **Owner decision (2026-07-20):** DEFER the permanent
  primary-book binding until L2's free-trial probe; do admissible **manual** capture
  on the fixed early-commit workflow meanwhile; **no sportsbook scraping.** Plan:
  L5 → done, **L2 → next**.
- **2026-07-20 (L2 step-1 partial probe + owner request for a deeper spike):** ran
  a free-trial probe (no sportsbook hit) and found real walls. SportsDataIO: its
  docs page embeds real endpoint/schema data server-side even though the rendered
  page is a loading shell — recovered it directly and confirmed `BettingMarketTypeID
  3 = "Head To Head Prop"` is a genuine, actively-defined NASCAR market type,
  present in real historical production rows (2 of 9 populated 2026 events). But the
  free trial itself can't confirm current depth/latency: only 9 of 99 2026 events
  have any market data at all, all frozen since 2026-04-16 (nothing for recent or
  upcoming races), and every identifying field (market/bet type, driver name,
  sportsbook name) is the literal string `"Scrambled"` with odds always empty.
  SportsGameOdds: no key obtained; its own reference docs and cheat sheet return
  real content but never mention NASCAR/motorsport/leagueID anywhere — a real
  negative signal. Cross-project check (read-only, `~/Downloads/nflverseanalytics`):
  that project's NFL odds vendor (The Odds API) is confirmed to have zero NASCAR
  coverage at any tier, and is itself on a free tier with an adjudicated
  ~$150/season upgrade trigger — no vendor consolidation possible there, but
  SportsDataIO prices its full commercial access as one quote across all 13 sports
  including NFL, so a future sales call should ask for an NFL+NASCAR bundle price.
  Full write-up: `research/odds_source_evaluation.md` section 8 (commits `6f3cf9a`,
  `a82b7ad`). **Owner asked for a much more in-depth spike** rather than continuing
  piecemeal, and to explicitly cover historical vs. ongoing pricing with a
  cost-conscious (hobby-project) lens. Plan updated: **L6** (new, comprehensive
  vendor-research spike, Opus 4.8 · thinking on · xhigh) is now `next`; **L2**
  demoted to `blocked`, reduced to "build the fetcher" once L6 recommends and the
  owner gives GO. All 10 gates re-verified green after the plan edit.
- **2026-07-20 (L6 done — odds-vendor spike; owner opened a strategic pivot):**
  `research/odds_source_evaluation.md` §9 landed (comprehensive vendor spike + a ranked
  ledger; propose-only, no endpoint hit, no spec/model touched). **Finding:** no vendor is
  simultaneously hobby-affordable + real-time-admissible + confirmed-NASCAR + public-repo-
  ToS-clean — every candidate fails ≥1 axis (SportsGameOdds & OddsPapi owner-verified
  NASCAR-free; SportsDataIO's only affordable tier is next-day-delayed = inadmissible, its
  live tier ~$16.5k/yr; OpticOdds=OddsJam ~$5k/mo; OddsMatrix/Sportradar enterprise-only).
  **Standing recommendation: STAY MANUAL** — admissibility is owned by the T-45
  commit-and-push workflow, not the source; per-race H2H depth was pinned ~12–15/book at
  close (higher than the spec's 5–10 assumption), so the benchmark can still reach an
  adequately-powered verdict. **Mid-session the owner opened a strategic pivot:** shift the
  project's center of gravity from the beat-the-line market benchmark toward the project's
  own multi-market **model book** — simulation-priced fair odds across all bet types,
  self-graded by a walk-forward **calibration backtest** on the existing 163 races (needs no
  book odds), with PL (frozen baseline) + Bayesian-PL (F10) as a gated A/B and Monte-Carlo as
  the pricing layer. Calibration (model-vs-reality, free) ≠ edge (model-vs-market, needs real
  prices, gates roadmap #5). Deferred to **F20**, an adversarial design-vetting session
  (Opus 4.8 · thinking on · xhigh) that decides whether the beat-the-line benchmark **stays,
  demotes, or drops**. L2 stays blocked pending F20's re-sequencing. No purchase, no binding,
  no build.
- **2026-07-20 (F20 done — model-book pivot vetted; fork = DEMOTE + tether):**
  `research/pivot_model_book_vetting.md` landed (deep read of the frozen specs +
  audit + F7 + L5/L6 + **6 independent adversarial refutation passes**). The naive
  pivot framing was **refuted** on four load-bearing claims (self-graded
  calibration is a fast+free benchmark substitute; coherent ⇒ trustworthy; honest
  fair odds you can bet; price all bet types); a reshaped, rescoped thread
  survives. **Owner decision (memo §8): DEMOTE + tether** — build the reshaped
  calibration/pricing thread as a co-equal near-term focus; the market benchmark
  stays the **sole external check and sole roadmap-#5 gate**; three mechanical
  tether gates ship in the same beat that demotes. DROP rejected; STAY was the
  conservative alternative.
- **2026-07-20 (M1 done — pivot pre-registered):** three NEW pre-registration
  specs authored (no pricing/production code, no frozen-spec edit — they are new
  files, not amendments): `specs/pricing_layer.md` (a **diagnostic** order-derived
  Monte-Carlo readout — analytic-where-exact, coherence = internal-consistency
  only [**not** correctness], pinned determinism + committed fixture, a
  faithful-read gate proving it changes nothing frozen); `specs/calibration_backtest.md`
  (ONE locked primary decision cell = H2H Brier skill score vs an as-of
  Bradley–Terry marginal baseline, pooled non-SS, **forward stream only**; the
  163-race backtest is an in-sample dev smoke test barred from any decision and
  from fitting any recalibration map; 2026 = peeked secondary; dual pooled+per-type
  reporting with a pooling-launder ban; power triage; the C-trigger split — non-SS
  tail arms F7-C T1, SS confirms stand-down); `specs/tether_gates.md` (the three
  tether gates M4 builds). Plan re-sequenced onto **phase M (M1–M5)**; F10 re-homed
  as pivot step 2; F20 → done; L2 moot. All gates green before + after.
- **2026-07-20 (M2 done — diagnostic pricer built):** `src/pricing_layer.py`
  (analytic win/H2H/group-best-of/manufacturer softmax + one pinned Gumbel block
  for top-N/joint/group-count; add-half + eps floors; MC-reliability
  exclude-or-raise-N; fair American odds), `src/fixtures/pricing_fixture.json`
  (two committed sub-fixtures: race 5618's real 37-driver vector, and a synthetic
  5-driver toy field exercising manufacturer/group/set/SS-flag/tail-flag paths;
  numpy 2.1.3 / scipy 1.15.3 / python 3.13.5 recorded), `src/gate_pricing.py`
  (section-4 coherence + section-5.4 fixture reprove [bit-exact] + section-6
  faithful-read [1,443 marginals vs race 5618's JSON, all within tolerance]),
  and `src/capture_template.py` (section 7). Wired into `run_gates.sh`/`GATES.md`
  as the repo's **11th gate**; confirmed red on an injected doubled-utility defect
  (6,000+ mismatches). Zero design-judgment escalations needed — three mechanical
  resolutions recorded in the spec's RESULT block (§4 point 3 read as
  floating-point-exact not bit-exact; `mfr_bestof`'s manufacturer set taken as
  exactly the caller's `manufacturer_of` keys; `topN_joint`/`group_topN_count`
  emit the full count pmf since the pinned signature has no explicit `m`). No
  change to `predict_next.py` / `walkforward.py`; H2H pick rule (ITT continuity)
  untouched. All 11 gates green before (10/10, inherited) and after. Full detail:
  `specs/pricing_layer.md` `## RESULT — pricing layer`.
- **2026-07-20 (M3 done — calibration backtest run):** `src/calibration_backtest.py`
  built and run per `specs/calibration_backtest.md` section 10. Baseline
  replication **PASS** (0.413/0.476/0.447, exact, against the frozen anchor
  `gate_gold.py`'s R0 uses). Primary decision (section 3): forward stream =
  race 5618 only, **K=1 non-SS forward race, N=666 H2H pairs**, point BSS=0.0010
  (degenerate bootstrap bounds at K=1) — **VERDICT: UNDERPOWERED**, exactly the
  pre-registered outcome at N=1 per the terminal-only amendment (K≥60 needed to
  declare CALIBRATED-SKILL/NULL). Sealed secondary family (S1–S6) computed and
  reported, non-citable, no action taken (gated on a terminal CALIBRATED-SKILL
  primary, not reached). IN-SAMPLE dev smoke test (128 races, 2022–2026) and the
  2026-OOS peeked cut (20 races) both show a positive, small pooled non-SS H2H
  BSS (0.0307 and 0.0528 respectively) with SS near-zero/negative as expected
  (confirms stand-down, not a C-trigger), and a consistent underconfidence
  reliability signature (fitted slope>1, intercept<0) matching the audit's known
  finding at every non-SS cut. F7-C trigger T1: **NOT ARMED** (N=1 forward race
  cannot establish a "documented finding"). A genuine sign bug was caught and
  fixed mid-build: `walkforward.run`'s `collect_preds` utility is fit on `-X`
  (higher u = worse finish, the opposite of `pricing_layer`'s "higher=better"
  convention) — confirmed empirically and negated before pricing IN-SAMPLE/2026
  races; the FORWARD stream was unaffected (reads the JSON's own already-correct
  `utility` field). Full detail: `report/CALIBRATION_BACKTEST.md`,
  `## RESULT — calibration backtest` in the spec. No frozen-spec edit; no change
  to `predict_next.py`/`walkforward.py`/`scores_log.csv`. Gate surface 11/11
  green before and after (M3 has no gate obligation of its own).
- **Next single step (plan `next` = M4):** ship the 3 tether gates + formalize
  the demote, per `specs/tether_gates.md` (**Sonnet 5 · thinking on · high**).
  This is the natural continuation of the M1→M2→M3 pivot chain and was already
  co-startable off M1; M3's UNDERPOWERED (as pre-registered) result does not
  block it. The verbatim kickoff is in `plan/schedule.yml` (session M4) and
  rendered in `PLAN.md`. Independently, the standing weekly loop (E1) fires at
  the next Cup race — predict / seal / push before the green flag, record
  closing prices **before the scheduled flag** (5618's were post-flag →
  inadmissible), then score after results post. The D2 cutover still needs a
  **second** scored, *admissibly-priced* race before its two-clean-cycle bar can
  be assessed. The calibration backtest (M3) should be re-run periodically as
  the forward stream accrues non-SS races toward K≥20 (interim, no decision
  weight) and K≥60 (terminal, decision-grade) — no new session is required to
  re-run it, just `python3 calibration_backtest.py` from `src/`.

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
GATES.md            the 8-gate health surface + interpreter split;
                    run `src/run_gates.sh` to prove all 8 green in one command
DATA_DICTIONARY.md  human-readable field reference (parsed store, prediction
                    JSON, CSV contracts, raw cf.nascar.com feeds)
src/                pipeline: download.py, parse_lib.py, parse.py,
                    update_data.py, predict_next.py, walkforward.py (engine),
                    report_plan.py (plan renderer), step2/3/4/6 (audit analyses)
                    -- medallion rebuild: bronze_fetch.py (ingestion,
                    --full/--update/--verify/--sync-legacy-cache), warehouse.py
                    (duckdb catalog: bronze/silver/gold schemas + gold.scores/
                    gold.predictions read-only views), bronze_report.py
                    (coverage matrix), silver_build.py + gate_silver.py (C1/C2),
                    gold_build.py + gate_gold.py (D1) -- score_race.py +
                    test_score_race.py + market_benchmark.py (D2, frozen specs,
                    verbatim) -- gold_predict_dryrun.py (D2, dry-run only:
                    section 7.3 dual-run proof; NOT the cutover, predict_next.py
                    is untouched and still the path of record)
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
