# specs/ — pre-registered design documents

Written 2026-07-18 in a planning-only session (no production code, no model
changes, no predictions). Each spec is **execution-ready**: exact
definitions, every known edge case resolved, a pre-registered kill/keep
rule, and a mechanical implementation checklist, so a later implementation
session (any model tier) makes zero judgment calls.

## Pre-registration discipline

- A spec's frozen sections are **immutable once committed.** The only
  permitted edits: (a) the dated `## RESULT` block a spec explicitly
  provides for, (b) a dated `## AMENDMENT` appended — never inline edits —
  and only while the data that the amended rule adjudicates **does not yet
  exist**. An amendment after results exist is a protocol violation; if it
  ever happens anyway, it must say so in bold and the pre-amendment rule's
  verdict must be reported alongside.
- Decision thresholds, statistics, and stopping rules cannot be
  renegotiated because a result is disliked. A well-run negative is a
  success (project doctrine).

## Files, in execution order

| Spec | Role | Runs when |
|---|---|---|
| `scoring_methodology.md` | How every forward prediction is scored; `scores_log.csv` contract; test fixtures | **First scoring: race 5618, after 2026-07-19 race** |
| `market_benchmark_decision_rule.md` | Pre-registered "live edge over the closing line?" statistic, sequential test, power, stopping rule (gates roadmap #5) | Accumulates from first priced race; looks per its §4 |
| `dnf_status_feature.md` | Roadmap #4a: 3 DNF/status variants, walk-forward A/B vs frozen config, kill/keep rule | scores_log ≥ 8 races |
| `team_mfr_pooling.md` | Roadmap #4b: org/manufacturer pooling variants (incl. the `team_name` data-layer prerequisite), same gate form | After #4a's decision is recorded |

## Explicitly out of scope (recorded decisions, not oversights)

- **Live-race / in-race MODELING:** still gated — by roadmap order it sits
  behind the market-benchmark gate (#5 territory at the earliest), and the
  audit marked in-race/telemetry claims unaudited. Infrastructure-side
  planning (data capture, odds recording, automation) now exists as a
  plan-only living document at `planning/aws_solutions.md` (2026-07-18,
  owner-authorized); nothing there is implemented, and none of it changes
  any frozen spec or the model.
- Clean-air causal pace (roadmap #5): gated on the market benchmark;
  §7 of the audit stands — the fixed-effects approach is a dead end, do
  not retry it.
- Calibration correction of the model's underconfidence (audit §7): known,
  real, and deliberately untouched — it would change the pick stream
  mid-benchmark. Revisit only via a pre-registered spec if ever.
