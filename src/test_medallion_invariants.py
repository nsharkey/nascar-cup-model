#!/usr/bin/env python3
"""Medallion data-invariants gate. Encodes structural claims that are asserted
in prose across HANDOFF/spec/reports but were never mechanically enforced, so a
future bronze/silver rebuild that silently violated one would slip through.

Read-only against data/nascar.duckdb. Plain stdlib asserts (no pytest); exits
nonzero on any violation. Run from src/ under the Anaconda interpreter (needs
duckdb):  `python test_medallion_invariants.py`.

Invariants checked:

  (c) BRONZE terminal condition (spec section 2.9 / report/BRONZE_COVERAGE.md):
      no coverage row is in state 'failed'. `failed = 0` is the stable terminal
      condition -- the stored/absent counts drift every week as races are added,
      but a genuine download/parse failure must never be a terminal state.

  (d) SILVER one-winner invariant: every (series_id, race_id) has exactly one
      finisher in position 1. Verified on silver.driver_race (`finish`) and
      silver.results (`finishing_position`). A parse defect producing zero or
      two winners for a race is exactly the kind of silent corruption this
      catches (cf. the HANDOFF B4 2017-recovery spot-check).

  (bonus) SILVER no-duplicate-driver: a driver appears at most once per
      (series_id, race_id) in both silver.driver_race and silver.results.

The check functions are pure (connection + table + column in, violation rows
out), so the gate SELF-VALIDATES: it runs each checker against an in-memory
synthetic table with KNOWN violations and fails if a checker does not flag
them. That bakes red-on-drift verification into every run -- the gate proves it
can still detect corruption, not merely that today's data is clean.
"""
import os
import sys

import duckdb
import warehouse

DB_PATH = warehouse.DB_PATH


# ---------------------------------------------------------------------------
# pure checkers (reused for the real warehouse and the synthetic self-test)
# ---------------------------------------------------------------------------
def one_winner_violations(con, table, win_col):
    """(series_id, race_id, winners) for races whose count of win_col==1 != 1."""
    return con.execute(f'''
        SELECT series_id, race_id, count(*) FILTER (WHERE {win_col} = 1) AS winners
        FROM {table}
        GROUP BY series_id, race_id
        HAVING count(*) FILTER (WHERE {win_col} = 1) <> 1
        ORDER BY series_id, race_id
    ''').fetchall()


def duplicate_driver_violations(con, table):
    """(series_id, race_id, driver_id, n) for drivers appearing >1 time in a race."""
    return con.execute(f'''
        SELECT series_id, race_id, driver_id, count(*) AS n
        FROM {table}
        GROUP BY series_id, race_id, driver_id
        HAVING count(*) > 1
        ORDER BY series_id, race_id, driver_id
    ''').fetchall()


def bronze_failed_count(con):
    """Coverage rows in a terminal 'failed' state (spec 2.9 terminal condition)."""
    return con.execute(
        "SELECT count(*) FROM bronze.coverage WHERE state = 'failed'").fetchone()[0]


# ---------------------------------------------------------------------------
# self-test: prove the checkers still detect corruption (red-on-drift, baked in)
# ---------------------------------------------------------------------------
def selftest():
    """Return a list of self-test failure strings (empty == checkers work)."""
    fails = []
    con = duckdb.connect(':memory:')
    # synthetic silver.driver_race with deliberate violations:
    #   race 100: one winner (OK)
    #   race 101: two winners (BAD)
    #   race 102: zero winners (BAD)
    #   race 103: driver 17 appears twice (dup) + otherwise one winner
    con.execute('CREATE TABLE dr(series_id INT, race_id INT, driver_id INT, finish INT)')
    con.execute('''INSERT INTO dr VALUES
        (1,100,11,1),(1,100,12,2),
        (1,101,13,1),(1,101,14,1),
        (1,102,15,2),(1,102,16,3),
        (1,103,17,1),(1,103,17,2),(1,103,18,3)''')

    win_viol = {(s, r) for s, r, _ in one_winner_violations(con, 'dr', 'finish')}
    if win_viol != {(1, 101), (1, 102)}:
        fails.append(f'selftest one_winner: detected {sorted(win_viol)}, expected races 101 & 102')

    dup_viol = {(s, r, d) for s, r, d, _ in duplicate_driver_violations(con, 'dr')}
    if dup_viol != {(1, 103, 17)}:
        fails.append(f'selftest duplicate: detected {sorted(dup_viol)}, expected (1,103,17)')

    # synthetic bronze.coverage with one failed row
    con.execute("CREATE SCHEMA bronze")
    con.execute("CREATE TABLE bronze.coverage(state VARCHAR)")
    con.execute("INSERT INTO bronze.coverage VALUES ('stored'),('absent'),('failed')")
    if bronze_failed_count(con) != 1:
        fails.append(f'selftest bronze_failed: got {bronze_failed_count(con)}, expected 1')

    con.close()
    return fails


def main():
    print('== test_medallion_invariants ==')
    failures = []

    # --- self-test first: if the checkers cannot catch corruption, stop ------
    st = selftest()
    for f in st:
        print(f'  FAIL {f}')
    if st:
        print('\nFAIL -- checker self-test failed (red-on-drift property broken); '
              'aborting before trusting a green verdict.')
        sys.exit(1)
    print('  ok   self-test: checkers detect injected zero/two-winner, dup-driver, '
          'and failed-state corruption')

    if not os.path.exists(DB_PATH):
        print(f'\nFAIL -- warehouse not found at {DB_PATH} (build it: python warehouse.py)')
        sys.exit(1)
    con = duckdb.connect(DB_PATH, read_only=True)

    # --- (c) bronze failed = 0 ----------------------------------------------
    nf = bronze_failed_count(con)
    if nf == 0:
        print("  ok   (c) bronze.coverage has no state='failed' rows")
    else:
        failures.append(f"(c) bronze.coverage has {nf} state='failed' row(s)")
        print(f"  FAIL (c) bronze failed rows: {nf}")

    # --- (d) one winner per race, both silver tables ------------------------
    for table, col in [('silver.driver_race', 'finish'),
                       ('silver.results', 'finishing_position')]:
        v = one_winner_violations(con, table, col)
        if not v:
            n = con.execute(f'SELECT count(DISTINCT (series_id, race_id)) FROM {table}').fetchone()[0]
            print(f'  ok   (d) {table}: exactly one {col}==1 across all {n} races')
        else:
            failures.append(f'(d) {table}: {len(v)} race(s) without exactly one winner: {v[:5]}')
            print(f'  FAIL (d) {table}: {len(v)} bad race(s): {v[:5]}')

    # --- (bonus) no duplicate driver per race -------------------------------
    for table in ['silver.driver_race', 'silver.results']:
        v = duplicate_driver_violations(con, table)
        if not v:
            print(f'  ok   (bonus) {table}: no driver appears twice in a race')
        else:
            failures.append(f'(bonus) {table}: {len(v)} duplicate (race,driver): {v[:5]}')
            print(f'  FAIL (bonus) {table}: {len(v)} dup(s): {v[:5]}')

    con.close()
    print()
    if failures:
        print(f'FAIL -- {len(failures)} invariant violation(s):')
        for f in failures:
            print(f'  - {f}')
        sys.exit(1)
    print('PASS -- bronze failed=0; silver one-winner-per-race and no-duplicate-driver '
          'hold on driver_race and results.')


if __name__ == '__main__':
    main()
