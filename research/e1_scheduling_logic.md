# E1 next-suggestion timing logic — research spike (E3)

**Session:** E3 research spike · Sonnet 5 · thinking on · high · 2026-07-21
**Status:** research memo — **proposes only.** No code, no `report_plan.py` /
`test_report_plan.py` / `schedule.yml` mechanism change happens in this
session. All queries below were read-only against the already-built
`data/nascar.duckdb` warehouse and on-disk bronze files (no new fetches).
**Deliverable:** a recommended design for *when E1 should be surfaced as plan
`next`*, evaluated against the real Cup schedule, with open questions for the
owner. A future BUILD session implements whatever this memo recommends.

---

## 0. Executive summary

1. **`next` promotion is already 100% manual — there is no automated
   evaluator anywhere in this repo.** `report_plan.py` only renders whatever
   `status:` values are already written in the YAML; `test_report_plan.py`
   only validates cardinality/schema of whatever's already written. Nobody
   and nothing currently *computes* `next` from a date or a live signal — a
   human (or the session closing out) hand-edits the field. This reframes
   the whole design space: the deliverable isn't a live "gate" that
   overrides the plan, it's a **decision procedure** for whoever is about to
   write `status: "next"` for E1.
2. **A pure static day-of-week guard ("never Mon–Thu") is wrong, not just
   rigid — it has real, recurring counter-evidence.** 21 of 432 Cup points
   races (4.9%) in bronze history landed on Mon/Wed/Thu, every one of them a
   weather-delayed carryover (most recently the fall-2025 Talladega playoff
   race, 2025-11-17, a Monday). A hardcoded guard would have suppressed E1's
   actionable step during a real race weekend in those years. §2.1.
3. **A live "has qualifying posted" check is schema-feasible but
   structurally can't be purely read-only against already-ingested data**,
   because the upcoming race's `weekend-feed` typically **doesn't exist on
   disk yet** — bronze has no cron, only manual `--update`. Verified
   directly: race 5619 (Brickyard 400, 2026-07-26, next scheduled Cup race)
   has zero files under `data/bronze/series_1/2026/5619/` as of this
   session. The check is real (`weekend_runs[].run_type==2` results, once
   present, are an unambiguous "qualifying posted" signal — verified against
   race 5618) but it needs a **fresh, targeted fetch as a precondition**,
   which is itself an action, not a read. §2.2.
4. **Off-week and exhibition handling is already solved for free by the
   data model, not something to hand-code.** `race_type_id` cleanly
   separates points races (1, n=432) from Clash/Duels/All-Star (2, n=59) —
   confirmed the Dover race on 2026-05-17 that looked anomalous is in fact
   the 2026 All-Star Race. And genuine bye weeks are real, not
   hypothetical: the live 2026 schedule has a confirmed 2-week gap between
   Brickyard (2026-07-26) and Iowa (2026-08-09) with no Cup points race in
   between. A schedule-driven ("what's the next unscored points race and
   what's its state") design absorbs both cases automatically; a
   day-of-week rule cannot see either one. §2.3.
5. **Recommendation: replace the day-of-week guard with a small read-only
   advisory helper** that reports the next unscored Cup points race's state
   from an enum (too-early / needs-fresh-fetch / qualifying-posted /
   awaiting-race / awaiting-score), defaulting to **surface ambiguity
   rather than silently resolving it** on stale or missing data. Keep the
   actual `schedule.yml` edit manual, as it already is. Fill off-weeks by
   rotating `next` onto a short pre-approved recurring/analytics roster
   (already exists in this plan — F-series items, gate/consolidation
   sweeps, `calibration_backtest.py` re-runs) rather than adding a new
   status value or carving an exception into the cardinality gate. §3–§5.

---

## 1. What "next" actually is today (context for everything below)

Read `src/report_plan.py` and `src/test_report_plan.py` end to end looking
specifically for any date/time-aware logic: there is none. `report_plan.py`
renders `PLAN.md`/`plan/PLAN.html` deterministically from whatever
`status:` strings are already in `plan/schedule.yml`; `test_report_plan.py`
enforces schema, exactly-one-`next`-while-open cardinality, completeness,
referential integrity, drift, verbosity, and shape-sync — all against the
YAML as authored, never against a clock or a data source. Every prior
session's `next` promotion (A6→E1→E3, and every phase transition before it)
was a human/session editorial act at close-out.

This matters for scope: the ask was to design "smarter logic," but there is
no existing automated mechanism to make smarter — there's a manual habit to
make *better-informed*. The two live options are (a) a documented checklist
a closing session follows, or (b) that plus a small helper script that does
the read-only lookups for step (a) instead of a human eyeballing dates. Both
keep the actual YAML edit manual, consistent with `specs/README.md`'s
pre-registration discipline and the standing "planning sessions don't
execute" doctrine (`CLAUDE.md`, global).

---

## 2. Investigation & evidence

### 2.1 Static day-of-week guard

Queried `bronze.races_index` for every Cup (`series_id=1`) points race
(`race_type_id=1`, n=432, full 2015–2026 history) and computed day-of-week
from `race_date`:

| Day | Count |
|---|---|
| Sun | 360 |
| Sat | 51 |
| Mon | 17 |
| Wed | 2 |
| Thu | 2 |

**21/432 (4.9%) fall outside Sat/Sun.** Every one of these is a
weather-delayed race that carried over to the following day(s) —
2016 Pocono, 2017 Bristol, 2018 Martinsville/Bristol/Indy, 2019
Dover/Michigan, 2020 (four — including a Covid-era Wednesday/Thursday
pair), 2021 Bristol-Dirt/Talladega, 2023 Dover/Charlotte/New Hampshire,
2024 Daytona, and **2025-11-17 Talladega** — the most recent Cup playoff
race, a Monday. This isn't a historical curiosity confined to early years;
it recurs almost every season and landed as recently as eight months
before this session.

**Verdict: a hardcoded "never Mon–Thu" rule is not sufficient — it has a
real, recurring failure mode** (suppressing the actionable step during an
actual race weekend), not just theoretical rigidity. A day-of-week signal
can still be useful as a *cheap first-pass filter* (e.g., "don't even check
before Thursday") but must never be the final word, and must never suppress
a race that bronze/silver data shows is genuinely still pending
(`has_winner=False`) regardless of what day it is.

### 2.2 Live check against ingested schedule/weekend-feed data

Confirmed the schema exists and is exactly the right shape for this check:

- `weekend-feed.json`'s `weekend_runs[]` includes an entry per practice/
  qualifying session with `run_type` and a `results[]` array. For race 5618
  (North Wilkesboro, already run), `run_type==2` is literally named "Busch
  Pole Qualifying" with 37 populated result rows — an unambiguous
  "qualifying has posted" signal when present.
- `race_list_basic.json` also carries a race-level `qualifying_date` field.
  For the two *upcoming* races checked (5619 Brickyard 2026-07-26, 5620 Iowa
  2026-08-09), it currently reads the sentinel `1900-01-01T00:00:00`
  (not-yet-announced), while 5618 (this week's already-run race) already
  carried a real date at the earliest fetched snapshot before the race.
  This is a plausible secondary signal, but **only one data point** confirms
  it — how many days out it flips from sentinel to a real value is unknown
  and needs multi-day monitoring of an upcoming race before a build session
  should rely on it (§5, open question 2).

**The blocker isn't the schema, it's freshness.** Checked whether the
upcoming race's data is even on disk: `data/bronze/series_1/2026/5619/`
does not exist yet — zero files. `bronze_fetch.py` has no cron; it only
runs when a session invokes `--update`. So a check that is purely "read
whatever's already in bronze/silver, don't fetch anything" can only ever
answer *"we don't know yet"* for a race that hasn't been fetched this week
— it cannot affirmatively resolve "qualifying not posted" vs. "we haven't
looked." A genuinely live check therefore needs a **lightweight targeted
fetch as a precondition** (e.g., `bronze_fetch.py --update` scoped to the
one upcoming race_id), which is an action, not a pure read — outside what
this read-only research session is chartered to do, and arguably outside
what a "check E1's status" step should silently trigger on its own without
being asked (see §3 for why this pushes toward an advisory script over a
fully automatic gate).

### 2.3 Off-week / bye-week / exhibition-race handling

`race_type_id` already cleanly separates points races (1, n=432, what E1
cares about) from everything else (2, n=59): Clash, Duels, and the All-Star
Race all carry `race_type_id=2`. Spot-checked the one entry that looked
anomalous in the 2026 index — a "Dover Motor Speedway" race on
2026-05-17 with `race_type_id=2` — against `race_list_basic.json`'s
`race_name` field: it's `"NASCAR All-Star Race"`, correctly excluded from
points scope. No special-casing needed; this is exactly what the field is
for.

Genuine bye weeks are real and already visible in the live 2026 schedule,
not a hypothetical to design against in the abstract: **Brickyard 400
(5619, 2026-07-26) → Iowa Corn 350 (5620, 2026-08-09) is a confirmed 2-week
gap with zero Cup points races in between.** A day-of-week rule has no way
to know this and would still fire "nothing to do" logic identically every
Friday/Saturday/Sunday regardless of whether a race exists that weekend — it
can suppress false positives Mon–Thu but can't suppress them on a bye-week
Saturday. A schedule-driven check (next race_date with `race_type_id=1` and
no result yet) absorbs both exhibition weeks and bye weeks automatically,
because in both cases there's simply no qualifying points race_id in the
near window — nothing to hardcode.

### 2.4 Fallback behavior if the live check can't run

Two failure modes are both real and asymmetric in cost:
- **False negative** (suppress E1 when it should have fired): the actual
  weekly loop is timestamp-gated — book prices must commit **before the
  scheduled green flag**, and race 5618's were ruled inadmissible for
  missing that window by 27 minutes. A plan tool that silently
  under-promotes could compound an already-tight deadline if it's the only
  thing reminding a session to act.
- **False positive** (claim "qualifying posted, predict now" when it
  hasn't): would send a session to run `predict_next.py` against a stale or
  absent qualifying grid, or worse, mask that bronze needs a fresh fetch
  first.

Given HANDOFF already states the perishable-capture doctrine is independent
of plan status (E1 fires on real race weekends "regardless of plan `next`
status"), the plan tool's job is advisory, not enforcement — so the
higher-cost failure mode is a *false positive* that sends a session down
the wrong action, not a suppressed suggestion that a human doctrine-aware
owner would likely catch anyway. **Recommended default: on any ambiguity
(stale warehouse, missing target-race bronze folder, DuckDB unreachable),
report an explicit `NEEDS_FRESH_FETCH` / `UNKNOWN` state — never silently
collapse it to either "show as next" or "suppress."** This is a third
option, not a binary safe/permissive choice: surface the uncertainty to
whoever is deciding, don't resolve it for them.

### 2.5 The cardinality tension

`test_report_plan.py` requires exactly one `next` whenever any session is
open (`pending`/`blocked`/`half_done`/`next`) and zero when the plan is
fully complete — confirmed by reading the check directly
(`n_next == 1` / `n_next == 0`, `src/test_report_plan.py:41-46`). This gate
is a genuine anti-drift feature of the plan (PLAN_FORMAT.md §4) and none of
the investigation above found a case where relaxing it is actually
necessary — see §4 for why a carve-out is a rejected option, and §3 for the
proposed fallback (rotate `next` onto a recurring roster during dead
weeks) that satisfies the gate as-is.

---

## 3. Recommended design

**A. Kill the day-of-week guard as the primary signal.** Keep a loose,
cheap pre-filter if useful for the helper script's own early-exit ("Cup
race weekends structurally can't need E1 action before Thursday of race
week"), but never let it suppress a race the schedule data itself shows is
still open, and never let it be the sole justification for promoting E1
either.

**B. Make the primary signal the schedule itself, not the calendar day.**
The next unscored Cup points race is already computable from data this
project owns: filter `bronze.races_index` (or `silver.races`) to
`race_type_id=1`, take the earliest race with no result yet
(`has_winner=False` / no `gold.scores` row), and use *that* race's own
`race_date`/`qualifying_date` and weekend-feed state as the basis for
everything else. This one query subsumes §2.1 (weekday-agnostic — a
delayed Monday race is still "the next unscored points race," correctly)
and §2.3 (a bye week or exhibition week simply has no candidate row, so
there's nothing to promote) without hand-coding either exception.

**C. Build a small read-only advisory helper, not a fully automatic gate.**
Given §2.2's freshness finding — the check needs a fresh fetch to be
meaningful, and freshness isn't something a "just read the warehouse"
script should silently trigger — the right shape is a script (e.g.
`src/e1_status.py`, future build item) that:
1. Finds the next unscored Cup points race per (B).
2. Reports one state from a small enum:
   `TOO_EARLY` (race is more than ~1 week out and nothing's expected yet),
   `NEEDS_FRESH_FETCH` (target race's bronze weekend-feed is stale or
   absent — the common case per §2.2's finding that 5619 isn't fetched
   yet),
   `QUALIFYING_POSTED_PREDICT_NOW` (`weekend_runs[].run_type==2` has
   populated results and no prediction file exists yet for this race),
   `PREDICTION_MADE_AWAITING_RACE` (prediction sealed/pushed, race not yet
   run — the odds-capture T-45 step is the only live action, and that's a
   minute-granularity workflow step HANDOFF already governs directly, not
   something the plan tool should try to resolve at session granularity),
   `RACE_DONE_NEEDS_SCORING`,
   `NO_UPCOMING_RACE_IN_WINDOW` (bye week or between-seasons).
3. Prints a one-line human-readable recommendation. The human/session
   closing out still writes the `schedule.yml` edit by hand, using this as
   an input — exactly like every other `next` promotion in this plan's
   history.

This keeps the plan's core discipline (manual, deliberate, one editorial
act per close-out) intact while removing the actual guesswork that
triggered this spike.

**D. Fallback rule:** any state the helper can't confidently resolve
reports `NEEDS_FRESH_FETCH`/unknown rather than guessing — per §2.4, this
is the conservative default in both directions, not just the suppress
direction.

**E. Cardinality:** during a `NO_UPCOMING_RACE_IN_WINDOW` or `TOO_EARLY`
week, rotate `next` onto the plan's existing recurring/analytics roster
(this plan already has standing candidates — e.g. periodic
`calibration_backtest.py` re-runs as forward races accrue toward K≥20/K≥60,
already flagged in HANDOFF's own current-status note; queued F-series
analytics extensions; a consolidation/gate-health sweep per the global
consolidation-cadence convention) instead of inventing a new status value.
This is a pure editorial choice available today, requires zero mechanism
change, and satisfies the existing cardinality gate exactly as written.

---

## 4. Rejected alternatives (and why)

- **Carve an exception into `test_report_plan.py`'s cardinality gate for
  "calendar-gated" items.** Not needed — §3E's roster rotation satisfies
  the existing gate without weakening it, and this gate is explicitly the
  thing keeping the plan from drifting into unverified prose.
- **Fully automate the `schedule.yml` edit** (a script or cron that writes
  `status: next` itself). Collides with `specs/README.md`'s pre-registration
  discipline, the global "planning sessions don't execute" doctrine, and
  `PLAN_FORMAT.md`'s drift gate, which assumes a human/session authors
  content. It would also need §2.2's fresh-fetch precondition to run
  unattended, which is a bigger, separate infrastructure decision (bronze
  currently has no cron by design) that this spike was not asked to make.
- **Trust `qualifying_date` alone as the live signal.** Only one data point
  confirms it converges from the sentinel to a real value before race day;
  not enough evidence yet to rely on it without the `weekend_runs`
  cross-check (§5, open question 2).

---

## 5. Open questions for the owner

1. **Scope of the future build item:** is a read-only advisory script
   (§3C) the right size, or does the owner want it wired into
   `report_plan.py` itself as a non-authoritative computed hint (e.g., an
   extra rendered line, never altering `status:`)? Recommendation is the
   standalone script — smaller, safer, and doesn't touch the frozen
   renderer/gate.
2. **`qualifying_date` lead time is unverified.** A future build session
   should pull `race_list_basic.json` snapshots for an upcoming race across
   several days to confirm how far ahead the sentinel (`1900-01-01`) flips
   to a real date, before treating it as a secondary signal alongside
   `weekend_runs`.
3. **Off-week roster:** should the 2–4 "always-valid recurring" fallback
   items (§3E) be pre-registered as an explicit fixed list now, or left to
   whichever session closes out during a dead week to pick from the plan's
   existing open items? Either is workable; a fixed list is slightly more
   drift-resistant but adds a maintenance surface.
4. **Minute-granularity odds-capture window** (T-45 min before the
   *scheduled* green flag) is a different, much narrower time scale than
   anything the plan tool operates at (session granularity). Confirming
   this stays governed by HANDOFF's existing weekly-protocol text rather
   than something the plan/`next` mechanism should ever try to resolve.
