#!/usr/bin/env python3
"""README headline-numbers drift gate. Asserts README.md's "Headline results"
table for THIS model still matches the model's authoritative backtest trio.
Plain stdlib asserts (no pytest); exits nonzero on any mismatch. Run from src/:
`python test_readme_numbers.py`.

Source of truth for the trio is `gate_gold.py`'s EXPECTED_BACKTEST /
EXPECTED_NONSS / EXPECTED_OOS constants -- the D-gate (section 6) reproves the
frozen model against these three every time it runs (all three legs verified
PASS against a live walk-forward computation on the anchor). So this gate ties
README statically to those constants, and gate_gold ties those constants to the
live computation: README therefore transitively matches a computed value,
without this fast/hermetic test re-running the model.

Both files are read statically (`ast` for gate_gold's constants, regex for
README's table) -- no model run, no pickle, no network.

Checks the three model rows:
  - "This model (PL: ...)"        == EXPECTED_BACKTEST (0.413)
  - "non-superspeedways only"     == EXPECTED_NONSS    (0.476)
  - "2026 out-of-sample"          == EXPECTED_OOS      (0.447)
and guards the regression the 2026-07-19 doc cleanup just fixed: the
2026-out-of-sample ROW must read 0.447, never the old 0.449.
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
README = os.path.join(REPO_ROOT, 'README.md')
GATE_GOLD = os.path.join(HERE, 'gate_gold.py')

FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok   {name}')
    else:
        FAILURES.append(f'{name}: {detail}')
        print(f'  FAIL {name}: {detail}')


def gate_gold_expected():
    """EXPECTED_BACKTEST / EXPECTED_NONSS / EXPECTED_OOS from gate_gold.py, read
    statically (no import of the numpy/scipy/pickle stack)."""
    tree = ast.parse(open(GATE_GOLD, encoding='utf-8').read())
    want = {'EXPECTED_BACKTEST', 'EXPECTED_NONSS', 'EXPECTED_OOS'}
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in want:
                    try:
                        out[tgt.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return out


def readme_headline_numbers():
    """The three model rows from README's headline table -> floats."""
    text = open(README, encoding='utf-8').read()
    out = {}
    m = re.search(r'This model[^|\n]*\|\s*\*{0,2}([\d.]+)\*{0,2}\s*\|', text)
    out['backtest'] = float(m.group(1)) if m else None
    m = re.search(r'non-superspeedways only\s*\|\s*\*{0,2}([\d.]+)\*{0,2}\s*\|', text)
    out['nonss'] = float(m.group(1)) if m else None
    m = re.search(r'2026 out-of-sample[^|\n]*\|\s*\*{0,2}([\d.]+)\*{0,2}\s*\|', text)
    out['oos'] = float(m.group(1)) if m else None
    return out


def main():
    print('== test_readme_numbers ==')
    exp = gate_gold_expected()
    rd = readme_headline_numbers()

    for k in ('EXPECTED_BACKTEST', 'EXPECTED_NONSS', 'EXPECTED_OOS'):
        check(f'gate_gold has {k}', k in exp, f'{k} not found in gate_gold.py')
    for k in ('backtest', 'nonss', 'oos'):
        check(f'readme parsed {k}', rd[k] is not None, f'could not parse {k} row from README table')
    if FAILURES:  # can't compare if either side failed to parse
        print('\nFAIL -- parse error(s) above')
        sys.exit(1)

    check('backtest  README==gate_gold', rd['backtest'] == exp['EXPECTED_BACKTEST'],
          f"README={rd['backtest']} gate_gold.EXPECTED_BACKTEST={exp['EXPECTED_BACKTEST']}")
    check('non-SS    README==gate_gold', rd['nonss'] == exp['EXPECTED_NONSS'],
          f"README={rd['nonss']} gate_gold.EXPECTED_NONSS={exp['EXPECTED_NONSS']}")
    check('2026-OOS  README==gate_gold', rd['oos'] == exp['EXPECTED_OOS'],
          f"README={rd['oos']} gate_gold.EXPECTED_OOS={exp['EXPECTED_OOS']}")
    # explicit anti-regression: the 2026-OOS row must be the corrected 0.447
    check('2026-OOS  row is corrected 0.447 (not stale 0.449)', rd['oos'] == 0.447,
          f"README 2026-OOS row = {rd['oos']}")

    print()
    if FAILURES:
        print(f'FAIL -- {len(FAILURES)} mismatch(es):')
        for f in FAILURES:
            print(f'  - {f}')
        sys.exit(1)
    print('PASS -- README headline trio (0.413 / 0.476 / 0.447) matches '
          'gate_gold.py EXPECTED_* (which the D-gate verifies against the live model).')


if __name__ == '__main__':
    main()
