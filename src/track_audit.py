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
