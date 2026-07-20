#!/usr/bin/env python3
"""Loader for the vendored NASCAR track-audit research package.

Package: research/track_audit/ (external research dependency, integrated
2026-07-19; provenance and validation in research/track_audit/INTEGRATION.md).
The six source files there are immutable — src/test_track_audit.py re-verifies
their SHA-256 hashes against the package manifest on every run.

Reading rules (do not weaken downstream):
  * The ten 1-10 ``*_prior`` fields are ANALYST STRUCTURAL PRIORS — explicitly
    labeled Working Hypotheses awaiting empirical calibration. They are not
    measured statistics and must not be fed into the frozen production model
    without walk-forward validation evidence (HANDOFF doctrine).
  * ``completed_points_races_*`` counts completed observations;
    ``future_scheduled_points_races_2026`` counts races that had NOT happened
    at the 2026-07-19 research cutoff. Never mix the two in training data.
  * ``track_id`` is a physical-configuration key: same facility, different
    configuration => different id (Atlanta pre/post 2022, Texas pre/post 2017,
    COTA full/short, ...). Do not collapse ids by facility name.
  * Similarity edges are analyst-prior feature distances, NOT validated
    outcome correlations.
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, 'research', 'track_audit')

MANIFEST = os.path.join(PKG_DIR, 'README_nascar_track_audit.md')
REPORT = os.path.join(PKG_DIR, 'nascar_cup_track_audit_2015_2026.md')
BUNDLE = os.path.join(PKG_DIR, 'nascar_cup_track_audit_bundle.json')
CONFIGS = os.path.join(PKG_DIR, 'nascar_cup_track_configurations.csv')
EDGES = os.path.join(PKG_DIR, 'nascar_track_similarity_edges.csv')
SOURCES = os.path.join(PKG_DIR, 'nascar_track_sources.csv')
CROSSWALK = os.path.join(PKG_DIR, 'crosswalk_track_ids.csv')  # derived, repo-authored

PRIOR_FIELDS = [
    'tire_degradation_prior', 'track_position_premium_prior',
    'passing_difficulty_prior', 'attrition_risk_prior',
    'restart_volatility_prior', 'pit_road_importance_prior',
    'qualifying_importance_prior', 'strategy_flexibility_prior',
    'dfs_dominator_concentration_prior', 'finish_variance_prior',
]
COUNT_FIELDS = [
    'completed_points_races_2015_2025', 'completed_points_races_2026_through_cutoff',
    'future_scheduled_points_races_2026', 'scheduled_points_races_2026_total',
    'scope_event_count_including_2026_schedule', 'first_year_in_scope',
    'last_year_in_scope_or_schedule',
]

# bundle `schedule_by_year` / `completed_2026_through_cutoff` / `future_2026_after_cutoff` are
# keyed by this display-name vocabulary, not by track_id -- this is the one mapping between the
# two. Single source of truth: src/test_track_audit.py imports this rather than redefining it.
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

# Transcribed from the "Recommended era keys" table + its two VF-cited callouts in
# nascar_cup_track_audit_2015_2026.md (narrative-only content, not in the JSON bundle -- see
# DATA_DICTIONARY section 7). season_end=9999 marks the current, still-open era (mirrors the
# crosswalk's own open-range convention). source_ids point into the S001-S041 ledger.
RULES_ERA = [
    {'era_key': 'gen6_2015_725hp', 'season_start': 2015, 'season_end': 2015,
     'description': 'Horsepower reduction versus prior Gen-6 baseline; keep separate when '
                    'older data are added.', 'source_ids': ''},
    {'era_key': 'gen6_low_downforce', 'season_start': 2016, 'season_end': 2018,
     'description': 'Lower-downforce development; Phoenix start/finish splits in fall 2018.',
     'source_ids': ''},
    {'era_key': 'gen6_2019_package', 'season_start': 2019, 'season_end': 2021,
     'description': '550-hp/high-downforce package at many larger ovals; superspeedways '
                    'transitioned from plates to tapered spacers.', 'source_ids': 'S036;S037'},
    {'era_key': 'nextgen_launch', 'season_start': 2022, 'season_end': 2022,
     'description': 'Next Gen baseline; Atlanta physical reconfiguration begins.',
     'source_ids': ''},
    {'era_key': 'nextgen_low_downforce_short_road', 'season_start': 2023, 'season_end': 2025,
     'description': 'Short-track/road-course aero revisions plus evolving tire strategies.',
     'source_ids': ''},
    {'era_key': 'nextgen_750hp_sub15_road', 'season_start': 2026, 'season_end': 9999,
     'description': '750 hp at road courses and ovals under 1.5 miles; broad coefficient-reset '
                    'candidate.', 'source_ids': 'S039'},
]


def load_rules_era():
    """6 rows: era_key, season_start, season_end, description, source_ids (see RULES_ERA)."""
    return [dict(r) for r in RULES_ERA]


def _read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_bundle():
    """Full structured bundle (metadata, schedules, tracks, sources, ...)."""
    with open(BUNDLE, encoding='utf-8') as f:
        return json.load(f)


def load_configurations():
    """43 configuration rows, typed: priors/counts -> int, length -> float,
    road_course -> bool. All other fields stay verbatim strings."""
    rows = _read_csv(CONFIGS)
    for r in rows:
        for k in PRIOR_FIELDS + COUNT_FIELDS + ['turns']:
            r[k] = int(r[k])
        r['length_mi'] = float(r['length_mi'])
        r['road_course'] = r['road_course'] == 'True'
    return rows


def load_similarity_edges():
    """Structural-prior nearest-neighbor edges (NOT outcome correlations)."""
    rows = _read_csv(EDGES)
    for r in rows:
        r['neighbor_rank'] = int(r['neighbor_rank'])
        r['structural_similarity_score'] = float(r['structural_similarity_score'])
        r['distance'] = float(r['distance'])
    return rows


def load_sources():
    """Source ledger S001-S041, verbatim."""
    return _read_csv(SOURCES)


def load_crosswalk():
    """Derived crosswalk: package track_id <-> feed track name, era-aware."""
    rows = _read_csv(CROSSWALK)
    for r in rows:
        r['season_start'] = int(r['season_start'])
        r['season_end'] = int(r['season_end'])
        r['in_repo_scope'] = r['in_repo_scope'] == 'true'
    return rows


def track_id_for(feed_track_name, season, month=None):
    """Resolve a feed track name + season (races_parsed.pkl vocabulary) to the
    package's configuration-level track_id.

    Returns None for names/seasons the crosswalk does not cover. Raises
    ValueError for the one documented season-level ambiguity (Phoenix 2018,
    split at the November start/finish relocation) unless ``month`` is given.
    """
    hits = [r for r in load_crosswalk()
            if r['feed_track_name'] == feed_track_name
            and r['season_start'] <= season <= r['season_end']]
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]['track_id']
    if feed_track_name == 'Phoenix Raceway' and season == 2018:
        if month is None:
            raise ValueError('Phoenix 2018 splits intra-season; pass month')
        return 'phoenix_post_2018f' if month >= 11 else 'phoenix_pre_2018f'
    raise ValueError(f'ambiguous crosswalk match: {feed_track_name} {season}')
