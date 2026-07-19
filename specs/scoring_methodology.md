# SPEC: Scoring methodology for forward-test predictions (FROZEN)

**Status:** pre-registered 2026-07-18, before any race has been scored.
**Governs:** HANDOFF weekly-protocol step 4, starting with race 5618
(North Wilkesboro, 2026-07-19). Once committed, the frozen sections of this
spec may not be edited — see `specs/README.md` for the amendment rule.
**Implements to:** `src/score_race.py` + `src/test_score_race.py` (new files;
no existing file is modified except the two documentation touches listed in
the checklist).

Everything below is written so that an implementing session makes **zero
judgment calls**. Where a choice existed, it is resolved here, with the
reason recorded.

---

## 1. Inputs

### 1.1 Prediction file

`predictions/race_{race_id}_{race_date}_prediction.json`, exactly as written
by `src/predict_next.py`. Relevant fields (verified against
`predictions/race_5618_2026-07-19_prediction.json`):

- `sha256_of_payload` — hex sha256 of the generation-time payload.
- `race_id` (int), `track` (str), `track_type` (str, one of
  SS/INT/SHORT/ROAD/OTHER/UNIQ), `race_date` (YYYY-MM-DD).
- `field[]` — one entry per predicted driver: `driver_id` (int), `name`,
  `grid`, `n_hist`, `utility`, `pred_rank` (1 = predicted best, no ties),
  `p_win`, `p_top5`, `p_top10`.
- `h2h_prob` — nested dict keyed by driver_id **strings**;
  `h2h_prob[a][b]` = model P(driver a finishes ahead of driver b), rounded
  to 4 decimals. Both orientations are stored; rounding can make
  `p[a][b] + p[b][a] ≠ 1.0000`.
- `book_prices` — at generation time exactly
  `{"note": "fill in matchup/win prices at close, then score", "entries": []}`.
- `stand_down` (bool) — true iff `track_type == "SS"`.

### 1.2 Official results

Source of truth: the weekend feed for the race —
`https://cf.nascar.com/cacher/{year}/1/{race_id}/weekend-feed.json` where
`year` = the year of `race_date`.

Procedure: if `src/data/races/{year}_{race_id}_wf.json` exists on disk (saved
by `update_data.py`), read it; otherwise fetch the URL (User-Agent
`Mozilla/5.0`, timeout 60 s) and save it to that path, then read it.
Results = `weekend_race[0].results`; a driver's official finish is
`finishing_position`. Keep every entry with `finishing_position >= 1`.

**`races_parsed.pkl` is deliberately NOT the scoring source** — its parser
applies quality filters (≥20 results, ≥30 green laps with full field) that
could drop a race whose official results exist. Scoring must never be blocked
by a lap-feed problem.

**Refusal rule:** if no entry has a truthy `finishing_position`, exit with an
error ("race not complete — refusing to score"). Never score a race that
has not been run.

### 1.3 Hash verification (mandatory, runs first)

The recorded `sha256_of_payload` was computed **before** book prices were
filled in, over `json.dumps(payload, sort_keys=True)` with default
separators, where `payload` contained the pristine `book_prices` block.
Filling in `book_prices.entries` per protocol step 3 therefore changes the
file **by design** without invalidating the seal. Verification procedure:

1. Load the JSON file into dict `d`.
2. `payload = {k: v for k, v in d.items() if k != "sha256_of_payload"}`
3. `payload["book_prices"] = {"note": "fill in matchup/win prices at close, then score", "entries": []}`
   (this exact string; it is what `predict_next.py` writes).
4. `sha = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()`
5. If `sha != d["sha256_of_payload"]`: **exit nonzero, write nothing.** Any
   edit to any field other than `book_prices` breaks the seal — that is the
   point. There is no override flag.

(Float round-trip is safe: all floats were written via `round(x, 4|6)` and
Python's json repr round-trips them; non-ASCII names are escaped identically
by `ensure_ascii=True` on both writes.)

---

## 2. The scored set

- **Common set** = drivers present in `field[]` **and** in official results
  with `finishing_position >= 1`, matched on integer `driver_id`.
- Predicted drivers absent from results (withdrew / replaced): excluded from
  all metrics; note `unscored (not in results): {ids}`.
- Result drivers absent from the prediction (post-qualifying additions):
  excluded from all metrics; note `unpredicted (in results only): {ids}`.
- `n` (logged) = size of the common set. No minimum is imposed; if
  `n < 20`, append note `small common set`. (`n < 3` → leave `rho` and
  `h2h_acc` blank; cannot occur in practice.)

### DNFs, DVP, and disqualifications — the single governing rule

**A driver's official `finishing_position` is their outcome, full stop.**

- A DNF (`finishing_status != "Running"`) does **not** void or adjust
  anything: NASCAR classifies every starter (DNFs ranked by laps completed),
  and the model's backtest target was exactly this official order — scoring
  must match it or the 0.413 benchmark is meaningless.
- `dvp` (Damaged Vehicle Policy) is just another non-running status.
- A disqualified driver (`disqualified == true`) is scored at the official
  (post-DQ) `finishing_position` the feed reports; append note
  `DQ: {names}`.
- Official ties are impossible; if a malformed feed produces one, proceed
  (Spearman uses midranks), skip that pair in H2H (§4), and append note
  `finish tie anomaly`.

---

## 3. Full-order metric: Spearman ρ (primary)

- `rho = scipy.stats.spearmanr(pred_ranks, finishes)[0]` over the common
  set, where `pred_ranks` = the JSON's `pred_rank` values (their relative
  order is unchanged by subsetting; identical to using `-utility`).
- Positive ρ = good. Log rounded to 4 decimals.
- **Full-order ρ is the primary metric** — it is what 0.413 (backtest),
  0.476 (non-SS), and 0.449 (2026 OOS) mean. Top-K variants (top-5/top-10
  hit counts) are **not** logged and are **not** decision inputs; anyone
  wanting them can recompute from the committed JSONs. Reason: one
  pre-registered primary metric, no post-hoc metric shopping.
- Comparability caveat, recorded here once: forward ρ is computed on the
  full published field (including `n_hist < 5` drivers, who carry
  feature-fallback values), while the backtest ρ averaged eligibility-
  filtered fields. The forward number scores *the prediction as published*.
  Do not "correct" it; do not compute a filtered variant for the log.

## 4. Head-to-head metric

- **Pair universe:** all unordered pairs {a, b} in the common set.
- **Canonical probability:** for the pair with `min_id = min(a,b)`,
  `max_id = max(a,b)`, use `p = h2h_prob[str(min_id)][str(max_id)]`. The
  reverse entry is ignored (kills the 4-decimal asymmetry ambiguity).
- **Model pick:** `min_id` if `p > 0.5`; `max_id` if `p < 0.5`; if
  `p == 0.5` exactly, or the key is missing, or the pair's official
  finishes tie — **skip the pair** (count skips; if any, note
  `h2h pairs skipped: {k}`).
- **Grading:** pick is correct iff the picked driver's official
  `finishing_position` is smaller. DNF drivers grade normally (§2).
- `h2h_n` = number of graded pairs; `h2h_acc` = correct / `h2h_n`,
  4 decimals. (This is the pairwise concordance of the published ranking —
  comparable to the backtest's 0.652 pairwise accuracy.)

## 5. Book comparison

### 5.1 `book_prices.entries` schema (frozen — protocol step 3 writes this)

Each recorded matchup is one JSON object appended to
`book_prices.entries` in the prediction file:

```json
{
  "book": "draftkings",
  "recorded_utc": "2026-07-19T21:40:00+00:00",
  "closing": true,
  "driver_id_a": 4023,
  "driver_id_b": 1361,
  "price_a": -115,
  "price_b": -105,
  "void": false,
  "note": ""
}
```

- `price_a` = American odds on "a finishes ahead of b"; `price_b` the other
  side. Integers, nonzero; a price of 0 or a missing side → entry is
  malformed → excluded with note `malformed book entries: {k}`.
- `closing`: true iff recorded at/near close (target: within ~30 min of
  green flag). Record earlier lines only if closing capture fails.
- `void`: set **after** the race, and only if the book actually voided the
  matchup under its house rules (e.g., a both-must-finish clause). For the
  book-comparison counts the book's own settlement is ground truth — it is
  a *market* benchmark. Model metrics (§3–§4) never use `void`.
- Record prices for SS races too (completeness); doctrine exclusion happens
  downstream (§7 and the market-benchmark spec), not at recording time.

### 5.2 Deduplication

One counted entry per unordered driver pair: prefer `closing == true`; then
latest `recorded_utc`; then last in file order. Duplicates noted:
`book entries deduped: {k}`.

### 5.3 Grading

For each deduped, non-void, well-formed entry whose two drivers are both in
the common set:

- Implied raw probabilities: for American odds `A`,
  `p_raw = |A| / (|A| + 100)` if `A < 0`, else `p_raw = 100 / (A + 100)`.
- Proportional devig: `imp_a = p_raw_a / (p_raw_a + p_raw_b)`.
- **Book pick:** driver a if `imp_a > 0.5`, driver b if `imp_a < 0.5`.
  If exactly equal (pick'em): the entry has no book pick — excluded from
  `book_n`, noted `pickem excluded: {k}`.
- **Model pick:** canonical h2h rule of §4 applied to the pair (skip rules
  identical; a §4-skipped pair is excluded here too).
- `book_n` = entries surviving all of the above (graded, deduped, non-void,
  strict book favorite, model pick exists, both drivers classified).
- `book_agree_n` = those where model pick == book pick.
- `model_beats_book_n` = among the `book_n − book_agree_n` disagreements,
  those where the **model's** pick finished ahead.
- No prices recorded (`entries` empty): `book_n = book_agree_n =
  model_beats_book_n = 0`, note `no book prices`.

### 5.4 Break-even reference (context only, frozen here so it can't drift)

Per-price break-even is `p* = |A|/(|A|+100)` (A<0) or `100/(A+100)` (A>0)
on the side taken. The **fixed fallback reference for prose and reports is
0.5300** — the conservative end of the audit's 52–53% band, ≈ two-sided
−113 juice (−110 → 0.5238, −115 → 0.5349). Adjudication of "is there an
edge" does NOT happen in this spec — it is pre-registered in
`specs/market_benchmark_decision_rule.md`, which consumes the raw JSON
entries, not the CSV counts.

---

## 6. `predictions/scores_log.csv` contract (frozen)

Header, exactly:

```
race_id,date,track,ttype,n,rho,h2h_acc,h2h_n,book_n,book_agree_n,model_beats_book_n,notes
```

| column | type/format | definition |
|---|---|---|
| race_id | int | from prediction JSON |
| date | YYYY-MM-DD | **race** date (not scoring date) |
| track | str | JSON `track`, verbatim |
| ttype | str | JSON `track_type` |
| n | int | §2 common-set size |
| rho | 4-dp float | §3; blank if n < 3 |
| h2h_acc | 4-dp float | §4; blank if h2h_n = 0 |
| h2h_n | int | §4 |
| book_n | int | §5.3 |
| book_agree_n | int | §5.3 |
| model_beats_book_n | int | §5.3 |
| notes | str | semicolon-separated clauses from §2–§5, `SS STAND-DOWN` first when applicable; empty allowed |

- **Amendment vs HANDOFF, recorded:** HANDOFF's column list lacked
  `book_n`; without it the disagreement count (`book_n − book_agree_n`) is
  underivable and `model_beats_book_n` is uninterpretable. `book_n` is
  inserted between `h2h_n` and `book_agree_n`. The checklist updates
  HANDOFF to point here.
- Write with Python's `csv` module, `QUOTE_MINIMAL` (notes containing
  commas get quoted automatically).
- **Idempotent upsert:** one row per `race_id`; re-scoring replaces the
  existing row. Rows kept sorted ascending by (date, race_id). Re-running
  the scorer on unchanged inputs must reproduce the file byte-identically.
- Created with header on first scoring.

## 7. Stand-down races (doctrine)

SS races are scored and logged **identically** to all others; the only
differences: notes begin with `SS STAND-DOWN — not actionable`, and the
market-benchmark spec excludes them from its statistic. Never skip scoring
an SS race; never act on one.

## 8. Scoring procedure (end-to-end order)

1. `python3 update_data.py` (keeps the training pickle current; not a
   scoring dependency).
2. `python3 score_race.py <race_id>` — with no argument, score the earliest
   race in `predictions_log.csv` lacking a `scores_log.csv` row.
3. The script: loads prediction JSON → **verifies hash (§1.3)** → loads
   results (§1.2, refusal rule) → builds common set (§2) → computes §3, §4,
   §5 → upserts the CSV row (§6) → prints a summary block (race, n, rho,
   h2h_acc h2h_n, book counts, notes).
4. Human steps after: update HANDOFF "Current status"; commit with message
   `score: <track> <YYYY-MM-DD> rho=<x.xxxx>`.

CLI affordance for tests only: `--prediction-json PATH` and
`--results-json PATH` override file discovery (no network). No other flags.

## 9. Test fixtures (all must pass before first real scoring)

`src/test_score_race.py`: plain stdlib asserts (no pytest), builds fixture
dicts inline, calls the scorer's pure functions plus a temp-dir end-to-end
run, exits nonzero on any failure. Fixture drivers use ids 101–105 with
`pred_rank` = 1–5 respectively; canonical h2h prob favors the lower id in
every pair (e.g. the §5.3-F5 matrix below). Required fixtures:

- **F1 clean race.** Finishes 101→1, 102→3, 103→2, 104→4, 105→5.
  Expect `rho = 0.9000`, `h2h_n = 10`, `h2h_acc = 0.9000` (only pair
  (102,103) wrong).
- **F2 DNF grading.** Finishes 101→4 (`dvp`), 102→1, 103→2, 104→3,
  105→5 (`accident`, 40 laps). Expect `rho = 0.4000`, `h2h_acc = 0.7000`
  — DNFs graded at official positions, nothing voided.
- **F3 withdrawal.** 6 predicted, driver 106 not in results. Expect n = 5,
  metrics over the 5, note `unscored (not in results): [106]`.
- **F4 unpredicted + DQ.** Results contain driver 107 (not predicted) and
  mark 104 `disqualified: true` at official finish 5. Expect 107 excluded
  with note, 104 scored at 5, note `DQ` present.
- **F5 book grading.** Finishes 101→1 … 105→5. Canonical model probs:
  101v102 .55, 101v103 .60, 101v104 .65, 101v105 .70, 102v103 .55,
  102v104 .60, 102v105 .65, 103v104 .55, 103v105 .60, 104v105 .55.
  Entries: e1 (101,102, −120/+100, closing) → book picks 101, agree;
  e2 (104 vs 103, −150/+130) → book picks 104, model picks 103,
  disagree, 103 finished ahead → model win; e3 (105 vs 102, +200/−250) →
  book picks 102, agree; e4 (103,105, −110/−110) → pick'em, excluded;
  e5 (101,104, −115/−105, `void: true`) → excluded; e6 duplicate of e1 at
  another book, `closing: false` → deduped. Expect `book_n = 3`,
  `book_agree_n = 2`, `model_beats_book_n = 1`, notes mention pickem,
  void, dedup.
- **F6 h2h rounding/skip.** One pair whose canonical prob is exactly
  0.5000 (reverse entry 0.5001): pair skipped, `h2h_n = 9` on a 5-driver
  field, note `h2h pairs skipped: 1`.
- **F7 stand-down.** `stand_down: true`, `track_type: "SS"`: metrics
  computed normally; notes start with `SS STAND-DOWN`.
- **F8 tamper.** Any payload field altered (e.g. one utility) with
  `book_prices` filled: hash check fails, scorer exits nonzero, CSV
  untouched. Also assert the positive case: pristine payload with
  **filled** `book_prices.entries` passes verification.
- **F9 idempotency.** Score F1 twice; CSV has one row and is
  byte-identical after the second run.
- **F10 tie anomaly.** Two drivers share `finishing_position`: rho uses
  midranks, their pair skipped, note `finish tie anomaly`.

## 10. Implementation checklist (mechanical, in order)

1. Create `src/score_race.py`: pure functions
   `verify_hash(d)`, `load_results(year, race_id, path_override)`,
   `common_set(pred, results)`, `score_rho(...)`, `score_h2h(...)`,
   `grade_books(...)`, `compose_row(...)`, `upsert_row(csv_path, row)`;
   `main()` wires them per §8. Network code only in `main()`/`load_results`.
2. Create `src/test_score_race.py` with F1–F10. Run it; all pass.
3. Run `python3 score_race.py 5618` for the real race (after North
   Wilkesboro completes and `update_data.py` has run).
4. Record book prices (if captured) into the JSON per §5.1 **before**
   scoring if possible; if not captured, score anyway (`no book prices`).
5. Update HANDOFF: protocol step 4 column list → replace with pointer to
   this spec; add status line. (Only documentation edits — no code or
   model files.)
6. Commit: `score: North Wilkesboro 2026-07-19 rho=<x.xxxx>` including the
   new scripts, updated JSON, scores_log.csv, HANDOFF.

## Resolved-ambiguity register (why, in one line each)

- DNF pairs grade by official position, never void → matches backtest
  target; books' void rules only affect book counts via the `void` flag.
- Full field (not eligibility-filtered) is the primary ρ → scores the
  published artifact; divergence from backtest averaging is documented, not
  patched.
- `book_n` added to HANDOFF's columns → disagreement denominator must exist.
- Fixed 0.53 fallback break-even → conservative end of the audit's own band;
  real adjudication uses recorded prices (market-benchmark spec).
- Canonical lower-id h2h entry → kills 4-decimal asymmetry nondeterminism.
- `weekend-feed.json`, not `races_parsed.pkl`, is the results source →
  parser quality filters must never block scoring.

## Flagged (not resolved — owner input welcome, non-blocking)

- Which sportsbook is the designated primary for the market benchmark
  depends on what the owner can actually access; §5.2's dedup makes
  multi-book recording safe meanwhile. See market-benchmark spec §2.

---

# Amendments — adversarial review, 2026-07-18 (pre-race; race 5618 has not
# run, no adjudicated data exists). Source: review/findings_phase1.md,
# adjudicated per review/STATE.md. Verbatim as proposed by the reviewer.

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

## AMENDMENT (2026-07-18, pre-race): §5 pipeline order and void note

Fixed order of operations for §5.2–§5.3: (1) drop malformed entries per §5.1
(note `malformed book entries: {k}`); (2) dedup the survivors per §5.2, comparing
`recorded_utc` as ISO-8601 instants (note `book entries deduped: {k}`); (3) drop
selected entries with `void == true` (note `book entries void: {k}`); (4) apply
§5.3's remaining filters (common set, strict favorite, model pick). A pair whose
*selected* entry is void or malformed is excluded even if a discarded duplicate
was clean: the preferred entry's settlement is the pair's settlement.

## AMENDMENT (2026-07-18, pre-race): book-entry provenance

`recorded_utc` is the time the price was observed at the book, never the
transcription time. Entries whose first appearance in a git commit postdates the
race's green flag must add the note clause `post-race price entry` to that race's
scores row; admissibility for the market benchmark is governed by that spec's §2
(record before the race, never after). The git history is the integrity mechanism
for `book_prices`, exactly as the commit timestamp is for the prediction itself.

## AMENDMENT (2026-07-18, pre-race): n < 3 rows

For n < 3 (cannot occur in practice, defined for completeness): no pairs are
graded at all — `h2h_n = 0`, `h2h_acc` blank, `book_n = book_agree_n =
model_beats_book_n = 0`, `rho` blank, note `small common set`. This reconciles
§2 with §6.

## AMENDMENT (2026-07-18, pre-race): clarifications from adversarial review

- Clarification (2026-07-18): the operative input is pred_rank; the "-utility"
  equivalence in §3 is illustrative and does not hold under 4-dp utility ties in
  the JSON. pred_rank governs.
- Clarification (2026-07-18): §8 step 2 "earliest" = minimum (race_date,
  race_id), reading predictions_log.csv with the csv module.
- Clarification (2026-07-18): note clauses appear in this order: SS STAND-DOWN —
  not actionable; small common set; unscored (not in results): {ids};
  unpredicted (in results only): {ids}; DQ: {names}; finish tie anomaly;
  h2h pairs skipped: {k}; malformed book entries: {k}; book entries deduped:
  {k}; book entries void: {k}; pickem excluded: {k}; post-race price entry;
  no book prices. Id lists sorted ascending; names comma-joined in ascending
  driver_id order.
- Clarification (2026-07-18): the §3 comparability caveat (full published field
  vs eligibility-filtered backtest) applies equally to h2h_acc vs the backtest's
  0.652/0.676 pairwise numbers.
- Clarification (2026-07-18): a missing or empty weekend_race or results is
  treated as "no entry has a truthy finishing_position" → the §1.2 refusal exit
  (mirror predict_next.py's guard).
