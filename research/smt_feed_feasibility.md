# SMT broadcast-telemetry feed — feasibility + acquisition (F17)

*Research spike, 2026-07-20. Deliverable of PLAN F17. Proposes only; builds nothing;
no frozen spec touched. **Zero NASCAR endpoints were contacted during this spike** —
the Terms-of-Service posture was decided first (§3) and no surface cleared it, so the
probe step resolved to no-probe by rule.*

**Method.** Heavy multi-agent deep research in F6's mold: a 73-agent workflow — 8
research agents (three access doors + ToS surfaces), 64 adversarial verification votes
across 41 extracted claims (load-bearing claims got 2 independent refute-prompted
verifiers, secondary claims 1), and a completeness critic — followed by inline
adjudication of split verdicts and two direct documentation fetches (Ably platform
docs) to close the one door whose research agent returned a malformed placeholder
(recorded honestly in §1). Research channels: public web, Wayback Machine captures
(nascar.com 403s non-browser clients), GitHub, app-store listings, press, and the
primary academic documents. Verification tags: **[V]** = confirmed by independent
refute-prompted verifier(s) against primary sources; **[V±]** = confirmed with a
recorded caveat; **[R]** = refuted, correction banked (§9).

---

## 0. Executive summary — door-by-door go/no-go

| Door | Verdict | One-line reason |
|---|---|---|
| **1. SMT Team Analytics** (via the former-crew-chief contact) | **NO-GO as transfer; relationship route only** | Team access is credentialed; NASCAR — not teams — controls distribution of driver telemetry (2018 pooling precedent [V]); no public evidence a team may redistribute, and the instrument that would say so is members-only. A scoped written team partnership (RCR×NC State precedent) is the legitimate variant. |
| **2. NASCAR app / broadcast fan feed** (Ably) | **NO-GO — no public surface exists** | A telemetry-bearing fan feed demonstrably exists (~2 Hz dashboard subsample of the ~120/s stream [V]), but every fan surface that renders it is account- or subscription-gated, the NASCAR App is an explicitly enumerated covered service of the NDM Network Terms [V], and Ably has no unauthenticated access mode at all [V]. Nothing to probe without circumventing auth — barred by this spike's hard constraints. |
| **3. Bastin & Healey 2024 "public SMT feed"** | **RESOLVED: not public** | The paper's own collaboration statement, the lead author's dissertation, and the absence of any data-availability statement show access ran through Richard Childress Racing / General Motors. "Public" is loose author phrasing for feeds NASCAR distributes to teams and broadcasters [V]. |
| *(found en route)* **NASCAR Event Racing Data Platform (ERDP)** | **The one standing ask-based route** | NASCAR's own developer telemetry platform (docs.nextgen.nascarracedata.com) is token-gated with access granted by emailed request [V] — exactly the "prior written consent" shape the NDM Terms contemplate. Owner-led email only; folded into A6. |
| *(found en route)* **Sportradar official NASCAR API** | Exists, fails hobby doctrine | Commercial B2B channel (media data rights since 2015, betting added 2023) [V]; corrects the "Genius Sports is the only licensing channel" claim [R]. No telemetry endpoints documented (F6 §6.2); no free production tier. |

**Bottom line:** no genuinely public, unauthenticated SMT-telemetry surface exists —
so **no L-series capture proposal is made**, and none should be built. The fallback
recorded at kickoff stands: **F13 (in-house loop metrics, done) + F15 (vendored
ratings, owner-gated)** already cover the analytical need from data we legitimately
hold. The two actionable residues are owner-led and free: fold the app-coverage
finding and the ERDP consent route into the **A6** ToS review, and (optionally) ask
the crew-chief contact the §4.4 questions to scope what a real team partnership
would entail.

---

## 1. Method notes and honest failures

- The `ably-channel` research agent returned a schema-validation placeholder instead
  of findings (its verification votes correctly refuted the placeholder). Its three
  load-bearing questions were independently answered elsewhere: the feed rate and
  fan downsample by two other doors' verified claims (§5.1), and the auth/retention
  questions by direct fetches of Ably's platform documentation (§5.3) — documentation
  reading, not endpoint contact.
- The completeness critic received a truncated compilation (a scripting slice bug)
  and flagged doors as "missing" that were in fact fully populated; its one genuine
  catch was the ably-channel placeholder above. Noted so the gap list is not
  over-read.
- Verification was not decorative: of 40 substantive claims, 36 confirmed, **2
  refuted outright and 2 split** — all four adjudicated in §9, and two of the four
  materially improved the picture (the fan-telemetry timeline and the Sportradar
  channel).

## 2. What SMT serves, to whom, at what rate

The tier structure below is the spike's factual backbone; every row is verified.

| Tier | Consumer | Content | Rate | Access |
|---|---|---|---|---|
| Capture | — | Per-car roof/rear-window "vector" unit: GPS position + fuel, RPM, speed, steering, brake, throttle (smt.com case study); the JDS paper enumerates GPS, speed, acceleration, throttle, brake, steering [V] | Ably (NASCAR's realtime vendor): "100 data points 120 times per second" per car [V]; NASCAR's ERDP docs put ECU channels (Engine Speed, aSteering, Throttle Position, Brake Pressure, nGear) at 10 Hz and IMU accel/gyro at 100 Hz [V] — "120/s" is best read as aggregate feed cadence, not per-channel sensor rate | ~1.3 TB/race | Rights-holder internal |
| Team | All Cup/Xfinity teams | Full SMT feed **including competitors' cars** — braking pressure/zone, throttle time and placement | Live, full-rate | **SMT Team Analytics**, launched Feb 2018, credentialed licensees [V] |
| Broadcast | TV production | RACEf/x graphics ingest (SMT fuses ~4 cm GPS + ECU; renders the throttle/brake/steering overlays) | Production | SMT→broadcaster pipeline, not a fan feed [V] |
| Developer | Approved requesters | ERDP GPS message: position/speed/heading/g-force (no throttle/brake documented at this tier) | 10–100 Hz by channel | Token-gated; access by emailed request to NASCAR race data support; 7-day tokens; teams scoped to their own cars [V] |
| Fan | NASCAR app / Race Center | "Subsample of dashboard data": speed, RPM, brake, throttle, fuel percentage | **2 updates/second** (downsample of 120/s) [V] | Ably pub/sub to NASCAR's clients; every telemetry-rendering surface account- or subscription-gated (§5.2) |
| Fan (timing) | Anyone | Timing/scoring: running order, lap times/speeds, pit, flags, loop aggregates | Seconds | cf.nascar.com JSON (what this project already archives) |

**Local baseline (checked from our own bronze, zero network):** the archived
`live-feed.json` final frame carries top-level race state plus per-vehicle
`running_position`, `delta`, lap times/speeds, pit stops, laps-led segments, and
loop-style aggregates (`average_running_position`, `passes_made`, `quality_passes`,
`position_differential_last_10_percent`, …). **No GPS, throttle, brake, or steering
fields.** The telemetry the fan app shows travels a different, gated path — it is
not hiding in the feeds we already fetch.

## 3. ToS posture — decided FIRST, before any probe (extends A6)

### 3.1 The app-coverage finding (new; the decisive fact)

- The NDM Network Terms' embedded covered-services table ("NASCAR Digital Media
  Network Services", anchor `#FullList`) **explicitly lists "NASCAR App"** (URL
  column "N/A") among 24 enumerated properties, per the latest Wayback capture
  (2026-07-16). Verified CONFIRMED by two independent verifiers against the raw
  archived HTML, including the row markup and the 24-row count. [V]
- The app's own terms pointers land on this same document, two ways: NASCAR's
  support article states the in-app Terms link is the `ndmnetworktermsofuse` URL
  (the `?mobileFooter=0&mobileHeader=0` embedded variant, captured continuously
  since Aug 2025) [V]; and the Apple App Store listing (seller NASCAR Digital
  Media, LLC) links `nascar.com/terms-of-use`, which 301-redirects to
  `/ndmnetworktermsofuse/` [V].
- **No 2026 revision exists**: the 2026-07-16 capture still carries "Effective as
  of: July 8, 2025" [V] — so F6 §6.5's verbatim analysis of the scraping/data-mining
  clause and the model/algorithm-development clause (both conditioned on NASCAR's
  prior written consent) remains current, and A6's input is unchanged on that front.
- The Terms name no product-level detail — zero occurrences of TrackPass, RaceView,
  telemetry, streaming, or "live timing" anywhere in the document [V]; apps are
  covered generically. And **cf.nascar.com remains absent** from the covered list,
  exactly as F6 found — the cacher posture is untouched by this spike.

### 3.2 The posture, recorded

**Decision (this spike, extending the existing conservative posture pending A6):
the NASCAR app and its Ably-delivered live data are treated as covered NDM Network
Services, and no automated access to them will be attempted without NASCAR's prior
written consent.** Three independent bars, each sufficient:

1. **Coverage:** the app is an enumerated covered service; its live data is "NASCAR
   Content" under Terms that prohibit scraping/data-mining and model/algorithm
   development without written consent — and this project is, definitionally, a
   model built from such data.
2. **Authentication:** every fan surface that renders telemetry is gated — Race
   Tracker behind a free Fan Rewards account, Live Telemetry behind paid NASCAR
   Premium, in-car cameras behind Max (§5.2) — and the kickoff's hard constraint
   bars circumventing any credentialed surface. Anonymous fans get only
   timing/scoring lists, i.e., nothing beyond what cf.nascar.com already serves us.
3. **Transport:** Ably has no unauthenticated access mode at all — "All
   interactions between a client and the Ably service must be authenticated"
   (Ably auth docs, fetched 2026-07-20); clients get short-lived, narrowly-scoped
   tokens issued by the customer's (NASCAR's) backend.

**Consequence: the probe step was not executed.** There is no genuinely public,
unauthenticated telemetry surface to probe politely; probing anything else would
mean either violating covered-service terms or circumventing auth. No NASCAR
endpoint, app backend, or Ably channel was contacted at any point in this spike.

### 3.3 What A6 gains

The owner's A6 review now has two additions: (i) the app-coverage finding above
(the NDM Terms' reach is *confirmed* for the app surface, in contrast to the
textually-unsupported reach over cf.nascar.com); (ii) a concrete written-consent
route exists — the ERDP request channel (§7.1) — should the owner ever want
telemetry enough to ask for it.

## 4. Door 1 — SMT Team Analytics and the team relationship

### 4.1 The product

SMT (SportsMEDIA Technology) has run NASCAR's car-tracking stack since RACEf/x
debuted in 2001 (built by Sportvision; SMT completed the acquisition 2016-10-06
[V]). **SMT Team Analytics** launched February 2018; virtually every Cup team
signed on, and since 2018 all Cup teams (and broadcasters) see live SMT data
*including competitors' cars* [V]. This is the feed the owner's former-crew-chief
contact had — as team personnel, under the team's license.

### 4.2 Transferability — the load-bearing question

- **NASCAR, not teams, controls distribution.** For 2018 NASCAR unilaterally gave
  all teams access to every competitor's SMT data over top drivers' objections that
  it was proprietary (Kyle Busch: "We look at it as proprietary, but NASCAR
  doesn't") [V]. A team that does not control distribution cannot grant it to a
  third party.
- **The restriction instrument is not publicly inspectable — mostly.** The Cup rule
  book is members-only (corroborated by ESPN reporting and the credential-gated
  rules portal) [V]; the only *publicly verified* confidentiality rule binding team
  personnel is betting-scoped (§19.2.5, primary text via Sportradar's integrity-
  tutorial hosting; fines to $200k) [V]. Adjudication note: one verifier correctly
  observed that the 2025 Charter Agreement has become publicly inspectable through
  the 23XI/Front Row antitrust litigation — a partial correction to "cannot be
  inspected" (§9.4) — but no public SMT-redistribution clause was surfaced from it
  in this spike.
- **Net: "unverifiable restriction," not "verified absence."** Combined with the
  distribution-authority precedent, the working assumption must be that a former
  crew chief's access does not transfer, and that even a current team could not
  hand over raw feeds without NASCAR/SMT sign-off. This matches the kickoff's
  prior ("likely not transferable") — now with evidence rather than assumption.

### 4.3 What a legitimate partnership looks like (the precedent)

The RCR × NC State relationship is real, two-layered, and instructive [V]:
sponsored student engineering projects since ~2014 plus an Institute for Advanced
Analytics practicum (sponsor-provided data under a practicum agreement), and the
Bastin & Healey paper itself — an explicit collaboration with RCR and GM personnel
as domain experts, whose public artifact was **code only, no data** (the
supplementary repo contained Python only, and is now 404) [V]. That
code-public/data-private posture is exactly this repo's existing doctrine, which
means a partnership would not require changing how we publish.

### 4.4 Questions for the crew-chief contact (flag, don't assume)

If the owner wants to scope this door, these six questions (drafted from the
verified record) are what the contact/team conversation must answer:

1. Who licenses SMT Team Analytics data — the team, NASCAR, or SMT — and does the
   team hold any contractual right to share raw feeds vs. derived analyses?
2. Did the RCR–NCSU work run under an NDA with the team, NASCAR, or SMT — and did
   students receive raw data or supervised on-premises access?
3. Which rule-book/charter section governs data confidentiality, and would NASCAR
   sign-off be needed for any share?
4. Would a team sign a written research agreement scoping non-commercial use,
   code-only public repo (no raw-data redistribution), publication review, term?
5. Is the realistic path a team *introduction* to NASCAR's Analytics & Insights
   group or SMT, rather than a team-granted feed?
6. What betting-policy exposure (§19.2.5) would public model outputs create for
   team personnel involved?

**Door-1 verdict: NO-GO as a data transfer; report as a relationship route.** The
route is real (precedented, doctrine-compatible) but is owner-led relationship
work, not a build — and it inherits whatever terms the team's own license imposes.

## 5. Door 2 — the fan feed (NASCAR app / Ably)

### 5.1 What exists

A telemetry-bearing fan feed **does** exist, and its shape is now pinned [V]:

- NASCAR broadcasts "in-car dashboard data like speed, throttle, and brake
  application" — the case study also names RPM and fuel percentage — "twice a
  second" via Ably Channels, a subsample of the ~120/s internal stream
  (~1.3 TB/race; 2024 Daytona 500: 370M+ messages to 56K+ concurrent users).
- It feeds the NASCAR Drive experience / app premium surfaces; Ably's webinar
  material markets it as "100+ per-car data points" and "the same detailed data
  used by teams and OEMs" (marketing upper bound — no source enumerates the exact
  fan-visible field list) [V±].
- NASCAR's own follow-live marketing (June 2025 capture) advertises a "Raw Feed"
  of 75+ data points and a "Race Tracker" doing real-time car tracking [V].

### 5.2 Every telemetry surface is gated [V]

| Surface | Content | Gate |
|---|---|---|
| App leaderboard (anonymous) | List-style timing/scoring, lap-by-lap commentary, broadcast radio | None — but carries no telemetry beyond what cf.nascar.com serves |
| Race Tracker (real-time car tracking) | Live car positions | **Free NASCAR Fan Rewards account** |
| "Live Telemetry" + enhanced leaderboard | Real-time race data incl. dashboard telemetry | **Paid NASCAR Premium** (~$4.99/mo or $29.99/season) |
| In-car cameras (ex-NASCAR Drive, which bundled cameras "along with telemetry data") | Onboards | **Paid Max** (2025-, nascar.com/drive is now a stub pointing at Max) |
| RaceView (2007–2020) | 3D per-car telemetry visualization | Discontinued 2020, no like-for-like successor [V] |

Timeline correction from verification (§9.2): the paid fan-telemetry surface dates
to **2024**, not 2025 — the app advertised "premium access, unlocking real-time
telemetry data" by Feb 2024, and the Sept 2024 App Store listing carried "Brand
new for 2024 … Live Telemetry" under Premium [R→corrected].

### 5.3 Transport and history (Ably platform facts, fetched from docs 2026-07-20)

- **Auth is mandatory**: "All interactions between a client and the Ably service
  must be authenticated." Client devices use short-lived scoped tokens issued by
  the customer's backend; there is no unauthenticated mode.
- **History is not retrievable**: Ably stores messages for **two minutes** by
  default; longer retention (24 h free tier … 365 d) is a channel-rule option of
  the *customer's* (NASCAR's) account, not something a subscriber can invoke
  retroactively. **Backfill depth of the fan telemetry stream is therefore zero**
  — it is perishable in exactly the way our live-feed snapshot stream is, and
  unlike the cacher archives, nothing survives post-race to fetch.

### 5.4 Community/OSINT cross-check [V]

Every substantive open-source NASCAR live-data project consumes timing-and-scoring
only: rNascar23.Sdk (endpoints FlagState/LapTimes/LiveFeed/LoopData/PitStops/
Points/Schedules; a full-source grep found zero telemetry/websocket/Ably
references), Dennist03/nascar-tracker, jemorriso/nascar, rbiesser/nascar-api,
BelNaruto/nascar-api — all cf.nascar.com JSON shapes. The one counterexample a
verifier surfaced (§9.3): **jdamiani27/pyraceview**, which parsed the *binary
stream of the discontinued RaceView product* (per-car X/Y/Z GPS, throttle,
steering) — proof the fan-telemetry stream concept existed and was parseable, on a
paid product that died in 2020. No documented cease-and-desist history against
third-party feed consumers was found (an absence, not a permission signal) [V±].

### 5.5 Data dictionary — documented upper bound (never probed)

What public documentation attests the fan telemetry stream carries, per car at
~2 Hz: `speed`, `rpm`, `throttle`, `brake`, `fuel percentage`, plus live position
(Race Tracker implies per-car coordinates); Ably materials additionally name
acceleration, steering angle, tire pressure and temperature among captured
parameters without confirming they reach fan clients. Contrast with the field
schema we already archive (§2 local baseline): the delta is precisely
GPS + driver-input channels. Recorded for completeness only — **no capture of
this stream is proposed** (§3.2).

**Door-2 verdict: NO-GO.** The only fan surfaces carrying telemetry are
account/subscription-gated covered services; the transport requires NASCAR-issued
tokens; retention is ~2 minutes so there is nothing retrospective to fetch even
under a changed posture. A capture proposal here would be a proposal to violate
either the Terms or the auth constraint — so none is made.

## 6. Door 3 — the Bastin & Healey "public SMT feed" claim, resolved

The paper ("Visual Analytics for NASCAR Motorsports," *Journal of Data Science*
23(1):149–170, DOI 10.6339/24-JDS1141, published 2024-07-02, CC BY) **does**
verbatim call SMT feeds "public sources of information … provided by NASCAR,"
enumerating GPS/speed/acceleration/throttle/brake/steering [V]. Three verified
facts resolve what "public" means [all V]:

1. The paper's first sentence declares the RCR collaboration; the acknowledgments
   thank "NASCAR collaborators from Richard Childress Racing and General Motors";
   there is **no data-availability statement** anywhere in its 22 pages; and the
   abstract applies "publically available" to the scanner *audio*, not telemetry.
2. Bastin's 2023 NCSU dissertation (same project) gives the fuller provenance:
   NASCAR releases the feeds *to teams*, who stream them to their engineers; it
   pictures the RCR Command Center and the SMT team-analytics tool, defines truly
   public data as "what a spectator could have seen," and credits the author's
   husband for the NASCAR domain connection — the team conduit.
3. The supplementary repo was Python code only — no data files, no license — and
   is now 404 (Wayback capture 2025-03-31 survives).

**Door-3 verdict: the claim does not evidence an open endpoint.** "Public" is
loose author phrasing for rights-holder feeds accessed through a credentialed team
relationship. Door 2's assessment does not flip; door 3 collapses into door 1's
partnership precedent — where it is actually *encouraging* (peer-reviewed work was
published from this data, with a code-only public artifact).

## 7. Residual doors found en route

### 7.1 NASCAR Event Racing Data Platform (ERDP) — the ask-based route

NASCAR operates a documented developer platform for Next Gen car data
(docs.nextgen.nascarracedata.com): token-gated (7-day expiry), access granted by
emailed request to NASCAR race data support, per-team data scoping per NASCAR's
AWS engineering material; its GPS message carries position/speed/heading/g-force;
ECU channels documented at 10 Hz, IMU at 100 Hz [V]. This is the one standing,
documented channel where a written request for access is the *designed* entry
path — i.e., the "prior written consent" shape the NDM Terms condition everything
on. **Proposal: none (no build).** Recorded as an A6 option: an owner-led email
costs nothing, and a "no" leaves us exactly where we are. A non-commercial
personal archive is an unusual grantee, so expectations should be low.

### 7.2 Sportradar official NASCAR API

Verification of a refuted claim (§9.1) established: NASCAR↔Sportradar media data
rights since 2015, extended 2023 (adding official betting data); a commercial
developer portal serves real-time official NASCAR data B2B. F6 §6.2 already
found no telemetry endpoints in its documented list and no free production tier —
under the hobby cost doctrine this stays a known-but-unpriced door, relevant only
if the market benchmark ever returns EDGE and a licensed stack is being built
anyway.

## 8. Verdict, fallback, and what changes in the plan

- **No public telemetry surface exists → no capture session is proposed.** Said
  plainly, as the kickoff required. The L-series pattern has nothing admissible to
  capture.
- **The fallback stands and is largely already banked:** F13 (in-house loop-metric
  histories from our own archived laps — done) and F15 (nascaR.data vendored
  ratings — owner-licensing-gated) cover the "richer driver signal" need this door
  would have served. The frozen model, the forward test, and E1 capture are
  untouched.
- **A6 absorbs the governance residue:** the app-coverage finding (§3.1), the
  recorded posture (§3.2), and the optional ERDP written-consent route (§7.1).
- **Door 1 remains available as owner-led relationship work** with §4.4 as the
  agenda — it is the only path to team-grade (~120/s all-car) data, and it runs
  through people, not code.

## 9. Corrections banked by adversarial verification

Kept on record so they are not re-imported (F6 Appendix B discipline):

1. **"The 2019 Genius Sports deal is the only external licensing channel for
   NASCAR official data" — REFUTED (0–2).** Sportradar has held NASCAR media data
   rights since 2015 (extended 2023-08-29, adding official betting data
   distribution to BetMGM/FanDuel/Penn), with a public commercial developer
   portal. The narrower true statement: no *telemetry* licensing program for
   outsiders was found anywhere.
2. **"As of June 2024 live SMT telemetry was not available on any fan surface" —
   REFUTED (0–1).** Wayback evidence: the app advertised premium "real-time
   telemetry data" by 2024-02-24; Sept 2024 App Store notes list "Live Telemetry"
   under Premium; a May 2024 nascar.com/drive capture carried a live telemetry
   panel (rpm/fuel/throttle/brake/gear). The Frontstretch column's advocacy framing
   was about *full* SMT depth, not the existence of any fan telemetry.
3. **"Every open-source NASCAR live-data project consumes timing-and-scoring
   only" — corrected (1–1, adjudicated).** True of every *current* project
   surveyed; falsified as a universal by jdamiani27/pyraceview, which parsed the
   discontinued RaceView product's binary telemetry stream (dead since 2020).
4. **"The instrument that would contain an SMT-redistribution restriction cannot
   be publicly inspected" — narrowed (1–1, adjudicated).** The Cup rule book is
   members-only [V], but the 2025 Charter Agreement entered the public record via
   the 23XI/Front Row antitrust litigation; no SMT clause was surfaced from it in
   this spike, so the conclusion ("unverifiable restriction, not verified
   absence") stands on the rule book while the premise is narrowed.

---

## Appendix A — Source ledger (all accessed 2026-07-20)

| Source | What it evidences |
|---|---|
| web.archive.org/web/20260716193402/…ndmnetworktermsofuse?mobileHeader=0&mobileFooter=0 | NDM Terms, latest capture: covered-services table incl. "NASCAR App"; July 8, 2025 effective date; clause keyword scan |
| support.nascar.com/927604-… | In-app Terms link = ndmnetworktermsofuse (mobile-embedded variant) |
| apps.apple.com/us/app/nascar-mobile/id552764013 | Seller NASCAR Digital Media LLC; terms pointer; Premium "Live Telemetry"; tier structure |
| web.archive.org/…/nascar.com/terms-of-use/ (2026-07-16) | 301 → /ndmnetworktermsofuse/ |
| web.archive.org/…/nascar.com/followlive/ (2025-06-16) | "Raw Feed" 75+ data points; Race Tracker real-time car tracking; Fan Rewards gate |
| ably.com/case-studies/nascar | Dashboard data fields (speed/RPM/brake/throttle/fuel); "broadcast twice a second"; 120/s + 1.3 TB/race; Daytona 500 scale; NASCAR Drive |
| ably.com/resources/webinars/how-nascar-delivers-realtime-data | 100+ per-car points; 120→2/s downsample; "same detailed data used by teams and OEMs" (marketing) |
| ably.com/docs/auth; ably.com/docs/storage-history/storage | Auth mandatory, no unauthenticated mode; 2-minute default retention; customer-side persistence tiers |
| docs.nextgen.nascarracedata.com (DeveloperGuide: IoT Data; token_connection) | ERDP channels/rates; token gating; request-based access |
| smt.com/case-study/nascar/; smt.com 2017 RACEf/x release; smt.com 2019 Team Analytics article | Vector unit fields; RACEf/x lineage; Team Analytics Feb 2018 + all-team adoption |
| globenewswire.com 2016-10-06 SMT/Sportvision release | Acquisition completed |
| thedrive.com/accelerator/18560 | 2018 pooling precedent; Busch "proprietary, but NASCAR doesn't" |
| prnewswire.com NASCAR–Genius 2019 release | Betting-data exclusivity quote (scope corrected by §9.1) |
| Sportradar 2023-08-29 release + developer portal (via verifiers) | Media rights since 2015; 2023 extension; commercial NASCAR API |
| jds-online.org/journal/JDS/article/1374/info + healey.csc.ncsu.edu/publications/37882.pdf | Paper text: "public sources… provided by NASCAR"; RCR/GM acknowledgment; no data-availability statement |
| repository.lib.ncsu.edu (Bastin 2023 dissertation) | Team-credentialed provenance; "what a spectator could have seen" |
| web.archive.org/web/20250331075852/github.com/cghealey/JDS | Supplement was code-only; live repo 404 |
| github.com: RRoberts4382/rNascar23.Sdk, Dennist03/nascar-tracker, jemorriso/nascar, rbiesser/nascar-api, BelNaruto/nascar-api, jdamiani27/pyraceview | OSS landscape: timing-and-scoring only; pyraceview = dead RaceView stream parser |
| web.archive.org/…/frontstretch.com/2024/06/06/live-smt-data-… | 2024 advocacy baseline; RaceView 2007–2020 |
| en.wikipedia.org/wiki/NASCAR_rules_and_regulations (+ ESPN 2015, Sportradar-hosted §19.2 PDF via verifiers) | Rule book members-only; betting-scoped confidentiality §19.2.5 |
| web.archive.org/…/nascar.com/news-media/2019/11/14/nascar-nbc-trackpass-platform-faq/ | TrackPass = video product |

## Appendix B — Claim scoreboard

41 claims extracted (1 placeholder discarded); 64 verification votes. Load-bearing
claims (2 votes each): 17 of 19 substantive confirmed 2–0; 1 refuted 0–2 (§9.1);
1 split 1–1 (§9.4, adjudicated). Secondary claims (1 vote): 19 of 21 confirmed;
1 refuted (§9.2); 1 split-source correction (§9.3 arrived via a load-bearing
claim's dissenting verifier). Full per-claim statements, quotes, and verdict
reasoning are preserved in the session workflow journal.
