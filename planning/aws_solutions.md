# AWS solutions roadmap — PLANNING ONLY, nothing implemented

**Authorized 2026-07-18** by the owner: "plan future AWS solutions but not
implement them right now." This is a **living planning document** — unlike
`specs/`, it carries no freeze discipline and may be revised as facts
change. Every item below requires its own explicit go decision before any
build session runs. Nothing in this document touches the frozen model, the
weekly protocol, or the pre-registered specs.

## DECISION 2026-07-19 — AWS indefinitely deferred; local-first

The owner directed: **indefinitely defer any AWS build-out; lock up the
local capture solutions first before doing any AWS work.** Consequences:

- The **AWS build sessions A1–A3 (below) are frozen** — none may run until
  the owner explicitly lifts this deferral. They remain documented as the
  eventual cloud target, not a near-term plan.
- The **local capture plan (next section) is now the active path.** Every
  capture need is served locally first; AWS is revisited only if a local
  approach proves inadequate (the one concrete gap: a poller/odds job
  firing while the laptop is off — see per-item notes).
- No GitHub Actions on this private repo, local or otherwise (quota trap).
- This is still planning: each local item below needs its own owner go
  before a build session runs.

## Local-first capture plan (active)

All fetching already runs locally — `src/update_data.py` is a 4-line
`urllib` loop against `cf.nascar.com/cacher/...`. "Local capture" is
therefore mostly extending an existing loop; only the ephemeral live-feed
poller is genuinely new engineering. macOS scheduling primitives: `launchd`
(fires at wall-clock time, re-runs missed jobs on wake), `pmset schedule
wake` (wakes the Mac from sleep), `caffeinate -i` (holds the machine awake
for a race-window poll). The reliability gap vs AWS is only ever "the Mac
must be awake"; it does not matter for anything fetched after the fact.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---|---|---|---|---|---|
| L1 | Archive mirror + endpoint expansion | pending, ⬅ next local | Sonnet 5, thinking on, high | ~1 h | Back up all source data and start saving three extra archived feeds, so nothing is lost if NASCAR stops serving old races | Extend the `update_data.py` fetch loop to also pull `live-pit-data.json`, `live-flag-data.json`, `lap-notes.json` per race → `data/races/`; one-time backfill of ~163 races + fold into the weekly increment |
| L2 | Local closing-odds capture | pending, gated on odds-API coverage check | Sonnet 5, thinking on, high | 1–2 h | Automatically record betting prices every race morning from this machine | `launchd` job ~1 h pre-green → licensed odds API → raw JSON + paste-ready spec-§5.1 `book_prices.entries`; human still pastes+commits. Soft-fails (noticed, fixable) if Mac off Saturday |
| L3 | Local weekly pipeline | pending, gated on GitHub remote existing | Sonnet 5, thinking on, high | 1–2 h | Make the weekly public prediction post fire automatically | `launchd` detects qualifying off weekend feed → `update_data.py` + `predict_next.py` → git commit/push via existing local SSH key (no cloud credentials — simpler than the AWS version) |
| L4 | Local live-feed poller | pending, opportunistic (no consumer yet) | Sonnet 5, thinking on, high | 1–2 h | Start recording the one race-day stream that's otherwise lost forever, accepting gaps when the laptop is asleep | `pmset` wake pre-green → `launchd` starts poller → `caffeinate` held → poll `live-feed.json` @5–10 s → gzip JSONL to `data/`. Log will have holes on asleep/off race days |

Local ordering (flips the AWS priority): **L1 first** (trivial, immediate
retention hedge), **L2** if odds-API coverage checks out (the picks-feeding
link), **L3** once the GitHub remote exists, **L4** opportunistically —
irreversibility argues for starting *some* snapshot log, but no roadmap
item consumes it and the awake-Mac fragility makes a local log
"better-than-nothing," not dependable.

## Ground truth this plan stands on (probed live, 2026-07-18)

- `cf.nascar.com` is AWS CloudFront — the project already consumes
  AWS-served data. There is no separate "AWS feed" to unlock.
- The branded broadcast telemetry (throttle/brake/corner speeds, "powered
  by AWS") has **no public endpoint**. No solution below pretends otherwise.
- Archived and free, verified back to ≥2022 for the first race of every
  season: `live-pit-data.json` (per-stop in/out times, duration, tires,
  positions gained/lost), `live-flag-data.json` (timestamped flag
  transitions with lap numbers and comments), `lap-notes.json` (per-lap
  notes with driver IDs) — plus the already-used `lap-times.json` and
  `weekend-feed.json`.
- **The only ephemeral data:** the `live-feed.json` in-race snapshot stream
  (full running order, gaps to leader, last-lap speeds, ~5 s cadence).
  Post-race, only the final frame survives. Un-polled races are lost
  permanently.
- NASCAR's retention policy is undocumented. Four seasons of archives exist
  today; nothing guarantees they exist tomorrow.

## Candidate solutions, priority order

### S1 — Closing-odds capture (priority 1: feeds the project's central question)

- **Problem it solves.** The market benchmark
  (`specs/market_benchmark_decision_rule.md`) is fed *only* by closing H2H
  prices recorded before green flag. Manual capture is the single most
  fragile link in the whole forward test: a forgotten Saturday = zero picks
  from that race, forever (the spec forbids after-the-fact backfill). The
  power table says sample size N is the binding constraint — missed races
  are the most likely road to a wasted two-year UNDERPOWERED verdict.
- **Sketch.** EventBridge schedule on race days → small Lambda → a
  *licensed* odds API with NASCAR H2H matchup coverage → raw snapshot JSON
  to S3 → a formatter emits ready-to-paste `book_prices.entries` blocks
  (scoring spec §5.1 schema). A human still pastes and commits — the
  tamper-evidence workflow and the "recorded before the race" guarantee
  stay human-verifiable.
- **Cost.** AWS ≈ $0–1/mo (free-tier Lambda + pennies of S3). Odds-API
  pricing and NASCAR coverage must be verified at build time — coverage is
  the go/no-go fact.
- **Build trigger.** Owner go + confirmation that an accessible odds API
  actually lists NASCAR H2H matchups. Cost of delay: real and permanent
  (every unpriced race shrinks N).
- **Build session.** Sonnet 5, thinking on, effort high; ~1–2 h wall clock
  including account setup. No Fable needed — the judgment work is this plan.
- **Local alternative.** A cron job on the owner's machine does the same
  job with zero cloud setup but fails when the laptop is off on a race
  Saturday — reliability is the argument for AWS here, not capability.

### S2 — Race-day live-feed poller (priority 2: the only irreplaceable data)

- **Problem.** The snapshot stream is the one dataset that cannot be
  acquired later. No current roadmap item consumes it; its plausible future
  customers are all behind the market gate (in-race analysis, restart
  dynamics at sub-lap resolution). The argument for building *early*
  is purely the irreversibility; the argument against is doctrine (no
  consumer exists, and may never exist).
- **Sketch.** EventBridge → Lambda in 15-min segments (or one Step
  Function) across the race window (start time from `race_list_basic.json`
  + generous buffer) → poll every 5–10 s → gzipped JSONL per race to S3.
  Order ~50–100 MB/race raw, far less gzipped.
- **Cost.** ≈ $0–1/mo. Build: Sonnet 5 high, ~1–2 h. **Decision framing
  for the owner:** this is a pennies-per-month insurance policy against
  "we wish we'd been recording since 2026"; equally defensible to build
  next month or to consciously accept the gap until the gate reads EDGE.

### S3 — Raw-feed archive mirror (priority 3: cheap insurance)

- **Problem.** The project's replicability rests on NASCAR keeping four
  seasons of archives public. Retention is undocumented.
- **Sketch.** One-time backfill of every consumed endpoint for all 163+
  races (~a few hundred MB total) to S3, plus a weekly increment (the
  fetch paths already exist in `update_data.py`). Could equally be a local
  directory synced to any cloud storage.
- **Cost.** Cents/month. Build: Haiku or Sonnet, ~1 h; sensible to bundle
  into whichever of S1/S2 builds first rather than its own session.
- **Trigger.** Any sign of endpoint deprecation — or "while we're in
  there" during S1/S2.

### S4 — Weekly pipeline automation (priority 4: protocol integrity)

- **Problem.** The pre-race prediction commit is manual and deadline-bound
  (public timestamp before green flag). Human forgetfulness is the failure
  mode; one missed week costs a race from the forward log.
- **Sketch.** Scheduled job detects qualifying completion (grid posted in
  the weekend feed), runs `update_data.py` + `predict_next.py`, commits and
  pushes. Hardest parts: robust qualifying detection and git credentials in
  the cloud; **requires the GitHub remote to exist first** (it still
  doesn't). Explicitly NOT GitHub Actions on this private repo
  (account-wide Actions-minutes quota has burned twice before).
- **Cost.** ≈ $0–1/mo. Build: Sonnet 5 high, 2–4 h (credential handling
  dominates). **Trigger.** First missed or nearly-missed pre-race commit,
  or planned owner absence. While the owner is engaged weekly, manual is
  fine and keeps a human eye on every prediction before it publishes.

### S5 — In-race analytics / live betting infrastructure (deferred, not designed)

Behind three gates, in order: market benchmark reads EDGE → S2 has
accumulated real snapshot history → its own pre-registered spec. Designing
it now would be speculation stacked on an unproven edge. Recorded here only
so its absence is a decision, not an oversight.

## Guardrails (apply to all of the above)

- Planning only: no item builds without a per-item owner go.
- Licensed APIs only for odds — no scraping in terms-of-service gray zones.
- No GitHub Actions pollers/schedulers on this private repo (quota trap).
- Nothing bypasses the human commit loop or touches frozen specs/model.
- At build time, re-verify pricing/coverage claims — this document records
  2026-07-18 facts.

## AWS build sessions — FROZEN (deferred indefinitely, see DECISION 2026-07-19)

These remain the eventual cloud target if a local approach proves
inadequate. **None may run until the owner lifts the AWS deferral.** The
active plan is the local-first table above.

Goal: capture-side infrastructure that protects the forward test's sample
size and preserves irreplaceable data, at ~$1–3/mo total.

| # | Session | Status | Model + settings | Wall clock | Executive summary | Technical summary |
|---|---|---|---|---|---|---|
| A1 | S1 odds capture | pending, ⬅ next if any triggers | Sonnet 5, thinking on, high | 1–2 h | Stop losing the betting-price data the project's main question depends on; a robot records the prices every race morning | Verify odds-API NASCAR H2H coverage; EventBridge+Lambda snapshot to S3; formatter emits spec-§5.1 `book_prices.entries`; human pastes+commits |
| A2 | S2 live poller (+ S3 mirror bundled) | pending | Sonnet 5, thinking on, high | 1–2 h | Start recording the one race-day data stream that is otherwise lost forever; also back up all source data for pennies | Race-window Lambda segments polling `live-feed.json` @5–10 s → gzip JSONL → S3; one-time backfill of all consumed endpoints + weekly increment |
| A3 | S4 weekly automation | pending, gated on GitHub remote existing | Sonnet 5, thinking on, high | 2–4 h | Make the weekly public prediction post automatic so a busy Saturday can't break the experiment | Qualifying-detection off weekend feed; run update+predict; git commit/push with cloud-held credentials; alerting on failure |

Independence: A1, A2, A3 are fully independent of each other and of all
`specs/` work; any subset can build in any order. None may run before its
owner go.

**Bottom line:** AWS is deferred indefinitely (2026-07-19). Capture is
local-first — L1 (archive mirror) is the next actionable build, then L2
(odds) if coverage checks out, L3 once a remote exists, L4 opportunistically.
The AWS sessions above stay frozen as the eventual cloud fallback and run
only if the owner lifts the deferral.
