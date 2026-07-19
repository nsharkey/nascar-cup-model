# PLAN_FORMAT.md — sprint-plan format & anti-drift mechanism

Adapted from the `nflverseanalytics` plan system (its `docs/PLAN_FORMAT.md` +
decision 182) to this Python repo. The point: a sprint plan described in prose
and retyped each session **drifts**. Here the plan is structured data, the
display is rendered deterministically from it, and a test fails if the two ever
diverge — so there is nothing left to rebuild by hand, and nothing to rebuild
wrong.

Three parts, one source of truth:

1. **Data** — `plan/schedule.yml` is the *only* file anyone edits.
2. **Renderer** — `src/report_plan.py` turns the YAML into `PLAN.md` (the
   git-diffable source-of-record) and `plan/PLAN.html` (the Economist
   house-style human display). "Show me the plan" means "run the renderer."
3. **Gate** — `src/test_report_plan.py` validates the schema and asserts the
   committed renders byte-match `report_plan.py`'s output. A hand-edit or reskin
   fails it.

## Commands

```bash
python src/report_plan.py --open     # THE way to view the plan: render, then open plan/PLAN.html locally
python src/report_plan.py            # validate + (re)write PLAN.md and plan/PLAN.html (no browser)
python src/report_plan.py --check    # validate + assert committed renders match; exit 1 on drift
python src/report_plan.py --markdown # print Markdown to stdout, write nothing
python src/test_report_plan.py       # the full gate (schema + cardinality + drift); exit 1 on any failure
```

**"Show me / look at the sprint plan" always means: run `python src/report_plan.py --open`.**
It regenerates from `plan/schedule.yml` (so the view is never stale) and opens the
Economist-style `plan/PLAN.html` in the local browser — no publishing, nothing leaves
the machine. Publish the artifact form only when the user explicitly wants a shareable link.

## 1. Source of truth — `plan/schedule.yml`

Editing a rendered file by hand is a gate failure, not a workflow. The schema:

- `meta`: `plan_name`, `as_of` (absolute date, never "today"), `spec_version`,
  `standfirst`, `bottom_line`, optional `handoff_note`.
- `phases[]`: `key` (unique), `num` (roman numeral for display), `title`,
  `model` (nominal tier as `"Model · thinking on · effort"`), `note`.
- `sessions[]`: `id` (unique, sorts within phase), `phase` (→ a phase key),
  `status` (enum below), `model`, `settings: {thinking: bool, effort: enum}`,
  `wall_clock` (kickoff→closeout, **not** babysit time), `exec_summary`
  (non-technical: plain outcome/blocker, no IDs or function names),
  `tech_summary` (implementation detail), `deps[]` (session ids), optional
  `ref` (commit/PR for done items), `status_note` (dated free text),
  `dagger` (true when a session ran off its phase's nominal tier),
  `kickoff_prompt` (**required iff `status: next`** — the verbatim paste-ready
  prompt).

## 2. Status enum → marker

Authors write the enum; the renderer draws the glyph.

| enum | marker |
|------|--------|
| `done` | ✅ done |
| `half_done` | ⚠ half-done |
| `blocked` | ⛔ blocked |
| `pending` | pending |
| `next` | ⬅ next |

## 3. Rendered output

One table **per phase**, each preceded by a one-line phase-goal + model line.
Columns, in this exact order — never a bare `# | Session | Model` table:

`# | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary`

Then a **Handoff** block for the single `next` session — a plain
"Model & settings: …" sentence (never a `/model` slash command) and the full
`kickoff_prompt` inline in a fenced block (never a pointer to where it lives) —
and a one-to-two sentence **Bottom line** (not a restatement of every row). The
renderer always emits the *full* plan; there is no status-only digest mode.

## 4. The gate — `src/test_report_plan.py`

Fails on: (1) **schema** — required fields + correct types, `effort` in
{low,medium,high,xhigh,max}, `status` in the enum; (2) **cardinality** — exactly
one `next` while work is open, zero when complete; (3) **completeness** —
`exec_summary`/`tech_summary`/`model`/`wall_clock` present on every row, the
`next` session has a `kickoff_prompt`; (4) **referential** — every `phase` and
every `dep` resolves; (5) **drift** — committed `PLAN.md` *and* `plan/PLAN.html`
equal the render. This is what makes the display model-independent: any session,
on any model, either regenerates from the YAML (identical output by construction)
or fails the gate. A model cannot restyle the plan and still pass.

## 5. The HTML display look — The Economist house style

`plan/PLAN.html` renders in The Economist house style: white ground **always**
(never a dark theme — white + red is the identity), Economist red `#E3120B`, a
red masthead flag, per-row Model + settings, serif heads over sans data, the
`next` row tinted with a red left rule. Palette tokens live in `report_plan.py`'s
`_ECON_TMPL`. The Markdown render is the source-of-record and diff target; the
HTML is the human-facing view. Both are pure functions of the one YAML.

## 6. Out of scope

This spec governs the plan's *shape, enforcement, and display identity* — not
its *content*. What the sessions are lives in `plan/schedule.yml`; the roadmap
narrative lives in `HANDOFF.md`.
