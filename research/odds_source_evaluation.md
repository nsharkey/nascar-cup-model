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
