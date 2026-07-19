# NASCAR Cup Track Audit — Artifact Manifest

Research cutoff: 2026-07-19. Primary scope: points-paying Cup races; 2015-2025 completed history plus the full scheduled 2026 slate. Non-points events are deliberately deferred.

## Files

- `nascar_cup_track_audit_2015_2026.md` — self-contained human- and machine-readable research report.
- `nascar_cup_track_audit_bundle.json` — complete structured bundle: schedule mapping, 43 configurations, priors, metric specifications, hypotheses and source ledger.
- `nascar_cup_track_configurations.csv` — one row per physical configuration.
- `nascar_track_similarity_edges.csv` — up to five within-supergroup structural neighbors per configuration.
- `nascar_track_sources.csv` — standalone source ledger.

## Integrity

| File | Bytes | SHA-256 |
|---|---:|---|
| `nascar_cup_track_audit_2015_2026.md` | 109571 | `a0911589ea3dcc86eb82ee7b33b0aba26231fe09560a2da88bf7d0ee7c9bd22e` |
| `nascar_cup_track_audit_bundle.json` | 141932 | `135e437ee3a72d3821c8b05ee4ba99663d176f37ddd5fcc98e98c4ea67dfbdef` |
| `nascar_cup_track_configurations.csv` | 58175 | `534616028734cac0632252d96c5b24cb86b2450c9d734664365cb8dbc510daab` |
| `nascar_track_similarity_edges.csv` | 21292 | `edebba59547dc379cd67fe114f0e5da7e6a10302d6e5e3d54f68fd2a912c013d` |
| `nascar_track_sources.csv` | 9221 | `44f06d12472cec1fd364a4751158c76fc2a4015a0da36aea95804548bddd0bde` |

The 1-10 score fields are explicitly analyst structural priors, not empirical measurements. See the main report methodology before production use.