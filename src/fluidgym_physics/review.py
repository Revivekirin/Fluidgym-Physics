"""Explicit matrix approval bound to a successful preflight and immutable input manifest."""
from __future__ import annotations

import hashlib
import copy
import json
from pathlib import Path

from .characterization import PRIMARY_ENV_IDS, digest, estimate, load_matrix, write_json
from .upstream import verify_upstream


def object_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def approve_matrix(matrix_path, preflight_path, output, accept_budget=False):
    verify_upstream()
    if not accept_budget:
        raise ValueError('Review the plan and preflight first; --accept-budget explicitly approves this matrix')
    matrix=load_matrix(matrix_path)
    report=json.loads(Path(preflight_path).read_text())
    if report.get('status')!='passed' or report.get('matrix_sha256')!=digest(matrix_path):
        raise ValueError('preflight must have passed for this exact matrix file')
    if not report.get('input_manifest') or not report.get('data_root'):
        raise ValueError('preflight lacks input manifest/data root; rerun preflight with --output')
    est=estimate(matrix)
    if (est['wall_hours_scenario'][1] > matrix['budget']['max_wall_hours'] or
            est['output_gib_estimate'] > matrix['budget']['max_output_gib']):
        raise ValueError('planning estimate exceeds caps; revise matrix and rerun preflight')
    for path, item in report['input_manifest'].items():
        if digest(path)!=item['sha256']: raise ValueError(f'input changed after preflight: {path}')
    output=Path(output)
    if output.exists(): raise FileExistsError('review output already exists; choose a new directory')
    output.mkdir(parents=True)
    source_sha=digest(matrix_path)
    matrix['review_status']='reviewed'
    write_json(output/'matrix.json',matrix)
    approval={'schema_version':1,'status':'approved','source_matrix_sha256':source_sha,
              'reviewed_matrix_sha256':digest(output/'matrix.json'),
              'preflight_sha256':digest(preflight_path),
              'input_manifest_sha256':object_digest(report['input_manifest']),
              'data_root':report['data_root'],'estimate':est,'budget':matrix['budget'],
              'dataset_source':report.get('dataset_source'),
              'acceptance':'Explicit approve-matrix --accept-budget invocation; no campaign launched.'}
    write_json(output/'approval.json',approval)
    return {'status':'approved','matrix':str(output/'matrix.json'),
            'approval':str(output/'approval.json'),'estimate':est}


def check_approval(approval_path, matrix_path, provenance=None):
    approval=json.loads(Path(approval_path).read_text())
    if (approval.get('schema_version')!=1 or approval.get('status')!='approved' or
            approval.get('reviewed_matrix_sha256')!=digest(matrix_path)):
        raise ValueError('approval does not match this reviewed matrix')
    if provenance is not None:
        if (approval['data_root']!=provenance['data_root'] or
                approval['input_manifest_sha256']!=object_digest(provenance['input_manifest'])):
            raise ValueError('data root/input manifest changed since approval; rerun preflight and review')
    return approval


def primary_draft(full_matrix):
    """Pure planning transformation; never grants approval or runs CFD."""
    if full_matrix['schema_version'] != 1:
        raise ValueError('primary preparation requires the original complete 15-variant matrix')
    matrix = copy.deepcopy(full_matrix)
    matrix.update(schema_version=2, matrix_id='primary-cylinderjet2d-rbc2d-v1',
                  scope='primary_cylinderjet2d_rbc2d', review_status='draft_not_authorized')
    matrix['deferred_2d'] = [r['env_id'] for r in full_matrix['environments']
                             if r['env_id'] not in PRIMARY_ENV_IDS]
    by_id = {r['env_id']:r for r in matrix['environments']}
    matrix['environments'] = [by_id[e] for e in PRIMARY_ENV_IDS]
    matrix['budget']['max_wall_hours'] = 72
    matrix['budget']['max_output_gib'] = 20
    matrix['budget']['note'] = (
        'Primary six-environment proposal. Uncalibrated timing assumptions retained from full matrix; '
        '50% time margin, 72-hour wall cap and 20-GiB output cap proposed for review. '
        'Dataset storage excluded. No CFD authorization.')
    return matrix


def prepare_primary(matrix_path, preflight_path, output):
    verify_upstream()
    full = load_matrix(matrix_path)
    report = json.loads(Path(preflight_path).read_text())
    if report.get('status') != 'passed' or report.get('matrix_sha256') != digest(matrix_path):
        raise ValueError('successful full-matrix preflight required before preparing the primary matrix')
    if not report.get('input_manifest'):
        raise ValueError('full preflight input manifest missing')
    for path, item in report['input_manifest'].items():
        if digest(path) != item['sha256']:
            raise ValueError(f'input changed after full preflight: {path}')
    matrix = primary_draft(full)
    output = Path(output)
    if output.exists(): raise FileExistsError('primary output exists; choose a new directory')
    output.mkdir(parents=True)
    write_json(output/'matrix.json',matrix)
    load_matrix(output/'matrix.json')
    result = {'status':'draft_not_authorized','source_matrix_sha256':digest(matrix_path),
              'full_preflight_sha256':digest(preflight_path),
              'primary_matrix_sha256':digest(output/'matrix.json'),
              'env_ids':list(PRIMARY_ENV_IDS),'future_expansion_2d':matrix['deferred_2d'],
              'estimate':estimate(matrix),'budget':matrix['budget'],
              'dataset_source':report.get('dataset_source')}
    write_json(output/'preparation.json',result)
    return {'matrix':str(output/'matrix.json'), **result}
