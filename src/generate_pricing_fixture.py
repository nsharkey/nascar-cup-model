#!/usr/bin/env python3
"""Generates src/fixtures/pricing_fixture.json -- specs/pricing_layer.md section 5.4.

Run ONCE (or deliberately, on a dated numpy-bump amendment) on the conda 3.13
interpreter: `python generate_pricing_fixture.py`. gate_pricing.py never calls
this file -- it only re-derives the same numbers from the committed fixture's
own `input` blocks and asserts equality against the committed `output` blocks
(the gate reproves, it never re-generates).

Two sub-fixtures per section 5.4:
  - `real_race_5618`: the real committed as-of utility vector (race 5618,
    predictions/race_5618_2026-07-19_prediction.json, `field[].utility`
    verbatim), no manufacturer/group/set -- pins the win/h2h/topN_single
    markets at full field size (37 drivers) to full float precision.
  - `toy_field`: a synthetic 5-driver field (track_type SS, so the
    SS_STAND_DOWN flag is also exercised) with a manufacturer_of map, one
    group, and one set -- small enough to hand-check, exercises every market
    (group_bestof, mfr_win, mfr_bestof, topN_joint, group_topN_count) and the
    section 4 coherence invariants, including the tail_stand_down path (a
    5-driver field makes topN=10 a near-certain event).
"""
import json
import os
import sys

import numpy as np
import scipy

import pricing_layer as pl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURE_PATH = os.path.join(HERE, 'fixtures', 'pricing_fixture.json')
PRED_5618 = os.path.join(REPO_ROOT, 'predictions', 'race_5618_2026-07-19_prediction.json')


def build_real_race_5618():
    d = json.load(open(PRED_5618))
    ids = [e['driver_id'] for e in d['field']]
    u = [e['utility'] for e in d['field']]
    race_id = d['race_id']
    track_type = d['track_type']
    seed = [pl.PRICING_SEED_BASE, race_id]
    priced = pl.price_race(u, ids, track_type, race_id, topN=(3, 5, 10), seed=seed)
    return {
        'input': {
            'race_id': race_id, 'track_type': track_type,
            'driver_ids': ids, 'utility': u,
            'topN': [3, 5, 10], 'seed': seed,
        },
        'output': pl.to_jsonable(priced),
    }


def build_toy_field():
    race_id = 0
    track_type = 'SS'      # also exercises the SS_STAND_DOWN flag path
    ids = [101, 102, 103, 104, 105]
    u = [1.2, 0.5, 0.0, -0.3, -1.0]
    mfr_of = {101: 'Ford', 102: 'Chevrolet', 103: 'Ford', 104: 'Toyota', 105: 'Chevrolet'}
    groups = [[101, 102, 103]]
    sets = [[102, 104]]
    seed = [pl.PRICING_SEED_BASE, race_id]
    priced = pl.price_race(u, ids, track_type, race_id, manufacturer_of=mfr_of,
                            groups=groups, sets=sets, topN=(3, 5, 10), seed=seed)
    return {
        'input': {
            'race_id': race_id, 'track_type': track_type,
            'driver_ids': ids, 'utility': u,
            'manufacturer_of': {str(k): v for k, v in mfr_of.items()},
            'groups': groups, 'sets': sets,
            'topN': [3, 5, 10], 'seed': seed,
        },
        'output': pl.to_jsonable(priced),
    }


def main():
    fixture = {
        'meta': {
            'spec': 'specs/pricing_layer.md section 5.4',
            'numpy_version': np.__version__,
            'scipy_version': scipy.__version__,
            'python_version': sys.version.split()[0],
            'interpreter': sys.executable,
            'note': ('Regenerating this fixture is a deliberate, dated act (a numpy '
                     'upgrade that changes an output value) -- never a silent overwrite. '
                     'gate_pricing.py records and asserts the numpy version below.'),
        },
        'real_race_5618': build_real_race_5618(),
        'toy_field': build_toy_field(),
    }
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, 'w') as f:
        json.dump(fixture, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'wrote {FIXTURE_PATH}')
    print(f'  numpy {np.__version__}, scipy {scipy.__version__}, python {sys.version.split()[0]}')


if __name__ == '__main__':
    main()
