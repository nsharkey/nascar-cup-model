#!/usr/bin/env python3
"""Gate C -- roadmap-#5 stays market-gated (specs/tether_gates.md, FROZEN).

Claim encoded: specs/clean_air_causal_pace.md's execution gate (section 0, FROZEN,
read-only -- this gate never edits it) reads the market-benchmark verdict, never a
calibration verdict. The forbidden inference (calibration -> edge -> roadmap #5)
cannot be committed without this gate going red.

Hermetic static scan (read-only, no execution, no network).

  1. Positive assertions on clean_air_causal_pace.md section 0: references
     market_benchmark_decision_rule.md, the word EDGE, and "UNDERPOWERED does not
     unlock" (sentinel 4). Missing any -> RED.
  2. Section 0 contains no CALIBRATION-token (C, from gate_calibration_not_edge) and
     no reference to "calibration_backtest". Any present -> RED.
  3. Negative scan over the doc set D (gate B's D): RED iff any line contains a
     #5-token (F) AND an UNLOCK-token (U) AND a CALIBRATION-token (C) AND no
     SEPARATION-phrase (S) -- i.e. it ties #5 execution to calibration.
  4. Positive assertion: specs/calibration_backtest.md section 3 contains the
     sentinel-3 clause "never unlocks roadmap #5 (tether gate 3)". Missing -> RED.

C and S are imported from gate_calibration_not_edge (not redefined here) so the two
gates' token lists can never drift apart -- the spec names them "C from gate B"
verbatim. Sentinel/token matching uses the same markdown-bold-stripped,
whitespace-normalized, quote-stripped approach as Gate B (see that module's
docstring for why quote-stripping is required against this repo's own hand-wrapped
prose and worked-example text).

Plain stdlib; exits nonzero on any failure. Run from src/ on the conda interpreter.
"""
import os
import re
import sys

from gate_calibration_not_edge import (
    CALIBRATION_TOKENS, SEPARATION_PHRASES, doc_files, normalize, strip_quotes, has_token,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

CLEAN_AIR_PATH = os.path.join(REPO_ROOT, 'specs', 'clean_air_causal_pace.md')
CALIB_PATH = os.path.join(REPO_ROOT, 'specs', 'calibration_backtest.md')

SENTINEL_4_MARKET_REF = 'market_benchmark_decision_rule.md'
SENTINEL_4_UNLOCK_TEXT = 'underpowered does not unlock'
SENTINEL_3 = 'never unlocks roadmap #5 (tether gate 3)'

FIVE_TOKENS = ['roadmap #5', 'roadmap-#5', 'clean-air', 'clean_air', 'g2']
UNLOCK_TOKENS = ['unlock', 'gates', 'execute', 'execution gate', 'trigger']


# ---------------------------------------------------------------------------
def extract_section(text, section_num, next_section_num):
    """Text of a `## <section_num>. ...` heading up to (not including) the next
    `## <next_section_num>. ...` heading. FROZEN-section extraction, read-only."""
    pattern = rf'\n## {re.escape(section_num)}\..*?\n(.*?)\n## {re.escape(next_section_num)}\.'
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 1-2. positive assertions + calibration-freedom on clean_air section 0
# ---------------------------------------------------------------------------
def check_clean_air_section0(failures):
    text = open(CLEAN_AIR_PATH, encoding='utf-8').read()
    sec0 = extract_section(text, '0', '1')
    if sec0 is None:
        failures.append('specs/clean_air_causal_pace.md: could not locate section 0 '
                        '("## 0. ..." through "## 1. ...")')
        return

    if SENTINEL_4_MARKET_REF not in sec0:
        failures.append(f'clean_air_causal_pace.md section 0 missing reference to '
                        f'{SENTINEL_4_MARKET_REF!r}')
    if 'EDGE' not in sec0:
        failures.append('clean_air_causal_pace.md section 0 missing the word "EDGE"')
    sec0_norm = normalize(sec0).lower()
    if SENTINEL_4_UNLOCK_TEXT not in sec0_norm:
        failures.append(f'clean_air_causal_pace.md section 0 missing sentinel 4: '
                        f'"UNDERPOWERED does not unlock"')

    sec0_low = sec0.lower()
    hit_c = [t for t in CALIBRATION_TOKENS if t in sec0_low]
    if hit_c:
        failures.append(f'clean_air_causal_pace.md section 0 contains CALIBRATION-token(s) '
                        f'{hit_c} -- roadmap #5 execution is being conditioned on calibration')
    if 'calibration_backtest' in sec0_low:
        failures.append('clean_air_causal_pace.md section 0 references calibration_backtest '
                        '-- roadmap #5 execution is being conditioned on calibration')


# ---------------------------------------------------------------------------
# 3. negative scan (F x U x C, no S)
# ---------------------------------------------------------------------------
def negative_scan_violations(files=None):
    files = files if files is not None else doc_files()
    violations = []
    for f in files:
        text = open(f, encoding='utf-8').read()
        for i, line in enumerate(text.split('\n'), 1):
            low = strip_quotes(line).lower()
            if (has_token(low, FIVE_TOKENS) and has_token(low, UNLOCK_TOKENS)
                    and has_token(low, CALIBRATION_TOKENS)
                    and not has_token(low, SEPARATION_PHRASES)):
                violations.append((os.path.relpath(f, REPO_ROOT), i, line.strip()))
    return violations


def check_negative_scan(failures):
    for relpath, lineno, line in negative_scan_violations():
        failures.append(f'{relpath}:{lineno}: #5-token + UNLOCK-token + CALIBRATION-token, '
                        f'no SEPARATION-phrase -- {line!r}')


# ---------------------------------------------------------------------------
# 4. positive assertion tying the pieces
# ---------------------------------------------------------------------------
def check_sentinel_3(failures):
    calib_norm = normalize(open(CALIB_PATH, encoding='utf-8').read()).lower()
    if SENTINEL_3 not in calib_norm:
        failures.append(f'specs/calibration_backtest.md section 3 missing sentinel 3: '
                        f'{SENTINEL_3!r}')


# ---------------------------------------------------------------------------
def main():
    print('=' * 78)
    print('gate_five_market_gated -- specs/tether_gates.md Gate C (FROZEN)')
    print('=' * 78)

    failures = []
    print('[gate_five_market_gated] 1/3 clean_air_causal_pace.md section 0 (market-gated, '
          'no calibration token)...')
    check_clean_air_section0(failures)
    print('[gate_five_market_gated] 2/3 negative scan (no #5=>unlock=>calibration claim)...')
    check_negative_scan(failures)
    print('[gate_five_market_gated] 3/3 calibration_backtest.md section 3 sentinel...')
    check_sentinel_3(failures)

    print()
    if failures:
        print(f'FAIL -- {len(failures)} violation(s):')
        for f in failures[:50]:
            print(f'  - {f}')
        if len(failures) > 50:
            print(f'  ... and {len(failures) - 50} more')
        sys.exit(1)

    print('PASS -- roadmap #5 execution gate reads only the market benchmark; no document '
          'ties #5 unlock to calibration.')
    sys.exit(0)


if __name__ == '__main__':
    main()
