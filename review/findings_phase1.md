All verification is complete — the session cut off just as I finished the last probes (feed field names, non-ASCII escapes, market-spec cross-references all checked). Nothing remains to verify; here is the complete findings report.

---

# Adversarial review — specs/scoring_methodology.md (pre-registration audit, phase 1)

**Scope:** `specs/scoring_methodology.md` (frozen 2026-07-18) vs. the live repo at `/Users/nicholassharkey/Downloads/nascar-cup-model` — hash procedure run against the real `predictions/race_5618_2026-07-19_prediction.json`, every §9 fixture recomputed with `.venv/bin/python` (numpy/scipy), §1.2 implementability tested against the live cf.nascar.com feeds (read-only), consistency checked against HANDOFF.md, `src/predict_next.py`, `src/update_data.py`, `src/walkforward.py`, `report/NASCAR_AUDIT_REPORT.md`, and `specs/market_benchmark_decision_rule.md`. **Date:** 2026-07-18. **Verdict: 1 MAJOR (URGENT), 3 MINOR, 5 NIT. Zero arithmetic errors; the hash procedure passes exactly as written. The spec is executable tomorrow, but the MAJOR finding should be amended before the green flag** — per `specs/README.md`, amendments are only legal while the adjudicated data does not yet exist, so the window closes when the race runs.

---

## Findings (most severe first)

### 1. URGENT [MAJOR] — "Official results" is not a fixed object: the spec never pins *which snapshot* of the feed governs, and the repo's own tooling can silently change it
**Spec sections:** §1.2 (results source + disk-cache rule), §2 (refusal rule), §6 (idempotent re-scoring "byte-identical on unchanged inputs").

**Failure scenario (concrete, live tomorrow):**
- The refusal rule fires only when **no** entry has a truthy `finishing_position`. A provisional post-checkered feed — before tech inspection — passes it. NASCAR post-race DQs (several per season; the spec itself handles `disqualified` in §2/F4) land **hours after** the feed first shows positions 1–N. Score Sunday night → pre-DQ order is frozen into `scores_log.csv`; score Monday → post-DQ order. Both runs are fully spec-compliant and produce different `rho`/`h2h_acc` for the same race. The spec claims zero judgment calls; "when to run it" is now a judgment call that changes the primary metric.
- Worse, the disk-cache rule interacts badly with `src/update_data.py`. Evidence from code: `update_data.py` saves `data/races/{yr}_{rid}_wf.json` **before** parsing (lines 29–32), and a race only enters the `known` set if `parse_race` succeeds (line 35). A race with a permanently bad lap feed — *exactly* the case §1.2 exists to survive ("scoring must never be blocked by a lap-feed problem") — is refetched and its `_wf.json` **overwritten on every subsequent weekly run**. §1.2 says "if the file exists on disk, read it", so a re-score under §6's upsert can silently consume a different results snapshot than the one that produced the committed row, while the operator believes inputs were "unchanged." §6's byte-identical guarantee is then unverifiable and false in practice.
- Gaming corollary: nothing forbids deleting the cached `_wf.json` (or re-running `update_data.py` for an unparsed race) to refetch a revised, more favorable official order, then "re-scoring" under §6's legitimate upsert. No provenance of which snapshot produced a row exists anywhere.

**Evidence:** live feed checks — pre-race 5618 feed: 37 entries, all `finishing_position: 0` (refusal correctly fires today); completed Atlanta (5615): 38 entries, positions 1–38, `disqualified` field present. `update_data.py` overwrite path confirmed by code read as cited.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-race — race 5618 has not run; no adjudicated data exists)

**Results finality and snapshot freeze (binds §1.2, §2, §6).**

1. **Completeness gate.** Before loading results, `score_race.py` must confirm the race
   is complete: the race's entry in that year's `race_list_basic.json` (read from
   `src/data/race_list_{year}.json` if present, else fetched with the §1.2 headers)
   has a truthy `winner_driver_id` — the same completion gate `update_data.py` uses.
   If not, exit with the §1.2 refusal error. This supplements, not replaces, the
   "no truthy finishing_position" refusal.
2. **Snapshot freeze.** On the first successful scoring of a race, `score_race.py`
   writes an exact copy of the results JSON it used to
   `src/data/races/{year}_{race_id}_wf_scored.json`. On every subsequent run for that
   race this file, when present, takes precedence over both the `_wf.json` path and
   the network (extending §1.2's read order to: `_wf_scored.json` → `_wf.json` →
   fetch). It is never overwritten or deleted.
3. **Consequence, recorded:** official revisions published after a race is first
   scored (late penalties, DQ reversals) do NOT restate the row; the frozen snapshot
   governs permanently. §6's byte-identical re-run guarantee is defined against the
   frozen snapshot.
```

### 2. [MINOR] — §5's book pipeline is order-ambiguous (dedup vs. malformed vs. void), and the void note clause F5 demands is never defined
**Spec sections:** §5.1–§5.3, §9-F5.

**Failure scenario:** pair {a,b} has two recorded entries: e_closing (`closing: true`, but `price_b` missing → malformed) and e_early (well-formed, `closing: false`). Reader 1 dedups first (§5.2 prefers closing) → the survivor is malformed → pair contributes nothing. Reader 2 drops malformed first → e_early survives dedup → pair counts in `book_n`. Both readers claim compliance; `book_n` differs. The same divergence exists for a void closing entry shadowing a non-void earlier one. Separately, F5 requires "notes mention … void", but §5 defines note clauses only for malformed, pickem, dedup, and `no book prices` — the void clause text is a forced invention, contradicting the zero-judgment-calls claim.

**Evidence:** §5.3's phrase "For each deduped, non-void, well-formed entry" lists attributes without an order; no void note format appears anywhere in the spec; F5 expects one.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-race): §5 pipeline order and void note

Fixed order of operations for §5.2–§5.3: (1) drop malformed entries per §5.1
(note `malformed book entries: {k}`); (2) dedup the survivors per §5.2, comparing
`recorded_utc` as ISO-8601 instants (note `book entries deduped: {k}`); (3) drop
selected entries with `void == true` (note `book entries void: {k}`); (4) apply
§5.3's remaining filters (common set, strict favorite, model pick). A pair whose
*selected* entry is void or malformed is excluded even if a discarded duplicate
was clean: the preferred entry's settlement is the pair's settlement.
```

### 3. [MINOR] — `book_prices.entries` live entirely outside the seal with self-reported timestamps; dedup preference makes selective recording able to choose which book's line counts
**Spec sections:** §1.3 (by design), §5.1–§5.2; interacts with `market_benchmark_decision_rule.md` §2.

**Failure scenario:** a future session records prices from memory/screenshots after the race, choosing the book (or fabricating `recorded_utc`, which §5.2 uses as a tiebreak) whose near-even line flips a disagreement toward the model. Verification: I confirmed computationally that **any** content in `book_prices` — including replacing the `note` string wholesale — passes §1.3 verification (the whole block is substituted in step 3). The market spec says "record prices before the race, never after," but the scoring spec's own §10 step 4 ("Record book prices (if captured) into the JSON per §5.1 before scoring if possible") permits post-race transcription with no provenance marker, and neither spec defines whether `recorded_utc` is observation time or transcription time. The spec flags primary-book designation as open, so this is partially acknowledged — but the provenance gap is not.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-race): book-entry provenance

`recorded_utc` is the time the price was observed at the book, never the
transcription time. Entries whose first appearance in a git commit postdates the
race's green flag must add the note clause `post-race price entry` to that race's
scores row; admissibility for the market benchmark is governed by that spec's §2
(record before the race, never after). The git history is the integrity mechanism
for `book_prices`, exactly as the commit timestamp is for the prediction itself.
```

### 4. [MINOR] — §2 and §6 contradict each other for n < 3, and `h2h_n`'s value there is undefined
**Spec sections:** §2 ("`n < 3` → leave `rho` and `h2h_acc` blank"), §6 ("h2h_acc … blank if h2h_n = 0").

**Failure scenario:** n = 2 → one gradeable pair → §4 yields `h2h_n = 1` and a defined `h2h_acc`; §2 orders `h2h_acc` blank; §6 says blank *only* when `h2h_n = 0`. An implementer writing `h2h_n = 1` with a blank `h2h_acc` satisfies §2 and violates §6; writing the accuracy violates §2. The spec's own "cannot occur in practice" note does not resolve which rule the fixture-level code should implement.

**Proposed fix — verbatim amendment:**

```markdown
## AMENDMENT (2026-07-18, pre-race): n < 3 rows

For n < 3 (cannot occur in practice, defined for completeness): no pairs are
graded at all — `h2h_n = 0`, `h2h_acc` blank, `book_n = book_agree_n =
model_beats_book_n = 0`, `rho` blank, note `small common set`. This reconciles
§2 with §6.
```

### 5. [NIT] — §3's parenthetical "identical to using `-utility`" is not strictly true
**Spec section:** §3. The JSON's `utility` is rounded to 4 dp while `pred_rank` was computed from unrounded utilities; a 4-dp tie would make `spearmanr(-utility, fin)` (midranks) differ from `spearmanr(pred_rank, fin)` (distinct ranks). Verified: the real 5618 file has **0** tied 4-dp utilities among 37 drivers, and the operative instruction (use `pred_rank`) is unambiguous — so this is documentation sloppiness, not a live defect. **Amendment:** append `Clarification (2026-07-18): the operative input is pred_rank; the "-utility" equivalence in §3 is illustrative and does not hold under 4-dp utility ties in the JSON. pred_rank governs.`

### 6. [NIT] — §8 step 2's no-argument default ("earliest race … lacking a scores_log row") has no defined sort key
**Spec section:** §8. `predictions_log.csv` rows carry both `generated_utc` and `race_date`; with two pending races generated out of order, "earliest" is ambiguous. Also evidentiary: `predict_next.py` writes that CSV via raw f-string (line 159), so a hypothetical comma-bearing track name would break naive parsing (none exist in the current calendar). **Amendment:** append `Clarification (2026-07-18): §8 step 2 "earliest" = minimum (race_date, race_id), reading predictions_log.csv with the csv module.`

### 7. [NIT] — Note-clause order and formats beyond "SS STAND-DOWN first" are unpinned, so §6's byte-identical guarantee holds only within one implementation
**Spec sections:** §2, §6, §9. `DQ: {names}` never defines name formatting or ordering; multi-id lists have no defined sort; clause order (beyond SS-first) is unstated. Two compliant implementations produce different `notes` bytes. **Amendment:** append `Clarification (2026-07-18): note clauses appear in this order: SS STAND-DOWN — not actionable; small common set; unscored (not in results): {ids}; unpredicted (in results only): {ids}; DQ: {names}; finish tie anomaly; h2h pairs skipped: {k}; malformed book entries: {k}; book entries deduped: {k}; book entries void: {k}; pickem excluded: {k}; post-race price entry; no book prices. Id lists sorted ascending; names comma-joined in ascending driver_id order.`

### 8. [NIT] — §4's "comparable to the backtest's 0.652" omits the full-field caveat §3 carefully records for ρ
**Spec section:** §4. The 0.652 (and 0.676 non-SS) pairwise numbers in `report/NASCAR_AUDIT_REPORT.md` (line 77, 80) were computed on eligibility-filtered fields; forward `h2h_acc` includes `n_hist < 5` fallback drivers. §3 documents exactly this divergence for ρ but §4 asserts comparability without it. **Amendment:** append `Clarification (2026-07-18): the §3 comparability caveat (full published field vs eligibility-filtered backtest) applies equally to h2h_acc vs the backtest's 0.652/0.676 pairwise numbers.`

### 9. [NIT] — A literal §1.2 implementation crashes instead of refusing when `weekend_race` is empty/missing
**Spec section:** §1.2. "Results = `weekend_race[0].results`" raises IndexError on an empty list (e.g., feed momentarily blank), bypassing the clean refusal path; `predict_next.py` guards with `(wf.get('weekend_race') or [{}])[0].get('results') or []`. **Amendment:** append `Clarification (2026-07-18): a missing or empty weekend_race or results is treated as "no entry has a truthy finishing_position" → the §1.2 refusal exit (mirror predict_next.py's guard).`

---

## Verified clean

- **§1.3 hash procedure, implemented verbatim against the real file: PASS.** Recorded `1f0e5aed…ce1ca` reproduced exactly; matches `predictions_log.csv`. Still passes with a filled §5.1-schema entry appended to `book_prices.entries`. Tampering one `utility` by 0.0001 fails verification. `json.dumps(json.load(...))` round-trip is byte-stable (floats written via `round(x, 4|6)`); `ensure_ascii` claim exercised by the real non-ASCII name `"Daniel Su\u00e1rez"`. The written procedure matches what `predict_next.py` actually does (sha over `json.dumps(payload, sort_keys=True)` with default separators, pristine `book_prices`; the file's `indent=1` is irrelevant because verification re-canonicalizes).
- **§9 fixture arithmetic — every number recomputed, all correct.** F1: ρ = 0.9000 exactly, 10 pairs, acc 0.9000, only (102,103) wrong. F2: ρ = 0.4000 exactly, acc 0.7000. F5 devig directions and counts: e1 imp_a 0.5217 → book 101, agree; e2 imp_a 0.5798 → book 104 vs model 103, disagree, model wins; e3 imp_a 0.3182 → book 102, agree; e4 −110/−110 → imp_a exactly 0.5, pickem; e5 void; e6 deduped → `book_n = 3, book_agree_n = 2, model_beats_book_n = 1`. F6: 10 − 1 = 9. F10: `spearmanr` handles tied finishes via midranks. §5.4: −110 → 0.5238, −115 → 0.5349, −113 → 0.5305 ≈ 0.53 — all as stated.
- **§1.2 implementability against the live feed.** URL pattern correct (matches `update_data.py`/`predict_next.py`); all named fields exist in real result entries (`finishing_position`, `finishing_status`, `disqualified`, `driver_id`, `starting_position`); completed race 5615 shows positions 1–38 all ≥ 1, statuses `Running`/`Accident`/`Mechanical`, `disqualified` boolean, `driver_id` int. Pre-race 5618 feed: 37 entries, all `finishing_position: 0` → the refusal rule fires correctly today. Disk path `src/data/races/{year}_{race_id}_wf.json` matches `update_data.py`'s write path.
- **§1.1 schema vs the real JSON.** `pred_rank` bijective 1..37; `driver_id` all int; `race_id` int; `h2h_prob` complete in both orientations (666 unordered pairs); no canonical entry exactly 0.5000; canonical picks 100% concordant with `pred_rank` order (§4's concordance claim holds); no 4-dp utility ties; the pristine `book_prices` block in the file is byte-identical to §1.3 step 3's string.
- **Sign/orientation consistency with the backtest engine.** Forward ρ = `spearmanr(pred_rank, finish)` is orientation-identical to `walkforward.py`'s `rho_PL_*` (`u` aligned with finish position, positive = good); 0.413 / 0.476 / 0.449, the 0.652/0.676 pairwise numbers, and the 52–53% break-even band all confirmed in HANDOFF.md and the audit report.
- **Cross-spec consistency.** §5.4 correctly defers adjudication to `market_benchmark_decision_rule.md`, whose §6 confirms it consumes raw JSON entries (not CSV counts) and re-verifies hashes. The `book_n` column addition vs HANDOFF's sketch is recorded identically in both documents. §7's stand-down handling matches doctrine. CSV `QUOTE_MINIMAL` correctly covers comma-bearing note clauses; the (date, race_id) sort is well-defined.

**Bottom line:** the spec's arithmetic and its tamper-evidence machinery are sound as pre-registered. The one thing genuinely worth fixing before tomorrow's green flag is Finding 1 (results finality/snapshot freeze) — it is the only place where two fully compliant scoring runs can commit different numbers for the primary metric, and the amendment window closes when the race runs.

---

# Adjudication (orchestrating session, 2026-07-18, pre-race — per review/STATE.md protocol)

| # | Severity | Verdict | Reason |
|---|---|---|---|
| 1 | MAJOR URGENT | **ACCEPT** — amendment applied verbatim | Reproducible from code (`update_data.py` re-saves `_wf.json` before parse success; refusal rule passes on provisional feeds). The freeze-at-first-score policy is the only resolution consistent with §6's own byte-identical idempotency guarantee and the anti-gaming posture, so it is forced, not discretionary. |
| 2 | MINOR | **ACCEPT** — applied verbatim | Real order-of-operations ambiguity; two compliant readers diverge on `book_n`. Void note clause was genuinely undefined while F5 required it. |
| 3 | MINOR | **ACCEPT** — applied verbatim | Verified computationally that arbitrary `book_prices` content passes §1.3 by design; provenance semantics for `recorded_utc` were undefined. Git history as integrity mechanism matches the project's existing public-timestamp doctrine. |
| 4 | MINOR | **ACCEPT** — applied verbatim | §2/§6 contradiction at n<3 is real; reconciliation is mechanical. |
| 5–9 | NIT | **ACCEPT** — applied as one clarifications block, sentences verbatim | All reproducible documentation/determinism gaps; none change any metric on realistic inputs. |

No finding was judgment-shaped enough to require OWNER escalation: every accepted fix either reconciles the spec with itself or pins a previously unpinned mechanical detail. Operational note for the owner (not spec text): given Finding 1, prefer scoring after official results settle (typically the morning after the race) — the freeze makes any timing deterministic, but post-tech-inspection scoring minimizes divergence from the final official record.
