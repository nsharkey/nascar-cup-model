#!/usr/bin/env python3
"""Market-benchmark decision rule (specs/market_benchmark_decision_rule.md, FROZEN, including its
2026-07-18 calibration/admissibility/book-binding amendments), implemented verbatim.

specs/medallion_architecture.md section 5.5 pins the inputs: the sealed prediction JSONs
(hash-verified per scoring spec 1.3) and the score_race.py snapshot files
(src/data/races/{year}_{race_id}_wf_scored.json) -- nothing else. A race counts for this script's
statistic exactly when its snapshot file exists (market spec's "section 6 inputs pinned"
amendment). Idempotent: recomputes every pick from scratch on every run. Fixed seed 20260718.

Imports only two things from score_race.py, per the market spec's own resolved-ambiguity register:
the entry schema (scoring 5.1) and the malformed->dedup->void pipeline (scoring 5.2 + its
pipeline-order amendment). Scoring 5.3's strict-book-favorite filter does NOT apply here -- a
pick'em-priced entry is still a graded pick (the model bets its own side regardless of whether the
book itself had a favorite), so this spec's N is not sum(book_n) by design.

Run from anywhere; repo root resolves via __file__ (matching score_race.py / the other medallion
modules). No CLI flags -- always recomputes the full look sequence from scratch.
"""
import glob
import json
import os
import subprocess
from datetime import datetime, timezone

import numpy as np
from scipy import stats

import score_race as sr

REPO_ROOT = sr.REPO_ROOT
PREDICTIONS_DIR = sr.PREDICTIONS_DIR
RACES_CACHE_DIR = sr.RACES_CACHE_DIR

SEED = 20260718
B = 10000
K_FLOOR = 20                       # amendment: race-count floor -- no boundary fires below this
BREAKEVEN_REF = 0.5300             # scoring spec 5.4, imported as secondary-stat context only
FINAL_LOOK_N = 400
FINAL_LOOK_CALENDAR_BACKSTOP = datetime(2028, 2, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def load_all_predictions():
    """All sealed prediction JSONs, hash-verified. Loudly reports (does not raise on) any file
    that fails verification -- it is simply excluded, per section 6: 'skip and loudly report'."""
    paths = sorted(glob.glob(os.path.join(PREDICTIONS_DIR, 'race_*_prediction.json')))
    preds = []
    for p in paths:
        d = json.load(open(p))
        if not sr.verify_hash(d):
            print(f'[market_benchmark] SKIPPING {p}: hash verification FAILED')
            continue
        preds.append((p, d))
    return preds


def load_snapshot(year, race_id):
    """A race counts for this script exactly when its score_race.py snapshot exists. Never reads
    _wf.json or the network (section 6 inputs-pinned amendment)."""
    path = os.path.join(RACES_CACHE_DIR, f'{year}_{race_id}_wf_scored.json')
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    results = sr._extract_results(d)
    return [r for r in results if r.get('finishing_position') and r['finishing_position'] >= 1]


def find_primary_book():
    """Amendment (primary book binding): the primary book is named in the same commit as the
    first recorded price anywhere in predictions/, and is thereafter fixed. Walks commit history
    oldest-first across predictions/, returns (book, commit_hash, committer_iso) at the first
    non-empty book_prices.entries found in any prediction file."""
    log = subprocess.run(['git', 'log', '--format=%H %cI', '--reverse', '--', 'predictions/'],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=True)
    for line in log.stdout.splitlines():
        h, _, ts = line.partition(' ')
        names = subprocess.run(['git', 'show', '--name-only', '--format=', h, '--', 'predictions/'],
                                cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=True)
        for relpath in names.stdout.splitlines():
            if not relpath.endswith('_prediction.json'):
                continue
            show = subprocess.run(['git', 'show', f'{h}:{relpath}'], cwd=REPO_ROOT,
                                   capture_output=True, text=True, timeout=60)
            if show.returncode != 0:
                continue
            try:
                snap = json.loads(show.stdout)
            except json.JSONDecodeError:
                continue
            entries = (snap.get('book_prices') or {}).get('entries') or []
            if entries:
                return entries[0].get('book'), h, ts
    return None, None, None


# ---------------------------------------------------------------------------
# Section 1 -- graded picks per race
# ---------------------------------------------------------------------------
def graded_picks_for_race(pred_path, pred, classified_results, primary_book, green_flag_utc):
    counts = dict(seen=0, off_book=0, not_common=0, tie=0, no_model_pick=0, inadmissible=0, graded=0)
    if pred.get('track_type') == 'SS':          # doctrine stand-down: recorded, never a graded pick
        return [], counts

    common = sr.common_set(pred, classified_results)
    common_ids = set(common['common_ids'])
    res_by_id = common['res_by_id']
    survivors, _malformed, _deduped, _void = sr.malformed_dedup_void(pred['book_prices']['entries'])
    h2h_prob = pred['h2h_prob']
    rel_path = os.path.relpath(pred_path, REPO_ROOT)

    picks = []
    for e in survivors.values():
        counts['seen'] += 1
        if e.get('book') != primary_book:
            counts['off_book'] += 1
            continue
        a_id, b_id = int(e['driver_id_a']), int(e['driver_id_b'])
        if a_id not in common_ids or b_id not in common_ids:
            counts['not_common'] += 1
            continue
        lo, hi = min(a_id, b_id), max(a_id, b_id)
        f_lo, f_hi = res_by_id[lo]['finishing_position'], res_by_id[hi]['finishing_position']
        if f_lo == f_hi:
            counts['tie'] += 1
            continue
        p = h2h_prob.get(str(lo), {}).get(str(hi))
        if p is None or p == 0.5:
            counts['no_model_pick'] += 1
            continue
        model_pick, other = (lo, hi) if p > 0.5 else (hi, lo)

        commit_utc = None
        if green_flag_utc is not None:
            try:
                commit_utc = sr._git_first_commit_utc_for_entry(rel_path, e)
            except (subprocess.SubprocessError, OSError):
                commit_utc = None
        if commit_utc is None or commit_utc >= green_flag_utc:
            counts['inadmissible'] += 1
            continue

        price = int(e['price_a']) if model_pick == a_id else int(e['price_b'])
        won = res_by_id[model_pick]['finishing_position'] < res_by_id[other]['finishing_position']
        profit = (100.0 / abs(price) if price < 0 else price / 100.0) if won else -1.0
        counts['graded'] += 1
        picks.append({'race_id': pred['race_id'], 'date': pred['race_date'], 'model_pick': model_pick,
                      'other': other, 'price': price, 'won': won, 'profit': profit,
                      'config': pred['config']})
    return picks, counts


# ---------------------------------------------------------------------------
# Sections 3-4 -- pinned resampling mechanics, decision schedule
# ---------------------------------------------------------------------------
def compute_state(picks):
    races = sorted({(p['date'], p['race_id']) for p in picks})
    K = len(races)
    N = len(picks)
    idx_of = {r: i for i, r in enumerate(races)}
    race_totals = np.zeros(K)
    race_counts = np.zeros(K, dtype=np.int64)
    for p in picks:
        i = idx_of[(p['date'], p['race_id'])]
        race_totals[i] += p['profit']
        race_counts[i] += 1
    total_profit = float(race_totals.sum())
    roi = total_profit / N if N else float('nan')

    rng = np.random.default_rng(SEED)                       # fresh at every look (pinned mechanics)
    idx = rng.integers(0, K, size=(B, K))
    resample_totals = race_totals[idx].sum(axis=1)
    resample_counts = race_counts[idx].sum(axis=1)
    resample_mean = resample_totals / resample_counts
    p_boot = (1 + int(np.sum(resample_totals <= 0))) / (B + 1)          # add-one convention
    futility_bound = float(np.sort(resample_mean)[9500])                # 9,501st ascending order stat

    if K > 1 and np.std(race_totals, ddof=1) > 0:
        p_ttest = float(stats.ttest_1samp(race_totals, popmean=0.0, alternative='greater').pvalue)
    else:
        p_ttest = 1.0                                        # degenerate sd -> no rejection

    return dict(N=N, K=K, total_profit=total_profit, roi=roi, p_boot=p_boot,
                futility_bound=futility_bound, p_ttest=p_ttest)


def evaluate_look(state):
    """Interim look: K-floor gates BOTH arms (amendment item 2: 'interim efficacy, futility...
    may [not] fire at a look with K < 20')."""
    if state['K'] < K_FLOOR:
        return None
    N = state['N']
    if N >= 50 and state['p_boot'] <= 0.001 and state['p_ttest'] <= 0.001:   # dual interim boundary
        return 'EDGE'
    if N >= 100 and state['futility_bound'] < 0:
        return 'NO-EDGE'
    return None


def evaluate_final(state):
    """Final-look-precedence amendment. 'A final look with K < 20 returns UNDERPOWERED' is
    unconditional -- it overrides every arm, not just EDGE."""
    if state is None:
        return 'UNDERPOWERED', 'no graded picks'
    if state['K'] < K_FLOOR:
        return 'UNDERPOWERED', f"K={state['K']} < floor {K_FLOOR}"
    N = state['N']
    if state['p_boot'] <= 0.045:
        return 'EDGE', f"p={state['p_boot']:.4f} <= 0.045"
    if N >= 200:
        return 'NO-EDGE', f'N={N} >= 200'
    if N >= 100 and state['futility_bound'] < 0:
        return 'NO-EDGE', f"N={N}>=100 and futility bound {state['futility_bound']:.4f} < 0"
    return 'UNDERPOWERED', f'N={N}'


def final_look_triggered(N):
    """Calendar-backstop amendment: first of N>=400, last 2027 points race scored, or first run
    on/after 2028-02-15. The '2027 season complete' condition needs a full 2027 schedule this
    script does not have a source for yet (2026-07-19) -- conservatively treated as not-yet-met;
    a human should re-check this near end of 2027 rather than trust it silently."""
    if N >= FINAL_LOOK_N:
        return True, f'N>={FINAL_LOOK_N}'
    if datetime.now(timezone.utc) >= FINAL_LOOK_CALENDAR_BACKSTOP:
        return True, 'calendar backstop 2028-02-15 reached'
    return False, None


def reconstruct_and_decide(picks_by_race):
    """'Looks are states, not acts' amendment: replays the full look sequence in ascending
    (race_date, race_id) order; the standing verdict is the FIRST boundary crossing."""
    cumulative = []
    for date, race_id, picks in picks_by_race:
        cumulative = cumulative + picks
        state = compute_state(cumulative)
        v = evaluate_look(state)
        if v is not None:
            return dict(kind='interim', date=date, race_id=race_id, verdict=v, state=state)

    if not cumulative:
        return dict(kind='none', date=None, race_id=None, verdict=None, state=None)

    final_state = compute_state(cumulative)
    triggered, reason = final_look_triggered(final_state['N'])
    if not triggered:
        return dict(kind='interim-only', date=picks_by_race[-1][0], race_id=picks_by_race[-1][1],
                    verdict=None, state=final_state)
    verdict, why = evaluate_final(final_state)
    return dict(kind='final', date=picks_by_race[-1][0], race_id=picks_by_race[-1][1],
                verdict=verdict, state=final_state, why=why, trigger=reason)


# ---------------------------------------------------------------------------
# Secondary (descriptive only, never a gate) + by-config split
# ---------------------------------------------------------------------------
def secondary_stats(picks):
    if not picks:
        return None
    win_rate = sum(1 for p in picks if p['won']) / len(picks)
    pstars = [abs(p['price']) / (abs(p['price']) + 100) if p['price'] < 0
              else 100 / (p['price'] + 100) for p in picks]
    return dict(win_rate=win_rate, mean_pstar=float(np.mean(pstars)), fixed_ref=BREAKEVEN_REF)


def by_config_split(picks):
    groups = {}
    for p in picks:
        key = json.dumps(p['config'], sort_keys=True)
        groups.setdefault(key, []).append(p)
    out = {}
    for key, group in groups.items():
        n = len(group)
        profit = sum(p['profit'] for p in group)
        out[key] = dict(n=n, profit=profit, roi=profit / n)
    return out


# ---------------------------------------------------------------------------
def main():
    preds = load_all_predictions()
    primary_book, primary_commit, primary_ts = find_primary_book()

    print('=' * 78)
    print('[market_benchmark] market-benchmark decision rule')
    print('=' * 78)
    print(f'[market_benchmark] {len(preds)} sealed prediction(s) hash-verified')
    if primary_book is None:
        print('[market_benchmark] no book_prices entries recorded anywhere yet -- N=0.')
        print('=' * 78)
        return
    print(f'[market_benchmark] primary book: {primary_book!r} '
          f'(bound at commit {primary_commit[:10]}, {primary_ts})')

    picks_by_race = []
    agg_counts = dict(seen=0, off_book=0, not_common=0, tie=0, no_model_pick=0, inadmissible=0,
                       graded=0)
    unscored = 0
    for pred_path, pred in preds:
        year = int(str(pred['race_date'])[:4])
        race_id = pred['race_id']
        classified = load_snapshot(year, race_id)
        if classified is None:
            unscored += 1
            continue
        green = sr._green_flag_utc(year, race_id)
        picks, counts = graded_picks_for_race(pred_path, pred, classified, primary_book, green)
        for k in agg_counts:
            agg_counts[k] += counts[k]
        if picks:
            picks_by_race.append((pred['race_date'], race_id, picks))
    picks_by_race.sort(key=lambda x: (x[0], x[1]))

    print(f'[market_benchmark] {unscored} sealed prediction(s) not yet scored (no snapshot) -- excluded')
    print(f'[market_benchmark] book_prices entries seen at any book (deduped/non-void/well-formed): '
          f"{agg_counts['seen']}")
    print(f"  off primary book: {agg_counts['off_book']}   not both in common set: "
          f"{agg_counts['not_common']}   finish tie: {agg_counts['tie']}")
    print(f"  no model pick (p=0.5 or missing): {agg_counts['no_model_pick']}   "
          f"inadmissible (post-race commit / no green-flag time): {agg_counts['inadmissible']}")
    print(f"  GRADED PICKS: {agg_counts['graded']}")

    all_picks = [p for _, _, picks in picks_by_race for p in picks]
    result = reconstruct_and_decide(picks_by_race)
    state = result['state']

    print('-' * 78)
    if state is None:
        print('[market_benchmark] N=0 graded picks -- no look has occurred yet.')
    else:
        print(f"N={state['N']}  K={state['K']}  total_profit={state['total_profit']:+.4f} units  "
              f"ROI/pick={state['roi']:+.4f}")
        print(f"bootstrap p={state['p_boot']:.4f}  futility 95% upper bound={state['futility_bound']:+.4f}  "
              f"one-sided t-test p={state['p_ttest']:.4f}")
        sec = secondary_stats(all_picks)
        print(f"win_rate={sec['win_rate']:.4f}  mean_pstar={sec['mean_pstar']:.4f}  "
              f"fixed_ref={sec['fixed_ref']:.4f}  (descriptive only, never a gate)")
        cfgs = by_config_split(all_picks)
        if len(cfgs) > 1:
            print('by-config split (descriptive only):')
            for key, v in cfgs.items():
                print(f"  {key}: n={v['n']} profit={v['profit']:+.4f} roi={v['roi']:+.4f}")

    print('-' * 78)
    kind = result['kind']
    if kind == 'none':
        print('VERDICT: no data (0 admissible graded picks)')
    elif kind == 'interim':
        print(f"VERDICT: {result['verdict']}  (interim look, first crossing at race_id="
              f"{result['race_id']} {result['date']})")
    elif kind == 'interim-only':
        print(f"VERDICT: no crossing yet (interim); final-look trigger not yet reached "
              f"(N={state['N']} < {FINAL_LOOK_N}, calendar backstop not reached, "
              f"2027-season-complete unchecked -- see final_look_triggered() docstring)")
    else:
        print(f"VERDICT: {result['verdict']}  (FINAL LOOK, trigger: {result['trigger']}; "
              f"{result['why']})")
    print('=' * 78)


if __name__ == '__main__':
    main()
