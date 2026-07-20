# Odds-source evaluation & primary-book recommendation — session L5

**Status:** research spike / recommendation. **Proposes only; acquires nothing.**
Changes no model and no spec. Produced 2026-07-20 (Opus 4.8, thinking on, xhigh).
The session **STOPS here for an owner GO** — steps 1–2 of L5 are done; step 3
(build the fetcher) is L2 and is owner-gated on the decisions below.

**Scope honored:** no gated/authenticated odds endpoint was hit. In particular
the DraftKings unofficial JSON (`sportsbook.draftkings.com/sites/US-SB/api/...`)
was **not** requested — hitting it is the very action the posture decision below
gates. All research came from public informational pages (news guides, vendor
pricing/coverage pages, published terms), never a live odds feed.

**Governs / feeds:** plan item **L2** (local closing-odds capture). Resolves L2's
dead "licensed odds API" assumption. Coordinates with **A6** (owner ToS posture)
and mirrors its method. Consumes the FROZEN
`specs/market_benchmark_decision_rule.md` amendments (primary-book binding,
admissibility, full-board duty) and `specs/scoring_methodology.md` §5.

---

## 0. The one finding that reframes everything

**Race 5618's inadmissibility was a *timing/workflow* failure, not a *source*
failure.** The manual DraftKings prices were fine data; they were committed at
23:26 UTC against a 23:00 UTC *scheduled* green flag — 26 minutes too late — so
they fail the admissibility amendment
(`market_benchmark_decision_rule.md` §"admissibility of price entries"): the first
commit containing an entry must be **earlier than the scheduled start** and, now
that a public remote exists (E2 — `github.com/nsharkey/nascar-cup-model`), that
commit must also be **an ancestor of a ref pushed before the scheduled start**.

The consequence: **every** candidate source (manual, licensed API, scrape) yields
admissible prices *if and only if* the entry is captured, committed, **and pushed
before the scheduled green flag**. Admissibility is a discipline the recording
workflow must enforce; it is orthogonal to which source we pick. Get the workflow
right (§4) and the N=0 bottleneck breaks with *any* of the sources below. Pick the
source for reliability, precision, effort, cost, and ToS posture — not for
admissibility, which the workflow owns.

---

## 1. What the owner is actually deciding (three coupled decisions)

| # | Decision | Reversible? | Recommendation (details below) |
|---|---|---|---|
| **D1** | **Primary book** — the single book whose closing H2H line is THE benchmark. Named in the first admissible priced commit, then **fixed** (spec §"primary book binding"). | **No** — permanent once bound (successor only by dated addendum, before any successor price). | **FanDuel** (mild lean), because it is the book a *licensed, non-scrape* feed is confirmed to carry — with **DraftKings** an equally-valid benchmark if you prefer manual capture. |
| **D2** | **Capture method** — manual / licensed aggregator / sportsbook scrape. | Yes — can change week to week; does not rebind D1. | **Licensed aggregator if a free-trial probe confirms NASCAR H2H depth; manual capture as the always-available clean floor. Do NOT scrape a sportsbook.** |
| **D3** | **Recording workflow** — the admissibility discipline. | Yes | Capture ~T-45, commit **and push** by ~T-30 vs *scheduled* green; full board; `closing:true`; primary book fixed. (§4) |

D1 and D2 are coupled: **choosing the primary book to match where a licensed feed
exists is what lets us avoid scraping entirely.** That coupling is the core of the
recommendation.

---

## 2. Evidence ledger

Credibility labels follow the F6 scan convention: **[V]** = verified from a primary
/authoritative page; **[vendor]** = vendor-asserted marketing/coverage claim not
independently confirmed at the market-name level; **[3p]** = third-party report.

### 2a. Does the H2H matchup market exist, and is it the right benchmark?

| Fact | Evidence | Cred |
|---|---|---|
| NASCAR driver **head-to-head matchups** (pick which of two drivers finishes ahead; American-odds two-outcome market) are a standard, popular Cup market. | FOX Sports NASCAR betting guide; CBS Sports NASCAR guide; Covers "how to bet" (worked example Hamlin −130 / Keselowski +100); NASCAR.com "Sports betting 101: H2H driver matchups". | [V] |
| Offered by the major US books: **DraftKings** (explicit `driver-props / matchups` subcategory), **FanDuel** ("driver matchups" listed for major events), BetMGM, Caesars, Fanatics, bet365. | FOX Sports guide; DK & FD motorsports pages (page *titles/paths* only — pages not fetched). | [V]/[vendor] |
| H2H is the correct benchmark market and ~52–53% pairwise is break-even after hold; H2H two-outcome hold is *low* (~4–6% two-sided) relative to 36–40-driver outrights. | `research/external_knowledge_scan.md` §4.1 (Sirois, NASCAR Bets; FOX Bet trading-ops example). | [V] |
| **Matchups offered per Cup race — count NOT pinned from public pages.** Guides say "dozens of drivers" and "browse all of them" but give no number. This is the single biggest driver of whether N reaches the §4/§5 boundaries (≥5–10/race → N≈220–440 by end-2027; thin → UNDERPOWERED). | Multiple guides queried; none quantify. Spec §5 already flags this exact risk. | residual (§5) |

### 2b. Licensed feeds (no sportsbook scrape — cleanest posture)

| Provider | NASCAR? | H2H driver matchups? | Books sourced | Price | Cred |
|---|---|---|---|---|---|
| **The Odds API** (the cheap default) | **No** — 26 sports, no motorsport, re-confirmed 2026-07-20. | — | — | — | **[V] dead end** |
| **SportsDataIO** | Yes (dedicated NASCAR API). | **Yes — "head-to-head driver matchups"**, plus **closing lines** and pre-match/in-play/historical; props published 3–5 days pre-race. | **FanDuel** now; "additional sportsbooks being integrated soon". | Production **sales-gated** (no public price; reported "exorbitant"); **free trial** exists. | [vendor] |
| **SportsGameOdds** | Yes. | "Prop markets include… head-to-head driver matchups" (generic; **not confirmed at market-name for NASCAR**). | 80+ books incl. **DK, FanDuel, BetMGM, Pinnacle**. | **Free tier** (9 books, 10-min delay); **Rookie $99/mo** (77 books, 3-min delay); Pro $249. **Per-event** billing (cheap for one race). 7-day trial on paid. | [vendor] |
| **OpticOdds** | Books incl. BetMGM/Kambi/Entain; 200+ books, fastest. | NASCAR H2H **not** confirmed. | 200+ | Custom quote, no public price; free trial. | [vendor] |
| **OddsMatrix** | Yes — "350+ pre-race & live NASCAR markets incl. driver matchups". | Yes (asserted). | B2B/bookmaker-facing. | Enterprise/licensing-gated. | [vendor] |
| **OddsJam** | Yes (100+ books, props). | Asserted. | 100+ | **~$5,000/mo [3p]** — out. | [3p] |

**Key takeaways:** (i) the *free/cheap licensed* trifecta is real only if
**SportsGameOdds** (free/$99) turns out to carry NASCAR H2H matchups at adequate
depth — unconfirmed without a trial probe. (ii) The *confirmed* licensed H2H route
is **SportsDataIO**, and it sources **FanDuel** — but at sales-gated (likely high)
cost. (iii) Using an aggregator does **not** violate primary-book binding: we
filter its response to the one bound book and record only that book's entries; the
aggregator is a *capture method*, not a multi-book blend.

### 2c. Sportsbook scrape (DK unofficial JSON, or a scraper vendor)

| Fact | Evidence | Cred |
|---|---|---|
| **DraftKings ToS explicitly prohibits** "using automated means including harvesting bots, robots, parser, spiders, or screen scrapers to obtain, collect, or access any information on the Website… **for any purpose**." | DraftKings Terms of Use (`sportsbook.draftkings.com/legal/watl-terms-of-use`); ToS;DR case 150; lineups.com T&C summary. | **[V]** |
| Enforced: DK has issued **cease-and-desist letters** and reviews scrapers for **account termination**. | Legal Sports Report ("DraftKings Issues A Cease And Desist Letter"). | [V] |
| The DK **unofficial JSON** (`.../sites/US-SB/api/v5/eventgroups/{id}`) is served from `sportsbook.draftkings.com` — squarely DK's own covered service — so it is inside the ToS, unlike cf.nascar.com which A6 found *outside* NASCAR's covered-services list. | prior finding (memory `nascar-odds-source-options`); §3 below. | [V] |
| **Third-party scrapers** (Apify "DraftKings odds" actors) exist at ~$0.01–0.04/snapshot or ~$25/mo + usage, $5 free credit. | Apify actor listings (parseforge, mherzog, zen-studio, harvest). | [vendor] |
| A scraper vendor does **not** launder the ToS problem: the data still originates from an automated scrape of DK's covered service, and it adds a fragile third-party dependency. | reasoning. | — |

---

## 3. ToS / scrape posture (L5 step 1) — coordinated with A6

Mirroring A6's discipline (verbatim clauses + verified technical facts; **no legal
position**; the judgment is the owner's):

- **The odds-scrape posture is *more* adverse than A6's NASCAR-feed posture, and
  the direction is reversed.** A6 found cf.nascar.com is **not** on NASCAR's
  covered-services list, carries no ToS link, and isn't bot-blocked — so formal ToS
  coverage of the JSON feeds is *textually unsupported*. For sportsbooks the
  opposite holds: DK's ToS **explicitly** names bots/scrapers/spiders and bars them
  "for any purpose," and the unofficial JSON lives on DK's own covered domain.
  There is no textual-coverage ambiguity to lean on here — the prohibition is clear
  and enforced (C&D, account termination). The same reading applies to FanDuel and
  any book's own automated surface.
- **Therefore the conservative posture — the one the repo already keeps (respect
  the source's terms; don't scrape bot-blocked/ToS-covered surfaces) — resolves the
  odds side by *avoiding the scrape*, not by parsing coverage.** A **licensed
  aggregator** holds the redistribution rights and moots the sportsbook-ToS
  question entirely. **Manual viewing + transcription** is ordinary use, not
  "automated means," so it is outside the automated-access clause.
- **Net posture recommendation:** do **not** scrape a sportsbook (neither the DK
  JSON directly nor via an Apify-style vendor). Use a licensed feed if a trial
  confirms it; otherwise capture manually. This keeps the odds posture consistent
  with A6's and needs **no** close ToS reading to proceed — the recommended routes
  simply don't trigger the clause. If the owner nonetheless wants the DK-JSON route,
  that is an explicit, informed posture call that belongs to the owner (as with
  A6), and it additionally risks the owner's **betting account** if tied to their
  identity — I recommend against it given a clean route exists.
- **One separate nuance to flag (not a scraping question):** the workflow commits
  raw odds *numbers* into the public prediction JSON. Individual odds values are
  facts (not copyrightable); a handful of matchup prices for a non-commercial
  research log is low-risk. A large redistributed odds *database* would be a
  distinct compilation/licensing consideration (some paid feeds also restrict
  redistribution). No legal position taken — surfaced for owner awareness, mirroring
  A6's "the model-development clause is the one to read personally."

---

## 4. Admissibility-safe recording workflow (L5 step 2 deliverable; D3)

This is what L2 must implement, and what the owner can do **manually starting this
weekend** regardless of the D1/D2 decision. It is the fix for the 5618 failure.

1. **Read the deadline from the feed.** The admissible-until moment is
   `start_time_utc` of the `event_name == "Race"` entry in that year's
   `race_list_basic.json` schedule block (the exact field the admissibility
   amendment names). Compute it up front so the deadline is explicit, not guessed.
   *(Note: this checkout currently has `src/data/race_list_2026.json`; L2 must read
   the schedule block the amendment specifies — a small provenance check for L2, not
   a blocker for this decision.)*
2. **Capture window:** snapshot the primary book's full H2H board at **~T-45 min**
   before *scheduled* green. Commit **and push** by **~T-30 to T-25** — comfortably
   before the scheduled start, with margin for clock drift and the (rare) early
   green. Never wait until T-0; that is exactly what sank 5618.
3. **Full-board duty (spec §"full-board recording"):** record **every** primary-book
   H2H matchup whose *both* drivers are in the predicted field — never a subset. If
   capture is partial (market pulled, access failure), note what was missed in the
   scores row.
4. **Entry fields (`scoring_methodology.md` §5.1):** each entry carries the fixed
   `"book"` value (the bound primary book — same string on every admissible entry),
   `recorded_utc`, `closing: true`, `driver_id_a/b`, `price_a/b` (nonzero American
   odds), `void:false`. Primary book is **named in this first commit** and fixed
   thereafter (D1 binding).
5. **Admissibility check (belt-and-suspenders):** after pushing, confirm the pushed
   commit's timestamp precedes `start_time_utc`. The `market_benchmark.py` §6 script
   already recomputes admissibility from git history at every look — this step just
   catches a miss the same night.

**Inherent, pre-registered property to understand (not a defect, not a change):**
because admissibility keys off *scheduled* start and NASCAR greens are usually
*delayed*, a T-45 snapshot is the **best admissible approximation of the closing
line**, not the last tick before green. That is locked by the frozen rule; L5 does
not touch it. Directionally, a slightly earlier line is marginally softer, which
biases *very slightly toward* detecting EDGE — the effect is small for low-hold
two-outcome H2H markets, and it is pre-registered and identical every week
(consistency is exactly what the primary-book-binding rationale protects). Flagged
for owner awareness only.

---

## 5. Residual unknowns (resolved by L2's first action, not blockers now)

1. **Matchups offered per Cup race** (drives N and thus the entire power picture).
   Not pinnable from public pages. **Resolved empirically** by the first 2–3 weekly
   captures — and it is the same number whether captured manually or by API, so it
   does not gate the source decision.
2. **Whether an *affordable* licensed feed (SportsGameOdds free/$99) actually
   returns NASCAR H2H matchups at adequate depth and latency.** Vendor pages assert
   it generically; confirmation needs a **free-trial / API-key probe**, which is L2
   implementation, not L5 research. This is the pivot: if it confirms → clean +
   cheap + programmatic; if not → SportsDataIO (clean, confirmed, costlier) or
   manual (clean, free, confirmed).

Both unknowns are **downstream of the GO**, not preconditions for it.

---

## 6. Recommendation to the owner (the GO)

**D1 — Primary book: FanDuel (mild lean), or DraftKings if you prefer manual.**
Both are co-largest, efficient US books with driver-matchup boards → both are valid,
"hard" benchmarks. The tie-breaker is *capture optionality*: FanDuel's NASCAR H2H
matchups are the ones a **licensed, non-scrape** feed is confirmed to carry
(SportsDataIO) and an affordable one plausibly carries (SportsGameOdds). Binding to
DraftKings leaves only a **ToS-violating scrape** or **manual capture** as
programmatic routes, because no licensed feed of *DK's* NASCAR H2H was confirmed and
DK's ToS bars scraping. If you would rather keep viewing the book you already use
(DK) and capture **manually**, DK is an equally good benchmark — the only cost is a
harder path to a future clean *programmatic* upgrade. **This decision is permanent
once bound, so it is genuinely yours to make.**

**D2 — Capture method (tiered):**
1. **Licensed aggregator, pending a trial probe.** In L2, free-trial
   **SportsGameOdds** (cheapest: free tier / $99 Rookie) and **SportsDataIO**
   (confirmed FanDuel H2H, sales-gated). Adopt the cheapest that returns the bound
   book's NASCAR H2H board at adequate depth and ≤10-min latency. Clean posture, no
   sportsbook ToS exposure.
2. **Manual capture — the always-available clean floor**, and the **interim you can
   start this weekend**: view the primary book's H2H board, transcribe per §5.1,
   commit+push per §4. Free, ToS-clean, confirmed.
3. **Not recommended: scraping a sportsbook** (DK JSON or Apify). Clear ToS
   violation ("for any purpose"; C&D + account-termination enforcement); risks your
   betting account; fragile. Only on an explicit, informed owner posture call — and
   avoidable, since a clean route exists.

**D3 — Recording workflow:** adopt §4 (capture ~T-45, commit+push by ~T-30 vs
*scheduled* green, full board, `closing:true`, fixed book). This is the actual fix
for the N=0 bottleneck and works under any D1/D2 choice.

**Bottom line:** the bottleneck was never the source — it was committing after the
scheduled green. Recommend **FanDuel as primary** (for the clean licensed-capture
path) with **manual capture on the fixed early-commit workflow starting the next
race weekend**, and a **licensed-aggregator trial** as L2's first task to decide
whether to automate. **No sportsbook scraping.** Awaiting your GO on D1/D2 before
any of L2 is built — nothing here is implemented.

---

## 7. DECISION (owner, 2026-07-20)

- **D1 — Primary book: DEFERRED.** Do **not** bind the primary book yet. Keep manual
  capture as the interim; let **L2's free-trial probe** reveal which book a clean,
  non-scrape licensed feed covers best for NASCAR H2H *before* the permanent binding
  is committed. Consequence: the binding takes effect (spec §"primary book binding")
  only in the first commit that records an admissible price naming the book — so
  **the interim manual captures below must not be treated as binding the book**
  unless/until the owner names it. (Practically: the owner should decide the book at,
  or just before, the first weekend they intend to capture *admissibly*; a manual
  capture done purely as anecdotal testing, like 5618, does not force the binding.)
- **D2 — Capture direction: manual now + trial a feed in L2.** Start admissible
  manual capture on the §4 fixed workflow at the next race weekend (via the E1 loop),
  and make **L2's first task** the free-trial probe of SportsGameOdds (free/$99) and
  SportsDataIO (free trial) to confirm NASCAR H2H depth/latency/cost and decide
  whether to automate. **No sportsbook scraping** (confirmed).
- **Not authorized in this session:** L2 is not built here (separate session);
  no spec/model touched; the plan/HANDOFF status edits are proposed to the owner,
  not applied unilaterally (parallel-session hygiene).

---

## 8. L2 step-1 probe results (2026-07-20)

**Status:** the free-trial probe this section's §6/§7 called for. Proposes only; no
fetcher built, no spec/model touched, no primary book bound. No sportsbook was ever
hit — only the two licensed aggregators, and only with keys the owner obtained
themselves (I have no browser/form-fill tool, so account creation was necessarily
the owner's action; I ran the read-only queries once a key existed).

### 8a. SportsDataIO — key-gated probe (real endpoint discovery + real trial data)

The public docs page (`sportsdata.io/developers/api-documentation/nascar`) is a
client-rendered shell, but its initial HTML payload embeds the full endpoint catalog
and coverage-tier copy server-side — fetched directly (not via the rendered page) to
recover it:

- **Real endpoint catalog** (the doc names differ from the guessed ones): `odds/json/
  BettingEvents/{season}`, `BettingEventsByDate/{date}`, `BettingMarkets/{eventId}`
  (not `BettingMarketsByEvent`), `BettingMarketsByMarketType/{eventID}/{marketTypeID}`,
  `BettingMarketsByRaceID/{raceID}`, `BettingMetaData`, `ActiveSportsbooks`,
  `RaceOdds/{Raceid}`, `RaceOddsLineMovement/{Raceid}`.
- **`BettingMetaData` (real, unscrambled reference data) confirms `BettingMarketTypeID
  3 = "Head To Head Prop"` is a genuine, actively-defined NASCAR market type** — not
  just marketing copy. The same embedded doc payload independently confirms this at
  the product-description level: NASCAR's "Props" coverage tier reads *"Race props
  include things like Head to Head props and Group Props 3+"*, and NASCAR's "Props"
  add-on reads *"available as both pre-match including timestamps for opening price,
  all line movement changes, and closing price"* — i.e., their production feed is
  documented to carry exactly the closing-price-with-timestamp shape
  `scoring_methodology.md` §5.1 needs, if bought.
- **What the free trial actually returns is not usable for confirming depth/latency.**
  Queried all 99 events on the 2026 Cup/Xfinity/Truck/Futures schedule via
  `BettingMarkets/{eventId}`:
  - Only **9 of 99 events have any market rows at all**, and every one is from
    **Feb 15 – Apr 19, 2026** (Daytona 500 through Kansas). Nothing since — not
    Coca-Cola 600, not last week's North Wilkesboro, not the upcoming Brickyard 400,
    not any playoff race. Last `Created` timestamp anywhere: 2026-04-16. This reads as
    a one-time stale sync at trial activation, not a live feed.
  - On every market row, `BettingMarketType`, `BettingBetType`, `BettingPeriodType`,
    and `DriverName` are the literal string `"Scrambled"`; `Name` and `DriverID` are
    `null`; `AvailableSportsbooks` and `BettingOutcomes` are always empty `[]`
    (`ActiveSportsbooks` similarly returns 17 real `SportsbookID`s all named
    `"Scrambled"`). Trial data cannot identify which book, which driver pair, or any
    price — matches the trial welcome page's own "some data points are scrambled"
    disclosure, more thoroughly than expected.
  - The numeric `BettingMarketTypeID` survives scrambling (only names are replaced).
    Cross-tabulating all 49 market rows from the 9 populated events against
    `BettingMetaData`'s real type table: **`3` (Head To Head Prop) appears 3 times,
    across 2 of the 9 events** (Pennzoil 400, Food City 500) — so the market type is
    confirmed *present in real historical production data*, not merely documented,
    but the observed depth (1–2 H2H rows per race that has any) is far below the
    "5–10 matchups/race" §5's accrual math assumed, and — because the data is frozen
    at April and every field that would prove it's the *current* board is scrambled —
    **this trial cannot confirm current-week depth, latency, or book coverage** for
    the upcoming Brickyard 400 or any live race. Filtering by
    `BettingMarketsByMarketType/{id}/3` did not reliably return only type-3 rows,
    so it isn't a dependable way to isolate H2H markets either.
  - **Net for D2:** the "does SportsDataIO carry NASCAR H2H matchups" question is
    now answered **yes, confirmed at the schema and historical-data level** — stronger
    than L5's `[vendor]`-only evidence. But "at what current depth, latency, and cost"
    remains **unresolved by the free trial** — that requires either the paid Props/
    Props Plus tier (sales-gated, per L5 likely high cost) or their separate Replay
    tool (real unscrambled historical playback — not probed this session; would need
    the owner to point at it from their dashboard, and it's retrospective, not a
    live-capture proof).

### 8b. SportsGameOdds — documentation-only (no key obtained this session)

No SportsGameOdds account was created. Public-page fetches (`/docs`, `/docs/reference`,
`/docs/basics/cheat-sheet`, `/motorsport-betting-odds-api/`) were checked the same
way as SportsDataIO's (raw HTML, not the rendered SPA shell) — these pages *did*
return real embedded content (100–190 KB each, not just a loading shell), unlike the
thinner marketing pages checked pre-signup. **None mention NASCAR, motorsport, or a
`leagueID` anywhere** — not in the endpoint reference, not in the parameter cheat
sheet. The dedicated "Motorsport Betting Odds API" landing page (checked in the
earlier evidence ledger, §2b) never names NASCAR specifically either, only generic
"motorsports." An unauthenticated call to `api.sportsgameodds.com/v2/leagues`
correctly 401s (`"Missing API key"`) — league enumeration needs a live key, so this
remains not-fully-ruled-out, but the complete absence of NASCAR from every
documentation surface checked (vs. SportsDataIO's explicit, repeated, market-name-
level NASCAR documentation) is a real negative signal, not just an absence of
positive evidence.

### 8c. Recommendation

**Automate: not yet — not at the free tier.** Neither provider's free/no-cost path
clears the bar §6 set ("adopt the cheapest that returns the bound book's NASCAR H2H
board at adequate depth and ≤10-min latency"): SportsDataIO's trial is real but
structurally blind to depth/book/latency (scrambled + stale); SportsGameOdds shows
no documented NASCAR H2H coverage to even trial. Recommend:

1. **Continue admissible MANUAL capture** (already authorized, E1) as the only
   currently-confirmed method — unchanged from L5.
2. **If the owner wants to pursue automation**, the concrete next step is a SportsDataIO
   sales conversation for **Props** or **Props Plus** pricing (Props Plus adds line
   movement, which would let capture timestamps be verified after the fact rather than
   trusted at capture time) — now backed by documentation confirming the market exists
   and carries closing-price timestamps, not just a trial-tier guess. SportsGameOdds is
   not recommended to pursue further absent a key showing real NASCAR coverage, given
   zero documentation surface for it.
3. **Primary book binding stays DEFERRED.** This probe did not produce grounds to name
   FanDuel or DraftKings with more confidence than L5 already had (SportsDataIO's
   confirmed feed still sources FanDuel per L5's original evidence) — no new
   information changes that lean, it's just less speculative now.
4. **Cross-project note (owner-raised, 2026-07-20):** the owner's unrelated NFL project
   (`~/Downloads/nflverseanalytics`) sources odds from **The Odds API**, currently on its
   **free tier** ($0/mo) with a documented upgrade trigger at **~$150/season**
   (`docs/decisions/163-player-prop-market-data.md` there) — verified read-only, no edits
   made. That vendor has zero NASCAR coverage at any tier (re-confirms §2b's The Odds API
   dead end from the other direction), so **no vendor consolidation is possible through
   it**. The angle that *does* exist: SportsDataIO's full commercial access is a single
   custom quote spanning all 13 of their covered sports (including NFL) at once, not
   priced per-sport — so **if a SportsDataIO sales conversation happens (item 2 above),
   ask for an NFL+NASCAR bundle quote, not a NASCAR-only quote**; a price that doesn't
   clear the bar for NASCAR alone might clear it once it's also displacing the NFL
   project's future paid-tier need. Not actioned — the NFL project's Odds API integration
   is real, working, decision-documented infrastructure (decisions 161/162/163) on a free
   tier with no urgency to change; this is a fact banked for whoever has that sales call,
   not a recommendation to migrate it.

**Not authorized in this session:** no fetcher built (Step 2 stays gated on owner GO
per this session's kickoff), no primary book bound, no spec/model touched. Plan/HANDOFF
edits proposed below, not applied — owner review requested before commit, consistent
with §7's parallel-session hygiene.

---

## 9. L6 — comprehensive vendor spike (2026-07-20)

**Status:** the deeper, wider spike §6/§8 called for. **Proposes and prices only** — no
production subscription acquired, no sportsbook endpoint hit, no primary book bound, no
model/spec touched. Evidence from public vendor/journalism pages, one owner-provided fact
(the SportsGameOdds league list), the SGO pricing page, and a read-only read of the owner's
NFL project (`~/Downloads/nflverseanalytics`, decision 163). Produced Opus 4.8, thinking on,
xhigh. Cost lens (owner, 2026-07-20): **hobby project, default $0/manual; a paid option must
earn its keep on quantified evidence, not marketing copy.**

Credibility labels as elsewhere: **[V]** primary/authoritative page · **[vendor]** marketing
claim · **[3p]** third-party report · **[owner]** owner-supplied fact.

### 9.0 Headline — no viable vendor; stay manual

**No odds vendor is viable for this project at hobby scale. Recommendation: continue
admissible MANUAL capture (E1's workflow), do not automate, do not buy anything.** A
vendor would have to be all four of these at once, and none is:

1. **Hobby-affordable** (not enterprise/sales-gated at $k/mo),
2. **Real-time enough to be admissible** — the closing price must be fetched and committed
   *before the scheduled green flag* (the admissibility amendment); a delayed/next-day feed
   can never satisfy this,
3. **Confirmed to actually carry NASCAR odds** (not generic "motorsports"), and
4. **ToS-clean for committing raw prices into the public repo** — which the admissibility
   mechanism *requires* (the pre-race public commit is the proof-of-timing).

Every candidate fails ≥1 axis, and among the licensed feeds the failures are effectively
mutually exclusive: the ones that *have* NASCAR (SportsDataIO, OddsMatrix) are
enterprise-priced and/or delayed and ToS-restricted; the ones that are *cheap and
self-serve* (SportsGameOdds, The Odds API, OddsPapi) all **lack NASCAR entirely** — SGO and
OddsPapi both owner-verified NASCAR-free (2026-07-20).
**Admissibility was never a *source* problem** — race 5618 failed because prices were
committed 26 min after the scheduled green, and the T-45 commit-and-push workflow (§4) fixes
that for free — so the manual DK-viewing path, already authorized under E1, is the only route
clean on all four axes.

### 9.1 Vendor comparison table

Ongoing = live/current-odds price. Historical = backfill (descriptive-only here — the
admissibility amendment bars backfilled prices from the market-benchmark statistic forever,
§9.4). "Admissible?" = can it deliver a pre-scheduled-green closing price at all.

| Vendor | NASCAR odds? | H2H matchups? | Ongoing $ | Historical $ | Real-time / admissible? | Self-serve? | Books | Public-repo ToS | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Manual view (DK / FanDuel)** | **Yes** [V] | **Yes** [V] | **$0** | n/a | **Yes** (T-45 workflow) | n/a (human) | the book itself | **Clean** — human viewing = ordinary use; odds logged as facts, no licensor contract | **IN — the floor & the recommendation** |
| SportsDataIO | Yes [V] | **Yes, documented** [V] | Discovery Lab $99–149/mo **(next-day-delayed)**; live = commercial quote **≈$16.5k/yr** [3p] | separate SKU, sales-gated (2019+) | **No** at hobby tier (delayed); yes only at ~$16.5k/yr | Discovery Lab yes (delayed); live no (sales) | FanDuel (+"more soon") | Bars publishing w/o written consent [V] | **OUT** — cheap tier inadmissible; admissible tier enterprise-priced; ToS |
| OddsMatrix (EveryMatrix) | Yes — "350+ NASCAR markets incl. driver matchups" [vendor] | Yes [vendor] | enterprise quote | enterprise | (enterprise) | **No** — sales-gated, bookmaker-facing | 150+ | contract-gated | **OUT** — no affordable self-serve door |
| OpticOdds / OddsJam **API** (same feed) | Unconfirmed (generic "Motorsports"; not documented) | Not documented | **≈$5k/mo** [3p], sales-gated | separate, undisclosed | (would be) | **No** — sales-only, no trial | DK yes; FanDuel unconfirmed | scraped feed, active litigation; contract | **OUT** — price, access, unconfirmed coverage |
| OddsJam **consumer** tool | NASCAR hub exists; H2H *display* unconfirmed | Unconfirmed | **$100–300/mo** (Screen plans) | — | (human read) | Yes, 7-day trial | DK + FanDuel | personal-use; transcription a gray area | **OUT** — cost with no edge over free DK viewing (single-book binding negates a multi-book screen) |
| OddsPapi | **No** — no motorsports odds (owner-verified 2026-07-20) | No | usage-based; no-card free tier | free (claimed) | — | Yes (instant key) | DK/FD/Pinnacle among 300+ | bars redistribution "as a standalone product" | **OUT** — no motorsports odds at all, same as SGO |
| SportsGameOdds | **No** [V][owner] | No | free / $99/mo | $299/mo Pro | — | Yes | DK/FD (paid tiers) | bars redistribution, no carve-out [V] | **OUT** — zero motorsport in the league list |
| The Odds API | **No** [V] | No | free / $30–249/mo | 10× multiplier | — | Yes | many | permits illustrative quotes | **OUT** — no NASCAR at any tier |
| Sportradar | **No odds** (NASCAR product = timing/scoring/settlement; Odds API omits NASCAR) [V] | No | ≈$10k+/mo [3p] | — | — | No (sales; 30-day trial) | 140+ | contract | **OUT** — no NASCAR *odds*; enterprise |
| Unabated | **No** (NASCAR not in sport list) [V] | No | $3,000/mo | — | — | Yes (API) | many | — | **OUT** — no NASCAR |
| Genius Sports / LSports | enterprise, NASCAR-H2H unconfirmed | unconfirmed | enterprise quote | enterprise | — | No (sales) | — | contract | **OUT** — enterprise-only |

### 9.1a Ranked — closest-to-viable first (all are currently OUT)

The ranking is "least far from viable for *this hobby project*," weighting confirmed-NASCAR
coverage, admissibility, cost, self-serve access, and public-repo ToS. It is the order in
which to revisit if a revisit trigger (§9.7 item 6) ever fires — **not** a buy list.

1. **SportsDataIO** — the strongest coverage by far (only vendor with documented NASCAR H2H +
   the full market suite) and it has a self-serve tier. OUT only because the affordable tier is
   next-day-delayed (inadmissible) and the admissible tier is ~$16.5k/yr, plus a publish-consent
   ToS. **Revisit first**: a real-time *NASCAR-only* sales quote (+ ask for non-commercial
   publishing consent, and whether Replay carries the NASCAR odds feed for free depth
   validation). Also the best (only documented) historical/descriptive option.
2. **OddsMatrix** — confirmed rich NASCAR coverage (driver matchups, real-time), but pure
   enterprise B2B: no self-serve, no public price. OUT on access; revisit only under a
   commercial framing.
3. **OpticOdds / OddsJam API** — ~$5k/mo, sales-gated, NASCAR H2H undocumented, scraped feed
   amid active litigation. OUT on cost + access + coverage-confidence + legal risk.
4. **OddsJam consumer Screen** — self-serve, $100–300/mo, but no edge over *free* DK viewing
   under single-book binding, and H2H display unconfirmed. OUT on value.
5. **Sportradar** — enterprise (~$10k+/mo), and its NASCAR product is timing/scoring/settlement
   data, not an H2H-odds feed. OUT.
6. **SportsGameOdds · OddsPapi · The Odds API · Unabated · Genius Sports · LSports** (bottom,
   tied) — **no NASCAR odds at all.** SGO and OddsPapi are both owner-verified NASCAR-free
   (2026-07-20); the whole cheap/self-serve category is empty of NASCAR. Nothing to revisit.

**What the re-rank exposes:** with OddsPapi confirmed out, the list splits cleanly — every
vendor that *has* NASCAR (#1–#3) is enterprise-priced, sales-gated, and/or inadmissible, and
*every* cheap self-serve option (#6) is confirmed to have no NASCAR. There is no longer any
low-cost door even to probe.

### 9.2 Per-vendor walls (one line each)

- **SportsDataIO** — the *only* vendor with market-name-documented NASCAR H2H (and the full
  suite). But its one affordable self-serve tier (**Discovery Lab, $99–149/mo**) is
  **next-day-delayed** → structurally inadmissible (a ~24h-stale line either isn't available
  pre-race or is far from close, corrupting "beat the *closing* line"); live/admissible odds
  need the **commercial tier, sales-gated ≈$16.5k/yr** [3p Vendr]; and the ToS bars publishing
  odds without written consent. Historical is a separate sales-gated SKU (2019+). The **Replay
  tool** is free + *unscrambled* but a testing replay on the live schedule — not a live feed,
  not a queryable history. Closing-price-with-timestamp requires the "Plus" line-movement
  endpoints.
- **OddsMatrix** — has exactly the data (driver matchups), but bookmaker-facing B2B licensing,
  no published price, no self-serve; the only door is "request a quote."
- **OpticOdds = OddsJam** — the same feed (OddsHoldings, acquired by Gambling.com Group),
  sold twice; ~$5k/mo, sales-gated, no trial, NASCAR driver-matchup market undocumented, feed
  built by scraping books amid active data-use litigation.
- **OddsJam consumer Screen** ($100–300/mo, self-serve) — has a NASCAR hub and DK/FanDuel, but
  couldn't confirm it *displays* driver H2H matchups; and since the benchmark binds **one**
  book, a multi-book aggregator screen buys nothing over viewing DK's own board for free.
- **OddsPapi** — RULED OUT: **owner-verified 2026-07-20 that it offers no motorsports odds at
  all** (like SGO). Cheap and self-serve, but zero NASCAR — the door that looked cheapest to
  probe is closed.
- **SportsGameOdds** — RULED OUT: zero motorsport in the `leagueID` authority list
  (owner-confirmed), plus a redistribution ToS wall.
- **The Odds API / Unabated / Sportradar-odds** — no NASCAR at all. **Sportradar's** NASCAR
  product is official timing/scoring/settlement data, not an H2H-matchup odds feed.

### 9.3 Per-race depth (the biggest unpinned number, now pinned) + power

**H2H matchups, single book, at close: ~12–15 (DraftKings-type ~15–25; FanDuel-type ~6–12
pure 1v1).** Hard anchor [V]: an odds-comparison grid for North Wilkesboro (an *ordinary*
short-track race) showed **44–50 distinct 1v1 matchup rows as the union across ~10 books**.
No single book fills every cell, so the per-book figure is a reasoned inference (the no-scrape
rule blocked counting a single book's own board), but a ~44–50 union can't be reconciled with
the widest book posting only 5–10. The board is **at/near its fullest at close** (matchups are
added after qualifying and rarely pulled). **This is higher than `market_benchmark_decision_
rule.md` §5's 5–10 assumption**, and it upgrades the power outlook:

| Single-book H2H depth | N by end-2026 | N by end-2027 | Terminal outlook |
|---|---|---|---|
| 5–10 (old §5 assumption) | ~70–140 | ~220–440 | marginal; UNDERPOWERED risk |
| **~12 (conservative central)** | **~160** | **~530 → capped at 400 final look** | reaches the final look; ~0.6–0.7 power at true 58% |
| ~15–20 (DraftKings) | ~200–260 | 660–880 → capped 400 | hits N=400 *during* 2027 |

So at realistic depth the frozen H2H benchmark **crosses N≥200 (NO-EDGE boundary) in early
2027 and reaches the N≥400 final look mid-2027** — adequately powered to detect a genuine
sharp edge (~58–60%), not only a blowout. Two riders: (i) only **one** book's ~12–15 counts —
the union ~40–50 is unusable because the primary-book-binding amendment prohibits a multi-book
blend; (ii) the single-book count is an inference the **first few weeks of real manual capture
will pin empirically** — precisely the residual unknown §5 itself flagged, now resolved by
*doing the capture*, not buying a feed.

**All bet types (owner scope, 2026-07-20): ~150–350 priced non-H2H outcomes per race, one
book.** The reliably-present-at-close backbone is ~150 [V-anchored on an archived DK Coca-Cola
600 board]: Race Winner (~38 drivers) + the Top-3/Top-5/Top-10 full-field ladder (~114) +
Manufacturer (3); group matchups add ~15–50; stage/pole/fastest-lap/laps-led/margin/specials
are thin/variable/marquee-only. **Holds vary sharply and matter:** Race Winner outright
**~32%** [V, computed] (very hard to beat — a poor skill test); Top-5/Top-10 yes/no
**~8–15%**; group matchups **>15%**; **H2H ~5–6%** (the lowest — exactly why it is the frozen
gate); championship futures ~26%. The model already emits `p_win`, `p_top5`, `p_top10`, and
the `h2h_prob` matrix, so all of these are *scoreable* — but hand-capturing the full ~150–350
board before each green flag is **not humanly feasible**, and no automation is viable to do it
(§9.0). This forces scoping (§9.7).

### 9.4 Ongoing vs historical (priced separately everywhere; historical de-prioritized)

- **Ongoing is the only kind the frozen benchmark can ever use** (admissibility = commit
  before scheduled green). **Historical/backfill can never feed the statistic** — the
  admissibility amendment structurally bars it. Its only legitimate role would be a separate,
  clearly-labeled **descriptive** retrospective calibration.
- **Historical is a separate, higher-cost product at every vendor that has it:** SportsDataIO
  (separate sales-gated SKU, 2019+), SGO (bundled only in the $299/mo Pro tier — but SGO has
  no NASCAR), OddsPapi (free — but no NASCAR, owner-verified). This mirrors the NFL project's decision
  163 finding (The Odds API historical = a hard **10× multiplier**): NASCAR vendors show the
  same directional "history costs more / is gated higher," structured as a separate SKU rather
  than a literal 10×.
- **Recommendation: do not pursue historical.** It is not cheap anywhere with *confirmed*
  NASCAR, it is descriptive-only, and its descriptive value is further discounted because the
  163 backtested races overlap the model's own fitting window (in-sample calibration is weak
  evidence). Revisit only if a **free, confirmed-NASCAR** source ever appears.

### 9.5 "All bet types" — scope reconciliation (no frozen change)

The owner's direction to analyze **all available bet types**, not just H2H, is well-founded
(the PL model already emits win/top-5/top-10/H2H probabilities). But it must respect one
boundary: **the frozen `market_benchmark_decision_rule.md` gate is H2H-only and immutable**
(H2H was chosen for its lowest hold — the cleanest skill test). "All bet types" therefore
lives as a **separate analysis layer** — descriptive, or a cleanly pre-registered *successor*
test (the extension-discipline amendment already permits one, using only picks first graded
after its own registration date) — **complementing, never rewriting** the H2H gate. It also
needs a **new capture schema**: the frozen `book_prices.entries` shape (scoring §5.1) is
H2H-specific (`driver_id_a/b`, `price_a/b`), so storing winner/top-5/top-10 odds is a new
structure and a new spec — **future design work, not part of L6 or L2.**

### 9.6 The ToS structural finding (why the public-commit requirement favors manual)

The admissibility mechanism *requires committing the raw prices into the public repo* — that
public commit is the proof-of-timing. Every licensed feed checked (SGO, SportsDataIO,
OddsPapi, OpticOdds) restricts redistribution/republishing of its data, mostly with **no
non-commercial/research carve-out**; The Odds API is the lone exception that permits "a handful
of illustrative quotes" — and it has no NASCAR. So the public-commit requirement **structurally
favors the manual path**: a human viewing a book's screen and logging the price as a *fact* is
not a licensee bound by a no-republish clause. Counterintuitively, "just view DK and
transcribe" is the *most* ToS-defensible route precisely because there is no licensor contract
— consistent with the A6 posture and the §3 conclusion.

### 9.7 Recommendation to the owner (the GO ask)

1. **Capture method — STAY MANUAL. Do not automate; buy nothing.** No vendor is
   affordable + admissible + confirmed-NASCAR + public-repo-ToS-clean. Admissibility is owned
   by the §4 workflow, not the source.
2. **Primary book — recommend DraftKings** (owner's permanent call; binds only at the first
   admissible-priced commit naming it). This **updates L5's mild FanDuel lean**: that lean
   rested on FanDuel being the book a *licensed feed* covered — now moot, since no licensed
   feed is viable. On the axis that remains, DraftKings offers **~15–25 H2H matchups vs
   FanDuel's ~6–12** — roughly **2× the depth, N, and power**. FanDuel stays a valid benchmark
   if preferred, at ~half the accrual.
3. **Scope of weekly capture (this is where "all bet types" resolves against feasibility):**
   - **Gate (do this):** the **H2H full board (~12–15)** at the bound book — feasible by hand
     in a few minutes, admissible via §4, and the frozen pre-registered statistic.
   - **Descriptive layer (opt-in, later, separate spec):** if pursued, capture the model's
     other *clean* two-outcome outputs — **top-5 and top-10** — not the full ~150–350 board.
     The high-hold outright winner market (~32%) is a poor skill test; thin/marquee markets are
     low value. Needs a new schema + new pre-registration (§9.5).
   - **Do not** attempt full-board all-market manual capture every week — infeasible, and no
     automation exists to do it.
4. **Historical — do not pursue** (§9.4). Descriptive-only, not cheap with confirmed NASCAR,
   leakage-discounted.
5. **L2 — "build the fetcher" is not actioned** (no vendor to fetch from). L2 could optionally
   be repurposed as a **manual-capture *assist*** (a script that surfaces the field's valid
   matchups and validates/timestamps the pasted entries against admissibility — no vendor
   fetch, no scrape). That is a smaller, different tool for the owner to decide on separately.
6. **Revisit triggers** (re-open automation only on one of): (a) a sportsbook publishes a
   **free official** NASCAR-matchup API with permissive ToS; (b) a **cheap self-serve** vendor
   **confirms** NASCAR H2H *and* has public-repo-friendly terms (no current candidate — both
   cheap self-serve aggregators, SGO and OddsPapi, are owner-confirmed NASCAR-free); (c) the
   project adopts a commercial framing that justifies an enterprise feed's cost.

**Bottom line:** the spike set out to find whether paying for odds automation earns its keep,
and the honest answer is **no — not at hobby scale, because no vendor clears all four
gates.** The manual path is not a fallback; it is the *only* option clean on admissibility,
coverage, cost, and ToS at once — and the newly-pinned depth (~12–15 H2H/book) shows it can
carry the benchmark to an adequately-powered verdict. Keep doing admissible manual capture on
the §4 workflow; bind DraftKings for depth when ready; treat "all bet types" as a scoped,
separate descriptive layer if and when the owner wants it. **No purchase, no binding, and no
fetcher build is authorized by this spike — awaiting the owner's GO.**

### 9.8 DECISION (owner, 2026-07-20) — superseded upstream by a strategic pivot

The vendor question is **resolved: no viable vendor; stay manual** (§9.0 / §9.7). But before the
three tactical decisions (stay-manual / DraftKings binding / all-bet-types layer) were called, the
owner opened a **strategic pivot** that sits *upstream* of them: shift the project's center of
gravity from the market benchmark ("beat the closing line," which needs the perishable manual odds
capture this spike showed has no cheap source) toward the project's own **multi-market model book**
— simulation-priced fair odds across all bet types, self-graded by a walk-forward **calibration
backtest** on data already in hand, with PL (frozen baseline) + Bayesian-PL (F10) as a gated A/B and
Monte-Carlo as the pricing layer. Calibration (model-vs-reality, free) ≠ edge (model-vs-market,
needs real prices, gates roadmap #5).

That pivot is deferred to a dedicated, adversarially-vetted design session — **F20** (Opus 4.8 ·
thinking on · xhigh) — which decides whether the beat-the-line benchmark **stays, is demoted, or is
dropped**, and only then are these three decisions (or their replacements) settled. **L6's role is
complete:** it proved the vendor path is closed, which is itself part of what motivates the pivot.
No purchase, no binding, no build.
