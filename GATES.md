# GATES.md — the repo's health surface (how to run every gate)

This repo is guarded by **16 gates**. They are the standing proof that the
medallion foundation still reproduces the validated model, that the frozen
specs still bind the code, that the market benchmark stays alive under the
model-book DEMOTE, and that the plan/docs have not drifted. Run them whenever
you touch anything, and always before a push.

## One command

```bash
src/run_gates.sh
```

Runs all 16 gates with the correct interpreter and working directory, prints a
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
| Anaconda `python` | 3.13.x | duckdb, numpy, scipy, pyarrow | the **other 14** gates (all medallion / model / tether gates) |

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

## The 16 gates

| # | Gate | Interp | What it proves | Source of truth |
|---|------|--------|----------------|-----------------|
| 1 | `test_report_plan.py` | venv | Plan schema valid, exactly one `next`, `PLAN.md`/`plan/PLAN.html` render matches `plan/schedule.yml` | `PLAN_FORMAT.md`, `plan/schedule.yml` |
| 2 | `test_track_audit.py` | conda | Track-audit package manifest hashes, 43 configs consistent MD/JSON/CSV, 193 edges, 163/163 crosswalked, priors labeled non-empirical | `research/track_audit/` (immutable) |
| 3 | `test_score_race.py` | conda | Scoring fixtures F1–F10 (hash seal, DNF grading, book grading, idempotency, tie/skip rules) | `specs/scoring_methodology.md` (frozen) |
| 4 | `gate_silver.py` | conda | **C-gate:** silver rebuild is field-for-field identical to the 163-race anchor pkl (except the `fepace` ULP-tolerance amendment) | `specs/medallion_architecture.md` §4 (frozen) |
| 5 | `gate_gold.py` | conda | **D-gate:** gold feature bank reproduces the model trio **0.413 / 0.476 / 0.447** via R0→R3 with zero mismatches | `specs/medallion_architecture.md` §6 (frozen) |
| 6 | `gate_track_reference.py` | conda | Gold track-reference tables built and internally consistent (track_dim 43, xwalk 44, priors 430, similarity 193, rules_era 6) | gold track-reference build |
| 7 | `gate_track_profiles.py` | conda | **F3:** `gold.track_profiles`/`track_profiles_asof` internally consistent; build-graph isolated from `gold_build.py`/`walkforward.py`/`predict_next.py`; every `below_floor` row equals its family value exactly; as-of aggregates re-derive from strictly-prior races; TPP/RVS labels present; FVS-model sourced from the frozen engine, not reimplemented | `specs/track_profiles.md` §5 |
| 8 | `gate_track_similarity.py` | conda | **F4:** `gold.track_dst`/`track_dst_edges`/`track_pltree*` internally consistent; build-graph isolated from `gold_build.py`/`walkforward.py`/`predict_next.py`; `gate_gold.py` itself unedited; every `below_floor` row equals its family-pair value exactly; a sample of pairs and the pltree root split re-derive exactly from stored residuals/covariates; frozen-engine replay sourced from `pl_fit`/`wmean`/`znan`, not reimplemented | `specs/track_similarity.md` §6 |
| 9 | `test_frozen_config.py` | conda | Live production config (`predict_next.py` + `walkforward.pl_fit`) matches HANDOFF's frozen block on all seven fields + typology/typed | `HANDOFF.md` frozen block |
| 10 | `test_readme_numbers.py` | conda | README headline trio equals `gate_gold.py`'s `EXPECTED_*` (which the D-gate reproves live); 2026-OOS row is the corrected 0.447 | `README.md`, `gate_gold.py` |
| 11 | `test_stand_down.py` | conda | Doctrine's superspeedway stand-down set {Daytona, Talladega, Atlanta} == `walkforward.MY_TYPE`'s SS set == the tracks `predict_next` flags `stand_down` (`tt=='SS'`) | `HANDOFF.md` doctrine, `walkforward.py` (frozen) |
| 12 | `test_medallion_invariants.py` | conda | Bronze has no `failed` terminal state; silver has exactly one winner and no duplicate driver per (series, race) on both `driver_race` and `results`; checkers self-validate against injected corruption | `specs/medallion_architecture.md` §2.9, silver structure |
| 13 | `gate_pricing.py` | conda | Pricing layer: §4 coherence invariants (internal self-consistency only, not correctness), §5.4 committed-fixture reprove (bit-exact, numpy version recorded), §6 faithful-read (priced win/top5/top10/h2h reproduce every committed prediction JSON's own numbers within MC error) | `specs/pricing_layer.md` §§4, 5.4, 6 (frozen) |
| 14 | `gate_benchmark_liveness.py` | conda | **Gate A (liveness, state-dependent):** the market benchmark is still alive under the model-book DEMOTE -- reuses `market_benchmark.py`'s own functions verbatim; prints N/K/verdict/last-admissible-priced-race/capture-debt; RED iff predictions are active and capture-debt (scored non-SS races with no admissible priced pick) exceeds 2. **May legitimately red** when capture is genuinely behind -- that is its job, unlike every other gate here | `specs/tether_gates.md` Gate A (frozen) |
| 15 | `gate_calibration_not_edge.py` | conda | **Gate B (hermetic):** no document asserts an edge on the strength of calibration evidence -- doctrine sentinels present verbatim + a token co-occurrence scan (EDGE-token + CALIBRATION-token + no SEPARATION-phrase) over README/HANDOFF/specs/report | `specs/tether_gates.md` Gate B (frozen) |
| 16 | `gate_five_market_gated.py` | conda | **Gate C (hermetic):** roadmap #5's execution gate reads only the market benchmark, never calibration -- asserts `clean_air_causal_pace.md` §0's market-gate text + no calibration token, plus a #5-token + UNLOCK-token + CALIBRATION-token co-occurrence scan | `specs/tether_gates.md` Gate C (frozen) |

## Notes

- Gate 5 (`gate_gold.py`) is the slow one (~30–60 s: it runs the walk-forward
  engine R0→R3). Everything else is seconds.
- Running the full surface leaves the working tree **clean**. A bare
  `gate_silver.py` run is read-only and does **not** rewrite
  `report/SILVER_REGRESSION.md`; regenerate that report deliberately with
  `gate_silver.py --write` (its Environment block records the interpreter that
  generated it, so refresh it only on purpose). If `git status` shows any
  change after `run_gates.sh`, that is a bug in a gate, not expected output.
- Gates 7–10 are "prose→gate" tests: they exist so a documented claim can
  never silently drift from the code/data it describes (frozen config, README
  numbers, the stand-down list, the bronze/silver invariants). Gates 11 and 12
  are self-validating — 11's comparison runs against mutated temp copies at
  build time, and 12 runs its checkers against injected corruption on every
  invocation. Add more of these when a prose-only claim is cleanly and
  passingly encodable (each must also be verified to go red on drift).
  (Renumbered from "9 and 10" as F3/F4 each inserted a new gate before this
  group — a reminder that these are position numbers, re-derived from
  `run_gates.sh`'s actual array order at wiring/edit time, never hard-coded
  elsewhere; see the tether-gate note below for the same discipline.)
- Gates 14–16 are the **tether gates** (`specs/tether_gates.md`) that ship the
  model-book DEMOTE: 15 (B) and 16 (C) are hermetic prose→gate scans in the
  gates-9–12 idiom (B and C share their CALIBRATION-token and
  SEPARATION-phrase lists via a single import, so the two can never drift
  apart); 14 (A) is different in kind — a **liveness** gate that reconstructs
  live benchmark state (predictions + git history + the local race-schedule
  cache) and may legitimately go red if weekly odds capture falls behind,
  which is its entire purpose. Gate B's negative scan strips text inside
  straight double-quote pairs before token-matching each line — quoted text
  in this repo's specs is a worked example (e.g. the literal injection string
  used to prove Gate B goes red on a violation), not an assertion, and a scan
  that can't tell the two apart would go permanently red on its own defining
  spec (verified against the live corpus before shipping).
