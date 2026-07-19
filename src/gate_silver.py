#!/usr/bin/env python3
"""C-gate -- the silver regression protocol (specs/medallion_architecture.md, section 4, FROZEN
except for the 2026-07-19 fepace amendment -- see the AMENDMENT block above `## RESULT -- C-gate`).

Adjudicates: silver.driver_race reproduces the section-4.1 anchor (races_parsed.pkl, frozen
copy in data/anchors/) field-for-field. Must run against a --full silver build (section 3.5).

Exit code 0 on PASS, 1 on FAIL, 2 if a mismatch needs owner escalation (section 4.3 step 1
has no legacy-import sha baseline to attribute against -- see the known C1 blocker).
"""
import glob, gzip, hashlib, math, os, pickle, sys
from collections import Counter

import duckdb
import pyarrow

import warehouse
from bronze_fetch import race_dir, latest_stored_path, LEGACY_IMPORT_DIR

REPO_ROOT = warehouse.REPO_ROOT
ANCHORS_DIR = os.path.join(REPO_ROOT, 'data', 'anchors')
REPORT_PATH = os.path.join(REPO_ROOT, 'report', 'SILVER_REGRESSION.md')

# section 3.3's null map: which columns are "NULL iff key absent from the pkl driver dict"
# (the five pace/nlaps columns) vs "NULL iff pkl value is None" (qspeed/fepace/practice) vs
# "never null" (finish/status/laps_led/laps_completed) vs "nullable, source may omit"
# (start/team/make). All of these fall out of a plain dict.get() on both sides, so gate
# comparison doesn't need to special-case them -- just compare present-value-or-None.
DRIVER_FIELDS = ['finish', 'start', 'qspeed', 'status', 'team', 'make', 'laps_led',
                  'laps_completed', 'pace_med85', 'pace_mean70', 'pace_p20', 'pace_best',
                  'nlaps', 'fepace', 'practice']
STRING_FIELDS = {'status', 'make'}

# 2026-07-19 amendment (see spec, dated AMENDMENT block before `## RESULT -- C-gate`): fepace
# is the only column computed via np.linalg.lstsq (an SVD solve), and its cross-environment
# BLAS/LAPACK non-reproducibility (confirmed mechanism, ULP-scale diffs) is exempted from
# exact `==`. Every other section-3.3 column is unaffected and still compares exactly.
FEPACE_REL_TOL = 1e-9
FEPACE_ABS_TOL = 1e-12


def _fepace_tolerant_eq(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return math.isclose(a, b, rel_tol=FEPACE_REL_TOL, abs_tol=FEPACE_ABS_TOL)


def _latest_anchor_path():
    paths = sorted(glob.glob(os.path.join(ANCHORS_DIR, 'races_parsed_anchor_*.pkl')))
    if not paths:
        sys.exit('[gate_silver] no anchor found under data/anchors/ -- run section 4.1 first')
    return paths[-1]


def _num_eq(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return float(a) == float(b)


def _str_eq(a, b):
    a = a or ''
    b = b or ''
    return a == b


def _field_eq(field, a, b):
    if field in STRING_FIELDS:
        return _str_eq(a, b)
    return _num_eq(a, b)


def _legacy_import_sha(feed, sid, year, race_id):
    """Section 2.6 legacy-import sha for a given feed/race, if one was ever imported.
    Known C1 blocker (report/BRONZE_COVERAGE.md, B3): only race_list_2026.json was legacy-
    imported in this checkout -- no per-race lap-times/weekend-feed cache exists, so this
    returns None for every anchor race. Kept general (not hardcoded to fail) in case an
    owner-recovered legacy cache is ever dropped into data/bronze/legacy_import/."""
    candidates = [
        os.path.join(LEGACY_IMPORT_DIR, f'{year}_{race_id}_{"lt" if feed == "lap-times" else "wf"}.json.gz'),
    ]
    for path in candidates:
        if os.path.exists(path):
            with gzip.open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
    return None


def run_gate():
    anchor_path = _latest_anchor_path()
    with open(anchor_path, 'rb') as f:
        anchor_bytes = f.read()
    anchor_sha = hashlib.sha256(anchor_bytes).hexdigest()
    anchor_races = pickle.loads(anchor_bytes)
    print(f'[gate_silver] anchor: {anchor_path}')
    print(f'[gate_silver] anchor sha256: {anchor_sha}')
    print(f'[gate_silver] anchor race count: {len(anchor_races)}')

    warehouse.build_warehouse()
    con = duckdb.connect(warehouse.DB_PATH, read_only=True)

    driver_race_rows = con.sql("""
        SELECT * FROM silver.driver_race WHERE series_id = 1
    """).fetchall()
    driver_race_cols = [d[0] for d in con.sql(
        "SELECT * FROM silver.driver_race WHERE series_id = 1 LIMIT 0"
    ).description]
    by_race = {}
    for row in driver_race_rows:
        rec = dict(zip(driver_race_cols, row))
        by_race.setdefault(rec['race_id'], {})[rec['driver_id']] = rec

    races_rows = con.sql("SELECT * FROM silver.races WHERE series_id = 1").fetchall()
    races_cols = [d[0] for d in con.sql("SELECT * FROM silver.races WHERE series_id = 1 LIMIT 0").description]
    races_by_id = {dict(zip(races_cols, row))['race_id']: dict(zip(races_cols, row)) for row in races_rows}

    con.close()

    field_comparisons = 0
    rows_compared = 0
    race_pass, race_pass_note, race_fail = [], [], []
    notes = []
    escalate = []

    for anchor_race in anchor_races:
        rid = anchor_race['rid']
        mismatches = []
        fepace_env_diffs = []

        races_row = races_by_id.get(rid)
        if races_row is None or races_row['parse_status'] != 'ok':
            mismatches.append(('race_present', 'anchor race missing from silver.driver_race '
                                f'(parse_status={races_row["parse_status"] if races_row else "no row"})'))
        else:
            for field, anchor_key in [('race_date', 'date'), ('year', 'year'), ('race_id', 'rid'),
                                       ('track_name', 'track'), ('n_green', 'n_green'),
                                       ('n_fe', 'n_fe'), ('n_prac', 'n_prac')]:
                a, s = anchor_race[anchor_key], races_row[field]
                field_comparisons += 1
                ok = _str_eq(a, s) if field in ('race_date', 'track_name') else _num_eq(a, s)
                if field == 'race_id':
                    ok = (a == s)
                if not ok:
                    mismatches.append((f'race.{field}', f'anchor={a!r} silver={s!r}'))

            silver_drivers = by_race.get(rid, {})
            anchor_driver_ids = set(anchor_race['drivers'].keys())
            silver_driver_ids = set(silver_drivers.keys())
            if anchor_driver_ids != silver_driver_ids:
                mismatches.append(('driver_set', f'anchor-only={anchor_driver_ids - silver_driver_ids} '
                                                  f'silver-only={silver_driver_ids - anchor_driver_ids}'))

            fepace_env_diffs = []
            for did in anchor_driver_ids & silver_driver_ids:
                a_row = anchor_race['drivers'][did]
                s_row = silver_drivers[did]
                rows_compared += 1
                for field in DRIVER_FIELDS:
                    field_comparisons += 1
                    av, sv = a_row.get(field), s_row.get(field)
                    if field == 'fepace':
                        if _num_eq(av, sv):
                            continue
                        if _fepace_tolerant_eq(av, sv):
                            fepace_env_diffs.append((did, av, sv))
                            continue
                        mismatches.append((f'driver[{did}].fepace',
                                            f'anchor={av!r} silver={sv!r} (beyond amendment tolerance)'))
                    elif not _field_eq(field, av, sv):
                        mismatches.append((f'driver[{did}].{field}', f'anchor={av!r} silver={sv!r}'))

        if not mismatches and not fepace_env_diffs:
            race_pass.append(rid)
            continue

        if not mismatches:
            # fepace-only, within the 2026-07-19 amendment tolerance: PASS-with-note.
            notes.append({'race_id': rid, 'date': anchor_race['date'], 'track': anchor_race['track'],
                           'note_kind': 'fepace_environment_tolerance',
                           'reason': 'fepace: environment (BLAS/LAPACK) floating-point '
                                     'non-reproducibility, not a parser or data difference',
                           'fepace_diffs': fepace_env_diffs})
            race_pass_note.append(rid)
            continue

        # section 4.3 mismatch attribution
        year = anchor_race['year']
        lt_path = latest_stored_path(race_dir(1, year, rid), 'lap-times')
        wf_path = latest_stored_path(race_dir(1, year, rid), 'weekend-feed')
        bronze_lt_sha = hashlib.sha256(gzip.open(lt_path, 'rb').read()).hexdigest() if lt_path else None
        bronze_wf_sha = hashlib.sha256(gzip.open(wf_path, 'rb').read()).hexdigest() if wf_path else None
        legacy_lt_sha = _legacy_import_sha('lap-times', 1, year, rid)
        legacy_wf_sha = _legacy_import_sha('weekend-feed', 1, year, rid)

        if legacy_lt_sha is None or legacy_wf_sha is None:
            escalate.append({'race_id': rid, 'date': anchor_race['date'], 'track': anchor_race['track'],
                              'mismatches': mismatches})
            continue

        # (mechanical path for the case a legacy per-race cache is later recovered -- unused
        # in this checkout since the sha lookup above always returns None here.)
        if bronze_lt_sha == legacy_lt_sha and bronze_wf_sha == legacy_wf_sha:
            print(f'\n[gate_silver] FAIL -- race {rid}: bronze shas match legacy-import shas, '
                  f'so this is a parser/plumbing regression, not an upstream data change.')
            for field, detail in mismatches:
                print(f'  {field}: {detail}')
            race_fail.append(rid)
            continue

        notes.append({'race_id': rid, 'date': anchor_race['date'], 'track': anchor_race['track'],
                       'note_kind': 'upstream_data_revision', 'mismatches': mismatches})
        race_pass_note.append(rid)

    if escalate:
        mismatch_fields = Counter()
        for e in escalate:
            for field, _ in e['mismatches']:
                mismatch_fields[field.split('.', 1)[-1].split('[')[0] if '.' in field else field] += 1
        print(f'\n[gate_silver] STOP -- {len(escalate)}/{len(anchor_races)} anchor race(s) mismatch '
              f'and section 4.3 step 1 has no legacy-import sha baseline to attribute against (known '
              f'C1 blocker, report/BRONZE_COVERAGE.md B3): only race_list_2026.json was ever legacy-'
              f'imported, no per-race lap-times/weekend-feed cache exists in this checkout.')
        print(f'[gate_silver] mismatching field(s) across all {len(escalate)} race(s): '
              f'{dict(mismatch_fields)}')
        print(f'[gate_silver] first mismatching race ({escalate[0]["race_id"]}, '
              f'{escalate[0]["date"][:10]}, {escalate[0]["track"]}):')
        for field, detail in escalate[0]['mismatches'][:10]:
            print(f'  {field}: {detail}')
        if len(escalate[0]['mismatches']) > 10:
            print(f'  ... and {len(escalate[0]["mismatches"]) - 10} more')
        print('[gate_silver] escalating to the owner per the C1 kickoff instructions -- '
              'not substituting a fallback baseline or guessing.')
        return {'verdict': 'ESCALATE', 'escalate': escalate, 'anchor_path': anchor_path,
                'anchor_sha': anchor_sha, 'anchor_count': len(anchor_races)}

    # section 4.2 point 5: no silver Cup/points 'ok' race inside the anchor's own date range
    # is missing from the anchor (else parse_race's skip behavior drifted since the pkl was
    # built). Anchor-era skip reasons don't need a separate check here: silver_build.py stores
    # 'skipped: {err}' verbatim from parse_race()'s own return value, so they match by
    # construction -- there is no other code path that could write a different string.
    anchor_ids = {r['rid'] for r in anchor_races}
    anchor_dates = sorted(r['date'] for r in anchor_races)
    lo, hi = anchor_dates[0], anchor_dates[-1]
    unexpected_ok = sorted(
        rid for rid, row in races_by_id.items()
        if row['parse_status'] == 'ok' and row['race_date'] is not None
        and lo <= row['race_date'] <= hi and rid not in anchor_ids
    )
    if unexpected_ok:
        print(f'\n[gate_silver] NOTE -- {len(unexpected_ok)} Cup/points race(s) parsed \'ok\' '
              f'inside the anchor date range [{lo}, {hi}] but absent from the anchor: '
              f'{unexpected_ok}. Not a gate failure by itself (section 4.1 says the universe '
              f'grows with newly appended races) -- flagged for the report.')

    verdict = 'PASS' if not race_fail else 'FAIL'
    print(f'\n[gate_silver] {verdict}')
    print(f'[gate_silver] anchor races: {len(anchor_races)}  pass: {len(race_pass)}  '
          f'pass-with-note: {len(race_pass_note)}  fail: {len(race_fail)}')
    print(f'[gate_silver] rows compared: {rows_compared}  field comparisons: {field_comparisons}')

    return {
        'verdict': verdict,
        'anchor_path': anchor_path,
        'anchor_sha': anchor_sha,
        'anchor_count': len(anchor_races),
        'unexpected_ok_in_range': unexpected_ok,
        'race_pass': race_pass,
        'race_pass_note': race_pass_note,
        'race_fail': race_fail,
        'rows_compared': rows_compared,
        'field_comparisons': field_comparisons,
        'notes': notes,
    }


def write_report(result):
    """section 4.4: anchor sha256 + race count, rows compared, field-comparison counts,
    every PASS-with-note in full, and the environment versions."""
    lines = []
    lines.append('# SILVER_REGRESSION.md -- C-gate report (specs/medallion_architecture.md section 4)')
    lines.append('')
    lines.append(f'**Verdict: {result["verdict"]}**')
    lines.append('')
    lines.append('Pre-amendment verdict (original FROZEN section-4.2 exact-`==` rule, before the '
                  '2026-07-19 mid-C1 fepace amendment): **FAIL** -- 162/163 anchor races failed, '
                  'every failure on exactly one field (`fepace`), zero on any other column. See the '
                  '`## AMENDMENT` block in the spec immediately above `## RESULT -- C-gate` for the '
                  'full root-cause analysis and owner authorization. Post-amendment verdict (below) '
                  'is what this report certifies.')
    lines.append('')
    lines.append('## Anchor')
    lines.append('')
    lines.append(f'- Path: `{os.path.relpath(result["anchor_path"], REPO_ROOT)}`')
    lines.append(f'- sha256: `{result["anchor_sha"]}`')
    lines.append(f'- Race count: {result["anchor_count"]}')
    lines.append('')
    lines.append('## Comparison counts')
    lines.append('')
    lines.append(f'- Rows compared (driver-races): {result["rows_compared"]}')
    lines.append(f'- Field comparisons: {result["field_comparisons"]}')
    lines.append(f'- Clean PASS: {len(result["race_pass"])}')
    lines.append(f'- PASS-with-note: {len(result["race_pass_note"])}')
    lines.append(f'- FAIL: {len(result["race_fail"])}')
    lines.append('')
    lines.append('## Environment')
    lines.append('')
    lines.append(f'- python: {sys.version.split()[0]}')
    lines.append(f'- numpy: {__import__("numpy").__version__}')
    lines.append(f'- duckdb: {duckdb.__version__}')
    lines.append(f'- pyarrow: {pyarrow.__version__}')
    lines.append('')
    if result['unexpected_ok_in_range']:
        lines.append('## Unexpected in-range parses (section 4.2 point 5)')
        lines.append('')
        lines.append(f'{len(result["unexpected_ok_in_range"])} Cup/points race(s) parsed `ok` inside '
                      f'the anchor\'s own date range but absent from the anchor -- not a gate failure '
                      f'(the universe grows with newly appended races, section 4.1), flagged here for '
                      f'visibility: {result["unexpected_ok_in_range"]}')
        lines.append('')
    lines.append('## PASS-with-note (in full)')
    lines.append('')
    lines.append(f'All {len(result["race_pass_note"])} are `fepace_environment_tolerance` -- see the '
                  'spec AMENDMENT for the mechanism. Format: race_id, date, track, then each '
                  '(driver_id: anchor value -> silver value) pair that differed beyond exact `==` but '
                  'within the amendment tolerance (`math.isclose(rel_tol=1e-9, abs_tol=1e-12)`).')
    lines.append('')
    for note in result['notes']:
        if note.get('note_kind') == 'fepace_environment_tolerance':
            lines.append(f'### race {note["race_id"]} -- {note["date"][:10]} -- {note["track"]}')
            lines.append('')
            for did, a, s in note['fepace_diffs']:
                lines.append(f'- driver {did}: `{a!r}` -> `{s!r}`')
            lines.append('')
        else:
            lines.append(f'### race {note["race_id"]} -- {note["date"][:10]} -- {note["track"]} '
                          f'({note.get("note_kind", "note")})')
            lines.append('')
            for field, detail in note['mismatches']:
                lines.append(f'- {field}: {detail}')
            lines.append('')

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'[gate_silver] wrote {REPORT_PATH}')


if __name__ == '__main__':
    result = run_gate()
    if result['verdict'] == 'PASS':
        write_report(result)
        sys.exit(0)
    elif result['verdict'] == 'ESCALATE':
        sys.exit(2)
    else:
        sys.exit(1)
