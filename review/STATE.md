# Red-team review of specs/ — run ledger (resume from here if interrupted)

**Started 2026-07-18, Fable 5 session (specs-author session orchestrating;
review itself done by fresh-context subagents to avoid author bias).**
Owner authorized the run with explicit instruction to persist state so a new
session can continue if this one hits a usage cap or Fable access ends
(2026-07-19).

## Why this exists

The four specs in `specs/` were pre-registered today and freeze how the
live forward test is judged; `scoring_methodology.md` executes tomorrow
(race 5618). Amendments are only cleanly allowed **before** the adjudicated
data exists (`specs/README.md`), so flaws must be found tonight for the
scoring spec, and before their gates for the rest. The review's job is to
REFUTE, not confirm. An empty findings report is a valid outcome.

## Protocol

- Each phase = one fresh-context subagent (no authoring context), reading
  only from disk, reporting severity-ranked findings with: exact spec
  section, concrete failure scenario, and verbatim proposed AMENDMENT text.
- Phases run **serially in priority order** (budget-cap hazard: parallel
  agents lose everything if the meter dies mid-flight; serial guarantees
  the urgent phase lands first). Findings are written to
  `review/findings_phase{N}.md` and committed immediately after each phase.
- Adjudication (after phases, or by resuming session): for each finding —
  ACCEPT (apply verbatim AMENDMENT block to the spec, dated) / REJECT
  (record why in the findings file) / OWNER (judgment-shaped dispute the
  owner must settle; leave spec untouched meanwhile). Mechanical findings
  (reproducible math/logic errors) may be adjudicated by the session;
  anything discretionary goes to OWNER.

## Phase status (update after every phase — this is the resume point)

| Phase | Scope | Status | Findings file |
|---|---|---|---|
| 1 (URGENT — executes tomorrow) | specs/scoring_methodology.md | pending | review/findings_phase1.md |
| 2 | specs/market_benchmark_decision_rule.md | pending | review/findings_phase2.md |
| 3 | specs/dnf_status_feature.md + specs/team_mfr_pooling.md | pending | review/findings_phase3.md |
| 4 | Adjudication + AMENDMENT application | pending | recorded in findings files + spec AMENDMENT blocks |

## How to resume in a NEW session

1. Read this file, then `HANDOFF.md`, then `specs/README.md`.
2. Run the next pending phase as a fresh-context subagent (or inline if the
   session itself is fresh — i.e., not the spec-authoring session). Model:
   Fable 5 if still available (access ends 2026-07-19); otherwise Opus 4.8,
   thinking on, effort xhigh.
3. Phase prompts: instruct the reviewer to REFUTE the named spec(s) —
   incomplete/contradictory/undefined rules; recompute all arithmetic
   (fixtures, power tables, boundaries) rather than trusting it; hunt
   judgment calls the spec claims not to require; verify claims against the
   real files (`predictions/race_5618_2026-07-19_prediction.json`,
   `src/races_parsed.pkl`, `src/*.py`). Findings format per Protocol above.
4. After each phase: write findings file, update the table above, commit
   (`redteam: phase N findings`).
5. Phase 4 adjudication per Protocol. Apply accepted amendments as dated
   `## AMENDMENT` blocks (allowed only while the spec's adjudicated data
   does not yet exist — for the scoring spec that means BEFORE race 5618 is
   scored). Update HANDOFF status; commit.

## Constraint reminders for any resuming session

- Do not edit frozen spec sections inline — AMENDMENT blocks only.
- Do not touch src/walkforward.py, src/predict_next.py, or the model.
- Race 5618 scoring must not proceed until Phase 1 adjudication is done.
- predictions/race_5618_* is sealed (sha256) — read-only evidence.
