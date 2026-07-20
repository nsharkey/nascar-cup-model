#!/usr/bin/env python3
"""F19 -- incentive-state analytics (Tier A, descriptive only).

research/domain_knowledge_scan.md sections 5/10.3 is the execution contract. This script
answers three descriptive questions about playoff-cutline pressure using silver.results
(2017+, results-grade -- verbatim weekend-feed, no lap-times dependency) and silver.stage_results
(2020+, schema floor). It reads data/nascar.duckdb read-only and writes nothing back to any
silver/gold table, walkforward.py, or predict_next.py -- Tier A per the kickoff prompt: never
joins a feature bank without its own later pre-registered A/B.

Definitions (frozen elsewhere, reused verbatim):
  - crash-class / mech-class DNF taxonomy: specs/dnf_status_feature.md section 1
    (status in {'accident','dvp'} = crash-class; DNF = status != 'running').
  - cutline distance: |points_position - 16|, read from the driver's most recent PRIOR
    in-season race (LAG by season_race_num within (year, driver_id) -- for the rare driver who
    sits out a race this is their last known state, not necessarily race t-1 exactly; documented
    in report/INCENTIVE_ANALYTICS.md, not silently assumed). Leak-free by construction (scan section
    5.2): race t's own points_position is post-race-t and is never read as race t's predictor.
  - regular season = the first 26 races of a season by date; playoffs = the last 10. Verified
    against silver.races.playoff_round for 2020-2025 (36 - 10/9 playoff rows == 26 in every season
    checked) rather than assumed; used instead of playoff_round directly because playoff_round
    is a schema floor (0/absent 2017-2019, per DATA_DICTIONARY 9g) and this rule is not.
  - late window = the last 5 regular-season races (season_race_num 22-26); a 3-race window
    (24-26) is reported alongside as a robustness check, per the kickoff's "3-5" range.
  - "ordinal-only" caveat (scan section 5.2/9.3): season point TOTALS are not in-feed; only
    points_position (rank) is official and exact. No points-distance metric is attempted anywhere
    in this script.
"""
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, pearsonr, spearmanr, ttest_1samp, wilcoxon

import warehouse

CUTLINE = 16
REGULAR_SEASON_LEN = 26
LATE_WINDOW_5 = (REGULAR_SEASON_LEN - 4, REGULAR_SEASON_LEN)  # 22-26
LATE_WINDOW_3 = (REGULAR_SEASON_LEN - 2, REGULAR_SEASON_LEN)  # 24-26
BUBBLE_MAX_DIST = 5       # ranks 11-21 (scan 5.3's "~6-10 bubble drivers" order of magnitude)
LOCKED_IN_MAX_RANK = 10   # comfortably inside the cutline (scan 5.1 claim (b))


def load_base():
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    df = con.sql("""
        SELECT r.year, r.race_id, r.race_date, res.driver_id, res.finishing_position,
               res.points_position, lower(trim(res.finishing_status)) AS status
        FROM silver.races r
        JOIN silver.results res USING (series_id, race_id)
        WHERE r.series_id = 1 AND r.race_type_id = 1
        ORDER BY r.year, r.race_date, res.driver_id
    """).df()
    stage = con.sql("""
        SELECT r.year, sr.race_id, sr.driver_id, sum(sr.stage_points) AS total_stage_points
        FROM silver.races r
        JOIN silver.stage_results sr USING (series_id, race_id)
        WHERE r.series_id = 1 AND r.race_type_id = 1
        GROUP BY r.year, sr.race_id, sr.driver_id
    """).df()
    con.close()
    return df, stage


def verify_regular_season_length():
    """Confirm the 26/10 split against playoff_round instead of assuming it (2020-2025 only --
    playoff_round is a schema floor before that, DATA_DICTIONARY 9g)."""
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)
    chk = con.sql("""
        SELECT year, count(*) n_races,
               sum(case when playoff_round is not null and playoff_round > 0 then 1 else 0 end) n_playoff
        FROM silver.races
        WHERE series_id = 1 AND race_type_id = 1 AND year BETWEEN 2020 AND 2025
        GROUP BY year ORDER BY 1
    """).df()
    con.close()
    notes = []
    for _, row in chk.iterrows():
        implied_regular = row['n_races'] - row['n_playoff']
        ok = implied_regular == REGULAR_SEASON_LEN or row['year'] == 2025  # 2025: 9 marked + 1 known gap = 10
        notes.append((int(row['year']), int(row['n_races']), int(row['n_playoff']), ok))
    return notes


def build_frame(df):
    df = df.sort_values(['year', 'race_date', 'driver_id']).copy()
    # season_race_num: dense rank of this race's date within its season (shared across drivers).
    race_order = (df[['year', 'race_id', 'race_date']].drop_duplicates()
                  .sort_values(['year', 'race_date']))
    race_order['season_race_num'] = race_order.groupby('year').cumcount() + 1
    df = df.merge(race_order[['year', 'race_id', 'season_race_num']], on=['year', 'race_id'], how='left')

    df = df.sort_values(['year', 'driver_id', 'season_race_num'])
    df['points_position_prior'] = df.groupby(['year', 'driver_id'])['points_position'].shift(1)
    df['cutline_distance'] = (df['points_position_prior'] - CUTLINE).abs()

    df['crash_class'] = df['status'].isin(['accident', 'dvp'])
    df['dnf'] = df['status'].fillna('') != 'running'

    df['regular_season'] = df['season_race_num'] <= REGULAR_SEASON_LEN
    df['late5'] = df['season_race_num'].between(*LATE_WINDOW_5)
    df['late3'] = df['season_race_num'].between(*LATE_WINDOW_3)
    return df


def question_a(df):
    """Crash-class DNF rate vs cutline proximity, late regular season, 2017-2025."""
    hist = df[(df['year'] <= 2025) & df['regular_season'] & df['cutline_distance'].notna()].copy()

    def dist_bucket(d):
        if d <= 2: return '0-2 (razor-edge)'
        if d <= 5: return '3-5 (bubble)'
        if d <= 10: return '6-10 (moderate)'
        return '11+ (comfortable)'
    hist['bucket'] = hist['cutline_distance'].apply(dist_bucket)

    def rank_bucket(rank):
        if rank <= 10: return '1-10 (safe)'
        if rank <= 16: return '11-16 (protecting)'
        if rank <= 21: return '17-21 (chasing)'
        return '22+ (backmarker, no realistic transfer hope)'
    hist['rank_bucket'] = hist['points_position_prior'].apply(rank_bucket)
    RANK_ORDER = ['1-10 (safe)', '11-16 (protecting)', '17-21 (chasing)',
                  '22+ (backmarker, no realistic transfer hope)']

    out = {}
    for label, window_col in [('last5', 'late5'), ('last3', 'late3'), ('rest_of_season', None)]:
        sub = hist[~hist['late5']] if window_col is None else hist[hist[window_col]]
        if len(sub) < 20:
            out[label] = {'n': len(sub)}
            continue
        r_crash, p_crash = pearsonr(sub['cutline_distance'], sub['crash_class'].astype(float))
        r_dnf, p_dnf = pearsonr(sub['cutline_distance'], sub['dnf'].astype(float))
        bt = (sub.groupby('bucket')
              .agg(n=('crash_class', 'size'), crash_rate=('crash_class', 'mean'), dnf_rate=('dnf', 'mean'))
              .reindex(['0-2 (razor-edge)', '3-5 (bubble)', '6-10 (moderate)', '11+ (comfortable)']))
        rt = (sub.groupby('rank_bucket')
              .agg(n=('crash_class', 'size'), crash_rate=('crash_class', 'mean'), dnf_rate=('dnf', 'mean'))
              .reindex(RANK_ORDER))
        out[label] = {
            'n': len(sub), 'r_distance_vs_crash': r_crash, 'p_crash': p_crash,
            'r_distance_vs_dnf': r_dnf, 'p_dnf': p_dnf, 'bucket_table': bt, 'rank_table': rt,
        }
    return out


def question_b(df, stage):
    """Bubble drivers' stage-point spike vs their own season baseline, 2020-2025 (stage_results floor)."""
    d = df[(df['year'] >= 2020) & (df['year'] <= 2025) & df['regular_season']].copy()
    d = d.merge(stage, on=['year', 'race_id', 'driver_id'], how='left')
    d['total_stage_points'] = d['total_stage_points'].fillna(0.0)

    baseline = (d[d['season_race_num'] <= (REGULAR_SEASON_LEN - 5)]
                .groupby(['year', 'driver_id'])['total_stage_points'].mean()
                .rename('season_baseline').reset_index())
    d = d.merge(baseline, on=['year', 'driver_id'], how='left')
    d['spike'] = d['total_stage_points'] - d['season_baseline']

    late = d[d['late5'] & d['season_baseline'].notna() & d['cutline_distance'].notna()]
    bubble = late[late['cutline_distance'] <= BUBBLE_MAX_DIST]
    locked_in = late[late['points_position_prior'] <= LOCKED_IN_MAX_RANK]

    def summarize(sub):
        if len(sub) < 5:
            return {'n': len(sub)}
        t_stat, t_p = ttest_1samp(sub['spike'], 0.0)
        return {'n': len(sub), 'mean_spike': sub['spike'].mean(), 'median_spike': sub['spike'].median(),
                'mean_baseline': sub['season_baseline'].mean(), 'mean_actual': sub['total_stage_points'].mean(),
                't_spike_vs_0': t_stat, 'p_spike_vs_0': t_p}

    out = {'bubble': summarize(bubble), 'locked_in': summarize(locked_in),
           'all_late_window': summarize(late)}
    if len(bubble) >= 5 and len(locked_in) >= 5:
        u_stat, u_p = mannwhitneyu(bubble['spike'], locked_in['spike'])
        out['bubble_vs_locked_in'] = {'u_stat': u_stat, 'p': u_p}
    return out


def question_c(df):
    """Locked-in cohort's expected-vs-actual finish correlation (rho), early season vs late window.

    Proxy for "expected finish" (Tier A, self-contained -- deliberately NOT the frozen PL model's
    walk-forward rho: that model's pace features have a lap-times data floor of 2020
    [DATA_DICTIONARY 8e] and gold scopes the model to year>=2022 [D1 amendment], so it cannot
    produce a walk-forward-safe rho back to 2017 without extending gated model machinery across
    years it was never proven on -- out of scope for a Tier A analytics session). The proxy used
    here is each driver's own season-to-date mean finishing position (races strictly before the
    current one, same season) -- the same "recent history predicts today's finish" concept the
    frozen model's `fin`/`typed` features encode, built only from silver.results (2017+, no
    pace/lap dependency).
    """
    d = df[(df['year'] <= 2025) & df['regular_season']].copy()
    d = d.sort_values(['year', 'driver_id', 'season_race_num'])
    d['expected_finish'] = (d.groupby(['year', 'driver_id'])['finishing_position']
                             .transform(lambda s: s.shift(1).expanding().mean()))

    locked_in = d[d['points_position_prior'] <= LOCKED_IN_MAX_RANK].copy()

    def per_race_rho(sub):
        rows = []
        for (year, rid), g in sub.groupby(['year', 'race_id']):
            g = g.dropna(subset=['expected_finish'])
            if len(g) < 5:
                continue
            rho, _ = spearmanr(g['expected_finish'], g['finishing_position'])
            if not np.isnan(rho):
                rows.append({'year': year, 'race_id': rid, 'rho': rho, 'n': len(g)})
        return pd.DataFrame(rows)

    early_rho = per_race_rho(locked_in[~locked_in['late5']])
    late_rho = per_race_rho(locked_in[locked_in['late5']])

    season_early = early_rho.groupby('year')['rho'].mean()
    season_late = late_rho.groupby('year')['rho'].mean()
    paired = pd.concat([season_early.rename('early'), season_late.rename('late')], axis=1).dropna()

    wstat, wp = (None, None)
    if len(paired) >= 5:
        wstat, wp = wilcoxon(paired['early'], paired['late'])

    return {
        'early_mean_rho': early_rho['rho'].mean(), 'early_n_races': len(early_rho),
        'late_mean_rho': late_rho['rho'].mean(), 'late_n_races': len(late_rho),
        'paired_by_season': paired, 'wilcoxon_stat': wstat, 'wilcoxon_p': wp,
    }


def live_2026(df, stage):
    d = df[df['year'] == 2026].copy()
    last_race = d.loc[d['season_race_num'].idxmax(), 'race_id']
    n_completed = d['season_race_num'].max()
    board = (d[d['race_id'] == last_race][['driver_id', 'points_position']]
             .assign(cutline_distance=lambda x: (x['points_position'] - CUTLINE).abs())
             .sort_values('points_position').head(21))
    return {'n_completed_races': int(n_completed), 'races_to_cutoff': REGULAR_SEASON_LEN - int(n_completed),
            'last_race_id': int(last_race), 'standings_board': board}


def main():
    df_raw, stage_raw = load_base()
    rs_check = verify_regular_season_length()
    df = build_frame(df_raw)

    qa = question_a(df)
    qb = question_b(df, stage_raw)
    qc = question_c(df)
    live = live_2026(df, stage_raw)

    print("[F19] regular-season-length verification (year, n_races, n_playoff, 26-implied-ok):")
    for row in rs_check:
        print("   ", row)

    print("\n[F19] Q(a) crash-class DNF rate vs cutline distance:")
    for k, v in qa.items():
        print(f"  window={k}: n={v.get('n')}")
        if 'r_distance_vs_crash' in v:
            print(f"    r(distance, crash)={v['r_distance_vs_crash']:.4f} p={v['p_crash']:.4f}")
            print(f"    r(distance, dnf)  ={v['r_distance_vs_dnf']:.4f} p={v['p_dnf']:.4f}")
            print("    -- by |distance| bucket (conflates front-runners & backmarkers) --")
            print(v['bucket_table'].to_string())
            print("    -- by rank (disaggregated: safe / protecting / chasing / backmarker) --")
            print(v['rank_table'].to_string())

    print("\n[F19] Q(b) stage-point spike, bubble vs locked-in, late window 2020-2025:")
    for k, v in qb.items():
        print(f"  {k}: {v}")

    print("\n[F19] Q(c) locked-in cohort rho (proxy expected-finish vs actual), early vs late:")
    print(f"  early: mean_rho={qc['early_mean_rho']:.4f} over {qc['early_n_races']} races")
    print(f"  late : mean_rho={qc['late_mean_rho']:.4f} over {qc['late_n_races']} races")
    print(f"  paired by season:\n{qc['paired_by_season'].to_string()}")
    print(f"  wilcoxon: stat={qc['wilcoxon_stat']}, p={qc['wilcoxon_p']}")

    print("\n[F19] live 2026 tracking:")
    print(f"  completed races: {live['n_completed_races']} / {REGULAR_SEASON_LEN} "
          f"({live['races_to_cutoff']} to the cutoff)")
    print(live['standings_board'].to_string())

    return {'rs_check': rs_check, 'qa': qa, 'qb': qb, 'qc': qc, 'live': live}


if __name__ == '__main__':
    main()
