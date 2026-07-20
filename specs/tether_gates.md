# SPEC: The three tether gates — the price of an honest DEMOTE (pre-registered design)

**Status:** pre-registered 2026-07-20 (plan session **M1**, Opus 4.8 · thinking on
· xhigh). NEW pre-registration file — **not** an amendment to any frozen spec.
Descends from `research/pivot_model_book_vetting.md` §1.2–§1.3 and §3.3 (owner fork
**DEMOTE + tether**, §8).
**Governs:** plan session **M4** (ship the three tether gates + formalize the
demote, in the same beat). Design here; code in M4.
**Implements to:** `src/gate_benchmark_liveness.py`, `src/gate_calibration_not_edge.py`,
`src/gate_five_market_gated.py` (new files) + wiring into `src/run_gates.sh` and
`GATES.md`. No existing gate or frozen spec is modified.

**Why these exist (FROZEN rationale).** A DEMOTE whose only protection is prose
("calibration is never edge; capture continues") is **strictly worse than STAY**:
it puts a gratifying, immediate-feedback, self-graded calibration scoreboard next
to a tedious, perishable, no-signal-until-2027 external chore, and attention flows
downhill by default — capture lapses, N stays pinned near 0, and "how's the model
doing?" gets silently answered by the calibration number. This repo's philosophy
is *prose drifts and only gates hold* (gates 7–10). These three gates convert the
governance boundary from prose to code, in the **same session that demotes** (M4).
Required for DEMOTE; recommended even under STAY.

The gates follow the **gates-7–10 prose→gate idiom**: each ties a documented claim
to a mechanical check, exits nonzero on drift, and must be verified to go **red**
on a violation before it counts (a gate that cannot fail is not a gate). Two are
hermetic static scans; the liveness gate reconstructs benchmark state.

---

## Sentinels this session (M1) plants (FROZEN — the gates read these)

So the gates have fixed anchors to assert against, M1 plants these exact strings
(the gates match on them; keep them verbatim if ever edited):

1. **HANDOFF.md doctrine line (canonical doctrine sentinel):**
   > **Calibration is model-quality, never edge, and never unlocks roadmap #5.**
2. **`specs/calibration_backtest.md` §0** contains: *"calibration is
   model-vs-**reality** … yields **zero** profit signal and can never establish an
   edge"* and *"Nothing here substitutes for it (tether gate 2)"*.
3. **`specs/calibration_backtest.md` §3** contains: the named-consequence clause
   *"never unlocks roadmap #5 (tether gate 3)"*.
4. **`specs/clean_air_causal_pace.md` §0** (FROZEN — **not edited**; already
   compliant): the market-gate text *"specs/market_benchmark_decision_rule.md …
   returns **EDGE**"* and *"**UNDERPOWERED does not unlock**"*, with **no**
   calibration token in its execution gate.

---

## Gate A — benchmark-liveness (the memo's "gate 11") (FROZEN)

**Claim encoded:** the market benchmark is still alive and being fed; capture is
not silently lapsing under the demote.

**Prints on every `run_gates.sh` run (red or green):**
`N` (admissible graded picks), `K` (contributing non-SS races), the standing
verdict, the **last admissible priced race** (`(date, race_id)` or `none — N=0`),
and the **capture-debt** figure.

**Reconstruction:** reuse `market_benchmark.py`'s own functions
(`load_all_predictions`, `load_snapshot`, `find_primary_book`,
`graded_picks_for_race`, `reconstruct_and_decide`) — the identical inputs (sealed
JSONs + frozen snapshots + git history; green-flag times from the local
`race_list_{year}.json` cache `update_data.py` maintains). It never recomputes
admissibility by a different rule.

**Definitions (pinned):**
- `P_scored_nonSS` = number of committed prediction JSONs that are **non-SS**
  (`track_type != 'SS'`) and **scored** (a `_wf_scored.json` snapshot exists).
- `K_adm` = number of those races contributing ≥ 1 **admissible** graded pick to
  the benchmark (exactly `market_benchmark`'s `K`).
- **`capture_debt = P_scored_nonSS − K_adm`** — non-SS scored races with no
  admissible priced pick (a post-flag commit, like race 5618, counts as debt: that
  is precisely the workflow lapse to catch).
- A race whose green-flag time or entry commit-time **cannot be resolved offline**
  is **excluded** from both counts and flagged `capture-state unknown` — it is
  **never** counted as debt (so an offline run degrades to advisory, never a
  spurious red).
- `predictions_active` = at least one committed prediction has a `race_date`
  within **`LIVE_WINDOW_DAYS = 45`** of the run date (the forward test is live).

**RED condition (pinned):**
> RED iff `predictions_active` **and** `capture_debt > TOL_DEBT`, with
> **`TOL_DEBT = 2`**.
Otherwise GREEN. (Current state 2026-07-20: race 5618 scored, non-SS,
inadmissible → `capture_debt = 1 ≤ 2` → GREEN. As non-SS races accrue without
admissible capture, debt climbs past 2 and the gate reds — loud and un-ignorable.)

**On RED, the printed remediation is fixed:** "capture is behind by
`{capture_debt}` non-SS races — record ALL primary-book matchups and **commit +
push before the scheduled green flag** for the missing race(s) (scoring §5.1 +
market-spec full-board duty), or record in that race's scores row why capture was
impossible." The offseason (no active predictions) is never red by this gate — the
market spec's own calendar backstop governs the terminal look.

**Non-goals:** it does not require a primary book to be **bound** (binding is
deferred per L5) — the first admissible capture binds it automatically; it enforces
**capture**, not binding. It never reads or reacts to any calibration number.

---

## Gate B — calibration-is-not-edge non-substitution (FROZEN)

**Claim encoded:** no document asserts an **edge** ("beats the book/market",
"betting edge over the closing line") on the strength of **calibration /
proper-scoring** evidence; the doctrine boundary is stated, not eroded.

Hermetic static scan over the doc set **D** =
`{README.md, HANDOFF.md, specs/*.md, report/*.md}` (read-only, no execution).

**Positive assertions (the doctrine is present):**
1. HANDOFF.md contains the canonical doctrine sentinel (sentinel 1) **verbatim**.
2. `specs/calibration_backtest.md` contains the sentinel-2 non-substitution
   phrases.
Missing either → RED (the doctrine was deleted/weakened).

**Negative scan (no substitution claim):**
- **EDGE-tokens** `E` = {`"edge over"`, `"beats the book"`, `"beat the book"`,
  `"beats the market"`, `"beat the market"`, `"betting edge"`, `"live edge"`}.
- **CALIBRATION-tokens** `C` = {`"calibrat"`, `"Brier"`, `"log-loss"`,
  `"proper-scor"`, `"BSS"`, `"skill score"`}.
- **SEPARATION-phrases** `S` (the allowlist that marks a *legitimate* co-occurrence
  stating the boundary) = {`"never edge"`, `"not edge"`, `"not an edge"`,
  `"zero profit"`, `"no profit"`, `"cannot establish an edge"`,
  `"can never establish an edge"`, `"never substitute"`, `"not substitute"`,
  `"never unlocks"`, `"orthogonal"`, `"breaks even by construction"`}.
- **RED iff** any line in **D** contains a token from `E` **and** a token from `C`
  **and** no phrase from `S` — i.e. it asserts calibration ⇒ edge without stating
  the separation. Report the offending file:line. Legitimate separation statements
  (this spec, the calibration spec, HANDOFF's doctrine, the vetting memo) all carry
  an `S` phrase and pass; a new "we're calibrated so we beat the book" line fails.

This is self-maintaining: it does not enumerate allowed sentences, only requires
that any edge×calibration co-occurrence also state the boundary.

---

## Gate C — roadmap-#5 stays market-gated (FROZEN)

**Claim encoded:** `specs/clean_air_causal_pace.md`'s execution gate reads the
**market-benchmark** verdict, **never** a calibration verdict — the forbidden
inference (calibration → edge → #5) cannot be committed without a red gate.

Hermetic static scan (read-only).

**Positive assertions on `specs/clean_air_causal_pace.md` §0 (the FROZEN execution
gate):**
1. It references `market_benchmark_decision_rule.md`, the word `EDGE`, and
   `UNDERPOWERED does not unlock` (sentinel 4). Missing any → RED (the #5 gate was
   re-pointed or weakened).
2. Its §0 execution-gate section contains **no** CALIBRATION-token (`C` from
   gate B) and no reference to `calibration_backtest`. Any present → RED (#5
   execution is being conditioned on calibration).

**Negative scan over the doc set D (gate B's D):**
- **#5-tokens** `F` = {`"roadmap #5"`, `"roadmap-#5"`, `"clean-air"`, `"clean_air"`,
  `"G2"`}.
- **UNLOCK-tokens** `U` = {`"unlock"`, `"gates"`, `"execute"`, `"execution gate"`,
  `"trigger"`}.
- **RED iff** any line contains a token from `F`, a token from `U`, and a
  CALIBRATION-token from `C`, **and** no SEPARATION-phrase from `S` — i.e. it ties
  #5 execution to calibration. (Lines that state the negation — e.g. "calibration …
  never unlocks roadmap #5" — carry an `S` phrase and pass.)

**Positive assertion tying the pieces:** `specs/calibration_backtest.md` §3
contains the sentinel-3 clause `"never unlocks roadmap #5 (tether gate 3)"`.
Missing → RED.

---

## Wiring + verification (for M4) (FROZEN)

1. Add all three gates (conda interpreter — they read repo files, and gate A imports
   `market_benchmark`/`score_race`) to `src/run_gates.sh`'s registry, after the
   existing gates and after M2's `gate_pricing.py`. Final gate numbers are assigned
   in registry order at wiring time (do **not** hard-code "gate 11" anywhere —
   `GATES.md`'s table is the numbering authority). Update `GATES.md` with a row per
   gate and a note that A is a **liveness** gate (state-dependent, may legitimately
   red when capture is behind — that is its job) while B and C are hermetic
   prose→gate scans.
2. **Verify each goes red on a violation** before declaring done: gate A with an
   injected extra unpaired non-SS scored prediction (debt > 2); gate B with an
   injected "we are calibrated therefore we beat the book" line in a scratch doc on
   the scan path; gate C with an injected "calibration unlocks roadmap #5" line and
   with a calibration token injected into a copy of clean_air §0. Record the
   red-on-drift proof in the M4 report.
3. **Formalize the demote in the same commit** (memo §1.2 condition): update
   `plan/schedule.yml` `standfirst`/`bottom_line` and HANDOFF so the benchmark is
   described as **sovereign-and-gate-protected** with the model-book as a co-equal
   parallel thread — the demote and its tether ship together, never apart.
4. Leave the tree clean; all gates green (gate A green because capture is not yet
   behind), then commit.

---

## Resolved-ambiguity register (why, one line each)

- **Gate A counts capture-debt, tolerance 2** → the very first forward races settle
  the T-45 workflow; a sustained lapse (>2 non-SS races uncaptured while actively
  predicting) is the erosion the tether exists to catch. 5618's post-flag prices
  count as debt (that was the lapse), but sit under tolerance today.
- **Unresolvable races are advisory, never red** → an offline gate run must not
  spuriously block; only a genuine, resolvable lapse reds.
- **Gate A enforces capture, not book-binding** → binding is deferred (L5); the
  first admissible capture binds automatically, so requiring binding would double-
  punish a deliberate deferral.
- **Gate B is a boundary-scan with a separation allowlist, not a sentence
  whitelist** → self-maintaining: any new edge×calibration claim must also state
  the boundary, or it reds.
- **Gate C both asserts the market-gate text and forbids calibration tokens in #5
  execution** → the #5 unlock cannot be re-pointed to calibration without a red,
  which is the whole forbidden inference (calibration → edge → #5).
- **Numbers assigned at wiring time, not hard-coded** → `GATES.md` is the numbering
  authority; M2's pricing gate lands before these, so "gate 11" would be brittle.

---

## RESULT — tether gates (M4, 2026-07-20)

**Built, all three gates verified red-on-injected-violation, demote formalized in the same
commit, tree clean, 14/14 gates green.** `src/gate_benchmark_liveness.py` (Gate A),
`src/gate_calibration_not_edge.py` (Gate B), `src/gate_five_market_gated.py` (Gate C) — all
three implement this spec verbatim. Wired into `src/run_gates.sh` (after M2's
`gate_pricing.py`, conda interpreter) and `GATES.md` as gates 12/13/14 (numbers assigned at
wiring time, per `GATES.md`'s own numbering authority — not hard-coded as "gate 11/12/13").

**Gate A (liveness, state-dependent).** Reuses `market_benchmark.py`'s own
`load_all_predictions`/`load_snapshot`/`find_primary_book`/`graded_picks_for_race`/
`reconstruct_and_decide` verbatim — never recomputes admissibility. Today's run: 1 sealed
prediction (race 5618), primary book `draftkings` (bound at commit `5af852cce4`);
`P_scored_nonSS=1`, `K_adm=0` (the one non-SS scored race's book prices were post-flag,
inadmissible — this repo's own documented capture lapse), `capture_debt=1`. `TOL_DEBT=2`,
so **GREEN** — exactly the spec's own predicted "Current state 2026-07-20" line. 0
unresolvable races today. `predictions_active=True` (race 5618 is within `LIVE_WINDOW_DAYS=45`
of the run date), confirming the RED branch is reachable, not vacuously always-green.

**Gate B (hermetic).** Both positive sentinels present verbatim (whitespace-normalized,
markdown-bold-stripped match — spec prose is hand-wrapped at ~80–100 cols, so a literal
single-line substring check would spuriously miss sentinels split across physical lines by
word-wrap): HANDOFF's doctrine line, and `calibration_backtest.md`'s two non-substitution
phrases. Negative scan (EDGE-token × CALIBRATION-token × no SEPARATION-phrase, per-line,
quote-stripped) over the current doc set D (23 files): **0 violations.**

**Gate C (hermetic).** `clean_air_causal_pace.md` section 0 (FROZEN, read-only — never
edited) references `market_benchmark_decision_rule.md`, contains `EDGE`, and contains
sentinel 4 ("UNDERPOWERED does not unlock"); contains zero CALIBRATION-tokens and no
`calibration_backtest` reference. `calibration_backtest.md` section 3's sentinel-3 clause
present. Negative scan (#5-token × UNLOCK-token × CALIBRATION-token × no SEPARATION-phrase)
over D: **0 violations.**

**Red-on-injected-violation proof (spec's "Wiring + verification" point 2), all three
confirmed before shipping:**
- **Gate A:** an in-memory synthetic test (never touching real `predictions/` files, per
  doctrine's "no post-hoc predictions" — this exercises the gate's own code path only)
  monkeypatched `market_benchmark.load_snapshot`/`score_race._green_flag_utc` to add three
  extra resolvable, non-SS, zero-admissible-pick scored predictions on top of the real state,
  pushing `capture_debt` to 4 > `TOL_DEBT=2`. Confirmed RED.
- **Gate B:** a scratch file on the scan path (`specs/`) with one unquoted line asserting
  that the model's calibration means it out-performs the sportsbook — the same pattern the
  spec's own "we're calibrated so we beat the book" example describes — removed immediately
  after. Confirmed RED, correct file:line reported.
- **Gate C:** (a) a scratch file on the scan path with one unquoted line — the forbidden
  "calibration unlocks roadmap #5" inference stated as fact — removed immediately after;
  confirmed RED via the negative scan. (b) A calibration token injected
  into a **copy** of `clean_air_causal_pace.md` section 0 (in-memory mutation of the extracted
  section text, written to a `tempfile`, never touching the real frozen file); confirmed RED
  via `check_clean_air_section0`, and the real file re-verified to still produce 0 failures
  immediately after (frozen file integrity confirmed untouched).

**One genuine implementation-bridging finding, resolved (not escalated) — the same class of
choice C1/D1/M2/M3 resolved directly rather than stopping for owner input.** The negative
scan's literal reading (any line with an EDGE-token and a CALIBRATION-token and no
SEPARATION-phrase) false-positives on **this very spec's own defining prose** at both
raw-physical-line and blank-line-delimited-paragraph granularity, in three places: the Gate B
"Claim encoded" paragraph above (which describes, in order to forbid, the exact edge-from-
calibration assertion pattern); the Gate B worked example of a line that fails the scan; and
this spec's own Wiring-and-verification instructions for injecting that same example line to
prove Gate B goes red. All three *mention* the forbidden pattern as an illustration rather than
*asserting* it, but a mechanical per-line scan cannot tell mention from assertion by itself —
verified computationally against the live corpus (both granularities) before choosing a fix,
since this spec's own §"RED iff" text asserts as fact that this spec carries a
SEPARATION-phrase and passes, which is the acceptance bar the implementation must actually
meet. **Fix:** text inside straight double-quote pairs is stripped before token-matching each
line — a quoted phrase is mentioned (a worked example, an injection-test string) not asserted.
Verified: 0 false positives anywhere in D with the fix (down from 3), and the fix costs nothing against a
real violation — an actual bare, unquoted assertion is never inside quotes, so detection power
is unchanged (confirmed by the red-on-injection proofs above, none of which use quotes).
`CALIBRATION_TOKENS`/`SEPARATION_PHRASES`/`doc_files`/`strip_quotes`/`normalize` live in
`gate_calibration_not_edge.py` and are imported by `gate_five_market_gated.py` (not
redefined) so gates B and C's shared token lists can never drift apart — the spec's own
cross-reference "C from gate B" is implemented as a literal Python import, not a second copy.

**Demote formalized in the same commit.** `HANDOFF.md`'s doctrine paragraph and
`plan/schedule.yml`'s `bottom_line` now describe the market benchmark as **sovereign and
gate-protected** (mechanically, via gates 12–14 — not just by prose) with the model-book pivot
as a **co-equal parallel thread**, never a replacement. `plan/schedule.yml`: M4 → done; `next`
re-evaluated to **C4** (silver breadth extension #2 — the only ready, dependency-free,
non-owner-led item; M5 stays blocked on F10, F10/F1/F2 stay gated on ≥8 scored non-SS forward
races, G2 stays gated on market EDGE).

**No frozen-spec edit outside this RESULT block; `clean_air_causal_pace.md` read-only,
never edited; no change to `predict_next.py` / `walkforward.py` / `scores_log.csv`.** Gate
surface: 14/14 green before (11/11 inherited) and after. Environment: conda Python 3.13.5
(matches every other medallion gate).
