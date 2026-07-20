#!/usr/bin/env bash
# run_gates.sh -- one-command health check for the NASCAR Cup model repo.
#
# Runs all 17 repository gates with the correct interpreter and working
# directory, prints a pass/fail summary table, and exits nonzero if any gate
# is red. This is the repeatable form of the manual baseline sweep documented
# in every overnight report; see GATES.md for the full contract.
#
# INTERPRETER SPLIT (the tribal knowledge this harness encodes):
#   - test_report_plan.py needs the .venv interpreter (Python 3.14.x, PyYAML) --
#     it is the only gate that imports yaml and it does NOT need the medallion
#     scientific stack.
#   - the other 16 gates need the Anaconda interpreter (Python 3.13.x with
#     duckdb / numpy / scipy / pyarrow) and must run from src/.
#
# All gates run from src/ (this script's directory); paths inside the gates
# resolve from the repo root via __file__, so CWD only needs to be src/.
#
# Gates run SEQUENTIALLY on purpose: seven of them open the shared
# data/nascar.duckdb, and concurrent opens can contend on the file lock.
# Clarity over the ~1 min saved by parallelizing a health check.
#
# Override the interpreters if your local names differ:
#   VENV_PY=/path/to/venv/python CONDA_PY=/path/to/conda/python ./run_gates.sh
#
# Exit codes: 0 = all green; 1 = at least one gate red; 2 = interpreter
# preflight failed (nothing was executed).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_PY="${VENV_PY:-$REPO_ROOT/.venv/bin/python}"
CONDA_PY="${CONDA_PY:-python}"

# --- preflight: each interpreter must have its required libraries ------------
preflight_fail=0
if ! "$VENV_PY" -c 'import yaml' >/dev/null 2>&1; then
  echo "PREFLIGHT FAIL: VENV_PY ($VENV_PY) cannot import yaml."
  echo "  The plan gate needs the .venv interpreter (3.14.x, PyYAML)."
  preflight_fail=1
fi
if ! "$CONDA_PY" -c 'import duckdb, numpy, scipy, pyarrow' >/dev/null 2>&1; then
  echo "PREFLIGHT FAIL: CONDA_PY ($CONDA_PY) cannot import duckdb/numpy/scipy/pyarrow."
  echo "  The medallion gates need the Anaconda interpreter (3.13.x)."
  preflight_fail=1
fi
if [ "$preflight_fail" -ne 0 ]; then
  echo "Fix the interpreters (see GATES.md) and re-run. Nothing was executed."
  exit 2
fi

cd "$SCRIPT_DIR"

# --- gate registry: "interp|script|label" -----------------------------------
GATES=(
  "venv|test_report_plan.py|plan schema / render / cardinality"
  "conda|test_track_audit.py|track-audit manifest + crosswalk"
  "conda|test_score_race.py|scoring fixtures F1-F10"
  "conda|gate_silver.py|C-gate: silver vs anchor pkl"
  "conda|gate_gold.py|D-gate: reproduce 0.413/0.476/0.447"
  "conda|gate_track_reference.py|gold track reference tables"
  "conda|gate_track_profiles.py|F3: track profiles build-graph isolation + floor/asof checks"
  "conda|gate_track_similarity.py|F4: track DST build-graph isolation + floor/edge/pltree checks"
  "conda|gate_loop_metrics.py|F13: driver loop-metric histories build-graph isolation + re-derivation"
  "conda|test_frozen_config.py|frozen production config"
  "conda|test_readme_numbers.py|README headline trio"
  "conda|test_stand_down.py|superspeedway stand-down list"
  "conda|test_medallion_invariants.py|bronze/silver data invariants"
  "conda|gate_pricing.py|pricing layer: coherence + fixture reprove + faithful-read"
  "conda|gate_benchmark_liveness.py|Gate A: benchmark liveness (state-dependent, capture debt)"
  "conda|gate_calibration_not_edge.py|Gate B: calibration-is-not-edge (hermetic)"
  "conda|gate_five_market_gated.py|Gate C: roadmap-#5 stays market-gated (hermetic)"
)

LOGDIR="$(mktemp -d)"
RESULTS=()
fail_count=0
total=${#GATES[@]}

for spec in "${GATES[@]}"; do
  IFS='|' read -r interp script label <<< "$spec"
  if [ "$interp" = "venv" ]; then PY="$VENV_PY"; else PY="$CONDA_PY"; fi
  logf="$LOGDIR/$script.log"
  printf '... running %-28s (%s)\n' "$script" "$interp"
  if "$PY" "$script" >"$logf" 2>&1; then
    status="PASS"
  else
    status="FAIL"
    fail_count=$((fail_count + 1))
  fi
  RESULTS+=("$status|$interp|$script|$label|$logf")
done

# --- summary table ----------------------------------------------------------
echo
echo "========================================================================================"
printf '%-6s %-6s %-28s %s\n' "RESULT" "INTERP" "GATE" "CHECKS"
echo "----------------------------------------------------------------------------------------"
for r in "${RESULTS[@]}"; do
  IFS='|' read -r status interp script label logf <<< "$r"
  printf '%-6s %-6s %-28s %s\n' "$status" "$interp" "$script" "$label"
done
echo "========================================================================================"

if [ "$fail_count" -ne 0 ]; then
  echo "FAILED: $fail_count of $total gates red."
  for r in "${RESULTS[@]}"; do
    IFS='|' read -r status interp script label logf <<< "$r"
    if [ "$status" = "FAIL" ]; then
      echo "--- $script (last line + log path) ---"
      grep -v '^[[:space:]]*$' "$logf" | tail -1
      echo "  full log: $logf"
    fi
  done
  exit 1
fi

echo "ALL $total GATES GREEN."
exit 0
