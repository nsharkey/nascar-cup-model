# GATES.md — the repo's health surface (how to run every gate)

This repo is guarded by **8 gates**. They are the standing proof that the
medallion foundation still reproduces the validated model, that the frozen
specs still bind the code, and that the plan/docs have not drifted. Run them
whenever you touch anything, and always before a push.

## One command

```bash
src/run_gates.sh
```

Runs all 8 gates with the correct interpreter and working directory, prints a
pass/fail summary table, and exits:

- `0` — all green
- `1` — at least one gate red (the failing gate's last log line and full log
  path are printed)
- `2` — interpreter preflight failed; **nothing was executed** (fix the
  interpreters and re-run)

The script resolves its own location, so it works from anywhere
(`src/run_gates.sh`, `./run_gates.sh` from `src/`, etc.).

## The two-interpreter split (the thing that is easy to get wrong)

There are **two** Python interpreters in play, and using the wrong one is the
most common way to get a spurious red:

| Interpreter | Version | Has | Used by |
|---|---|---|---|
| `.venv/bin/python` | 3.14.x | PyYAML | the **plan** gate only (`test_report_plan.py`) |
| Anaconda `python` | 3.13.x | duckdb, numpy, scipy, pyarrow | the **other 7** gates (all medallion / model gates) |

- The plan gate reads `plan/schedule.yml`; it needs PyYAML but **not** the
  scientific stack.
- The medallion gates read `data/nascar.duckdb` and the anchor pickle; they
  need the Anaconda stack. Use Anaconda `python` — **not** `python3`.

All gates are run from `src/` (paths inside them resolve from the repo root via
`__file__`, so only the CWD being `src/` matters).

Override the interpreters if your local names differ:

```bash
VENV_PY=/path/to/venv/python CONDA_PY=/path/to/conda/python src/run_gates.sh
```

`run_gates.sh` preflights both interpreters (imports `yaml` under `VENV_PY`,
`duckdb/numpy/scipy/pyarrow` under `CONDA_PY`) and refuses to run any gate if
either is wrong — so a mis-set interpreter fails loudly (exit 2) instead of
looking like a real gate failure.

Gates run **sequentially on purpose**: seven of them open the shared
`data/nascar.duckdb`, and concurrent opens can contend on the file lock. The
~1 min saved by parallelizing a health check is not worth the flakiness.

## The 8 gates

| # | Gate | Interp | What it proves | Source of truth |
|---|------|--------|----------------|-----------------|
| 1 | `test_report_plan.py` | venv | Plan schema valid, exactly one `next`, `PLAN.md`/`plan/PLAN.html` render matches `plan/schedule.yml` | `PLAN_FORMAT.md`, `plan/schedule.yml` |
| 2 | `test_track_audit.py` | conda | Track-audit package manifest hashes, 43 configs consistent MD/JSON/CSV, 193 edges, 163/163 crosswalked, priors labeled non-empirical | `research/track_audit/` (immutable) |
| 3 | `test_score_race.py` | conda | Scoring fixtures F1–F10 (hash seal, DNF grading, book grading, idempotency, tie/skip rules) | `specs/scoring_methodology.md` (frozen) |
| 4 | `gate_silver.py` | conda | **C-gate:** silver rebuild is field-for-field identical to the 163-race anchor pkl (except the `fepace` ULP-tolerance amendment) | `specs/medallion_architecture.md` §4 (frozen) |
| 5 | `gate_gold.py` | conda | **D-gate:** gold feature bank reproduces the model trio **0.413 / 0.476 / 0.447** via R0→R3 with zero mismatches | `specs/medallion_architecture.md` §6 (frozen) |
| 6 | `gate_track_reference.py` | conda | Gold track-reference tables built and internally consistent (track_dim 43, xwalk 44, priors 430, similarity 193, rules_era 6) | gold track-reference build |
| 7 | `test_frozen_config.py` | conda | Live production config (`predict_next.py` + `walkforward.pl_fit`) matches HANDOFF's frozen block on all seven fields + typology/typed | `HANDOFF.md` frozen block |
| 8 | `test_readme_numbers.py` | conda | README headline trio equals `gate_gold.py`'s `EXPECTED_*` (which the D-gate reproves live); 2026-OOS row is the corrected 0.447 | `README.md`, `gate_gold.py` |

## Notes

- Gate 5 (`gate_gold.py`) is the slow one (~30–60 s: it runs the walk-forward
  engine R0→R3). Everything else is seconds.
- Running the full surface leaves the working tree **clean**. A bare
  `gate_silver.py` run is read-only and does **not** rewrite
  `report/SILVER_REGRESSION.md`; regenerate that report deliberately with
  `gate_silver.py --write` (its Environment block records the interpreter that
  generated it, so refresh it only on purpose). If `git status` shows any
  change after `run_gates.sh`, that is a bug in a gate, not expected output.
- Gates 7 and 8 are "prose→gate" tests: they exist so a documented claim can
  never silently drift from the code/data it describes. Add more of these when
  a prose-only claim is cleanly and passingly encodable (each must also be
  verified to go red on drift).
