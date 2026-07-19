# research/track_audit/ — vendored NASCAR Cup track & configuration audit

Integrated 2026-07-19. This directory vendors an externally-produced,
self-contained research package as a **first-class, versioned reference-data
dependency** of this repo. It is source material, not repo-authored analysis:
the six package files are immutable here, and everything repo-specific lives
in clearly-marked derived artifacts.

## What the package is

A zero-trust audit of the NASCAR Cup Series track universe:

- **Research cutoff:** 2026-07-19 (package version 1.0).
- **Primary scope:** points-paying Cup races only — completed 2015–2025
  (396 races) plus the full scheduled 2026 slate (36 races, 20 completed
  through 2026-07-12). 432 schedule slots total.
- **Deliberately deferred, not omitted:** the Clash, All-Star Race/Open,
  Daytona qualifying races, and all other non-points events (their formats
  distort points-race tendencies; see the report's Appendix A).
- **Granularity:** 43 materially distinct **physical configurations**, not
  facilities. Same facility ≠ same track: Atlanta pre/post-2022, Texas
  pre/post-2017, Kentucky pre/post-2016, Phoenix pre/post the Nov-2018
  start/finish relocation, Bristol concrete vs dirt, COTA full vs short,
  Charlotte oval vs Roval (v1/v2), Sonoma layout eras, the oval vs road
  layouts at Daytona/Indianapolis, and the temporary street circuits are all
  separate `track_id`s.
- **Physical configuration ≠ rules era.** The package keys physical layout
  changes as `track_id` splits and treats rules-package changes (e.g. the
  2019 tapered-spacer superspeedway package, the 2026 750-hp package at road
  courses and sub-1.5-mile ovals) as separate era overlays. Post-2022 Atlanta
  is a tapered-spacer-era drafting track — not a "restrictor-plate track";
  plates ended after the 2019 Daytona 500.

## Files

| File | Role |
|---|---|
| `README_nascar_track_audit.md` | Package manifest: file list, byte sizes, SHA-256 hashes. |
| `nascar_cup_track_audit_2015_2026.md` | The narrative audit (human-readable report; also machine-parseable front matter). |
| `nascar_cup_track_audit_bundle.json` | Complete structured bundle: metadata, per-year schedule mapping, 43 track records, similarity method, metric specs, hypotheses, sources, limitations. **Programmatic source of truth.** |
| `nascar_cup_track_configurations.csv` | One row per configuration (flat view of the bundle's track records). |
| `nascar_track_similarity_edges.csv` | ≤5 structural neighbors per configuration. **Analyst-prior feature distances, NOT validated outcome correlations.** |
| `nascar_track_sources.csv` | Source ledger S001–S041 (also embedded in the JSON). |
| `crosswalk_track_ids.csv` | **DERIVED, repo-authored** — see below. Not part of the package. |
| `INTEGRATION.md` | **DERIVED, repo-authored** — this file. |

## Provenance and integrity (verification record, 2026-07-19)

- Origin: owner-supplied package (`~/Downloads/nascar_cup_track_audit_package/`,
  also delivered as attachments). The six extracted files were added to the
  repo; the `.zip` was deliberately not (repo policy has no immutable-archive
  convention). Committing is the owner's call — the integration session itself
  committed nothing.
- **Byte-level verification performed:** all five manifest-listed files
  matched the manifest's byte sizes and SHA-256 hashes exactly at
  integration time, and the copies in this directory re-verify. The manifest
  itself (1,546 bytes, sha256 `eefd7a79ceb2…`) is not self-listed, by nature.
- Encoding: all files UTF-8, no NUL bytes. Canonical line endings differ by
  file and are pinned by the manifest hashes: the three CSVs are CRLF
  (standard csv-writer output); the Markdown and JSON are LF. Do not
  "normalize" them — that breaks the hashes.
- `src/test_track_audit.py` re-verifies the manifest hashes on every run, so
  any in-place edit of a package file turns the gate red. **A new package
  version must replace the six files together** (see "Updating" below).
- Live source spot-check (2026-07-19): S005 (nascaR.data) fetched 200 and
  matches its ledger description. nascar.com and jayski.com URLs (S001, S023,
  S039, S022 sampled) return HTTP 403 to automated fetchers (bot protection)
  — syntactically valid, live-status inconclusive from this environment, no
  evidence of link rot. No full re-research of sources was performed.

## The evidence model (preserve it)

Four evidence classes — **Verified Fact**, **Calculated Result**,
**Strong Inference**, **Working Hypothesis** — plus confidence labels
(`High`, `Medium-High`, and compound forms like
`High facts / Low sample`). Rules for consumers:

- The ten 1–10 `*_prior` fields (tire degradation, track-position premium,
  passing difficulty, attrition, restart volatility, pit importance,
  qualifying importance, strategy flexibility, DFS dominator concentration,
  finish variance) are **analyst structural priors** — explicitly labeled
  Working Hypotheses awaiting empirical calibration against loop/race data.
  They are not measurements and must never be presented as such.
- `completed_points_races_*` are observations;
  `future_scheduled_points_races_2026` are **not** — never mix future races
  into completed-race training data. The bundle keeps
  `completed_2026_through_cutoff` and `future_2026_after_cutoff` separate.
- Do not pool across `track_id`s merely because the facility matches, and do
  not strip source IDs, confidence labels, or sample-size caveats when
  deriving from these files.
- Doctrine interaction (HANDOFF): the frozen production config is untouched.
  **Nothing from this package feeds the production model.** Any future use of
  a prior as a model feature requires its own pre-registered, walk-forward
  validated spec, per repo doctrine.

## Derived crosswalk — `crosswalk_track_ids.csv`

The repo identifies tracks by the **feed's track-name string**
(`races_parsed.pkl` `track`, e.g. `Atlanta Motor Speedway`); the package
identifies **physical configurations** (`track_id`, era-split). Both ID
systems are preserved; the crosswalk maps between them. One row per
(`track_id`, era-range); `sonoma_short` has two rows (chute layout used
2015–2018 and again 2022+).

| column | meaning |
|---|---|
| `track_id` | Package configuration id (join key into all package files). |
| `feed_track_name` | cf.nascar.com feed string; empty only for `mapping=unmapped`. |
| `season_start`/`season_end` | Seasons this configuration answers for that name. `9999` (open-ended) only for configurations on the 2026 schedule; a configuration with no 2026 points date closes at its package last year (Dover, Mexico City, Chicago street) and is reopened consciously on a schedule return. Gate-enforced against the package's era bounds. |
| `date_note` | Set only where a season alone is ambiguous — Phoenix 2018 splits intra-season at the November start/finish relocation. |
| `mapping` | `one_to_one` \| `era_split` (name shared across configurations, resolved by season) \| `unmapped` (no verified feed string — only `daytona_road`, 2020–21). |
| `in_repo_scope` | Whether 2022+ parsed rows can map here. 36 of 43 ids are in scope; the 7 out-of-scope ids (`atlanta_pre_2022`, `kentucky_pre_2016`, `kentucky_post_2016`, `texas_pre_2017`, `phoenix_pre_2018f`, `daytona_road`, `sonoma_carousel`) exist for historical joins and stay available. |
| `my_type` | The repo's frozen production typology class (`walkforward.MY_TYPE`) for the feed name. Filled iff `in_repo_scope` (gate-enforced); blank for historical-only eras, because a name-keyed class validated on 2022+ data need not describe an earlier configuration (e.g. pre-2022 Atlanta was not a drafting track). |
| `package_primary_family` | The package's 12-family taxonomy. |

Caveats: historical feed strings for pre-2022 eras are **unverified** (the
repo dataset starts 2022) — facility renames (Dover International→Motor
Speedway 2021, Phoenix/ISM 2018–19, Richmond International→Raceway) are
flagged in `notes` and must be resolved when silver ever extends before
2022. `src/track_audit.py::track_id_for(name, season, month=None)` is the
join helper; it raises on the Phoenix-2018 ambiguity unless given a month.

## Reconciliation with existing repo logic (both preserved)

- **Two taxonomies, different jobs.** `MY_TYPE` (frozen, 6 buckets:
  SS/INT/SHORT/ROAD/OTHER/UNIQ) is the production model's validated
  pooling key and does not change. The package's `primary_family`
  (12 families) is finer-grained reference structure for DFS/betting/
  comparable-track work. Known primary-family-level disagreements, kept
  deliberately: Michigan and Auto Club → production `INT`, package
  "High-speed intermediate"; Pocono and Indianapolis oval → `INT`, package
  "Large flat oval"; WWT Gateway → `INT`, package "Flat short oval";
  Nashville → `INT`, package "High-banked compact oval"; Dover →
  production `SHORT`, package "High-banked compact oval". Darlington is
  *not* a primary-family disagreement — its package family is
  "Intermediate oval", the same family as the INT-defining tracks; its
  worn-track identity lives only in `secondary_family` ("extreme tire-wear
  driver track"). Neither taxonomy replaces the other; the crosswalk
  carries both.
- **Agreement worth noting:** both treat Daytona/Talladega/post-2022 Atlanta
  as the drafting group — the package's structure independently supports the
  repo's superspeedway stand-down doctrine (its attrition/finish-variance
  priors of 9–10 there are priors, not the reason for the doctrine).
- **Cross-validation of counts:** the package's "20 of 36 2026 races
  completed through 2026-07-12" exactly matches the repo dataset (20 races,
  last = Atlanta 2026-07-12); per-configuration 2022+ counts match for every
  track except one —
- **Finding (repo-side gap):** the package schedule implies **164** completed
  points races 2022 → cutoff; `races_parsed.pkl` holds **163**. The missing
  race is the **fall 2025 Talladega playoff race** (repo Talladega rids jump
  5555 → 5605). That race certainly ran, so this is a download/parse gap in
  the legacy pipeline, not a package error. Not fixed here (the legacy
  pipeline is mid-forward-test); flagged for the medallion **B3 bronze
  coverage session**, whose superset check should catch it. Model impact is
  minimal: Talladega is a stand-down track.

## Validation

```bash
cd src && python3 test_track_audit.py
```

Stdlib-only, same style as `test_report_plan.py`. Verifies: manifest SHA-256
hashes (immutability tripwire), encodings, JSON/CSV schemas, exactly 43
configurations with unique ids, all event-count identities (per-track and
schedule-by-year sums, 432/396/36/20/16), completed-vs-future separation,
similarity-edge referential integrity and rank/score monotonicity, S001–S041
ledger agreement between JSON and CSV, evidence/confidence vocabulary, the
"structural priors are not empirical" warnings, and crosswalk integrity
(id coverage; season ranges checked against the package's per-configuration
era bounds and raced seasons, so a corrupted `track_id` or range fails even
on a fresh clone without the pkl; era-overlap rules; `my_type` ⇔
`in_repo_scope`; and — when `races_parsed.pkl` is present — that every
parsed race resolves to exactly one `track_id` and that `my_type` matches
`walkforward.MY_TYPE`). The gate was mutation-tested at integration time:
eight corruption scenarios (byte flips, prior edits, deleted edges,
duplicated ids, label drift, a future→completed race move, a crosswalk id
swap, warning stripping) all turn it red — including when the attacker
regenerates the manifest hashes, since the semantic checks catch each one
independently.

## Updating or replacing the package

1. Obtain the new package version; verify its files against **its** manifest
   (sizes + SHA-256) before anything else.
2. Replace all six files in this directory together — never edit one in
   place, never mix versions.
3. Re-run `src/test_track_audit.py`; update `crosswalk_track_ids.csv` (and
   the gate's expectations) only if the configuration universe changed.
4. Record the version change and date in this file.
