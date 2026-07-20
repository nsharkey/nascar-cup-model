# Overnight health-hardening — 2026-07-20

**Session type:** consolidation / health-hardening (NOT feature velocity — no backlog
advanced, no model change, no frozen spec touched).
**Model:** Opus 4.8 (1M), thinking on.
**Working tree at start:** clean, `main` @ `e57c388`. **At end:** clean, `main` @ `774b0c2`
(5 new local commits, **none pushed** — owner controls publishing this public repo).

---

## TL;DR

- **All 10 gates green, start and end.** (The surface grew 8 → 10 this session.) The
  medallion foundation still reproduces the validated model (D-gate trio
  **0.413 / 0.476 / 0.447**). Nothing was red at any point.
- **The forward test scored its first race.** Race 5618 (North Wilkesboro) posted results
  overnight; scored per the frozen spec: **rho = 0.5458** (n=37), h2h_acc 0.6877 over 666
  pairs, book 3/3 agree. The 3 book prices are provenance-**inadmissible** for the market
  benchmark (recorded post-green-flag) but valid for descriptive counts — market benchmark
  still has **0 admissible priced races**.
- **The gate surface is now one command.** `src/run_gates.sh` runs all 10 gates with the
  right interpreter/CWD and a pass/fail summary; `GATES.md` documents the two-interpreter
  split that was previously tribal knowledge.
- **The read-only-verification-dirties-the-tree wart is fixed.** `gate_silver.py` now writes
  its report only under `--write`; a bare run leaves the tree clean.
- **Three more prose-only claims are gates** (stand-down list; bronze/silver invariants),
  each verified to go red on drift.
- **Nothing frozen/immutable touched:** no model code, no frozen spec section, no
  `research/track_audit/` package, no rendered plan file. `walkforward.py`, the HANDOFF
  frozen block, and `predict_next.py` were only *read*.

---

## 1. Gates — baseline and final (both all-green)

Interpreters: `.venv` python 3.14.6 (PyYAML) for the plan gate; Anaconda python 3.13.5
(duckdb/numpy/scipy/pyarrow) for the other 9, run from `src/`. Both sweeps via the new
`src/run_gates.sh` for the final; the baseline was run gate-by-gate before the harness existed.

| Gate | Interp | Baseline | Final |
|------|--------|----------|-------|
| `test_report_plan.py` | .venv | **PASS** | **PASS** |
| `test_track_audit.py` | conda | **PASS** | **PASS** |
| `test_score_race.py` | conda | **PASS** | **PASS** |
| `gate_silver.py` (C-gate) | conda | **PASS** (163 anchor: 1 clean, 162 pass-with-note, 0 fail) | **PASS** |
| `gate_gold.py` (D-gate) | conda | **PASS** (R0→R3, trio 0.413/0.476/0.447, 0 mismatches) | **PASS** |
| `gate_track_reference.py` | conda | **PASS** | **PASS** |
| `test_frozen_config.py` | conda | **PASS** | **PASS** |
| `test_readme_numbers.py` | conda | **PASS** | **PASS** |
| `test_stand_down.py` **(new)** | conda | — | **PASS** |
| `test_medallion_invariants.py` **(new)** | conda | — | **PASS** |

The final `run_gates.sh` run left the working tree **clean** — the gate_silver wart is gone.

---

## 2. Commits (local only, not pushed)

| SHA | One-liner | What / why |
|-----|-----------|------------|
| `e8725cf` | score: North Wilkesboro 2026-07-19 rho=0.5458 | Forward-test point #1. Scored race 5618 per the frozen `scoring_methodology.md` via the D2 path (`bronze_fetch.py --update` → `--sync-legacy-cache 5618` → `score_race.py 5618`). Hash seal verified; snapshot frozen; `post-race price entry` note auto-applied. `scores_log.csv` created; HANDOFF status updated. |
| `3c3c1a2` | build: one-command gate harness + GATES.md | `src/run_gates.sh` (all 10 gates, correct interp/CWD, summary table, exit 0/1/2, interpreter preflight). `GATES.md` documents the two-interpreter split + the 10-gate table. Verified all-green + FAIL/preflight paths self-tested. |
| `742587c` | fix: gate_silver report write behind --write | Read-only C-gate run no longer rewrites `report/SILVER_REGRESSION.md` (the tree-dirtying wart). Only the CLI wrapper + docstring changed; frozen §4 verdict/tolerance logic untouched. Verified twice-clean + `--write` still regenerates. |
| `120cd32` | test: encode 3 prose-only claims as gates | `test_stand_down.py` (doctrine SS list ⟷ `walkforward.MY_TYPE` ⟷ `predict_next` flag) and `test_medallion_invariants.py` (bronze failed=0; silver one-winner + no-dup-driver, self-validating). Both PASS + verified red-on-drift. |
| `774b0c2` | docs: DATA_DICTIONARY §5 — score_race.py is built | Dropped the stale "(to-be-built)" qualifier (§11 already documents it as built; this session used it). The only unambiguous doc drift found. |

Each commit carries its green-gate evidence and the standard co-author trailer; one logical change per commit.

---

## 3. Forward-test result #1 — race 5618 (the substantive outcome)

`predictions/scores_log.csv` (first row):

```
race_id,date,track,ttype,n,rho,h2h_acc,h2h_n,book_n,book_agree_n,model_beats_book_n,notes
5618,2026-07-19,North Wilkesboro Speedway,SHORT,37,0.5458,0.6877,666,3,3,0,post-race price entry
```

- **rho = 0.5458** on a SHORT track — above the 0.476 non-SS backtest and the 0.413 overall.
  One race is not a trend; this is a single, noisy data point, logged per doctrine.
- **h2h_acc = 0.6877** (666 graded pairs) — comparable region to the backtest's 0.652 pairwise.
- **Book: 3/3 agree, 0 model-beats-book.** All three recorded DraftKings matchups had the
  model and book on the same side; no disagreements to adjudicate.
- **Provenance:** the 3 prices were first committed 23:26 UTC vs the 23:00 scheduled green
  flag → the scorer auto-flagged `post-race price entry`. They are **inadmissible for the
  market-benchmark statistic** (per that spec's §2) but fully valid for the descriptive
  counts above. **The market benchmark still has 0 admissible priced races.**
- Hash seal verified (pristine `book_prices` restore matched the sealed sha256); results
  snapshot frozen to `data/races/2026_5618_wf_scored.json` (gitignored); scoring is idempotent.
- Doctrine honored: `update_data.py` detected the posted result; nothing was forced,
  fabricated, or hand-constructed; `predict_next` was never run on the completed race.

---

## 4. What was deliberately NOT done (guardrails honored)

- **No model change.** `walkforward.py` production config, `predict_next.py`, and the HANDOFF
  frozen block were read-only — asserted against, never edited.
- **No frozen spec section, no `research/track_audit/` package** touched.
- **No rendered plan file hand-edited.** `PLAN.md` / `plan/PLAN.html` / `plan/schedule.yml`
  untouched; E1 remains the single `next`; the plan drift gate still passes. (A stale plan
  *narrative* line is queued below, not edited — see §5.)
- **Race 5618 not forced.** It genuinely posted results; scored strictly per the frozen spec.
- **Doc sweep stayed surgical.** One unambiguous fix (§5 "to-be-built"). Bronze/silver counts
  are dated B2/C1 snapshots (left intact); the HANDOFF D2 "scoring pending" clause is a
  historical changelog line already superseded by the new 2026-07-20 scored entry (append-only,
  matching the owner's stated preference from the last session).

---

## 5. Forks that need YOUR judgment (queued — I did not decide these)

### 5a. Pre-existing owner-escalation items — carried forward untouched

1. **Legacy-cache SHA baseline for silver §4.3 (from B3/C1).** The legacy per-race JSON cache
   (`src/data/races/`) that `races_parsed.pkl` was built from does not exist in this checkout
   (gitignored, never persisted). The C-gate passes because every anchor race's only deviation
   is `fepace` (tolerance amendment), so §4.3's mismatch-attribution never had to run in
   isolation — **but it remains open for any future *non-fepace* mismatch on a silver rebuild**,
   which would have no baseline to attribute against. Decision you own: recover/rebuild a legacy
   cache, or bless an owner-directed fallback attribution method, before the next silver rebuild
   that could surface one. *(Unchanged tonight.)*

2. **A6 — NASCAR NDM ToS review (`plan/schedule.yml` A6, `pending`, owner-led).** Governance/legal
   posture, not code: the July-2025 NASCAR terms have real scraping/model-building clauses, but
   their coverage of the `cf.nascar.com` JSON feeds this project uses is textually unsupported
   (feed carries no ToS link, no bot-block, absent from the covered-services list). Gates the
   DK-odds-capture route and F15. Only you can set and record the posture. *(Unchanged tonight.)*

### 5b. New this session

3. **Plan meta-narrative is stale on race 5618.** `plan/schedule.yml`'s `bottom_line` and
   `handoff_note` still say "score race 5618 once NASCAR posts results" as the pending
   calendar-gated step — but it's now scored. I did **not** edit it: updating the living plan's
   narrative during a consolidation beat is judgment-adjacent (plan-caution guardrail; touches
   rendered files + `shape_sig`), so per "conservative action" I queued it. Recommended fix (next
   session, correct mechanism): edit `schedule.yml`'s `bottom_line`/`handoff_note` to note 5618 is
   scored (rho=0.5458, book prices inadmissible), keep **E1 as the single `next`**, then
   `python src/report_plan.py` to re-render and confirm `test_report_plan` passes.

4. **Whether to surface the first forward-test rho on the public README.** README's "The forward
   test" section describes the mechanism but not the (now-existing) first result. Adding rho=0.5458
   is a public-facing judgment call about presenting a single, noisy, book-inadmissible data point —
   doctrine says one race is not a conclusion. Left to you. (HANDOFF's private status already records it.)

5. **The D2 §7.3 dual-run identity check could not be encoded as a standing gate tonight.**
   Now that race 5618 is complete, both `predict_next.py` and `gold_predict_dryrun.py` correctly
   refuse to run on it (no-post-hoc doctrine), so there is nothing to dual-run. To make it a
   standing gate it must either run against the **next** race *before* its green flag, or be
   refactored to replay frozen inputs. Logged, not forced.

---

## 6. Health state → next beat

The health surface is now materially stronger than at session start: **10 gates behind one
command**, the interpreter split documented, and the last read-only-dirties-the-tree wart closed.
The consolidation backlog from the previous report is essentially discharged — what remains
(§5) is owner-judgment, not consolidation work.

**The plan's actual `next` is E1 (the standing weekly loop).** With race 5618 now scored, the
next actionable is the **next Cup race's weekly cycle** — and it is calendar-gated on that race,
not an overnight task. One process lesson banked for it: **record the closing book prices *before*
the green flag** next time (5618's were captured post-flag, which cost them market-benchmark
admissibility).

---

## 7. Next-session handoff

**Next step:** E1 weekly cycle at the next Cup race (calendar-gated — do it once qualifying posts
for that race). **Model & settings:** Sonnet 5, thinking on, effort high — this is well-specified,
test-guarded work (the frozen weekly protocol + the tested `score_race.py`); escalate to Opus 4.8
xhigh only if a scoring edge case (DQ, withdrawal, tie, or a book-price provenance question) arises.

Paste-able kickoff prompt:

```
Weekly forward-test cycle for the NASCAR Cup model. Read HANDOFF.md (esp. the
"Weekly protocol" and "Doctrine" sections) and report/OVERNIGHT_2026-07-20.md first.
Confirm the tree is clean and the medallion foundation is present locally. Interpreters:
.venv/bin/python (plan gate); Anaconda `python` from src/ (everything else). Prove all
10 gates green first with `src/run_gates.sh`; if any is red, STOP and report.

This week, in order:
1. After qualifying posts for the next Cup race: `cd src && python update_data.py`
   then `python predict_next.py`. It writes the prediction to predictions/ and refuses
   to run once results exist.
2. Commit and PUSH the prediction BEFORE the green flag — the public timestamp is the point.
3. Record the closing book head-to-head prices into the prediction JSON's book_prices
   block *before* the flag (last week's were captured post-flag and were ruled inadmissible
   for the market benchmark). Commit.
4. After the race posts results: `python update_data.py` → `python bronze_fetch.py --update`
   → `python bronze_fetch.py --sync-legacy-cache <race_id>` → `python score_race.py <race_id>`,
   following specs/scoring_methodology.md EXACTLY. Append scores_log.csv, update HANDOFF
   status, commit `score: <track> <date> rho=<x.xxxx>`. Never force/fabricate a result;
   never run predict_next on a completed race; superspeedways are logged stand-downs.
5. Re-run src/run_gates.sh (all green) before finishing. Do NOT push scoring commits without
   the owner unless it's the pre-race prediction seal in step 2.

Guardrails: frozen walkforward.py config, frozen spec sections, research/track_audit/ are
DO-NOT-TOUCH. Never hand-edit PLAN.md/plan/PLAN.html — regenerate via src/report_plan.py
from plan/schedule.yml; keep exactly one `next`. One logical change per commit with
green-gate evidence + the standard co-author trailer.
```

*This session ran on Opus 4.8 (judgment tier), appropriate for the consolidation + the
scoring edge-case sensitivity. The routine weekly cycle above does not need Opus.*

---

## 8. Push command for the morning

Nothing is pushed. When you're ready to publish tonight's five commits:

```bash
cd /Users/nicholassharkey/Downloads/nascar-cup-model && git push origin main
```

That publishes `e8725cf`, `3c3c1a2`, `742587c`, `120cd32`, `774b0c2` (score 5618 + gate
harness + gate_silver determinism + 2 new gates + one doc fix). All 10 gates are green and
the tree is clean. `git push origin main` sends the whole branch, so it also publishes the
addendum commits in §9 below.

---

## 9. Addendum — commits made after this report was drafted (Task 7)

Two more local commits landed during the optional prospect step, after §2 was written:

| SHA | One-liner | What / why |
|-----|-----------|------------|
| `f543b37` | docs: run_gates.sh header says 10 gates | Doc-currency: the `run_gates.sh` top comment still said "Runs all 8 repository gates" after `120cd32` grew the registry to 10 (surfaced by the prospect code-health scan; my own session's drift). Cosmetic comment only — the "ALL N GATES GREEN" line derives from the array length. `bash -n` clean. |
| `270aee8` | prospect: ranked next-steps spread for the morning | Optional Task 7. Read-only `/prospect` (Opus 4.8, top judgment tier) → `report/prospect_2026_07_20.md`: 11 ranked spikes (3 transformational, 3 high, 3 moderate, 2 marginal) with paste-ready kickoff prompts. Proposes only; `plan/schedule.yml` untouched. |

**Prospect headline (for the morning):** the ranking's dominant theme is that the entire
forward-looking backlog is bottlenecked on **N=0 admissible priced races** — so the top items all
either grow that sample faster (extend to Xfinity/Trucks; automate the weekly loop; the L5 book
decision) or protect it (a pre-green admissibility self-check to prevent another 5618-style void; and
fixture-testing the untested `market_benchmark.py` that will decide EDGE/NO-EDGE). Full detail +
copy-paste prompts in `report/prospect_2026_07_20.md`; reply with item numbers to get a sprint schedule.

The final full `src/run_gates.sh` after all commits: **all 10 green, tree clean.** `git push origin
main` publishes all eight of tonight's commits (`e8725cf` … `270aee8`) plus this report update.
