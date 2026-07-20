# Overnight consolidation & health-hardening — 2026-07-19

**Session type:** consolidation / health-hardening (NOT feature velocity — no backlog
advanced, no new features, no model change).
**Model:** Opus 4.8 (1M), thinking on.
**Working tree at start:** clean, `main` @ `ddfc31c`. **At end:** clean, `main` @ `4a3b5c3`
(3 new local commits, **none pushed** — owner controls publishing this public repo).

---

## TL;DR

- **All gates green, start and end.** The medallion foundation reproduces the validated
  model (D-gate trio **0.413 / 0.476 / 0.447**). Nothing was red at any point.
- **Documentation currency:** reconciled the 2026 out-of-sample figure to the production
  model's **0.447** in README + the HANDOFF header (with provenance), leaving all
  historical/published-record **0.449** citations intact by design.
- **Two prose-only claims are now gates:** the frozen production config, and README's
  headline backtest numbers. Both pass and both were verified to go red on drift.
- **Nothing frozen or immutable was touched.** No model code, no frozen spec section, no
  `research/track_audit/` package, no rendered plan file.
- **Forks queued for you** (details below): two pre-existing owner-escalation items carried
  forward untouched (legacy-cache SHA baseline; A6 ToS review), plus two low-risk edits I
  made that touch judgment-adjacent surfaces and want your eyes (a public README footnote;
  a one-clause edit to a dated HANDOFF status entry), plus one health wart worth fixing next.

---

## 1. Gates — honest baseline (final sweep, 2026-07-19 23:41)

Ran twice: once at the start (step 1, run-only) and once at the end after all changes. Every
gate green both times. Interpreters: `.venv` python 3.14.6 for the plan gate (PyYAML);
Anaconda python 3.13.5 (duckdb/numpy/scipy/pyarrow) for everything else. Medallion gates run
from `src/`.

| Gate | Interp | Result |
|------|--------|--------|
| `test_report_plan.py` | .venv | **PASS** — schema/cardinality/renders/shape (50 sessions, 9 phases) |
| `test_track_audit.py` | conda | **PASS** — manifest hashes, 43 configs, 193 edges, 163/163 crosswalked |
| `test_score_race.py` | conda | **PASS** — all fixtures F1–F10 |
| `gate_silver.py` (C-gate) | conda | **PASS** — 163 anchor races: 1 clean, 162 pass-with-note (fepace ULP), 0 fail |
| `gate_gold.py` (D-gate) | conda | **PASS** — R0→R1→R2→R3, trio **0.413/0.476/0.447**, 0 mismatches |
| `gate_track_reference.py` | conda | **PASS** — track_dim 43, xwalk 44, priors 430, sim 193, rules_era 6 |
| `test_frozen_config.py` **(new)** | conda | **PASS** — live config == HANDOFF frozen block (20 checks) |
| `test_readme_numbers.py` **(new)** | conda | **PASS** — README trio == gate_gold EXPECTED_* (10 checks) |

Cross-environment note (extra confirmation, no action needed): the committed
`report/SILVER_REGRESSION.md` was generated under python 3.14.6 / numpy 2.5.1; the C-gate
**still passed** here under Anaconda 3.13.5 / numpy 2.1.3. That is additional evidence the
2026-07-19 fepace tolerance amendment holds across BLAS/LAPACK environments, exactly as its
mechanism predicts.

---

## 2. Commits made (local only, not pushed)

| SHA | One-liner | What / why |
|-----|-----------|------------|
| `114e419` | docs: reconcile 2026-OOS figure to production model's 0.447 | README table row + HANDOFF header cited **0.449** (the 5-feature `prior_all` variant), not the frozen 4-feature `fpts` model in production. Corrected both to **0.447** (what the D-gate computes for the frozen config); added a README provenance footnote → `report/GOLD_REPROOF.md`; updated D1's "pending cleanup" marker to reflect completion. Historical citations (audit report, PLAN/schedule.yml D-gate design narratives) left at 0.449. |
| `f981a43` | test: gate the frozen production config against HANDOFF | New `src/test_frozen_config.py`. Three-way tie: HANDOFF frozen block ⟷ `predict_next.py` live constants + logged config ⟷ `walkforward.pl_fit` default λ. Hermetic (all reads via `ast`; never executes predict_next, which does network I/O on import). PASS + red-on-drift verified. |
| `4a3b5c3` | test: gate README headline trio against gate_gold EXPECTED_* | New `src/test_readme_numbers.py`. Ties README's 0.413/0.476/0.447 to `gate_gold.py`'s `EXPECTED_BACKTEST/NONSS/OOS` — the constants the D-gate reproves against a live computation each run. Plus an explicit anti-regression check that the 2026-OOS row is 0.447, locking in `114e419`. PASS + red-on-drift verified. |

Each commit carries its green-gate evidence in the message and the standard co-author trailer.
One logical change per commit.

---

## 3. What was deliberately NOT done (guardrails honored)

- **No model change.** `walkforward.py` production config and `predict_next.py` read-only —
  only *asserted against*, never edited.
- **No frozen spec sections, no `research/track_audit/` package** touched.
- **No rendered plan file hand-edited.** `PLAN.md` / `plan/PLAN.html` untouched;
  `plan/schedule.yml` untouched; E1 remains the single `next`. The plan drift gate still passes.
- **Doc sweep stayed surgical.** Only production-model 0.449→0.447 citations changed; all
  historical/published-record 0.449 left intact per DATA_DICTIONARY §10e. All ~35 referenced
  file/dir paths in the HANDOFF & README maps verified to exist — no stale paths.
- **Race 5618 not forced.** `scores_log.csv` still absent (NASCAR has not posted results);
  HANDOFF's "Next single step" (score 5618) is therefore still current, not stale. No post-hoc
  prediction, no fabricated 5618 result.

---

## 4. Forks that need YOUR judgment (queued — I did not decide these)

### 4a. Pre-existing owner-escalation items — carried forward untouched

1. **Legacy-cache SHA baseline for silver §4.3 (from B3/C1).** The legacy per-race JSON cache
   (`src/data/races/`) that `races_parsed.pkl` was built from does not exist in this checkout
   (gitignored, never persisted). C1's C-gate passed anyway because every anchor race's only
   deviation was `fepace` (resolved by the tolerance amendment), so §4.3's mismatch-attribution
   never had to run in isolation — **but it remains genuinely open for any future *non-fepace*
   mismatch on a silver rebuild**, which would have no baseline to attribute against. Decision
   you own: recover/rebuild a legacy cache, or bless an owner-directed fallback attribution
   method, before the next silver rebuild that could surface one. *(Unchanged tonight.)*

2. **A6 — NASCAR NDM ToS review (`plan/schedule.yml` A6, status `pending`, owner-led).**
   Governance/legal posture, not code: the July-2025 NASCAR terms have real
   scraping/model-building clauses, but their coverage of the `cf.nascar.com` JSON feeds this
   project uses is textually unsupported (feed carries no ToS link, no bot-block, absent from
   the covered-services list). This gates the DK-odds-capture route and F15. Only you can set
   the posture and record it. *(Unchanged tonight.)*

### 4b. Two edits I made that touch judgment-adjacent surfaces — veto if you disagree

3. **Public README footnote (in `114e419`).** I added a short provenance footnote under the
   README headline table explaining 0.447 vs the earlier 0.449 (4-feature vs 5-feature,
   0.4473 vs 0.4487 rounding boundary), pointing at `report/GOLD_REPROOF.md`. Rationale: a
   public reader comparing README (now 0.447) to the linked audit report (still 0.449) would
   otherwise see an unexplained contradiction. It is public-facing prose on your public repo —
   glance and confirm you're happy with the wording, or tell me to trim it to just the number.

4. **One-clause edit to a *dated* HANDOFF status entry (in `114e419`).** The D1 entry's
   parenthetical said the header/README "predate this finding and are unchanged." After my fix
   that present-tense "unchanged" was false, so I changed it to note the cleanup "was completed
   in the 2026-07-19 overnight consolidation." This lightly edits a historical changelog line
   rather than strictly append-only. If you prefer append-only changelog semantics, say so and
   I'll revert the clause and add a fresh dated entry instead.

### 4c. Provenance calls — confidence level

The 0.447 reconciliation itself was **not** ambiguous: DATA_DICTIONARY §10e explicitly
earmarks "HANDOFF.md/README.md's own headline 0.449 citations" for exactly this documentation
cleanup and says new production-model citations "should use 0.447." I found no *ambiguous*
citation that needed queuing rather than editing. If any single call above reads differently
to you, it's trivially revertible.

---

## 5. Health observation → basis for the next beat

**A gate dirties the working tree just by running.** `gate_silver.py` rewrites
`report/SILVER_REGRESSION.md`'s environment block to whatever interpreter ran it (it flipped
to Anaconda's numpy 2.1.3 vs the committed 3.14.6/2.5.1 tonight). I reverted it both times to
keep the tree clean, but `git status` going dirty from a read-only verification is a
reproducibility wart. Combined with the **two-interpreter split** (undocumented which is
canonical) and the `cd src` CWD requirement, running the full gate surface is tribal knowledge.
That's the case for the next session.

---

## 6. Recommended next session (consolidation beat) + handoff

**Recommendation:** another consolidation/health beat — a **one-command gate harness +
reproducibility fixes**. Not feature velocity. Concretely:
(a) `run_gates.sh` (or `make gates`) that runs all 8 gates with the correct interpreter/CWD and
prints a pass/fail summary — turning tonight's manual baseline into a repeatable health check
and a CI seed;
(b) make `SILVER_REGRESSION.md`'s env block deterministic (or pin the canonical gate
interpreter) so a gate run no longer dirties the tree;
(c) encode 2–3 more prose-only claims as gates beyond tonight's cap (candidates: the
superspeedway stand-down track list Daytona/Talladega/Atlanta; the D2 §7.3 dual-run identity
check as a standing test).

The plan's actual `next` is **E1** (the standing weekly loop), but it is **calendar-gated on
race 5618 posting results** — a weekly-protocol action (`bronze_fetch.py --update` →
`--sync-legacy-cache 5618` → `score_race.py 5618`), not an overnight consolidation. Do E1 the
moment results post; the consolidation beat above is the right *overnight* fill otherwise.

**Model & settings for the consolidation beat:** Sonnet 5, thinking on, effort high — it's
well-specified, test-guarded build work (the implementation-engine tier), with only light
judgment (which interpreter is canonical, which claims to gate next). Escalate that one session
to effort xhigh only if the prose-gate selection turns thorny; no need for Opus.

Paste-able kickoff prompt for that session:

```
Consolidation/health beat for the NASCAR Cup model repo (NOT feature velocity — do
not advance the backlog). Read HANDOFF.md and report/OVERNIGHT_2026-07-19.md first.
Confirm the working tree is clean and the medallion foundation is present locally
(data/ bronze/silver/gold + nascar.duckdb, src/races_parsed.pkl). Interpreters:
.venv/bin/python (3.14.6, PyYAML) for the plan gate; Anaconda `python` (3.13.5,
duckdb/numpy/scipy) for the medallion gates, run from src/.

Do, in order, committing each safe gate-verified change locally (DO NOT PUSH):
1. Prove all 8 gates green as a baseline (test_report_plan, test_track_audit,
   test_score_race, gate_silver, gate_gold, gate_track_reference, test_frozen_config,
   test_readme_numbers). If any is red, STOP and report.
2. Build src/run_gates.sh: run all 8 with the correct interpreter+CWD, print a
   pass/fail summary table, exit nonzero if any fail. Add a short "How to run the
   gates" note to HANDOFF (or a GATES.md) documenting the interpreter split.
3. Make report/SILVER_REGRESSION.md's environment block deterministic (or pin the
   canonical gate interpreter) so gate_silver.py no longer dirties the tree on a
   read-only run. Verify: run gate_silver twice, tree stays clean.
4. Encode 2–3 more prose-only claims as gates that PASS (superspeedway stand-down
   list; D2 §7.3 dual-run identity as a standing test). Add only tests that pass and
   that you verify go red on drift.
5. Morning report at report/OVERNIGHT_<date>.md: gate results, commits, and any
   owner-judgment forks (carry forward the two still-open ones: legacy-cache SHA
   baseline, A6 ToS).

Guardrails: frozen walkforward.py config, frozen spec sections, and
research/track_audit/ are DO-NOT-TOUCH. Never hand-edit PLAN.md/plan/PLAN.html —
regenerate via src/report_plan.py from plan/schedule.yml only; preserve exactly-one
`next` (E1). One logical change per commit, green-gate evidence in the message,
standard co-author trailer. Any red gate or owner-judgment fork → stop and report.
If today is a race weekend and race 5618 has posted results, E1 duties (score 5618)
come first.
```

---

## 7. Push command for the morning

Nothing is pushed. When you're ready to publish tonight's three commits:

```bash
cd /Users/nicholassharkey/Downloads/nascar-cup-model && git push origin main
```

That publishes `114e419`, `f981a43`, `4a3b5c3` (docs reconciliation + two new gates).
Everything is gate-verified and the tree is clean.
