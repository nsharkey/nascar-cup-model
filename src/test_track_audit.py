#!/usr/bin/env python3
"""Zero-trust validation gate for the vendored track-audit research package
(research/track_audit/) — the analogue of test_report_plan.py for reference
data. Runs with plain stdlib asserts (no pytest); exits nonzero on any failure.

Fails on:
  1. Integrity   — a committed package file no longer matches the manifest's
                   byte size / SHA-256 (immutability tripwire), or contains
                   NUL bytes / CRLF / invalid UTF-8.
  2. Schema      — missing files, unparseable JSON/CSV, missing columns,
                   wrong row counts, bad numeric/boolean values.
  3. Identity    — duplicate/empty track_id or source_id, event-count
                   identities broken, schedule sums wrong, completed vs
                   future 2026 races not kept distinct.
  4. Referential — similarity edge endpoints or source_ids that resolve to
                   nothing; JSON and CSV serializations that disagree.
  5. Labeling    — evidence/confidence vocabulary drift, or loss of the
                   "structural priors are not empirical measurements" warnings.
  6. Crosswalk   — derived crosswalk_track_ids.csv out of sync with the
                   package or (when races_parsed.pkl is present) with the
                   feed track names the production pipeline actually uses.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import track_audit as ta  # noqa: E402

EVIDENCE_LABELS = {'Verified Fact', 'Calculated Result', 'Strong Inference',
                   'Working Hypothesis'}
CONFIDENCE_ALLOWED = {
    'High', 'Medium-High',
    'High facts / Low predictive', 'High facts / Low generalization',
    'High facts / Low sample', 'High facts / Medium behavior',
    'High facts / Medium priors', 'High facts / Low points-sample',
}
EDGE_METHOD = 'Analyst-prior feature distance; not historical outcome correlation'

CONFIG_COLUMNS = [
    'track_id', 'facility', 'configuration', 'location', 'length_mi', 'shape',
    'surface', 'road_course', 'turns', 'banking', 'primary_family',
    'secondary_family', 'tire_degradation_prior', 'track_position_premium_prior',
    'passing_difficulty_prior', 'attrition_risk_prior', 'restart_volatility_prior',
    'pit_road_importance_prior', 'qualifying_importance_prior',
    'strategy_flexibility_prior', 'dfs_dominator_concentration_prior',
    'finish_variance_prior', 'key_comparables', 'key_change_notes',
    'racing_analysis', 'dfs_betting_implications', 'source_ids', 'confidence',
    'status', 'completed_points_races_2015_2025',
    'completed_points_races_2026_through_cutoff',
    'future_scheduled_points_races_2026', 'scheduled_points_races_2026_total',
    'scope_event_count_including_2026_schedule', 'first_year_in_scope',
    'last_year_in_scope_or_schedule', 'event_count_evidence', 'score_type',
    'evidence_class', 'structural_nearest_neighbors',
]
EDGE_COLUMNS = ['source_track_id', 'neighbor_rank', 'target_track_id',
                'structural_similarity_score', 'distance', 'method']
SOURCE_COLUMNS = ['source_id', 'title', 'publisher', 'url', 'source_type',
                  'reliability', 'coverage']
CROSSWALK_COLUMNS = ['track_id', 'feed_track_name', 'season_start', 'season_end',
                     'date_note', 'mapping', 'in_repo_scope', 'my_type',
                     'package_primary_family', 'notes']

# package display names (schedule_by_year vocabulary) -> track_id
DISPLAY_TO_ID = {
    'Daytona oval': 'daytona_oval', 'Talladega': 'talladega_oval',
    'Atlanta pre-2022': 'atlanta_pre_2022', 'Atlanta post-2022': 'atlanta_post_2022',
    'Auto Club': 'auto_club_2mi', 'Charlotte oval': 'charlotte_oval',
    'Chicagoland': 'chicagoland_oval', 'Darlington': 'darlington',
    'Homestead': 'homestead', 'Kansas': 'kansas',
    'Kentucky pre-2016': 'kentucky_pre_2016', 'Kentucky post-2016': 'kentucky_post_2016',
    'Las Vegas': 'las_vegas', 'Michigan': 'michigan',
    'Texas pre-2017': 'texas_pre_2017', 'Texas post-2017': 'texas_post_2017',
    'Indianapolis oval': 'indianapolis_oval', 'Pocono': 'pocono',
    'Bristol concrete': 'bristol_concrete', 'Bristol dirt': 'bristol_dirt',
    'Dover': 'dover', 'Iowa': 'iowa', 'Martinsville': 'martinsville',
    'Nashville': 'nashville', 'New Hampshire': 'new_hampshire',
    'North Wilkesboro': 'north_wilkesboro',
    'Phoenix pre-2018F': 'phoenix_pre_2018f', 'Phoenix post-2018F': 'phoenix_post_2018f',
    'Richmond': 'richmond', 'WWT Gateway': 'wwt_gateway',
    'Charlotte Roval v1': 'charlotte_roval_v1', 'Charlotte Roval v2': 'charlotte_roval_v2',
    'Chicago street': 'chicago_street', 'COTA full': 'cota_full',
    'COTA short': 'cota_short', 'Daytona road': 'daytona_road',
    'Indianapolis road': 'indianapolis_road', 'Mexico City': 'mexico_city',
    'Road America': 'road_america', 'San Diego street': 'san_diego_street',
    'Sonoma short': 'sonoma_short', 'Sonoma carousel': 'sonoma_carousel',
    'Watkins Glen': 'watkins_glen',
}


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # ---- 1. files, encoding, manifest integrity -----------------------------
    package_files = [ta.MANIFEST, ta.REPORT, ta.BUNDLE, ta.CONFIGS, ta.EDGES,
                     ta.SOURCES, ta.CROSSWALK]
    for p in package_files:
        check(os.path.exists(p), f'[files] missing: {p}')
    if failures:
        print('FAIL — package files missing:', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1

    # Canonical line endings (pinned by the manifest hashes): the three package
    # CSVs are CRLF (standard csv-writer output); MD/JSON and the derived
    # crosswalk are LF. Bare CR is corruption anywhere.
    crlf_files = {ta.CONFIGS, ta.EDGES, ta.SOURCES}
    for p in package_files:
        raw = open(p, 'rb').read()
        name = os.path.basename(p)
        check(b'\x00' not in raw, f'[encoding] {name}: NUL byte found')
        check(raw.count(b'\r') == raw.count(b'\r\n'),
              f'[encoding] {name}: bare CR found')
        if p in crlf_files:
            check(raw.count(b'\r\n') == raw.count(b'\n'),
                  f'[encoding] {name}: expected uniform CRLF (canonical form)')
        else:
            check(b'\r' not in raw, f'[encoding] {name}: expected LF-only')
        try:
            raw.decode('utf-8')
        except UnicodeDecodeError as e:
            check(False, f'[encoding] {name}: invalid UTF-8 ({e})')

    manifest = open(ta.MANIFEST, encoding='utf-8').read()
    rows = re.findall(r'\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{64})`\s*\|',
                      manifest)
    check(len(rows) == 5, f'[manifest] expected 5 integrity rows, found {len(rows)}')
    for fname, size, digest in rows:
        p = os.path.join(ta.PKG_DIR, fname)
        if not os.path.exists(p):
            check(False, f'[manifest] listed file missing: {fname}')
            continue
        raw = open(p, 'rb').read()
        check(len(raw) == int(size),
              f'[manifest] {fname}: {len(raw)} bytes on disk, manifest says {size}')
        check(hashlib.sha256(raw).hexdigest() == digest,
              f'[manifest] {fname}: sha256 mismatch — package files are immutable; '
              f'a new package version must update the manifest too')

    # ---- 2. bundle JSON ------------------------------------------------------
    bundle = ta.load_bundle()
    for key in ['metadata', 'evidence_labels', 'schedule_by_year',
                'completed_2026_through_cutoff', 'future_2026_after_cutoff',
                'tracks', 'similarity_method', 'metric_specifications',
                'novel_hypotheses', 'sources', 'limitations']:
        check(key in bundle, f'[bundle] missing top-level key: {key}')

    meta = bundle['metadata']
    check(meta.get('research_cutoff') == '2026-07-19',
          f"[bundle] research_cutoff {meta.get('research_cutoff')!r} != '2026-07-19'")
    check(meta.get('configuration_count') == 43, '[bundle] configuration_count != 43')
    check(meta.get('completed_points_races_2015_2025') == 396,
          '[bundle] completed 2015-2025 != 396')
    check(meta.get('scheduled_points_races_2026') == 36, '[bundle] 2026 slate != 36')
    check(meta.get('completed_2026_through_cutoff') == 20,
          '[bundle] completed 2026 through cutoff != 20')
    check('structural priors' in meta.get('score_warning', ''),
          '[bundle] score_warning lost the structural-priors caveat')
    check(set(bundle['evidence_labels']) == EVIDENCE_LABELS,
          f"[bundle] evidence labels {sorted(bundle['evidence_labels'])} != expected 4")
    check('Not historical outcome correlation'
          in bundle['similarity_method'].get('warning', ''),
          '[bundle] similarity_method warning lost the not-outcome-correlation caveat')

    jtracks = {t['track_id']: t for t in bundle['tracks']}
    check(len(bundle['tracks']) == 43, f"[bundle] {len(bundle['tracks'])} tracks != 43")
    check(len(jtracks) == len(bundle['tracks']), '[bundle] duplicate track_id')

    for tid, t in jtracks.items():
        c1525 = t['completed_points_races_2015_2025']
        c26 = t['completed_points_races_2026_through_cutoff']
        f26 = t['future_scheduled_points_races_2026']
        s26 = t['scheduled_points_races_2026_total']
        scope = t['scope_event_count_including_2026_schedule']
        check(c26 + f26 == s26,
              f'[bundle] {tid}: completed-2026 {c26} + future-2026 {f26} != scheduled {s26}')
        check(c1525 + s26 == scope,
              f'[bundle] {tid}: 2015-25 {c1525} + 2026 sched {s26} != scope {scope}')
        check(t['first_year_in_scope'] <= t['last_year_in_scope_or_schedule'],
              f'[bundle] {tid}: first_year > last_year')
        for pf in ta.PRIOR_FIELDS:
            check(isinstance(t[pf], int) and 1 <= t[pf] <= 10,
                  f'[bundle] {tid}: {pf}={t[pf]!r} outside 1-10')
        check('not an empirical measurement' in t.get('score_type', ''),
              f'[bundle] {tid}: score_type lost the not-empirical warning')

    check(sum(t['completed_points_races_2015_2025'] for t in jtracks.values()) == 396,
          '[bundle] per-track 2015-2025 completions do not sum to 396')
    check(sum(t['completed_points_races_2026_through_cutoff'] for t in jtracks.values()) == 20,
          '[bundle] per-track 2026 completions do not sum to 20')
    check(sum(t['future_scheduled_points_races_2026'] for t in jtracks.values()) == 16,
          '[bundle] per-track 2026 future races do not sum to 16')

    sched = bundle['schedule_by_year']
    check(sorted(sched) == [str(y) for y in range(2015, 2027)],
          '[bundle] schedule_by_year does not cover exactly 2015-2026')
    for yr, tracks in sched.items():
        check(sum(tracks.values()) == 36, f'[bundle] {yr} schedule sums to '
              f'{sum(tracks.values())}, not 36')
        for disp in tracks:
            check(disp in DISPLAY_TO_ID, f'[bundle] {yr}: unknown display name {disp!r}')

    comp26, fut26 = bundle['completed_2026_through_cutoff'], bundle['future_2026_after_cutoff']
    check(sum(comp26.values()) == 20, '[bundle] completed_2026_through_cutoff != 20 races')
    check(sum(fut26.values()) == 16, '[bundle] future_2026_after_cutoff != 16 races')
    for disp in set(sched['2026']) | set(comp26) | set(fut26):
        check(comp26.get(disp, 0) + fut26.get(disp, 0) == sched['2026'].get(disp, 0),
              f'[bundle] 2026 completed+future != scheduled for {disp!r} — '
              f'completed and future races must stay distinct and exhaustive')

    # display-name schedule vs per-track counts
    id_to_disp = {v: k for k, v in DISPLAY_TO_ID.items()}
    for tid, t in jtracks.items():
        disp = id_to_disp[tid]
        hist = sum(sched[str(y)].get(disp, 0) for y in range(2015, 2026))
        check(hist == t['completed_points_races_2015_2025'],
              f'[bundle] {tid}: schedule_by_year 2015-2025 sums to {hist}, '
              f"track record says {t['completed_points_races_2015_2025']}")
        check(sched['2026'].get(disp, 0) == t['scheduled_points_races_2026_total'],
              f'[bundle] {tid}: 2026 schedule count mismatch')

    # ---- 3. configurations CSV ----------------------------------------------
    configs = ta.load_configurations()
    check(len(configs) == 43, f'[configs] {len(configs)} rows != 43')
    raw_cols = list(configs[0].keys()) if configs else []
    check(raw_cols == CONFIG_COLUMNS,
          f'[configs] column drift: {set(raw_cols) ^ set(CONFIG_COLUMNS) or "order changed"}')
    cids = [r['track_id'] for r in configs]
    check(len(set(cids)) == 43 and all(cids), '[configs] track_id not unique/nonempty')
    check(set(cids) == set(jtracks), '[configs] track_id set differs from bundle JSON')
    for r in configs:
        tid = r['track_id']
        for pf in ta.PRIOR_FIELDS:
            check(1 <= r[pf] <= 10, f'[configs] {tid}: {pf}={r[pf]} outside 1-10')
        check(r['length_mi'] > 0 and r['turns'] > 0, f'[configs] {tid}: bad length/turns')
        check(r['confidence'] in CONFIDENCE_ALLOWED,
              f"[configs] {tid}: unknown confidence label {r['confidence']!r}")
        check('not an empirical measurement' in r['score_type'],
              f'[configs] {tid}: score_type lost the not-empirical warning')
        for lbl in EVIDENCE_LABELS:
            check(lbl in r['evidence_class'],
                  f'[configs] {tid}: evidence_class no longer names {lbl!r}')
        check(r['completed_points_races_2026_through_cutoff']
              + r['future_scheduled_points_races_2026']
              == r['scheduled_points_races_2026_total'],
              f'[configs] {tid}: 2026 completed+future != scheduled')
        check(r['completed_points_races_2015_2025']
              + r['scheduled_points_races_2026_total']
              == r['scope_event_count_including_2026_schedule'],
              f'[configs] {tid}: scope event count identity broken')

    # ---- 4. CSV <-> JSON field-for-field agreement --------------------------
    def same(a, b):
        if isinstance(a, bool):
            return str(a) == str(b)
        if isinstance(a, (int, float)):
            try:
                return float(a) == float(b)
            except (TypeError, ValueError):
                return False
        return str(a) == str(b)

    for r in configs:
        j = jtracks[r['track_id']]
        for col in CONFIG_COLUMNS:
            check(col in j, f"[cross] {r['track_id']}: field {col} absent from JSON")
            if col in j:
                check(same(j[col], r[col]),
                      f"[cross] {r['track_id']}.{col}: JSON {j[col]!r} != CSV {r[col]!r}")

    # ---- 5. similarity edges -------------------------------------------------
    edges = ta.load_similarity_edges()
    check(list(edges[0].keys()) == EDGE_COLUMNS if edges else False,
          '[edges] column drift')
    seen_pairs = set()
    by_source = {}
    for e in edges:
        s, t = e['source_track_id'], e['target_track_id']
        check(s in jtracks, f'[edges] unknown source {s!r}')
        check(t in jtracks, f'[edges] unknown target {t!r}')
        check(s != t, f'[edges] self-edge at {s!r}')
        check((s, t) not in seen_pairs, f'[edges] duplicate edge {s}->{t}')
        seen_pairs.add((s, t))
        check(0 < e['structural_similarity_score'] <= 100,
              f"[edges] {s}->{t}: score {e['structural_similarity_score']} outside (0,100]")
        check(e['distance'] >= 0, f'[edges] {s}->{t}: negative distance')
        check(e['method'] == EDGE_METHOD,
              f'[edges] {s}->{t}: method string drifted (must stay labeled as '
              f'analyst-prior distance, not outcome correlation)')
        by_source.setdefault(s, []).append(e)
    for s, es in by_source.items():
        es.sort(key=lambda e: e['neighbor_rank'])
        check([e['neighbor_rank'] for e in es] == list(range(1, len(es) + 1)),
              f'[edges] {s}: ranks not consecutive from 1')
        check(len(es) <= 5, f'[edges] {s}: more than 5 neighbors')
        scores = [e['structural_similarity_score'] for e in es]
        dists = [e['distance'] for e in es]
        check(scores == sorted(scores, reverse=True), f'[edges] {s}: scores not descending')
        check(dists == sorted(dists), f'[edges] {s}: distances not ascending')
    # neighbor lists embedded in the config table must agree with the edge file
    for r in configs:
        listed = [m.group(1) for m in
                  re.finditer(r'([a-z0-9_]+) \(', r['structural_nearest_neighbors'])]
        from_edges = [e['target_track_id'] for e in by_source.get(r['track_id'], [])]
        check(listed == from_edges or
              (r['structural_nearest_neighbors'].startswith('None') and not from_edges),
              f"[edges] {r['track_id']}: config neighbor list {listed} != edge file "
              f'{from_edges}')

    # ---- 6. source ledger ----------------------------------------------------
    sources = ta.load_sources()
    check(list(sources[0].keys()) == SOURCE_COLUMNS if sources else False,
          '[sources] column drift')
    sids = [s['source_id'] for s in sources]
    check(sids == [f'S{i:03d}' for i in range(1, 42)],
          '[sources] expected exactly S001-S041 in order')
    for s in sources:
        check(re.match(r'^https://\S+$', s['url']),
              f"[sources] {s['source_id']}: URL not https/whitespace-free: {s['url']!r}")
        check(all(s[c].strip() for c in SOURCE_COLUMNS),
              f"[sources] {s['source_id']}: empty field")
    jsources = {s['source_id']: s for s in bundle['sources']}
    check(set(jsources) == set(sids), '[sources] JSON and CSV ledgers list different ids')
    for s in sources:
        j = jsources.get(s['source_id'], {})
        for col in SOURCE_COLUMNS:
            check(j.get(col) == s[col],
                  f"[sources] {s['source_id']}.{col}: JSON != CSV")
    referenced = set()
    for r in configs:
        referenced.update(x.strip() for x in r['source_ids'].split(';') if x.strip())
    check(referenced <= set(sids),
          f'[sources] configs reference unknown source ids: {sorted(referenced - set(sids))}')

    # ---- 7. narrative report spot-checks ------------------------------------
    report = open(ta.REPORT, encoding='utf-8').read()
    for needle, why in [
        ('research_cutoff: "2026-07-19"', 'research cutoff'),
        ('configurations: 43', 'configuration count'),
        ('**Evidence labels**', 'evidence-label contract'),
        ('structural priors', 'prior warning'),
        ('## Appendix A', 'non-points deferral appendix'),
        ('| S041 |', 'source ledger completeness'),
    ]:
        check(needle in report, f'[report] lost {why} ({needle!r} not found)')

    # ---- 8. crosswalk (derived) ---------------------------------------------
    xwalk = ta.load_crosswalk()
    check(list(xwalk[0].keys()) == CROSSWALK_COLUMNS if xwalk else False,
          '[crosswalk] column drift')
    xids = {r['track_id'] for r in xwalk}
    check(xids == set(jtracks),
          f'[crosswalk] id coverage: missing {sorted(set(jtracks) - xids)}, '
          f'unknown {sorted(xids - set(jtracks))}')
    fam = {r['track_id']: r['primary_family'] for r in configs}
    by_name = {}
    for r in xwalk:
        tid = r['track_id']
        check(r['season_start'] <= r['season_end'], f'[crosswalk] {tid}: bad season range')
        check(r['mapping'] in {'one_to_one', 'era_split', 'unmapped'},
              f"[crosswalk] {tid}: unknown mapping {r['mapping']!r}")
        check((r['mapping'] == 'unmapped') == (r['feed_track_name'] == ''),
              f'[crosswalk] {tid}: unmapped rows and empty feed names must coincide')
        check(r['package_primary_family'] == fam[tid],
              f'[crosswalk] {tid}: package_primary_family drifted from the package')
        if r['feed_track_name']:
            by_name.setdefault(r['feed_track_name'], []).append(r)
    for name, rs in by_name.items():
        for i in range(len(rs)):
            for k in range(i + 1, len(rs)):
                a, b = rs[i], rs[k]
                overlap = (a['season_start'] <= b['season_end']
                           and b['season_start'] <= a['season_end'])
                if overlap:
                    check(a['date_note'] and b['date_note'],
                          f'[crosswalk] {name!r}: rows {a["track_id"]}/{b["track_id"]} '
                          f'overlap without a documented intra-season date split')

    # package-era consistency — pkl-independent, so a fresh clone still catches
    # a corrupted track_id or season range in the derived crosswalk
    by_id = {}
    for r in xwalk:
        by_id.setdefault(r['track_id'], []).append(r)
        check(bool(r['my_type']) == r['in_repo_scope'],
              f"[crosswalk] {r['track_id']}: my_type must be filled iff in_repo_scope "
              f'(blank for historical-only eras — a name-keyed MY_TYPE class need not '
              f'describe a pre-2022 configuration)')
    for tid, rs in by_id.items():
        t = jtracks[tid]
        first = min(r['season_start'] for r in rs)
        last = max(r['season_end'] for r in rs)
        check(first == t['first_year_in_scope'],
              f"[crosswalk] {tid}: range starts {first}, package era starts "
              f"{t['first_year_in_scope']}")
        if t['scheduled_points_races_2026_total'] > 0:
            check(last == 9999,
                  f'[crosswalk] {tid}: on the 2026 schedule but range closes at {last}')
        else:
            check(last == t['last_year_in_scope_or_schedule'],
                  f'[crosswalk] {tid}: range extends to {last} but the package era '
                  f"ends {t['last_year_in_scope_or_schedule']} — closed configurations "
                  f'must close (reopen consciously on a schedule return)')
        disp = id_to_disp[tid]
        for y in range(2015, 2027):
            if sched[str(y)].get(disp, 0):
                check(any(r['season_start'] <= y <= r['season_end'] for r in rs),
                      f'[crosswalk] {tid}: raced in {y} per the package schedule but '
                      f'no era row covers that season')

    # repo-join checks — only when the parsed dataset (gitignored) is present
    pkl = Path(__file__).resolve().parent / 'races_parsed.pkl'
    if pkl.exists():
        import pickle
        import walkforward  # loads races_parsed.pkl at import; safe: it exists
        races = pickle.load(open(pkl, 'rb'))
        known = set(walkforward.MY_TYPE)
        for name, rs in by_name.items():
            # Historical-only names (e.g. Kentucky Speedway, gone before the
            # repo's 2022 floor) are legitimately absent from MY_TYPE.
            if any(r['in_repo_scope'] for r in rs):
                check(name in known,
                      f'[crosswalk] in-scope feed name {name!r} not in walkforward.MY_TYPE')
            for r in rs:
                if r['my_type']:
                    check(walkforward.MY_TYPE.get(name) == r['my_type'],
                          f"[crosswalk] {r['track_id']}: my_type {r['my_type']!r} != "
                          f'walkforward.MY_TYPE[{name!r}]={walkforward.MY_TYPE.get(name)!r}')
        assigned = 0
        in_scope = {r['track_id'] for r in xwalk if r['in_repo_scope']}
        for race in races:
            try:
                tid = ta.track_id_for(race['track'], race['year'])
            except ValueError as e:
                check(False, f"[crosswalk] {race['track']} {race['year']}: {e}")
                continue
            check(tid is not None,
                  f"[crosswalk] unmapped repo race: {race['track']!r} {race['year']}")
            if tid is not None:
                assigned += 1
                check(tid in in_scope,
                      f'[crosswalk] {tid}: has repo rows but in_repo_scope is false')
        check(assigned == len(races),
              f'[crosswalk] only {assigned}/{len(races)} repo races resolve to a track_id')
        note = f'{assigned}/{len(races)} repo races crosswalked'
    else:
        note = 'races_parsed.pkl absent — repo-join checks SKIPPED (structural checks ran)'

    if failures:
        print(f'FAIL — {len(failures)} problem(s):', file=sys.stderr)
        for f in failures:
            print(f'  - {f}', file=sys.stderr)
        return 1
    print(f'PASS — manifest hashes verified, 43 configurations consistent across '
          f'MD/JSON/CSV, {len(edges)} edges valid, S001-S041 reconciled, '
          f'priors still labeled non-empirical; {note}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
