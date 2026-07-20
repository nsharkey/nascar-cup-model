#!/usr/bin/env python3
"""Gate A -- benchmark liveness (specs/tether_gates.md, FROZEN; the memo's "gate 11").

Claim encoded: the market benchmark is still alive and being fed -- capture is not
silently lapsing under the DEMOTE. Reuses market_benchmark.py's own functions
(load_all_predictions, load_snapshot, find_primary_book, graded_picks_for_race,
reconstruct_and_decide) verbatim; it never recomputes admissibility by a different
rule.

Definitions (pinned):
  - P_scored_nonSS = committed prediction JSONs that are non-SS and scored (a
    _wf_scored.json snapshot exists).
  - K_adm = races among those contributing >= 1 admissible graded pick to the
    benchmark -- exactly market_benchmark's K.
  - capture_debt = P_scored_nonSS - K_adm.
  - A race whose green-flag time cannot be resolved offline (network/parse failure)
    is EXCLUDED from both counts and flagged "capture-state unknown" -- never
    counted as debt, so an offline run degrades to advisory, never a spurious red.
  - predictions_active = >= 1 committed prediction has a race_date within
    LIVE_WINDOW_DAYS=45 of the run date.

RED iff predictions_active AND capture_debt > TOL_DEBT=2. Otherwise GREEN. This is a
STATE-DEPENDENT liveness gate (unlike gates B/C, which are hermetic) -- it may
legitimately red when capture is genuinely behind; that is its job. It never reads
or reacts to any calibration number, and it enforces capture, not book-binding (the
first admissible capture binds the primary book automatically, per L5).

Touches the network (via score_race._green_flag_utc, same as market_benchmark.py)
and git history (via market_benchmark.find_primary_book /
score_race._git_first_commit_utc_for_entry) -- not hermetic. Run from src/ on the
conda interpreter (matches every other medallion gate, GATES.md).
"""
import os
import sys
from datetime import datetime, timezone

import market_benchmark as mb

REPO_ROOT = mb.REPO_ROOT
LIVE_WINDOW_DAYS = 45
TOL_DEBT = 2


def _race_date(pred):
    return datetime.strptime(pred['race_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)


def predictions_active(preds, now):
    for _path, pred in preds:
        if abs((now - _race_date(pred)).days) <= LIVE_WINDOW_DAYS:
            return True
    return False


def compute_liveness_state(preds, primary_book, now):
    """Returns a dict: P_scored_nonSS, unresolved (list of (race_id, date, reason)),
    picks_by_race (market_benchmark-shaped, for reconstruct_and_decide), state."""
    p_scored_nonss = 0
    unresolved = []
    picks_by_race = []

    for pred_path, pred in preds:
        year = int(str(pred['race_date'])[:4])
        race_id = pred['race_id']
        classified = mb.load_snapshot(year, race_id)
        if classified is None:
            continue                                 # not yet scored -- not part of this gate
        if pred.get('track_type') == 'SS':
            continue                                 # doctrine stand-down -- never counted

        try:
            green_flag_utc = mb.sr._green_flag_utc(year, race_id)
        except (OSError, ValueError) as e:
            unresolved.append((race_id, pred['race_date'], f'{type(e).__name__}: {e}'))
            continue
        if green_flag_utc is None:
            unresolved.append((race_id, pred['race_date'], 'no Race event in race_list index'))
            continue

        p_scored_nonss += 1
        picks, _counts = mb.graded_picks_for_race(pred_path, pred, classified, primary_book,
                                                    green_flag_utc)
        if picks:
            picks_by_race.append((pred['race_date'], race_id, picks))

    picks_by_race.sort(key=lambda x: (x[0], x[1]))
    result = mb.reconstruct_and_decide(picks_by_race)
    return dict(p_scored_nonss=p_scored_nonss, unresolved=unresolved,
                picks_by_race=picks_by_race, result=result)


def main():
    print('=' * 78)
    print('gate_benchmark_liveness -- specs/tether_gates.md Gate A (FROZEN)')
    print('  STATE-DEPENDENT: may legitimately red on real capture debt (that is its job).')
    print('=' * 78)

    now = datetime.now(timezone.utc)
    preds = mb.load_all_predictions()
    primary_book, primary_commit, primary_ts = mb.find_primary_book()
    print(f'[gate_benchmark_liveness] {len(preds)} sealed prediction(s) hash-verified')
    if primary_book is None:
        print('[gate_benchmark_liveness] no primary book bound yet (N=0 admissible picks '
              'possible) -- capture enforcement still applies to P_scored_nonSS.')
    else:
        print(f'[gate_benchmark_liveness] primary book: {primary_book!r} '
              f'(bound at commit {primary_commit[:10]}, {primary_ts})')

    st = compute_liveness_state(preds, primary_book, now)
    result = st['result']
    state = result['state']
    K_adm = state['K'] if state else 0
    N = state['N'] if state else 0
    capture_debt = st['p_scored_nonss'] - K_adm

    print('-' * 78)
    print(f"P_scored_nonSS={st['p_scored_nonss']}  K_adm={K_adm}  N={N}  "
          f'capture_debt={capture_debt}')

    if st['unresolved']:
        print(f"[gate_benchmark_liveness] {len(st['unresolved'])} race(s) capture-state "
              f'UNKNOWN (excluded from both counts, never counted as debt):')
        for race_id, date, reason in st['unresolved']:
            print(f'  - race_id={race_id} ({date}): {reason}')

    kind = result['kind']
    if kind == 'none':
        verdict_line = 'no data (0 admissible graded picks)'
    elif kind == 'interim':
        verdict_line = (f"{result['verdict']} (interim look, first crossing at "
                        f"race_id={result['race_id']} {result['date']})")
    elif kind == 'interim-only':
        verdict_line = f"no crossing yet (interim); final-look trigger not yet reached (N={N})"
    else:
        verdict_line = f"{result['verdict']} (FINAL LOOK, trigger: {result['trigger']}; {result['why']})"
    print(f'standing market-benchmark verdict: {verdict_line}')

    if st['picks_by_race']:
        last_date, last_race_id, _picks = st['picks_by_race'][-1]
        last_admissible = f'{last_date} (race_id={last_race_id})'
    else:
        last_admissible = 'none -- N=0'
    print(f'last admissible priced race: {last_admissible}')

    active = predictions_active(preds, now)
    print(f'predictions_active={active} (>=1 committed prediction within '
          f'LIVE_WINDOW_DAYS={LIVE_WINDOW_DAYS} of run date {now.date().isoformat()})')

    print('-' * 78)
    red = active and capture_debt > TOL_DEBT
    if red:
        print(f'RED -- capture is behind by {capture_debt} non-SS races -- record ALL '
              f'primary-book matchups and commit + push before the scheduled green flag for '
              f'the missing race(s) (scoring section 5.1 + market-spec full-board duty), or '
              f'record in that race\'s scores row why capture was impossible.')
        print('=' * 78)
        sys.exit(1)

    print(f'GREEN -- capture_debt={capture_debt} <= TOL_DEBT={TOL_DEBT} '
          f'(or predictions_active=False).')
    print('=' * 78)
    sys.exit(0)


if __name__ == '__main__':
    main()
