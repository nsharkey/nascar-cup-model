# NASCAR Cup Series Finishing-Order Model

A walk-forward Plackett–Luce model for NASCAR Cup Series finishing positions
(Next Gen era, 2022–present), built from public `cf.nascar.com` timing feeds —
plus the zero-trust audit that produced it and a live, timestamped forward test.

Every number here was reproduced independently from raw feeds. The full audit —
replication of a prior modeling effort's five claims, sensitivity analysis,
typology corrections, out-of-sample 2026 validation, and calibration — is in
[`report/NASCAR_AUDIT_REPORT.md`](report/NASCAR_AUDIT_REPORT.md).

## Headline results (all walk-forward, no look-ahead)

| Predictor | Spearman ρ vs. actual finish |
|---|---|
| Qualifying position alone | 0.346 |
| Recency-weighted finish history | 0.354 |
| Prior effort's best (z-sum, typed) | 0.382 |
| **This model (PL: finish + pace + typed + start)** | **0.413** |
| — non-superspeedways only | 0.476 |
| — 2026 out-of-sample (20 races) | 0.449 |

Predictability is structurally uneven: short tracks ρ≈0.52, intermediates ≈0.41,
road courses ≈0.36, superspeedways ≈0.16 — and at superspeedways the model's
confident head-to-head picks score *worse than coin flips* (Brier 0.2514).
Hence the hard rule baked into the harness: **superspeedway weeks are
stand-downs.** Model output at Daytona, Talladega, and Atlanta is logged but
never actionable.

## Pipeline

```bash
pip install -r requirements.txt
cd src
python3 download.py      # pulls all Cup points races 2022–present (~130 MB, ~10 min)
python3 parse.py         # builds races_parsed.pkl (~1.6M lap records)
python3 predict_next.py  # after qualifying posts: prediction for the next race
```

`predict_next.py` refits the validated configuration (pace = per-race median of
fastest 85% green laps, half-life 8, corrected track typology with shrinkage,
features `[fin, pace, typed, start]`, ridge λ=0.5) on every completed race,
finds the next scheduled points race, reads the live grid, and writes to
`predictions/`:

- `race_<id>_<date>_prediction.md` — human-readable predicted order with
  P(win)/top-5/top-10,
- `race_<id>_<date>_prediction.json` — full field, fitted weights, complete
  head-to-head probability matrix, SHA-256 of the payload, and an empty
  `book_prices` block to fill in with closing matchup prices,
- `predictions_log.csv` — append-only index.

It **refuses to run once results exist**, so the log cannot contain post-hoc
"predictions."

## The forward test

The open question the audit could not answer from history alone: does ~0.41–0.45
correlation beat the closing line after the book's hold (~52–53% pairwise
break-even)? That is decided prospectively:

1. After qualifying each week: run `predict_next.py`, **commit and push the
   prediction before the race**. The public commit timestamp is the proof.
2. Record book head-to-head matchup prices at close in the JSON's
   `book_prices` block.
3. After the race: score model picks vs. book picks vs. results.

The forward log began **2026-07-18** with race 5618 (North Wilkesboro,
2026-07-19) — committed before the green flag.

## Repository map

```
src/            download → parse → predict pipeline, audit engine (walkforward.py),
                and the audit's analysis steps (sensitivity, typology, models, calibration)
report/         full written audit report
predictions/    the forward-test log (committed pre-race, hashed)
research/       vendored external research packages (immutable sources + derived
                crosswalks; see research/track_audit/INTEGRATION.md)
```

Raw feed data and the parsed pickle are intentionally not committed
(re-downloadable via `src/download.py`; see `.gitignore`).

## Reference research: track & configuration audit

`research/track_audit/` vendors a hash-verified external audit of the Cup
track universe (2015–2026, 43 physical configurations, points races only):
narrative report, structured JSON/CSV reference data, structural-similarity
edges, and a source ledger. Its 1–10 scores are **analyst structural priors,
not measurements**, and nothing from it feeds the frozen production model.
A derived crosswalk maps its configuration-level `track_id`s to the feed
track names this pipeline uses. Provenance, evidence model, and validation:
[`research/track_audit/INTEGRATION.md`](research/track_audit/INTEGRATION.md);
gate: `cd src && python3 test_track_audit.py`.

## Honest caveats

- Absolute win probabilities are conservative (regularization-induced
  underconfidence, measured in the audit). The ordering and head-to-head
  probabilities are the calibrated product.
- Timing data is NASCAR's; this repo redistributes code only. Respect the
  source's terms when downloading.
- Nothing here is betting advice. The forward test exists precisely because
  no one yet knows whether this clears the market — a negative result is a
  valid outcome.
