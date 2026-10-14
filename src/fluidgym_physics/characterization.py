"""Versioned matrix expansion and conservative, explicitly uncalibrated budgets."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .inventory import registrations
from .upstream import read_lock


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    # O_EXCL prevents overwrites even between concurrent invocations.
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def _positive(value, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('expected a finite positive number')
    if integer and not isinstance(value, int):
        raise ValueError('expected a positive integer')


def load_matrix(path):
    m = json.loads(Path(path).read_text())
    expected = {'schema_version','matrix_id','upstream_commit','review_status','mode','action',
                'protocols','replicates','budget','environments','deferred_3d'}
    if set(m) != expected or m['schema_version'] != 1 or m['upstream_commit'] != read_lock().commit:
        raise ValueError('unknown matrix schema/keys or upstream revision')
    if m['mode'] not in ('train','val','test') or m['action'] != 'zero':
        raise ValueError('only nominal zero-action characterization is supported')
    if m['protocols'] != ['benchmark','extended']:
        raise ValueError('both separate protocols are required')
    reg = registrations()
    seen = set()
    for row in m['environments']:
        if set(row) != {'env_id','extended_steps','discard_steps','snapshot_stride','seconds_per_step_scenario'}:
            raise ValueError('unknown environment row keys')
        eid = row['env_id']
        if eid not in reg or reg[eid]['ndims'] != 2 or eid in seen:
            raise ValueError(f'unsupported or duplicate execution row: {eid}')
        seen.add(eid)
        for key in ('extended_steps','discard_steps','snapshot_stride'):
            _positive(row[key], integer=True)
        if not reg[eid]['config']['episode_length'] < row['extended_steps'] or row['discard_steps'] >= row['extended_steps']:
            raise ValueError('extended horizon must exceed benchmark and discard interval')
        lo, hi = row['seconds_per_step_scenario']
        _positive(lo); _positive(hi)
        if lo > hi: raise ValueError('inverted timing scenario')
    if seen != {e for e, i in reg.items() if i['ndims'] == 2}:
        raise ValueError('matrix must cover every registered 2D variant')
    if set(m['deferred_3d']) != {e for e, i in reg.items() if i['ndims'] == 3}:
        raise ValueError('matrix must explicitly defer every 3D variant')
    labels = set()
    for rep in m['replicates']:
        if set(rep) != {'label','seed','randomize'} or type(rep['randomize']) is not bool:
            raise ValueError('invalid replicate')
        if type(rep['seed']) is not int or rep['seed'] < 0:
            raise ValueError('invalid seed')
        label = rep['label']
        if not label or not all(c.isalnum() or c == '-' for c in label) or label in labels:
            raise ValueError('unsafe or duplicate replicate label')
        labels.add(label)
    deterministic = [r['seed'] for r in m['replicates'] if not r['randomize']]
    randomized = [r['seed'] for r in m['replicates'] if r['randomize']]
    if len(deterministic) < 2 or len(set(deterministic)) != 1 or len(set(randomized)) < 3:
        raise ValueError('require repeated deterministic seed and at least three randomized seeds')
    for key in ('max_wall_hours','max_output_gib','minimum_free_gib','max_gpu_allocated_gib','timing_margin'):
        _positive(m['budget'][key])
    if m['budget']['timing_margin'] < 1: raise ValueError('timing margin must be >= 1')
    return m


def runs(matrix):
    reg = registrations()
    for row in matrix['environments']:
        item = reg[row['env_id']]
        for protocol in matrix['protocols']:
            steps = item['config']['episode_length'] if protocol == 'benchmark' else row['extended_steps']
            for rep in matrix['replicates']:
                yield {**row, **rep, 'protocol':protocol, 'steps':steps, 'mode':matrix['mode'],
                       'discard_steps':0 if protocol == 'benchmark' else row['discard_steps'],
                       'run_id':f"{row['env_id']}__{protocol}__{rep['label']}"}


def estimate(matrix):
    reg = registrations()
    lo = hi = storage = steps = count = 0
    for run in runs(matrix):
        n = run['steps']; count += 1; steps += n
        lo += n * run['seconds_per_step_scenario'][0]
        hi += n * run['seconds_per_step_scenario'][1]
        # Include reset snapshot, uncompressed NPZ headers, and ample scalar/provenance allowance.
        storage += (n // run['snapshot_stride'] + 1) * (reg[run['env_id']]['snapshot_bytes_float32'] + 4096)
        storage += n * 8192 + 1024 * 1024
    margin = matrix['budget']['timing_margin']
    return {'runs':count, 'environment_steps':steps, 'wall_hours_scenario':[lo*margin/3600,hi*margin/3600],
            'output_gib_estimate':storage/2**30, 'timing_measured':False,
            'excluded':['initial datasets','GPU solver workspaces','reset/compilation time beyond timing margin'],
            'note':'Not a hardware guarantee. Runtime caps abort at step boundaries; no automatic retries.'}
