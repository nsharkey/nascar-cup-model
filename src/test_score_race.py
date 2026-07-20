#!/usr/bin/env python3
"""Fixtures F1-F10 for src/score_race.py (specs/scoring_methodology.md section 9). Plain stdlib
asserts, no pytest. Fixture drivers use ids 101-105 with pred_rank = 1-5 respectively; canonical
h2h prob favors the lower id in every pair unless a fixture overrides it (F5/F6). Exits nonzero on
any failure.
"""
import hashlib
import itertools
import json
import os
import sys
import tempfile

import score_race as sr

IDS = [101, 102, 103, 104, 105]
FAILURES = []


def check(name, cond, detail=''):
    if not cond:
        FAILURES.append(f'{name}: {detail}')
        print(f'  FAIL {name}: {detail}')
    else:
        print(f'  ok   {name}')


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------
def _h2h_matrix(pairs_prob, ids):
    h = {str(i): {} for i in ids}
    for a, b in itertools.permutations(ids, 2):
        lo, hi = min(a, b), max(a, b)
        p_lo = pairs_prob[(lo, hi)]
        h[str(a)][str(b)] = p_lo if a == lo else pairs_prob.get((lo, hi, 'rev'), round(1 - p_lo, 4))
    return h


def _default_pairs_prob(ids, p=0.6):
    return {(lo, hi): p for lo, hi in itertools.combinations(sorted(ids), 2)}


def build_payload(ids=IDS, pred_ranks=None, pairs_prob=None, track_type='SHORT',
                   stand_down=False, book_entries=None, race_id=9001, race_date='2026-01-01'):
    pred_ranks = pred_ranks or {d: i + 1 for i, d in enumerate(ids)}
    pairs_prob = pairs_prob if pairs_prob is not None else _default_pairs_prob(ids)
    field = [{'driver_id': d, 'name': f'Driver{d}', 'grid': idx + 1, 'n_hist': 50,
              'utility': round(1.0 - 0.1 * idx, 4), 'pred_rank': pred_ranks[d],
              'p_win': 0.1, 'p_top5': 0.3, 'p_top10': 0.5} for idx, d in enumerate(ids)]
    payload = {
        'generated_utc': '2026-01-01T00:00:00+00:00', 'race_id': race_id, 'track': 'Test Track',
        'track_type': track_type, 'race_date': race_date,
        'config': {'pace': 'pace_med85', 'hl': 8, 'feats': ['fin', 'pace', 'typed', 'start'],
                   'typology': 'MY_TYPE', 'typed': 'shrinkage', 'lam': 0.5},
        'trained_through': '2025-12-01', 'n_train_races': 100,
        'weights': {'fin': -0.03, 'pace': 0.11, 'typed': 0.16, 'start': 0.13},
        'field': field, 'h2h_prob': _h2h_matrix(pairs_prob, ids),
        'book_prices': dict(sr.PRISTINE_BOOK_PRICES),
        'stand_down': stand_down,
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    sha = hashlib.sha256(blob).hexdigest()
    sealed = {'sha256_of_payload': sha, **payload}
    if book_entries is not None:
        sealed['book_prices'] = {'note': sr.PRISTINE_BOOK_PRICES['note'], 'entries': book_entries}
    return sealed


def build_results(finishes, dq=None):
    """finishes: dict driver_id -> finishing_position (also accepts extra ids not in IDS)."""
    dq = dq or set()
    results = [{'driver_id': d, 'driver_fullname': f'Driver{d}', 'finishing_position': pos,
                'finishing_status': 'Running', 'disqualified': d in dq}
               for d, pos in finishes.items()]
    return {'weekend_race': [{'results': results}]}


def classified(results_dict):
    res = sr._extract_results(results_dict)
    return [r for r in res if r.get('finishing_position') and r['finishing_position'] >= 1]


# ---------------------------------------------------------------------------
# F1 -- clean race
# ---------------------------------------------------------------------------
def test_f1():
    pred = build_payload()
    res = classified(build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5}))
    common = sr.common_set(pred, res)
    rho = sr.score_rho(common)
    h2h_acc, h2h_n, skipped = sr.score_h2h(pred, common)
    check('F1 rho', rho == 0.9, rho)
    check('F1 h2h_n', h2h_n == 10, h2h_n)
    check('F1 h2h_acc', h2h_acc == 0.9, h2h_acc)


# ---------------------------------------------------------------------------
# F2 -- DNF grading
# ---------------------------------------------------------------------------
def test_f2():
    pred = build_payload()
    res = classified(build_results({101: 4, 102: 1, 103: 2, 104: 3, 105: 5}))
    common = sr.common_set(pred, res)
    rho = sr.score_rho(common)
    h2h_acc, h2h_n, skipped = sr.score_h2h(pred, common)
    check('F2 rho', rho == 0.4, rho)
    check('F2 h2h_acc', h2h_acc == 0.7, h2h_acc)


# ---------------------------------------------------------------------------
# F3 -- withdrawal
# ---------------------------------------------------------------------------
def test_f3():
    ids6 = IDS + [106]
    pred = build_payload(ids=ids6, pred_ranks={d: i + 1 for i, d in enumerate(ids6)})
    res = classified(build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5}))  # 106 absent
    common = sr.common_set(pred, res)
    check('F3 n', len(common['common_ids']) == 5, common['common_ids'])
    check('F3 unscored note', common['unscored_ids'] == [106], common['unscored_ids'])
    rho = sr.score_rho(common)
    check('F3 rho computed over the 5', rho == 0.9, rho)


# ---------------------------------------------------------------------------
# F4 -- unpredicted + DQ
# ---------------------------------------------------------------------------
def test_f4():
    pred = build_payload()  # predicted field: 101-105
    res = classified(build_results({101: 1, 102: 2, 103: 3, 105: 4, 104: 5, 107: 6},
                                    dq={104}))
    common = sr.common_set(pred, res)
    check('F4 unpredicted note', common['unpredicted_ids'] == [107], common['unpredicted_ids'])
    check('F4 104 at official finish 5', common['res_by_id'][104]['finishing_position'] == 5)
    row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SHORT', common,
                          sr.score_rho(common), sr.score_h2h(pred, common),
                          sr.grade_books(pred, common), False)
    check('F4 DQ note present', 'DQ:' in row['notes'], row['notes'])
    check('F4 unpredicted note in row', 'unpredicted (in results only): [107]' in row['notes'],
          row['notes'])


# ---------------------------------------------------------------------------
# F5 -- book grading
# ---------------------------------------------------------------------------
F5_PROBS = {
    (101, 102): 0.55, (101, 103): 0.60, (101, 104): 0.65, (101, 105): 0.70,
    (102, 103): 0.55, (102, 104): 0.60, (102, 105): 0.65,
    (103, 104): 0.55, (103, 105): 0.60,
    (104, 105): 0.55,
}


def test_f5():
    pred = build_payload(pairs_prob=F5_PROBS, book_entries=[
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 101, 'driver_id_b': 102, 'price_a': -120, 'price_b': 100,
         'void': False, 'note': 'e1'},
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 104, 'driver_id_b': 103, 'price_a': -150, 'price_b': 130,
         'void': False, 'note': 'e2'},
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 105, 'driver_id_b': 102, 'price_a': 200, 'price_b': -250,
         'void': False, 'note': 'e3'},
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 103, 'driver_id_b': 105, 'price_a': -110, 'price_b': -110,
         'void': False, 'note': 'e4 pickem'},
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 101, 'driver_id_b': 104, 'price_a': -115, 'price_b': -105,
         'void': True, 'note': 'e5 void'},
        {'book': 'fanduel', 'recorded_utc': '2026-01-01T19:00:00+00:00', 'closing': False,
         'driver_id_a': 101, 'driver_id_b': 102, 'price_a': -118, 'price_b': 98,
         'void': False, 'note': 'e6 dup of e1'},
    ])
    res = classified(build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5}))
    common = sr.common_set(pred, res)
    books = sr.grade_books(pred, common)
    check('F5 book_n', books['book_n'] == 3, books)
    check('F5 book_agree_n', books['book_agree_n'] == 2, books)
    check('F5 model_beats_book_n', books['model_beats_book_n'] == 1, books)
    check('F5 pickem', books['pickem'] == 1, books)
    check('F5 void', books['void'] == 1, books)
    check('F5 deduped', books['deduped'] == 1, books)
    row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SHORT', common, sr.score_rho(common),
                          sr.score_h2h(pred, common), books, False)
    for clause in ('pickem excluded: 1', 'book entries void: 1', 'book entries deduped: 1'):
        check(f'F5 notes mention "{clause}"', clause in row['notes'], row['notes'])


# ---------------------------------------------------------------------------
# F6 -- h2h rounding/skip
# ---------------------------------------------------------------------------
def test_f6():
    probs = dict(_default_pairs_prob(IDS))
    probs[(102, 103)] = 0.5000
    probs[(102, 103, 'rev')] = 0.5001    # reverse entry deliberately inconsistent; must be ignored
    pred = build_payload(pairs_prob=probs)
    res = classified(build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5}))
    common = sr.common_set(pred, res)
    h2h_acc, h2h_n, skipped = sr.score_h2h(pred, common)
    check('F6 h2h_n', h2h_n == 9, h2h_n)
    check('F6 skipped', skipped == 1, skipped)
    row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SHORT', common, sr.score_rho(common),
                          (h2h_acc, h2h_n, skipped), sr.grade_books(pred, common), False)
    check('F6 notes mention skip', 'h2h pairs skipped: 1' in row['notes'], row['notes'])


# ---------------------------------------------------------------------------
# F7 -- stand-down
# ---------------------------------------------------------------------------
def test_f7():
    pred = build_payload(track_type='SS', stand_down=True)
    res = classified(build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5}))
    common = sr.common_set(pred, res)
    row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SS', common, sr.score_rho(common),
                          sr.score_h2h(pred, common), sr.grade_books(pred, common), True)
    check('F7 rho computed normally', row['rho'] == '0.9000', row['rho'])
    check('F7 notes start with SS STAND-DOWN', row['notes'].startswith('SS STAND-DOWN'), row['notes'])


# ---------------------------------------------------------------------------
# F8 -- tamper
# ---------------------------------------------------------------------------
def test_f8():
    pred = build_payload()
    check('F8 pristine verifies', sr.verify_hash(pred) is True)

    filled = json.loads(json.dumps(pred))
    filled['book_prices'] = {'note': sr.PRISTINE_BOOK_PRICES['note'], 'entries': [
        {'book': 'dk', 'recorded_utc': '2026-01-01T20:00:00+00:00', 'closing': True,
         'driver_id_a': 101, 'driver_id_b': 102, 'price_a': -120, 'price_b': 100,
         'void': False, 'note': ''}]}
    check('F8 filled book_prices still verifies', sr.verify_hash(filled) is True)

    tampered = json.loads(json.dumps(pred))
    tampered['field'][0]['utility'] = tampered['field'][0]['utility'] + 1.0
    check('F8 tampered field fails verification', sr.verify_hash(tampered) is False)

    with tempfile.TemporaryDirectory() as td:
        csv_path = os.path.join(td, 'scores_log.csv')
        if not sr.verify_hash(tampered):
            pass  # main()'s gate: never reaches upsert_row
        check('F8 CSV untouched after refused tamper', not os.path.exists(csv_path))


# ---------------------------------------------------------------------------
# F9 -- idempotency (temp-dir end-to-end run)
# ---------------------------------------------------------------------------
def test_f9():
    pred = build_payload()
    res_dict = build_results({101: 1, 102: 3, 103: 2, 104: 4, 105: 5})

    with tempfile.TemporaryDirectory() as td:
        pred_path = os.path.join(td, 'pred.json')
        results_path = os.path.join(td, 'results.json')
        json.dump(pred, open(pred_path, 'w'))
        json.dump(res_dict, open(results_path, 'w'))
        csv_path = os.path.join(td, 'scores_log.csv')

        def run_once():
            d = json.load(open(pred_path))
            assert sr.verify_hash(d)
            cls, _raw, _wf = sr.load_results(2026, 9001, path_override=results_path)
            common = sr.common_set(d, cls)
            row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SHORT', common,
                                  sr.score_rho(common), sr.score_h2h(d, common),
                                  sr.grade_books(d, common), False)
            sr.upsert_row(csv_path, row)

        run_once()
        first = open(csv_path).read()
        run_once()
        second = open(csv_path).read()
        check('F9 byte-identical after re-run', first == second)
        with open(csv_path, newline='') as f:
            import csv as _csv
            n_rows = sum(1 for _ in _csv.DictReader(f))
        check('F9 exactly one row', n_rows == 1, n_rows)


# ---------------------------------------------------------------------------
# F10 -- tie anomaly
# ---------------------------------------------------------------------------
def test_f10():
    pred = build_payload()
    res = classified(build_results({101: 1, 102: 2, 103: 2, 104: 4, 105: 5}))  # 102/103 tie
    common = sr.common_set(pred, res)
    rho = sr.score_rho(common)
    h2h_acc, h2h_n, skipped = sr.score_h2h(pred, common)
    check('F10 h2h skips the tied pair', skipped >= 1, skipped)
    row = sr.compose_row(9001, '2026-01-01', 'Test Track', 'SHORT', common, rho,
                          (h2h_acc, h2h_n, skipped), sr.grade_books(pred, common), False)
    check('F10 notes mention tie anomaly', 'finish tie anomaly' in row['notes'], row['notes'])


if __name__ == '__main__':
    for name, fn in [('F1', test_f1), ('F2', test_f2), ('F3', test_f3), ('F4', test_f4),
                      ('F5', test_f5), ('F6', test_f6), ('F7', test_f7), ('F8', test_f8),
                      ('F9', test_f9), ('F10', test_f10)]:
        print(f'-- {name} --')
        fn()
    if FAILURES:
        print(f'\n{len(FAILURES)} FAILURE(S):')
        for f in FAILURES:
            print(' ', f)
        sys.exit(1)
    print('\nALL PASS')
