#!/usr/bin/env python3
"""Gate B -- calibration-is-not-edge non-substitution (specs/tether_gates.md, FROZEN).

Claim encoded: no document asserts an EDGE ("beats the book/market", "betting edge over
the closing line") on the strength of CALIBRATION / proper-scoring evidence -- the
doctrine boundary (HANDOFF.md: "Calibration is model-quality, never edge, and never
unlocks roadmap #5.") is stated, not eroded.

Hermetic static scan (read-only, no execution, no network) over the doc set D =
{README.md, HANDOFF.md, specs/*.md, report/*.md}.

  1. Positive assertions: HANDOFF.md carries the canonical doctrine sentinel (sentinel 1)
     verbatim; specs/calibration_backtest.md carries the sentinel-2 non-substitution
     phrases. Missing either -> RED.
  2. Negative scan: RED iff any line in D contains an EDGE-token (E) and a
     CALIBRATION-token (C) and no SEPARATION-phrase (S) -- i.e. it asserts
     calibration => edge without stating the boundary.

Sentinel/token matching is markdown-bold-stripped and whitespace-normalized (spec
prose is hand-wrapped at ~80-100 cols; a sentinel split across two physical lines by
word-wrap must still match). The negative scan additionally strips text inside
straight double-quote pairs before token-matching on each line: this spec's own
"Wiring + verification" and Gate-B "Claim encoded" text MENTIONS example violating
phrases in quotes (e.g. the injection text used to verify red-on-drift) without
ASSERTING them -- quoted text is mention, not use, and a mechanical scan that can't
tell the two apart would go permanently red on its own defining spec. Verified against
the live corpus (2026-07-20): zero negative-scan hits with quote-stripping; three
false positives (tether_gates.md lines 104/130/182, all inside quotes) without it.

CALIBRATION_TOKENS / SEPARATION_PHRASES / doc_files / normalize / strip_quotes are
imported by gate_five_market_gated.py (Gate C reuses C and S verbatim, per the spec's
own cross-reference "C from gate B").

Plain stdlib; exits nonzero on any failure. Run from src/ on the conda interpreter.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

DOC_GLOBS = ['README.md', 'HANDOFF.md', 'specs/*.md', 'report/*.md']

SENTINEL_1 = 'Calibration is model-quality, never edge, and never unlocks roadmap #5.'
SENTINEL_2A = 'calibration is model-vs-reality'
SENTINEL_2B = 'yields zero profit signal and can never establish an edge'
SENTINEL_2C = 'nothing here substitutes for it (tether gate 2)'

EDGE_TOKENS = ['edge over', 'beats the book', 'beat the book', 'beats the market',
               'beat the market', 'betting edge', 'live edge']
CALIBRATION_TOKENS = ['calibrat', 'brier', 'log-loss', 'proper-scor', 'bss', 'skill score']
SEPARATION_PHRASES = ['never edge', 'not edge', 'not an edge', 'zero profit', 'no profit',
                       'cannot establish an edge', 'can never establish an edge',
                       'never substitute', 'not substitute', 'never unlocks',
                       'orthogonal', 'breaks even by construction']


# ---------------------------------------------------------------------------
# shared helpers (also imported by gate_five_market_gated.py)
# ---------------------------------------------------------------------------
def doc_files():
    """The doc set D = {README.md, HANDOFF.md, specs/*.md, report/*.md}, repo-root relative."""
    files = []
    for pat in DOC_GLOBS:
        files.extend(sorted(glob.glob(os.path.join(REPO_ROOT, pat))))
    return files


def normalize(text):
    """Strip markdown bold markers and collapse all whitespace (incl. newlines from
    hand-wrapped prose) to single spaces, for sentinel substring matching."""
    return re.sub(r'\s+', ' ', text.replace('**', ''))


def strip_quotes(line):
    """Remove text within straight double-quote pairs -- a quoted phrase is mentioned
    (an example, an illustration) not asserted, so it is exempt from token matching."""
    return re.sub(r'"[^"]*"', ' ', line)


def has_token(text_lower, tokens):
    return any(t in text_lower for t in tokens)


# ---------------------------------------------------------------------------
# 1. positive assertions
# ---------------------------------------------------------------------------
def check_sentinels(failures):
    handoff_path = os.path.join(REPO_ROOT, 'HANDOFF.md')
    calib_path = os.path.join(REPO_ROOT, 'specs', 'calibration_backtest.md')

    handoff_norm = normalize(open(handoff_path, encoding='utf-8').read())
    if SENTINEL_1 not in handoff_norm:
        failures.append(f'sentinel 1 MISSING from HANDOFF.md (doctrine sentinel not found '
                        f'verbatim): {SENTINEL_1!r}')

    calib_norm = normalize(open(calib_path, encoding='utf-8').read()).lower()
    for label, phrase in (('2a', SENTINEL_2A), ('2b', SENTINEL_2B), ('2c', SENTINEL_2C)):
        if phrase not in calib_norm:
            failures.append(f'sentinel {label} MISSING from specs/calibration_backtest.md: '
                            f'{phrase!r}')


# ---------------------------------------------------------------------------
# 2. negative scan
# ---------------------------------------------------------------------------
def negative_scan_violations(files=None, edge_tokens=None, calib_tokens=None, sep_phrases=None):
    """Returns a list of (relpath, lineno, line) for every line with an EDGE-token AND a
    CALIBRATION-token AND no SEPARATION-phrase (quote-stripped, case-insensitive)."""
    files = files if files is not None else doc_files()
    edge_tokens = edge_tokens if edge_tokens is not None else EDGE_TOKENS
    calib_tokens = calib_tokens if calib_tokens is not None else CALIBRATION_TOKENS
    sep_phrases = sep_phrases if sep_phrases is not None else SEPARATION_PHRASES

    violations = []
    for f in files:
        text = open(f, encoding='utf-8').read()
        for i, line in enumerate(text.split('\n'), 1):
            low = strip_quotes(line).lower()
            if (has_token(low, edge_tokens) and has_token(low, calib_tokens)
                    and not has_token(low, sep_phrases)):
                violations.append((os.path.relpath(f, REPO_ROOT), i, line.strip()))
    return violations


def check_negative_scan(failures):
    for relpath, lineno, line in negative_scan_violations():
        failures.append(f'{relpath}:{lineno}: EDGE-token + CALIBRATION-token, no '
                        f'SEPARATION-phrase -- {line!r}')


# ---------------------------------------------------------------------------
def main():
    print('=' * 78)
    print('gate_calibration_not_edge -- specs/tether_gates.md Gate B (FROZEN)')
    print('=' * 78)

    files = doc_files()
    print(f'[gate_calibration_not_edge] doc set D: {len(files)} files '
          f'({", ".join(sorted(DOC_GLOBS))})')

    failures = []
    print('[gate_calibration_not_edge] 1/2 positive sentinels (doctrine present)...')
    check_sentinels(failures)
    print('[gate_calibration_not_edge] 2/2 negative scan (no calibration=>edge claim)...')
    check_negative_scan(failures)

    print()
    if failures:
        print(f'FAIL -- {len(failures)} violation(s):')
        for f in failures[:50]:
            print(f'  - {f}')
        if len(failures) > 50:
            print(f'  ... and {len(failures) - 50} more')
        sys.exit(1)

    print('PASS -- doctrine sentinels present; no document asserts an edge on the '
          'strength of calibration evidence.')
    sys.exit(0)


if __name__ == '__main__':
    main()
