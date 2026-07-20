#!/usr/bin/env python3
"""Frozen-config drift gate. Asserts the LIVE production config the forward-test
harness actually runs still equals the frozen config stated in HANDOFF.md's
"Production config (FROZEN ...)" block. Plain stdlib asserts (no pytest); exits
nonzero on any mismatch. Run from src/:  `python test_frozen_config.py`.

This encodes a prose-only claim (HANDOFF.md's frozen block + predict_next.py's
docstring) as a mechanical check. It is a THREE-WAY tie, so drift in any leg is
caught:

  1. HANDOFF.md's frozen block (the human-stated source of truth), parsed from
     the "Production config (FROZEN ...)" paragraph.
  2. predict_next.py's live constants (HL, BURN, MIN_HIST, MIN_DRV, PACE_KEY,
     FEATS) and its logged `config` dict (typology / typed / lam).
  3. walkforward.py's `pl_fit` default `lam` -- the ridge lambda predict_next
     actually fits with (it calls `pl_fit(Xs, Os)` with no lam override).

Nothing here EXECUTES predict_next.py (it does network I/O and writes a
prediction on import) or loads the pickle -- everything is read statically via
`ast`, so the gate is hermetic and fast. It reads walkforward.py/predict_next.py
read-only; it never modifies the frozen engine.

Fields checked (the seven HANDOFF names plus typology + typed):
  pace, half-life, features, ridge lambda, burn, min_hist, min_drv,
  corrected typology (MY_TYPE), shrinkage typed history.
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
HANDOFF = os.path.join(REPO_ROOT, 'HANDOFF.md')
PREDICT = os.path.join(HERE, 'predict_next.py')
WALKFWD = os.path.join(HERE, 'walkforward.py')

FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok   {name}')
    else:
        FAILURES.append(f'{name}: {detail}')
        print(f'  FAIL {name}: {detail}')


# ---------------------------------------------------------------------------
# static readers (no execution)
# ---------------------------------------------------------------------------
def module_constants(path):
    """Top-level literal assignments -> {name: value}. Handles single-name and
    tuple-unpacking targets (e.g. `A, B = 1, 2`)."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            try:
                if isinstance(tgt, ast.Name):
                    out[tgt.id] = ast.literal_eval(node.value)
                elif isinstance(tgt, (ast.Tuple, ast.List)) and isinstance(
                        node.value, (ast.Tuple, ast.List)):
                    for nm, val in zip(tgt.elts, node.value.elts):
                        if isinstance(nm, ast.Name):
                            out[nm.id] = ast.literal_eval(val)
            except (ValueError, TypeError):
                pass  # non-literal RHS (references, calls) -- skip
    return out


def func_default(path, funcname, argname):
    """Default value of a named arg in a top-level def, or None if absent."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            args = node.args.args
            defaults = node.args.defaults
            named = args[len(args) - len(defaults):]
            for a, d in zip(named, defaults):
                if a.arg == argname:
                    return ast.literal_eval(d)
    return None


def logged_config_dict(path):
    """The `dict(...)` call in predict_next that logs the run config -- return
    its literal (Constant-valued) keywords, keyed by name. Identified by its
    `typology` keyword, which the feature-bank `dict(...)` calls don't have."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'dict'
                and any(k.arg == 'typology' for k in node.keywords)):
            out = {}
            for k in node.keywords:
                if isinstance(k.value, ast.Constant):
                    out[k.arg] = k.value.value
            return out
    return {}


def imports_name(path, name):
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(a.name == name for a in node.names):
                return True
    return False


# ---------------------------------------------------------------------------
# HANDOFF.md frozen block (human-stated source of truth)
# ---------------------------------------------------------------------------
def parse_handoff_frozen_block():
    text = open(HANDOFF, encoding='utf-8').read()
    m = re.search(r'Production config \(FROZEN.*?\n(.*?)(?:\n\n|\n## )', text, re.S)
    if not m:
        FAILURES.append('handoff: could not locate the "Production config (FROZEN ...)" block')
        return None
    block = m.group(1)
    out = {}
    pace = re.search(r'pace = `([a-z0-9_]+)`', block)
    hl = re.search(r'half-life (\d+)', block)
    feats = re.search(r'PL features\s*`\[([^\]]+)\]`', block)
    lam = re.search(r'ridge\s*λ\s*=\s*([\d.]+)', block)
    burn = re.search(r'burn (\d+)', block)
    mh = re.search(r'min_hist (\d+)', block)
    md = re.search(r'min_drv (\d+)', block)
    out['pace'] = pace.group(1) if pace else None
    out['hl'] = int(hl.group(1)) if hl else None
    out['feats'] = [f.strip() for f in feats.group(1).split(',')] if feats else None
    out['lam'] = float(lam.group(1)) if lam else None
    out['burn'] = int(burn.group(1)) if burn else None
    out['min_hist'] = int(mh.group(1)) if mh else None
    out['min_drv'] = int(md.group(1)) if md else None
    out['has_my_type'] = 'MY_TYPE' in block
    out['has_shrinkage'] = 'shrinkage' in block
    return out


def main():
    print('== test_frozen_config ==')
    hand = parse_handoff_frozen_block()
    if hand is None:
        print('\nFAIL -- could not parse HANDOFF frozen block')
        sys.exit(1)

    pn = module_constants(PREDICT)
    cfg = logged_config_dict(PREDICT)
    pl_lam = func_default(WALKFWD, 'pl_fit', 'lam')

    # sanity: HANDOFF block parsed the values we expect to compare against
    for k in ('pace', 'hl', 'feats', 'lam', 'burn', 'min_hist', 'min_drv'):
        check(f'handoff parsed {k}', hand[k] is not None, f'regex missed {k} in frozen block')

    # 1. pace
    check('pace  handoff==live', hand['pace'] == pn.get('PACE_KEY'),
          f"handoff={hand['pace']} predict_next.PACE_KEY={pn.get('PACE_KEY')}")
    # 2. half-life
    check('half-life  handoff==live', hand['hl'] == pn.get('HL'),
          f"handoff={hand['hl']} predict_next.HL={pn.get('HL')}")
    # 3. features
    check('features  handoff==live', hand['feats'] == pn.get('FEATS'),
          f"handoff={hand['feats']} predict_next.FEATS={pn.get('FEATS')}")
    # 4. ridge lambda -- HANDOFF == pl_fit default == logged config
    check('ridge-lambda  handoff==pl_fit-default', hand['lam'] == pl_lam,
          f"handoff={hand['lam']} walkforward.pl_fit lam default={pl_lam}")
    check('ridge-lambda  pl_fit-default==logged-config', pl_lam == cfg.get('lam'),
          f"pl_fit default={pl_lam} predict_next logged config lam={cfg.get('lam')}")
    # 5. burn
    check('burn  handoff==live', hand['burn'] == pn.get('BURN'),
          f"handoff={hand['burn']} predict_next.BURN={pn.get('BURN')}")
    # 6. min_hist
    check('min_hist  handoff==live', hand['min_hist'] == pn.get('MIN_HIST'),
          f"handoff={hand['min_hist']} predict_next.MIN_HIST={pn.get('MIN_HIST')}")
    # 7. min_drv
    check('min_drv  handoff==live', hand['min_drv'] == pn.get('MIN_DRV'),
          f"handoff={hand['min_drv']} predict_next.MIN_DRV={pn.get('MIN_DRV')}")

    # typology + typed history
    check('typology  handoff mentions MY_TYPE', hand['has_my_type'], 'frozen block lost MY_TYPE')
    check('typology  predict_next imports MY_TYPE', imports_name(PREDICT, 'MY_TYPE'),
          'predict_next no longer imports MY_TYPE from walkforward')
    check('typology  logged config == MY_TYPE', cfg.get('typology') == 'MY_TYPE',
          f"logged config typology={cfg.get('typology')}")
    check('typed  handoff mentions shrinkage', hand['has_shrinkage'], 'frozen block lost shrinkage')
    check('typed  logged config == shrinkage', cfg.get('typed') == 'shrinkage',
          f"logged config typed={cfg.get('typed')}")

    print()
    if FAILURES:
        print(f'FAIL -- {len(FAILURES)} mismatch(es):')
        for f in FAILURES:
            print(f'  - {f}')
        sys.exit(1)
    print('PASS -- live production config (predict_next.py + walkforward.pl_fit) '
          'matches HANDOFF.md frozen block on all seven fields + typology/typed.')


if __name__ == '__main__':
    main()
