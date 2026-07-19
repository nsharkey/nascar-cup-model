#!/usr/bin/env python3
"""Drift gate for the sprint plan — the Python analogue of nflverseanalytics'
test-plan-schedule.R. Runs with plain stdlib asserts (no pytest); exits nonzero on
any failure. Assert this in CI / before committing a plan change.

Fails on:
  1. Schema      — every session/phase has required fields with correct types.
  2. Cardinality — at most one 'next' (exactly one while live; zero when complete).
  3. Completeness— exec/tech/model/wall_clock present on every row; 'next' has a kickoff.
  4. Referential — every phase resolves; every dep id resolves to a session.
  5. Drift       — committed PLAN.md AND plan/PLAN.html byte-match report_plan's render.

A hand-edit of either rendered file — or a reskin of the HTML — turns this red.
That is the anti-drift guarantee: the display is a pure function of plan/schedule.yml.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_plan as rp  # noqa: E402


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    plan = rp.read_plan()

    # 1-4: schema / cardinality / completeness / referential (validate() covers these)
    errs = rp.validate(plan)
    for e in errs:
        failures.append(f"[schema/validate] {e}")

    # Cardinality nuance: a live plan has exactly one 'next'; a complete plan has zero.
    n_next = sum(1 for s in plan["sessions"] if s["status"] == "next")
    n_open = sum(1 for s in plan["sessions"] if s["status"] in ("pending", "blocked", "half_done", "next"))
    if n_open > 0:
        check(n_next == 1, f"[cardinality] plan has open work but {n_next} sessions marked 'next' (want exactly 1)")
    else:
        check(n_next == 0, f"[cardinality] plan is complete but {n_next} sessions still marked 'next'")

    # 5: drift — committed renders must equal the current render of the YAML
    md = rp.render_markdown(plan)
    htmlout = rp.render_html(plan)
    check(rp.PLAN_MD.exists() and rp.PLAN_MD.read_text(encoding="utf-8") == md,
          "[drift] PLAN.md differs from render — run `python src/report_plan.py`, never hand-edit it")
    check(rp.PLAN_HTML.exists() and rp.PLAN_HTML.read_text(encoding="utf-8") == htmlout,
          "[drift] plan/PLAN.html differs from render — run `python src/report_plan.py`, never hand-edit it")

    if failures:
        print(f"FAIL — {len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"PASS — schema valid, cardinality OK, renders match "
          f"({len(plan['sessions'])} sessions, {len(plan['phases'])} phases).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
