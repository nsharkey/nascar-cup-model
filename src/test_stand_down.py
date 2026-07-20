#!/usr/bin/env python3
"""Superspeedway stand-down drift gate. Encodes the doctrine claim

    "Superspeedways (Daytona, Talladega, Atlanta) are stand-downs. The harness
     flags these."   (HANDOFF.md, Doctrine)

as a mechanical tie between the human-stated doctrine and the code that
actually classifies + flags those tracks. Plain stdlib asserts (no pytest);
exits nonzero on any mismatch. Run from src/:  `python test_stand_down.py`.

Three independent representations must agree; drift in ANY one is caught:

  1. HANDOFF.md doctrine prose  -> the short names in "Superspeedways (...)
     are stand-downs".
  2. walkforward.py `MY_TYPE`   -> the set of full track names the production
     typology labels 'SS' (the frozen engine's own SS membership).
  3. predict_next.py            -> `stand_down` is wired to `tt == 'SS'`, i.e.
     the harness flags exactly the SS-typed tracks (never acts on them).

Everything is read statically via `ast`/regex -- nothing executes the engine
or loads the pickle, so the gate is hermetic and fast. walkforward.py is FROZEN
and is only READ here, never modified.

The comparison lives in pure functions (`walkforward_ss_set`,
`handoff_ss_names`, `standdown_flag_wired`, `evaluate`) so its red-on-drift
behaviour can be exercised against mutated temp copies without touching the
real frozen files (see the companion red-on-drift check run at build time).
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
HANDOFF = os.path.join(REPO_ROOT, 'HANDOFF.md')
WALKFWD = os.path.join(HERE, 'walkforward.py')
PREDICT = os.path.join(HERE, 'predict_next.py')

# The canonical three, pinned so a swap that still parses (e.g. Atlanta -> some
# other "*Atlanta*"-free track) is also caught, not just a count change.
CANONICAL_SS = {
    'Daytona International Speedway',
    'Talladega Superspeedway',
    'Atlanta Motor Speedway',
}


# ---------------------------------------------------------------------------
# static readers (no execution)
# ---------------------------------------------------------------------------
def walkforward_ss_set(path):
    """Set of full track names that MY_TYPE labels 'SS', extracted from the
    `for t in [...]: MY_TYPE[t] = '<TYPE>'` loops via ast (no execution)."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    ss = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not (isinstance(node.target, ast.Name) and isinstance(node.iter, ast.List)):
            continue
        # find `MY_TYPE[t] = '<TYPE>'` in the loop body
        assigned_type = None
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Subscript)
                    and isinstance(stmt.targets[0].value, ast.Name)
                    and stmt.targets[0].value.id == 'MY_TYPE'
                    and isinstance(stmt.value, ast.Constant)):
                assigned_type = stmt.value.value
        if assigned_type != 'SS':
            continue
        for elt in node.iter.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                ss.add(elt.value)
    return ss


def handoff_ss_names(path):
    """Short track names from the doctrine line 'Superspeedways (...) are
    stand-downs'."""
    text = open(path, encoding='utf-8').read()
    m = re.search(r'Superspeedways\s*\(([^)]+)\)\s*are\s*stand-downs', text)
    if not m:
        return None
    return {s.strip() for s in m.group(1).split(',') if s.strip()}


def standdown_flag_wired(path):
    """True iff predict_next.py sets a dict key 'stand_down' to a comparison
    whose right-hand constant is 'SS' (i.e. stand_down <- tt == 'SS')."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if (isinstance(k, ast.Constant) and k.value == 'stand_down'
                    and isinstance(v, ast.Compare)):
                consts = [c.value for c in v.comparators if isinstance(c, ast.Constant)]
                if 'SS' in consts:
                    return True
    return False


# ---------------------------------------------------------------------------
# pure comparison (so red-on-drift can be exercised on temp copies)
# ---------------------------------------------------------------------------
def evaluate(wf_path, handoff_path, predict_path):
    """Return a list of failure strings (empty == PASS)."""
    failures = []
    ss = walkforward_ss_set(wf_path)
    doc = handoff_ss_names(handoff_path)

    if doc is None:
        failures.append('handoff: could not locate the "Superspeedways (...) are '
                        'stand-downs" doctrine line')
        doc = set()

    # 1. code side pins to exactly the canonical three
    if ss != CANONICAL_SS:
        failures.append(f'walkforward MY_TYPE SS set {sorted(ss)} != canonical '
                        f'{sorted(CANONICAL_SS)}')

    # 2. doctrine names exactly three
    if len(doc) != 3:
        failures.append(f'doctrine names {sorted(doc)} (expected exactly 3)')

    # 3. bijection: each doctrine short name matches exactly one SS full name,
    #    and every SS full name is matched (ties prose<->code without a third
    #    hardcoded list doing the work)
    if ss and doc:
        matched_full = set()
        for short in doc:
            hits = {full for full in ss if short.lower() in full.lower()}
            if len(hits) != 1:
                failures.append(f'doctrine name "{short}" matches {sorted(hits)} '
                                f'SS full names (expected exactly 1)')
            matched_full |= hits
        unmatched = ss - matched_full
        if unmatched:
            failures.append(f'SS full names not named in doctrine: {sorted(unmatched)}')

    # 4. the harness actually flags SS as stand-down
    if not standdown_flag_wired(predict_path):
        failures.append('predict_next.py no longer wires stand_down <- (tt == "SS")')

    return failures


def main():
    print('== test_stand_down ==')
    failures = evaluate(WALKFWD, HANDOFF, PREDICT)
    ss = walkforward_ss_set(WALKFWD)
    doc = handoff_ss_names(HANDOFF) or set()
    print(f'  walkforward MY_TYPE SS set : {sorted(ss)}')
    print(f'  HANDOFF doctrine names     : {sorted(doc)}')
    print(f'  stand_down wired to SS     : {standdown_flag_wired(PREDICT)}')
    print()
    if failures:
        print(f'FAIL -- {len(failures)} mismatch(es):')
        for f in failures:
            print(f'  - {f}')
        sys.exit(1)
    print('PASS -- doctrine {Daytona, Talladega, Atlanta} == walkforward MY_TYPE '
          "SS set == the tracks predict_next flags stand_down (tt=='SS').")


if __name__ == '__main__':
    main()
