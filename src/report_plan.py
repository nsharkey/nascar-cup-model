#!/usr/bin/env python3
"""Deterministic sprint-plan renderer — the Python analogue of nflverseanalytics'
report_plan(). ONE data source (plan/schedule.yml) renders to TWO views:
  - PLAN.md            git-diffable source-of-record + drift-gate target
  - plan/PLAN.html     Economist house-style human display

"Show me the plan" always means "run this" — never hand-build or hand-edit a
render. The gate (src/test_report_plan.py) fails if a committed render diverges
from what this script produces, so the display cannot drift. Format spec:
PLAN_FORMAT.md.

Usage:
  python src/report_plan.py            # validate + (re)write PLAN.md and plan/PLAN.html
  python src/report_plan.py --open     # ^ then open plan/PLAN.html locally — THE way to view the plan
  python src/report_plan.py --check    # validate + assert committed renders match; exit 1 on drift
  python src/report_plan.py --markdown # print Markdown to stdout, write nothing
"""
import argparse
import hashlib
import html
import re
import sys
import webbrowser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "plan" / "schedule.yml"
PLAN_MD = ROOT / "PLAN.md"
PLAN_HTML = ROOT / "plan" / "PLAN.html"

STATUS_MARKER = {           # enum -> Markdown marker (authors write the enum, never the glyph)
    "done": "✅ done",
    "half_done": "⚠ half-done",
    "blocked": "⛔ blocked",
    "pending": "pending",
    "next": "⬅ next",
    "retired": "⊘ retired",   # overtaken by events / superseded — kept as record, not active work
}
STATUS_ENUM = set(STATUS_MARKER)
EFFORT_ENUM = {"low", "medium", "high", "xhigh", "max", "ultra", None}

# Verbosity caps (words) per free-text field — the display is structured data, not an
# essay: detail belongs in the session rows and linked reports, not in a wall-of-text
# summary. Set comfortably above legitimate content, low enough to catch ~2x bloat.
# kickoff_prompt is deliberately uncapped (a verbatim paste-ready prompt). See PLAN_FORMAT.md §4.
MAX_WORDS = {
    "meta.standfirst":       80,
    "meta.bottom_line":      140,
    "meta.handoff_note":     100,
    "phase.note":            160,
    "session.exec_summary":  110,
    "session.tech_summary":  280,
    "session.status_note":   190,
}


def _word_count(text):
    return len(str(text or "").split())


# ------------------------------------------------------------------ load + validate
def read_plan(path=SCHEDULE):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def plan_shape_signature(plan):
    """Deterministic 16-hex signature of the plan's STRUCTURE — which phases and
    sessions exist (key/id + title), order-independent. It changes when a phase or
    session is added, removed, or renamed, and is unaffected by status, ref, deps,
    or any free-text field. Used to flag when meta.standfirst may have fallen behind
    the plan's scope (see PLAN_FORMAT.md §4, check 7)."""
    parts = []
    for p in plan.get("phases") or []:
        parts.append(f"P|{p.get('key')}|{p.get('title')}")
    for s in plan.get("sessions") or []:
        parts.append(f"S|{s.get('id')}|{s.get('phase')}|{s.get('title')}")
    canon = "\n".join(sorted(parts))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def shape_status(plan):
    """(ok, message). Compares the stored meta.shape_sig to the live shape so a
    structural change forces the author to reconcile meta.standfirst."""
    stored = (plan.get("meta") or {}).get("shape_sig")
    actual = plan_shape_signature(plan)
    if not stored:
        return False, ("meta.shape_sig is unset — after checking meta.standfirst still describes "
                       "the plan, run `python src/report_plan.py --sync-shape`")
    if stored != actual:
        return False, (f"plan structure changed since the standfirst was last reconciled "
                       f"(stored {stored}, now {actual}) — revisit meta.standfirst so its scope still "
                       f"matches the plan, then run `python src/report_plan.py --sync-shape` to re-affirm")
    return True, "shape in sync"


def _write_shape_sig(sig, path=SCHEDULE):
    """Rewrite (or insert) the `  shape_sig: \"...\"` line under meta, preserving the rest."""
    text = path.read_text(encoding="utf-8")
    line = f'  shape_sig: "{sig}"'
    if re.search(r"(?m)^\s*shape_sig:.*$", text):
        text = re.sub(r"(?m)^\s*shape_sig:.*$", line, text, count=1)
    else:  # insert right after the spec_version line
        text = re.sub(r"(?m)^(\s*spec_version:.*)$", r"\1\n" + line, text, count=1)
    path.write_text(text, encoding="utf-8")


def validate(plan):
    """Return a list of human-readable errors (empty = valid). Mirrors the gate's checks
    so `report_plan.py --check` and the test agree."""
    errs = []
    meta = plan.get("meta") or {}
    for k in ("plan_name", "as_of", "spec_version", "standfirst", "bottom_line"):
        if not meta.get(k) and meta.get(k) != 0:
            errs.append(f"meta.{k} missing or empty")

    phases = plan.get("phases") or []
    phase_keys = [p.get("key") for p in phases]
    if len(phase_keys) != len(set(phase_keys)):
        errs.append("phase keys are not unique")
    for p in phases:
        for k in ("key", "num", "title", "model", "note"):
            if not p.get(k):
                errs.append(f"phase {p.get('key')!r}: {k} missing or empty")

    sessions = plan.get("sessions") or []
    ids = [s.get("id") for s in sessions]
    if len(ids) != len(set(ids)):
        errs.append("session ids are not unique")
    id_set = set(ids)
    next_count = 0
    for s in sessions:
        sid = s.get("id")
        if s.get("phase") not in phase_keys:
            errs.append(f"session {sid!r}: phase {s.get('phase')!r} is not a defined phase")
        st = s.get("status")
        if st not in STATUS_ENUM:
            errs.append(f"session {sid!r}: status {st!r} not in {sorted(STATUS_ENUM)}")
        if st == "next":
            next_count += 1
        if not s.get("model"):
            errs.append(f"session {sid!r}: model missing (required on every row — the plan is the record)")
        settings = s.get("settings") or {}
        if not isinstance(settings.get("thinking"), bool):
            errs.append(f"session {sid!r}: settings.thinking must be boolean")
        if settings.get("effort") not in EFFORT_ENUM:
            errs.append(f"session {sid!r}: settings.effort {settings.get('effort')!r} not in {sorted(x for x in EFFORT_ENUM if x)}")
        for k in ("wall_clock", "exec_summary", "tech_summary"):
            if not s.get(k):
                errs.append(f"session {sid!r}: {k} missing or empty")
        for dep in s.get("deps") or []:
            if dep not in id_set:
                errs.append(f"session {sid!r}: dep {dep!r} does not resolve to a session")
        if st == "next" and not s.get("kickoff_prompt"):
            errs.append(f"session {sid!r}: status 'next' requires a non-empty kickoff_prompt")
    if next_count > 1:
        errs.append(f"{next_count} sessions marked 'next' — at most one allowed")

    # verbosity caps — a bloated free-text field fails the gate, so wall-of-text
    # summaries cannot creep back in as sessions are added (any phase, any field).
    def _cap(label, text, key):
        n = _word_count(text)
        if n > MAX_WORDS[key]:
            errs.append(f"{label}: {n} words exceeds the {MAX_WORDS[key]}-word cap — trim it "
                        f"(detail belongs in the session rows / linked reports, not the summary)")

    _cap("meta.standfirst", meta.get("standfirst"), "meta.standfirst")
    _cap("meta.bottom_line", meta.get("bottom_line"), "meta.bottom_line")
    if meta.get("handoff_note"):
        _cap("meta.handoff_note", meta.get("handoff_note"), "meta.handoff_note")
    for p in phases:
        _cap(f"phase {p.get('key')!r} note", p.get("note"), "phase.note")
    for s in sessions:
        for fld in ("exec_summary", "tech_summary", "status_note"):
            if s.get(fld):
                _cap(f"session {s.get('id')!r} {fld}", s.get(fld), f"session.{fld}")
    return errs


# ------------------------------------------------------------------ helpers
def _cell(text):
    """Flatten a value for a Markdown table cell: collapse whitespace, escape pipes."""
    s = " ".join(str(text).split())
    return s.replace("|", r"\|")


def _model_settings(session):
    """Table 'Model + settings' string. The `model` field already carries thinking/effort in
    canonical `· ` form for done rows; for live rows we compose from settings when effort is set."""
    base = session["model"]
    dagger = " †" if session.get("dagger") else ""
    return base + dagger


def _handoff_sentence(session):
    """Prose 'Model & settings' line for the handoff block."""
    model = session["model"].split(" · ")[0]
    settings = session.get("settings") or {}
    thinking = "on" if settings.get("thinking") else "off"
    effort = settings.get("effort")
    s = f"{model}, thinking {thinking}"
    if effort:
        s += f", effort {effort}"
    return s


def _sessions_of(plan, phase_key):
    return [s for s in plan["sessions"] if s["phase"] == phase_key]


def _find_next(plan):
    for s in plan["sessions"]:
        if s["status"] == "next":
            return s
    return None


# ------------------------------------------------------------------ Markdown render
def render_markdown(plan):
    meta = plan["meta"]
    out = []
    out.append(f"# {meta['plan_name']} — sprint plan")
    out.append("")
    out.append(
        f"*As of {meta['as_of']} · format v{meta['spec_version']} · source "
        f"`plan/schedule.yml`, rendered by `src/report_plan.py` — do not hand-edit.*"
    )
    out.append("")
    out.append(" ".join(str(meta["standfirst"]).split()))
    out.append("")

    header = "| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |"
    rule = "|---|---------|--------|------------------|------------|-------------------|-------------------|"
    for ph in plan["phases"]:
        out.append(f"## Phase {ph['key']} — {ph['title']}")
        out.append("")
        out.append(f"*{ph['model']}* — {' '.join(str(ph['note']).split())}")
        out.append("")
        out.append(header)
        out.append(rule)
        for s in _sessions_of(plan, ph["key"]):
            out.append(
                f"| {_cell(s['id'])} | {_cell(s['title'])} | {STATUS_MARKER[s['status']]} "
                f"| {_cell(_model_settings(s))} | {_cell(s['wall_clock'])} "
                f"| {_cell(s['exec_summary'])} | {_cell(s['tech_summary'])} |"
            )
        out.append("")

    nxt = _find_next(plan)
    if nxt:
        out.append(f"## Handoff — next session ({nxt['id']})")
        out.append("")
        out.append(f"**Model & settings:** {_handoff_sentence(nxt)}.")
        out.append("")
        if meta.get("handoff_note"):
            out.append(" ".join(str(meta["handoff_note"]).split()))
            out.append("")
        out.append("```")
        out.append(str(nxt["kickoff_prompt"]).rstrip("\n"))
        out.append("```")
        out.append("")

    out.append(f"**Bottom line:** {' '.join(str(meta['bottom_line']).split())}")
    out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------ HTML render (Economist house style)
def _esc(text):
    t = html.escape(" ".join(str(text).split()), quote=False)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)


def _ascii(s):
    """Encode every non-ASCII char as a numeric HTML entity so the page renders
    correctly regardless of the served charset — fixes mojibake (·→Â·, —→â€") when
    plan/PLAN.html is opened as a local file:// with no charset header. Applied to
    the whole rendered document, so template literals are covered too. The CSS must
    therefore be ASCII (its one glyph uses a CSS \\XXXX escape, not a raw char)."""
    return s.encode("ascii", "xmlcharrefreplace").decode("ascii")


_STLABEL = {"done": "done", "half_done": "half-done", "blocked": "blocked",
            "pending": "pending", "next": "next", "retired": "retired"}


def render_html(plan):
    meta = plan["meta"]
    phases_html = []
    for ph in plan["phases"]:
        rows = []
        for s in _sessions_of(plan, ph["key"]):
            dag = '<span class="dag">&dagger;</span>' if s.get("dagger") else ""
            trc = (' class="next"' if s["status"] == "next"
                   else ' class="retired"' if s["status"] == "retired" else "")
            rows.append(
                f'<tr{trc}>'
                f'<td class="num">{_esc(s["id"])}</td>'
                f'<td class="nm">{_esc(s["title"])}</td>'
                f'<td><span class="st {s["status"]}">{_STLABEL[s["status"]]}</span></td>'
                f'<td class="mdl">{_esc(s["model"])}{dag}</td>'
                f'<td class="wall">{_esc(s["wall_clock"])}</td>'
                f'<td class="exec">{_esc(s["exec_summary"])}</td>'
                f'<td class="tech">{_esc(s["tech_summary"])}</td>'
                f'</tr>'
            )
        phases_html.append(
            f'<section class="phase">'
            f'<div class="phase-h"><span class="pnum">{_esc(ph["num"])}</span>'
            f'<span class="ttl">{_esc(ph["title"])}</span>'
            f'<span class="pmdl">{_esc(ph["model"])}</span></div>'
            f'<p class="pnote">{_esc(ph["note"])}</p>'
            f'<div class="tw"><table><thead><tr>'
            f'<th>#</th><th>Session</th><th>Status</th><th>Model + settings</th>'
            f'<th>Wall clock</th><th>Executive summary</th><th>Technical summary</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
        )

    nxt = _find_next(plan)
    handoff = ""
    if nxt:
        note = f'<p class="hn">{_esc(meta["handoff_note"])}</p>' if meta.get("handoff_note") else ""
        kickoff = html.escape(str(nxt["kickoff_prompt"]).rstrip("\n"), quote=False)
        handoff = (
            f'<div class="handoff"><p class="hl">Handoff · next session ({_esc(nxt["id"])})</p>'
            f'<p class="hm"><b>Model &amp; settings:</b> {_esc(_handoff_sentence(nxt))}.</p>'
            f'{note}<pre>{kickoff}</pre></div>'
        )

    return _ascii(_ECON_TMPL.format(
        title=_esc(meta["plan_name"]),
        asof=_esc(meta["as_of"]),
        spec=_esc(meta["spec_version"]),
        standfirst=_esc(meta["standfirst"]),
        phases="\n".join(phases_html),
        handoff=handoff,
        bottom=_esc(meta["bottom_line"]),
    ))


_ECON_TMPL = """<!-- GENERATED by src/report_plan.py from plan/schedule.yml — DO NOT EDIT. -->
<style>
 /* The Economist house style: white ground ALWAYS — one visual world, never a dark theme. */
 :root, :root[data-theme="light"], :root[data-theme="dark"]{{
  --paper:#FBFAF8; --ink:#121212; --grey:#5C5C5C; --faint:#8C8C8C;
  --hair:#DCDAD6; --hair2:#EAE8E4; --accent:#E3120B; --panel:#F3F1ED;
  /* status hues — glyph/word carries meaning; color reinforces (r/g-safe). */
  --green:#1A7F37; --amber:#B45309; --blue:#0A5FB4;
 }}
 *{{box-sizing:border-box;}} body{{margin:0;}}
 .pg{{ background:var(--paper); color:var(--ink); min-height:100vh; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; padding:clamp(1.5rem,4vw,3.2rem);}}
 .wrap{{ max-width:74rem; margin:0 auto;}}
 .flag{{ display:inline-block; background:var(--accent); color:#fff; font-weight:700; font-size:.78rem; letter-spacing:.03em; text-transform:uppercase; padding:.32rem .75rem; margin-bottom:1rem;}}
 h1{{ font-family:"Georgia","Times New Roman",serif; font-weight:700; font-size:clamp(2.2rem,6vw,3.7rem); line-height:1.03; letter-spacing:-.012em; margin:0 0 .5rem; text-wrap:balance;}}
 .standfirst{{ font-family:"Georgia",serif; font-size:1.16rem; line-height:1.5; color:var(--ink); max-width:42em; margin:0;}}
 .redbar{{ border:0; border-top:5px solid var(--accent); margin:1.1rem 0 0;}}
 .subrule{{ border:0; border-top:1px solid var(--ink); margin:.15rem 0 0;}}
 .phase{{ margin-top:2.1rem;}}
 .phase-h{{ display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap; padding-bottom:.35rem; border-bottom:2px solid var(--accent);}}
 .phase-h .pnum{{ background:var(--accent); color:#fff; font-weight:700; font-size:.82rem; padding:.08rem .45rem; letter-spacing:.02em;}}
 .phase-h .ttl{{ font-family:"Georgia",serif; font-weight:700; font-size:1.28rem; flex:1;}}
 .phase-h .pmdl{{ font-size:.71rem; letter-spacing:.07em; text-transform:uppercase; color:var(--grey);}}
 .pnote{{ font-size:.81rem; color:var(--grey); margin:.45rem 0 .2rem; max-width:52em;}}
 .tw{{ overflow-x:auto;}} table{{ border-collapse:collapse; width:100%; min-width:60rem;}}
 thead th{{ font-size:.62rem; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); text-align:left; font-weight:700; padding:.7rem .7rem; border-bottom:1px solid var(--ink); white-space:nowrap; vertical-align:bottom;}}
 tbody td{{ padding:.85rem .7rem; border-bottom:1px solid var(--hair2); vertical-align:top; font-size:.9rem;}}
 tbody tr:last-child td{{ border-bottom:none;}}
 .num{{ font-family:ui-monospace,Menlo,monospace; font-size:.78rem; color:var(--faint); font-variant-numeric:tabular-nums; white-space:nowrap; font-weight:700;}}
 .nm{{ font-family:"Georgia",serif; font-weight:700; min-width:8.5rem;}}
 .mdl{{ font-size:.8rem; white-space:nowrap;}} .mdl code{{font-family:inherit;}}
 .wall{{ font-size:.8rem; color:var(--grey); font-variant-numeric:tabular-nums; min-width:5rem;}}
 .exec{{ font-family:"Georgia",serif; font-size:.96rem; min-width:15rem; max-width:22rem;}}
 .tech{{ font-size:.77rem; color:var(--grey); line-height:1.5; min-width:16rem; max-width:24rem;}}
 .tech code,.exec code{{ font-family:ui-monospace,Menlo,monospace; font-size:.9em; color:var(--accent);}}
 .st{{ font-size:.65rem; letter-spacing:.09em; text-transform:uppercase; font-weight:700; white-space:nowrap;}}
 .st.done{{color:var(--green);}} .st.blocked{{color:var(--accent);}} .st.pending{{color:var(--grey);}} .st.next{{color:var(--blue);}} .st.half_done{{color:var(--amber);}} .st.retired{{color:var(--faint); text-decoration:line-through;}}
 tr.retired .nm, tr.retired .exec{{ color:var(--faint); text-decoration:line-through;}}
 tr.next td{{ box-shadow:inset 4px 0 0 var(--blue); background:var(--panel);}} tr.next .st.next::before{{content:"\\25A0 ";}}
 .dag{{ color:var(--accent); font-size:.7rem; vertical-align:super;}}
 .handoff{{ margin-top:2rem; border-top:5px solid var(--accent); padding:1rem 0 1.1rem;}}
 .handoff .hl{{ font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:700; margin:0 0 .5rem;}}
 .handoff .hm{{ font-size:.9rem; margin:0 0 .3rem;}} .handoff .hm b{{font-weight:700;}}
 .handoff .hn{{ font-size:.78rem; color:var(--grey); margin:0 0 .7rem;}}
 .handoff pre{{ font-family:ui-monospace,Menlo,monospace; font-size:.76rem; line-height:1.5; color:var(--ink); background:var(--panel); border-left:3px solid var(--accent); padding:.7rem .9rem; margin:0; white-space:pre-wrap; overflow-x:auto;}}
 .botl{{ margin-top:1.8rem; border-top:2px solid var(--accent); padding-top:1rem;}}
 .botl .bl{{ font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:700; margin:0 0 .5rem;}}
 .botl p{{ font-family:"Georgia",serif; font-size:1.1rem; line-height:1.55; margin:0; max-width:44em;}} .botl b{{font-weight:700;}}
 footer{{ margin-top:2rem; padding-top:1rem; border-top:1px solid var(--hair); font-size:.72rem; color:var(--grey); line-height:1.5;}}
 footer code{{ font-family:ui-monospace,Menlo,monospace; color:var(--ink);}}
</style>
<div class="pg"><div class="wrap">
 <div class="mast">
  <span class="flag">Sprint Plan · nascar-cup-model</span>
  <h1>{title}</h1>
  <p class="standfirst">{standfirst}</p>
  <hr class="redbar"><hr class="subrule">
 </div>
 {phases}
 {handoff}
 <div class="botl"><p class="bl">Bottom line</p><p>{bottom}</p></div>
 <footer>As of {asof} · format v{spec}. Model + settings is per-row; a <span class="dag">&dagger;</span> marks a session run off its phase's nominal tier. Executive summaries carry no IDs or function names — those live in the technical column. Source of truth is <code>plan/schedule.yml</code>; this page is a render of it, never hand-edited.</footer>
</div></div>"""


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Render or verify the sprint plan.")
    ap.add_argument("--check", action="store_true",
                    help="validate + assert committed PLAN.md/plan/PLAN.html match the render; exit 1 on drift")
    ap.add_argument("--markdown", action="store_true", help="print Markdown to stdout, write nothing")
    ap.add_argument("--open", action="store_true", dest="open_",
                    help="render, then open plan/PLAN.html in the default browser (the canonical way to view the plan)")
    ap.add_argument("--sync-shape", action="store_true", dest="sync_shape",
                    help="recompute meta.shape_sig from the current phases/sessions and write it back — "
                         "do this after confirming meta.standfirst still describes the plan")
    args = ap.parse_args(argv)

    plan = read_plan()
    errs = validate(plan)
    if errs:
        print("PLAN VALIDATION FAILED:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if args.sync_shape:
        newsig = plan_shape_signature(plan)
        _write_shape_sig(newsig)
        print(f"meta.shape_sig synced to {newsig}. Confirm meta.standfirst still describes the "
              f"plan's scope, then re-render (`python src/report_plan.py`) and commit.")
        return 0

    md = render_markdown(plan)
    htmlout = render_html(plan)

    if args.markdown:
        print(md, end="")
        return 0

    if args.check:
        problems = []
        if not PLAN_MD.exists() or PLAN_MD.read_text(encoding="utf-8") != md:
            problems.append("PLAN.md differs from the render — re-run `python src/report_plan.py`; never hand-edit a render")
        if not PLAN_HTML.exists() or PLAN_HTML.read_text(encoding="utf-8") != htmlout:
            problems.append("plan/PLAN.html differs from the render — re-run `python src/report_plan.py`; never hand-edit a render")
        ok, msg = shape_status(plan)
        if not ok:
            problems.append(msg)
        if problems:
            print("PLAN CHECK FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print("plan OK: schema valid, renders match, shape in sync.")
        return 0

    PLAN_MD.write_text(md, encoding="utf-8")
    PLAN_HTML.write_text(htmlout, encoding="utf-8")
    n = len(plan["sessions"])
    print(f"wrote {PLAN_MD.relative_to(ROOT)} and {PLAN_HTML.relative_to(ROOT)} "
          f"({n} sessions across {len(plan['phases'])} phases)")
    if args.open_:
        webbrowser.open(PLAN_HTML.as_uri())
        print(f"opened {PLAN_HTML.relative_to(ROOT)} in your default browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
