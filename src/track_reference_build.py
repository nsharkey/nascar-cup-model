#!/usr/bin/env python3
"""Track reference tables from the vendored audit package (specs/medallion_architecture.md
section 3.4 conventions; derivation contract: research/track_audit_derivation.md section 2).

Builds, from research/track_audit/ (immutable, hash-gated) + src/track_audit.py's loader only --
no bronze/silver dependency for the first five tables:

  silver.track_dim              43 rows, one per track_id: T1 physical facts + T2 taxonomy +
                                 era bounds/counts + hp750_2026. Priors/narrative EXCLUDED by
                                 design (section 2.2) -- a fact table nobody can mistake for a
                                 Working Hypothesis.
  silver.track_xwalk            45 rows, the crosswalk verbatim + provenance.
  silver.track_priors            430 rows (43x10), long-form, quarantined (score_type/
                                 evidence_class carried on every row).
  silver.track_similarity_prior  193 rows, the structural-similarity edges verbatim, same
                                 quarantine treatment.
  silver.rules_era               6 rows, the narrative era table (track_audit.RULES_ERA).

Then, over silver.races (built by C1/C2's silver_build.py -- run that first):

  silver.race_track              (series_id, race_id, track_id) for every points race (any
                                 series) whose (track_name, year[, month]) resolves against the
                                 crosswalk -- unresolved races are simply absent (silver
                                 convention, section 3.4).
  silver.race_track_features     Cup-only (series_id=1) -- the section-2.3 leakage-free derived
                                 features (config_age_years, config_race_number,
                                 return_gap_years, era_key, era_race_number, hp750_2026),
                                 computed walk-forward from track_dim + the package's own
                                 schedule_by_year + race_track's own chronological order.
                                 Restricted to series_id=1 because schedule_by_year/track_dim's
                                 counts are Cup-points-race counts by the package's own stated
                                 scope (bundle metadata.scope) -- attaching them to a
                                 Xfinity/Truck race would misrepresent what they count.

Run from src/. `--full` is a no-op here (nothing is incremental -- every table is cheap to
fully rebuild from the immutable package + already-built silver.races every time).
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

import track_audit as ta
import warehouse

REPO_ROOT = warehouse.REPO_ROOT
SILVER_DIR = os.path.join(REPO_ROOT, 'data', 'silver')
TRACK_DIM_PATH = os.path.join(SILVER_DIR, 'track_dim.parquet')
TRACK_XWALK_PATH = os.path.join(SILVER_DIR, 'track_xwalk.parquet')
TRACK_PRIORS_PATH = os.path.join(SILVER_DIR, 'track_priors.parquet')
TRACK_SIMILARITY_PRIOR_PATH = os.path.join(SILVER_DIR, 'track_similarity_prior.parquet')
RULES_ERA_PATH = os.path.join(SILVER_DIR, 'rules_era.parquet')
RACE_TRACK_PATH = os.path.join(SILVER_DIR, 'race_track.parquet')
RACE_TRACK_FEATURES_PATH = os.path.join(SILVER_DIR, 'race_track_features.parquet')

PACKAGE_VERSION = '1.0'
POINTS_RACE_TYPE_ID = 1
NOT_EMPIRICAL_LABEL = 'Working Hypothesis'
SCHEDULE_YEAR_MIN, SCHEDULE_YEAR_MAX = 2015, 2026

# banking (verbatim free text, e.g. "31 deg turns; 18 deg tri-oval") -> (max_deg, secondary_deg).
# secondary_deg is populated ONLY where the text explicitly labels a tri-oval/frontstretch
# banking distinct from the turns banking (section 2.2); everything else (asymmetric turns 1-2
# vs 3-4, straights, multi-turn T1/T2/T3) folds into max_deg only, per the spec's literal note
# ("tri-oval/frontstretch where stated"). No "deg" number at all (road/street courses, one
# retired dirt oval) -> both None, not zero -- these tracks have no comparable banking metric.
_BANKING_DEG_RE = re.compile(r'(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?\s*deg')
_TRI_OVAL_RE = re.compile(r'tri-oval|frontstretch', re.IGNORECASE)


def parse_banking(banking_text):
    if not banking_text:
        return None, None
    primary_vals, secondary_val = [], None
    for segment in banking_text.split(';'):
        m = _BANKING_DEG_RE.search(segment)
        if not m:
            continue
        val = float(m.group(2)) if m.group(2) else float(m.group(1))
        if _TRI_OVAL_RE.search(segment):
            secondary_val = val
        else:
            primary_vals.append(val)
    return (max(primary_vals) if primary_vals else None), secondary_val


def _sha256_file(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# silver.track_dim
# ---------------------------------------------------------------------------

TRACK_DIM_SCHEMA = pa.schema([
    ('track_id', pa.string()), ('facility', pa.string()), ('configuration', pa.string()),
    ('location', pa.string()), ('status', pa.string()),
    ('length_mi', pa.float64()), ('shape', pa.string()), ('surface', pa.string()),
    ('road_course', pa.bool_()), ('turns', pa.int32()),
    ('banking_text', pa.string()), ('banking_max_deg', pa.float64()),
    ('banking_secondary_deg', pa.float64()),
    ('primary_family', pa.string()), ('secondary_family', pa.string()),
    ('first_year_in_scope', pa.int32()), ('last_year_in_scope_or_schedule', pa.int32()),
    ('completed_points_races_2015_2025', pa.int32()),
    ('completed_points_races_2026_through_cutoff', pa.int32()),
    ('future_scheduled_points_races_2026', pa.int32()),
    ('scheduled_points_races_2026_total', pa.int32()),
    ('hp750_2026', pa.bool_()),
    ('source_ids', pa.string()), ('confidence', pa.string()), ('evidence_class', pa.string()),
    ('package_version', pa.string()), ('source_sha256', pa.string()), ('built_at', pa.string()),
])


def build_track_dim():
    configs = ta.load_configurations()
    bundle_sha = _sha256_file(ta.BUNDLE)
    built_at = _now_iso()
    rows = []
    anomalies = []
    for c in configs:
        max_deg, sec_deg = parse_banking(c['banking'])
        if max_deg is None and any(ch.isdigit() for ch in c['banking']):
            anomalies.append(f"{c['track_id']}: banking text has digits but no parsed deg "
                              f"value: {c['banking']!r}")
        hp750 = bool(c['road_course']) or c['length_mi'] < 1.5
        rows.append({
            'track_id': c['track_id'], 'facility': c['facility'],
            'configuration': c['configuration'], 'location': c['location'],
            'status': c['status'],
            'length_mi': c['length_mi'], 'shape': c['shape'], 'surface': c['surface'],
            'road_course': c['road_course'], 'turns': c['turns'],
            'banking_text': c['banking'], 'banking_max_deg': max_deg,
            'banking_secondary_deg': sec_deg,
            'primary_family': c['primary_family'], 'secondary_family': c['secondary_family'],
            'first_year_in_scope': c['first_year_in_scope'],
            'last_year_in_scope_or_schedule': c['last_year_in_scope_or_schedule'],
            'completed_points_races_2015_2025': c['completed_points_races_2015_2025'],
            'completed_points_races_2026_through_cutoff':
                c['completed_points_races_2026_through_cutoff'],
            'future_scheduled_points_races_2026': c['future_scheduled_points_races_2026'],
            'scheduled_points_races_2026_total': c['scheduled_points_races_2026_total'],
            'hp750_2026': hp750,
            'source_ids': c['source_ids'], 'confidence': c['confidence'],
            'evidence_class': c['evidence_class'], 'package_version': PACKAGE_VERSION,
            'source_sha256': bundle_sha, 'built_at': built_at,
        })
    tbl = pa.Table.from_pylist(rows, schema=TRACK_DIM_SCHEMA)
    pq.write_table(tbl, TRACK_DIM_PATH)
    n_no_banking = sum(1 for r in rows if r['banking_max_deg'] is None)
    n_secondary = sum(1 for r in rows if r['banking_secondary_deg'] is not None)
    return {'rows': len(rows), 'anomalies': anomalies,
            'n_no_banking': n_no_banking, 'n_secondary': n_secondary}


# ---------------------------------------------------------------------------
# silver.track_xwalk
# ---------------------------------------------------------------------------

TRACK_XWALK_SCHEMA = pa.schema([
    ('track_id', pa.string()), ('feed_track_name', pa.string()),
    ('season_start', pa.int32()), ('season_end', pa.int32()),
    ('date_note', pa.string()), ('mapping', pa.string()),
    ('in_repo_scope', pa.bool_()), ('my_type', pa.string()),
    ('package_primary_family', pa.string()), ('notes', pa.string()),
    ('package_version', pa.string()), ('source_sha256', pa.string()), ('built_at', pa.string()),
])


def build_track_xwalk():
    rows = ta.load_crosswalk()
    xwalk_sha = _sha256_file(ta.CROSSWALK)
    built_at = _now_iso()
    for r in rows:
        r['package_version'] = PACKAGE_VERSION
        r['source_sha256'] = xwalk_sha
        r['built_at'] = built_at
    tbl = pa.Table.from_pylist(rows, schema=TRACK_XWALK_SCHEMA)
    pq.write_table(tbl, TRACK_XWALK_PATH)
    return {'rows': len(rows)}


# ---------------------------------------------------------------------------
# silver.track_priors -- the quarantine table (long form)
# ---------------------------------------------------------------------------

TRACK_PRIORS_SCHEMA = pa.schema([
    ('track_id', pa.string()), ('prior_name', pa.string()), ('score', pa.int32()),
    ('score_type', pa.string()), ('evidence_class', pa.string()),
    ('package_version', pa.string()),
])


def build_track_priors():
    configs = ta.load_configurations()
    rows = []
    for c in configs:
        for pf in ta.PRIOR_FIELDS:
            rows.append({
                'track_id': c['track_id'], 'prior_name': pf, 'score': c[pf],
                'score_type': c['score_type'], 'evidence_class': NOT_EMPIRICAL_LABEL,
                'package_version': PACKAGE_VERSION,
            })
    tbl = pa.Table.from_pylist(rows, schema=TRACK_PRIORS_SCHEMA)
    pq.write_table(tbl, TRACK_PRIORS_PATH)
    return {'rows': len(rows)}


# ---------------------------------------------------------------------------
# silver.track_similarity_prior -- optional quarantine table, edges verbatim
# ---------------------------------------------------------------------------

TRACK_SIMILARITY_PRIOR_SCHEMA = pa.schema([
    ('source_track_id', pa.string()), ('neighbor_rank', pa.int32()),
    ('target_track_id', pa.string()), ('structural_similarity_score', pa.float64()),
    ('distance', pa.float64()), ('method', pa.string()),
    ('evidence_class', pa.string()), ('package_version', pa.string()),
])


def build_track_similarity_prior():
    edges = ta.load_similarity_edges()
    for e in edges:
        e['evidence_class'] = NOT_EMPIRICAL_LABEL
        e['package_version'] = PACKAGE_VERSION
    tbl = pa.Table.from_pylist(edges, schema=TRACK_SIMILARITY_PRIOR_SCHEMA)
    pq.write_table(tbl, TRACK_SIMILARITY_PRIOR_PATH)
    return {'rows': len(edges)}


# ---------------------------------------------------------------------------
# silver.rules_era
# ---------------------------------------------------------------------------

RULES_ERA_SCHEMA = pa.schema([
    ('era_key', pa.string()), ('season_start', pa.int32()), ('season_end', pa.int32()),
    ('description', pa.string()), ('source_ids', pa.string()),
])


def build_rules_era():
    rows = ta.load_rules_era()
    tbl = pa.Table.from_pylist(rows, schema=RULES_ERA_SCHEMA)
    pq.write_table(tbl, RULES_ERA_PATH)
    return {'rows': len(rows)}


# ---------------------------------------------------------------------------
# silver.race_track -- convenience view materialized to parquet (section 2.2)
# ---------------------------------------------------------------------------

RACE_TRACK_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('track_id', pa.string()),
])


def build_race_track(con):
    """silver.races (points races, any series) JOIN track_xwalk on (track_name, year[, month]) --
    section 2.2's season-range rule, with the Phoenix-2018 month split implemented even though
    real feed data never actually hits it (2018 Phoenix races carry the 'ISM Raceway' track_name,
    which the crosswalk doesn't cover at all -- verified this session; see the build report).
    Unresolved/ambiguous-without-a-tiebreak races are simply absent, mirroring track_id_for()
    and the rest of the silver layer's coverage-by-absence convention."""
    if not os.path.exists(os.path.join(SILVER_DIR, 'races.parquet')):
        raise SystemExit('[track_reference_build] silver.races.parquet missing -- run '
                          'silver_build.py first (C1)')
    xwalk_rows = ta.load_crosswalk()
    con.register('_xwalk_stage', pa.Table.from_pylist(xwalk_rows))
    df = con.sql(f"""
        SELECT r.series_id, r.race_id, x.track_id AS xwalk_track_id, x.feed_track_name,
               month(CAST(r.race_date AS TIMESTAMP)) AS race_month
        FROM silver.races r
        JOIN _xwalk_stage x
          ON r.track_name = x.feed_track_name
         AND x.season_start <= r.year AND r.year <= x.season_end
        WHERE r.race_type_id = {POINTS_RACE_TYPE_ID}
    """).df()
    con.unregister('_xwalk_stage')

    resolved = []
    for (sid, rid), grp in df.groupby(['series_id', 'race_id']):
        if len(grp) == 1:
            resolved.append((sid, rid, grp.iloc[0]['xwalk_track_id']))
            continue
        # Only documented multi-match case: Phoenix's era_split, where pre/post season ranges
        # both cover 2018 (section 2.2's month rule). Never actually triggered by real feed
        # data -- 2018 Phoenix races carry the 'ISM Raceway' track_name, outside the
        # crosswalk's vocabulary entirely (verified this session) -- but implemented for parity
        # with track_audit.track_id_for()'s own ValueError-guarded logic.
        phoenix = grp[grp['feed_track_name'] == 'Phoenix Raceway']
        if len(grp) == 2 and len(phoenix) == 2:
            month = int(grp.iloc[0]['race_month'])
            want = 'phoenix_post_2018f' if month >= 11 else 'phoenix_pre_2018f'
            pick = grp[grp['xwalk_track_id'] == want]
            if len(pick) == 1:
                resolved.append((sid, rid, pick.iloc[0]['xwalk_track_id']))
                continue
        raise SystemExit(f'[track_reference_build] race (series {sid}, race {rid}) matched '
                          f"{len(grp)} track_ids with no tiebreak rule -- crosswalk ambiguity, "
                          f"needs owner escalation (mirrors track_id_for's ValueError): "
                          f"{grp['xwalk_track_id'].tolist()}")

    rows = [{'series_id': int(sid), 'race_id': int(rid), 'track_id': tid}
            for sid, rid, tid in resolved]
    tbl = pa.Table.from_pylist(rows, schema=RACE_TRACK_SCHEMA)
    pq.write_table(tbl, RACE_TRACK_PATH)
    return {'rows': len(rows),
            'by_series': df.groupby('series_id').size().to_dict()}


# ---------------------------------------------------------------------------
# silver.race_track_features -- section 2.3 derived features, Cup-only (see module docstring)
# ---------------------------------------------------------------------------

RACE_TRACK_FEATURES_SCHEMA = pa.schema([
    ('series_id', pa.int32()), ('race_id', pa.int32()), ('track_id', pa.string()),
    ('config_age_years', pa.int32()), ('config_race_number', pa.int32()),
    ('return_gap_years', pa.int32()),
    ('era_key', pa.string()), ('era_race_number', pa.int32()),
    ('hp750_2026', pa.bool_()),
])


def build_race_track_features(con):
    bundle = ta.load_bundle()
    sched = bundle['schedule_by_year']
    id_to_disp = {v: k for k, v in ta.DISPLAY_TO_ID.items()}
    track_dim_by_id = {r['track_id']: r for r in ta.load_configurations()}
    eras = ta.load_rules_era()

    def season_count(track_id, year):
        disp = id_to_disp.get(track_id)
        if disp is None or not (SCHEDULE_YEAR_MIN <= year <= SCHEDULE_YEAR_MAX):
            return 0
        return sched.get(str(year), {}).get(disp, 0)

    def era_for(year):
        for e in eras:
            if e['season_start'] <= year <= e['season_end']:
                return e['era_key']
        return None

    df = con.sql(f"""
        SELECT rt.series_id, rt.race_id, rt.track_id, r.year, r.race_date,
               row_number() OVER (
                   PARTITION BY rt.track_id, r.year ORDER BY CAST(r.race_date AS TIMESTAMP)
               ) - 1 AS within_season_order
        FROM read_parquet('{RACE_TRACK_PATH.replace(chr(92), '/')}') rt
        JOIN silver.races r ON r.series_id = rt.series_id AND r.race_id = rt.race_id
        WHERE rt.series_id = 1
        ORDER BY rt.track_id, r.year, CAST(r.race_date AS TIMESTAMP)
    """).df()

    rows = []
    for _, row in df.iterrows():
        tid, year = row['track_id'], int(row['year'])
        within = int(row['within_season_order'])
        dim = track_dim_by_id[tid]

        cum_prior = sum(season_count(tid, y) for y in range(SCHEDULE_YEAR_MIN, year))
        config_race_number = cum_prior + within + 1

        if within > 0:
            gap = 0
        else:
            prev_years = [y for y in range(SCHEDULE_YEAR_MIN, year) if season_count(tid, y) > 0]
            gap = (year - max(prev_years)) if prev_years else None

        era_key = era_for(year)
        era = next(e for e in eras if e['era_key'] == era_key)
        era_cum_prior = sum(season_count(tid, y)
                             for y in range(max(era['season_start'], SCHEDULE_YEAR_MIN), year))
        era_race_number = era_cum_prior + within + 1

        rows.append({
            'series_id': int(row['series_id']), 'race_id': int(row['race_id']), 'track_id': tid,
            'config_age_years': year - dim['first_year_in_scope'],
            'config_race_number': config_race_number,
            'return_gap_years': gap,
            'era_key': era_key, 'era_race_number': era_race_number,
            'hp750_2026': bool(dim['road_course']) or dim['length_mi'] < 1.5,
        })

    tbl = pa.Table.from_pylist(rows, schema=RACE_TRACK_FEATURES_SCHEMA)
    pq.write_table(tbl, RACE_TRACK_FEATURES_PATH)
    n_debuts = sum(1 for r in rows if r['return_gap_years'] is None and r['config_race_number'] == 1)
    return {'rows': len(rows), 'n_debut_races': n_debuts}


def main():
    os.makedirs(SILVER_DIR, exist_ok=True)
    report = {}
    report['track_dim'] = build_track_dim()
    report['track_xwalk'] = build_track_xwalk()
    report['track_priors'] = build_track_priors()
    report['track_similarity_prior'] = build_track_similarity_prior()
    report['rules_era'] = build_rules_era()

    warehouse.build_warehouse()  # picks up silver.races, needed by both steps below
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    report['race_track'] = build_race_track(con)
    report['race_track_features'] = build_race_track_features(con)
    con.close()

    warehouse.build_warehouse()  # final pass: register race_track/race_track_features views too

    print('=' * 78)
    print('TRACK REFERENCE BUILD (C3) -- report')
    print('=' * 78)
    for name in ('track_dim', 'track_xwalk', 'track_priors', 'track_similarity_prior',
                 'rules_era', 'race_track', 'race_track_features'):
        r = report[name]
        print(f"  silver.{name}: {r['rows']} rows")
    td = report['track_dim']
    print(f"  track_dim banking parse: {td['n_no_banking']}/43 no numeric banking (road/street "
          f"courses + retired dirt), {td['n_secondary']}/43 with a tri-oval/frontstretch "
          f"secondary value")
    if td['anomalies']:
        print(f"  track_dim banking anomalies: {td['anomalies']}")
    rt = report['race_track']
    print(f"  race_track by series: {rt['by_series']}")
    rtf = report['race_track_features']
    print(f"  race_track_features debut races (no prior gap, config_race_number=1): "
          f"{rtf['n_debut_races']}")
    print('=' * 78)
    return report


if __name__ == '__main__':
    main()
