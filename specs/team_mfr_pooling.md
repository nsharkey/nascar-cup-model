# SPEC: Teammate / manufacturer pooling — pre-registered A/B (roadmap #4b)

**Status:** pre-registered 2026-07-18, before any variant has been run.
**Sequencing:** runs AFTER the DNF spec's decision is recorded (roadmap
order) and its scores_log gate is met. **Baseline = the frozen config as of
execution date** — i.e. if the DNF A/B adopted a variant, that adopted
config (per HANDOFF's then-current frozen block) is the baseline here; the
baseline PL spec in the A/B script must reproduce it exactly.
**Motivation (audit §8):** "the next real gains lie in DNF-aware targets,
teammate/manufacturer pooling, and richer same-weekend data."

**Frozen model files are not modified.** The A/B lives in
`src/step8_pooling_ab.py`. Production changes only on a WIN, per §8.

---

## 1. Data-layer prerequisite — the organization key (verified 2026-07-18)

The parsed `team` field is `team_id`, which is **per-car**, not
per-organization: in the 2026-07-12 Atlanta feed, Blaney's #12 has
`team_id 1460` and Logano's #22 has `team_id 2593`, both
`team_name 'Team Penske'`. 47 distinct team_ids appear in the last 30
races vs ~17 organizations. **`team_id` must not be used for teammate
pooling.** The organization key is the feed's `team_name` (string; equals
`owner_fullname` in the current feed).

Prerequisite steps (own commit, before the A/B):

1. `src/parse_lib.py`: in the results loop, add
   `org=(r.get('team_name') or '').strip()` to the per-driver dict. No
   other change.
2. Full rebuild — raw feeds are not all on disk: run `src/download.py`
   then `src/parse.py` (~10 min per HANDOFF).
3. **Regression gate:** the rebuilt pickle must contain at least the same
   races (matched on `rid`) as the pre-rebuild pickle (new races appearing
   is fine — time passed), and for every matched race and driver, every
   pre-existing field must be exactly equal (compare full dicts after
   deleting the new `org` key). A throwaway comparison script proves it and
   its output is pasted into the commit message. If any field differs:
   STOP — investigate before anything else. (Precedent: the parse_lib
   refactor was verified 163/163 this way.)
4. Commit the updated `parse_lib.py` + rebuilt `races_parsed.pkl`.
5. `org` empty string (missing team_name) → the driver simply contributes
   to / reads from no org pool that race (treated as no-org, features NaN).

Manufacturer needs no prerequisite: `make` is already parsed and complete
(6,083/6,083 rows; values exactly {Chevrolet, Ford, Toyota} in recent data).

**Org renames are distinct entities** (e.g. Stewart-Haas Racing → Haas
Factory Team appear as different orgs): pre-registered as-is, no manual
alias table — zero judgment calls beats slightly longer histories. Recorded
as a known limitation; a future alias-table variant would need its own spec.

## 2. Variants (exactly three; all are single added features)

Frozen machinery identical to the DNF spec §2 preamble (hl 8 everywhere,
burn 15, min_hist 5, min_drv 20, λ 0.5, znan, etc.). All pooled features
are **exclude-self** — one rule everywhere, and it guarantees the feature
carries information the driver's own `fin`/`typed` features don't already
carry. All pools append **once per race** (per-race mean, then the
recency-weighted mean over races) so half-life 8 keeps meaning "8 races",
not "8 driver-entries".

State kept during the replay, appended after each race is processed:

- `ho[org]` — list over races of `{driver_id: finish}` for that org's cars
  in that race.
- `hot[(org, tt)]` — same, per corrected track type `tt` of the race.
- `hmt[(make, tt)]` — same, per manufacturer and track type.

Feature computation for driver `d` in the current race (org/make taken
from **this race's** entry for `d`):

```
pool_feature(hist_list, d, hl=8):
    vals = []
    for racedict in hist_list:                    # oldest → newest
        others = [f for dd, f in racedict.items() if dd != d]
        if others: vals.append(mean(others))
    return wmean(vals, hl) if vals else NaN       # NaN → 0 via znan
```

- **W1 `orgform`** = `pool_feature(ho[org], d)` — teammates' overall recent
  form. PL features: baseline + `[orgform]`.
- **W2 `mfrtyped`** = `pool_feature(hmt[(make, tt)], d)` — manufacturer
  form at this track type. PL features: baseline + `[mfrtyped]`.
  (Needs no org field — runs even if the §1 rebuild is blocked; if so, run
  W2 alone and record W1/W3 as blocked, gate α unchanged.)
- **W3 `orgtyped`** = `pool_feature(hot[(org, tt)], d)` — teammates' form
  at this track type. PL features: baseline + `[orgtyped]`.

Single-car orgs yield NaN → 0 for W1/W3 every week — that is the honest
encoding of "no teammates, no teammate information."

## 3. Live-prediction feasibility check (verify during implementation)

The A/B uses parsed historical data, but adoption requires the org key
pre-race. Before the A/B runs, assert on the next upcoming race's
weekend feed that pre-race entries (those with `starting_position`) carry
non-empty `team_name`. If they don't, the adoption fallback is: use the
driver's most recent parsed `org`; a driver with no parsed history gets
no-org. This fallback is pre-registered now so it isn't invented later.

## 4. Evaluation protocol

Identical to the DNF spec §3, with: sample = full pickle at execution (all
years passed explicitly); one replay evaluating `base` + W1 + W2 + W3
simultaneously on identical scored races; **baseline replication gate** —
`base` must reproduce the then-frozen config's documented walk-forward mean
ρ on the corresponding subsample within ±0.003 (if the DNF A/B adopted a
variant, the reference number is the one recorded in its RESULT block;
otherwise 0.413 on year ≤ 2025 scored races).

## 5. Kill/keep decision rule (frozen)

Identical in form to the DNF spec §4: per-race paired `d_i = ρ_W,i −
ρ_base,i`; one-sided Wilcoxon `alternative='greater'`; **adopt only if
p ≤ 0.0167 AND mean(d) ≥ +0.005**; multiple pass → highest mean(d), exact
4-decimal tie → W2 over W1 over W3 (least infrastructure: no org
dependency, then overall before typed); none pass → negative result
recorded, no tweaked retries under this spec. Diagnostics (by type, non-SS,
2026+, weights, bootstrap CI seed 7) reported, never gates. At most one
variant adopted.

## 6. Execution constraints

Same as DNF spec §5 (single process, minutes, bordered summary). If both
this and another backtest job ever need to run concurrently, they are
independent read-only consumers of the pickle — safe to parallelize; but
nothing here requires it.

## 7. Recording the result

Dated `## RESULT` block appended to this file (sample, gate value,
per-variant table, verdict, commit hash) + HANDOFF roadmap update. Only
permitted edit to this file.

## 8. Adoption procedure (only if a variant wins)

As DNF spec §7: `walkforward.py` untouched; `predict_next.py` gains the
winning pool's replay state + feature (exact §2 definitions) and bumps
`config_version`; HANDOFF frozen block updated with evidence; forward test
and market benchmark continue intention-to-treat, nothing rescored.
Additionally for W1/W3: `predict_next.py`'s live path uses entry
`team_name` with the §3 fallback.

## Resolved-ambiguity register

- `team_name`, not `team_id`, is the org key → verified per-car vs per-org
  against the live feed; this spec exists to stop a lesser model from
  "pooling" over car numbers.
- Once-per-race pool appends → preserves half-life semantics (hl counts
  races); per-entry appends would make hl=8 span ~2 races for a 4-car org.
- Exclude-self everywhere → one rule, and the feature is teammate/stable
  information by construction, not a re-encoding of the driver's own form.
- Org renames = new entities → no hand-maintained alias table, no judgment.
- W2 kept org-independent → a data-layer failure can't zero out the whole
  experiment.
- Baseline = then-current frozen config → roadmap order makes the DNF
  decision part of the environment, not a competitor here.

## Flagged (not resolved)

- Whether `team_name` is populated pre-race in the weekend feed (§3) —
  verifiable only against a live upcoming race; the fallback is
  pre-registered either way, so this blocks nothing.
