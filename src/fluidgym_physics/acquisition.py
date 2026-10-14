"""Explicit acquisition of required files from the official dataset, never from the runner."""
from __future__ import annotations

import hashlib
import math
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from .characterization import digest, load_matrix, write_json
from .runner import input_report
from .upstream import verify_upstream

OFFICIAL_REPO = 'safe-autonomous-systems/fluidgym-data'
OFFICIAL_ENDPOINT = 'https://huggingface.co'


def _git_blob_digest(path):
    h = hashlib.sha1(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _verify_file(path, remote):
    if path.stat().st_size != remote.size:
        raise ValueError(f'official file size mismatch: {remote.rfilename}')
    sha = digest(path)
    if remote.lfs is not None:
        if sha != remote.lfs.sha256:
            raise ValueError(f'official SHA-256 mismatch: {remote.rfilename}')
    elif not remote.blob_id or _git_blob_digest(path) != remote.blob_id:
        raise ValueError(f'official Git blob mismatch: {remote.rfilename}')
    return sha


def fetch_inputs(matrix_path, data_root, output, revision=None, max_download_gib=20):
    """Download only missing/empty required files, pin one remote commit, preserve existing data."""
    verify_upstream()
    matrix = load_matrix(matrix_path)
    root, output = Path(data_root).expanduser().resolve(), Path(output).resolve()
    if not math.isfinite(max_download_gib) or max_download_gib <= 0:
        raise ValueError('max-download-gib must be finite and positive')
    if output.exists(): raise FileExistsError('acquisition output already exists; choose a new directory')
    # Restrict the source to the official service, even if HF_ENDPOINT is set in the shell.
    if os.environ.get('HF_ENDPOINT', OFFICIAL_ENDPOINT).rstrip('/') != OFFICIAL_ENDPOINT:
        raise ValueError('unset nonofficial HF_ENDPOINT before acquiring official inputs')
    from huggingface_hub import HfApi, hf_hub_download
    before = input_report(matrix, root)
    required = []
    for domain_id in before['datasets']:
        required.append(f'{domain_id}/domain_statistics.json')
        for idx in range(10):
            required.extend(f'{domain_id}/{idx}/{matrix["mode"]}.{ext}' for ext in ('json','npz'))
    info = HfApi(endpoint=OFFICIAL_ENDPOINT).dataset_info(
        OFFICIAL_REPO, revision=revision, files_metadata=True)
    if not info.sha or len(info.sha) != 40:
        raise ValueError('official dataset did not return a full commit SHA')
    remote = {s.rfilename:s for s in info.siblings}
    absent = [r for r in required if f'initial_domains/{r}' not in remote]
    if absent: raise ValueError('required files absent from official dataset revision: '+', '.join(absent))
    missing = {r for d in before['datasets'].values() for r in d['missing_files']}
    total = 0
    retained = {}
    for rel in required:
        meta = remote[f'initial_domains/{rel}']
        if meta.size is None or meta.size <= 0:
            raise ValueError(f'unknown/empty official file size: {rel}')
        target = root/rel
        if not target.resolve().is_relative_to(root):
            raise ValueError(f'input path escapes data root: {target}')
        if target.is_symlink(): raise ValueError(f'symlink input requires manual inspection: {target}')
        if rel in missing:
            if target.exists():
                raise FileExistsError(f'empty input is preserved; move it aside and retry: {target}')
            total += meta.size
        else:
            # Do not mix an existing dataset with a different remote revision silently.
            retained[rel] = _verify_file(target, meta)
    if total > max_download_gib*2**30:
        raise ValueError(f'download requires {total/2**30:.3f} GiB, above {max_download_gib} GiB cap')
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 2*total + 2*2**30:
        raise ValueError('insufficient disk: reserve twice download size plus 2 GiB')
    output.mkdir(parents=True)
    write_json(output/'request.json', {
        'schema_version':1, 'matrix_sha256':digest(matrix_path), 'data_root':str(root),
        'repo_id':OFFICIAL_REPO, 'revision':info.sha, 'download_files':sorted(missing),
        'download_bytes':total, 'retained_sha256':retained, 'max_download_gib':max_download_gib,
        'note':'Existing nonempty files verified against this revision and never overwritten.'})
    print(f'Official dataset {info.sha}: {len(missing)} files, {total/2**30:.3f} GiB', file=sys.stderr, flush=True)
    acquired = {}
    try:
        # Stage on the target filesystem so publication is atomic. No partial data files are exposed.
        with tempfile.TemporaryDirectory(prefix='.fluidgym-fetch-', dir=root) as stage:
            for number, rel in enumerate(sorted(missing), 1):
                remote_name = f'initial_domains/{rel}'
                staged = Path(hf_hub_download(
                    repo_id=OFFICIAL_REPO, repo_type='dataset', revision=info.sha,
                    filename=remote_name, local_dir=stage, endpoint=OFFICIAL_ENDPOINT))
                sha = _verify_file(staged, remote[remote_name])
                target = root/rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink(): raise ValueError(f'input became a symlink: {target}')
                if target.exists():
                    # Even an empty pre-existing file is preserved; user can inspect/remove it explicitly.
                    # A concurrent writer that already published the right contents is safe to retain.
                    if target.stat().st_size == 0:
                        raise FileExistsError(f'empty file blocks publication; move it aside and retry: {target}')
                    if digest(target) != sha: raise FileExistsError(f'input changed during acquisition: {target}')
                else:
                    os.link(staged, target)  # Exclusive, atomic; no replacement of existing files.
                acquired[rel] = {'sha256':sha, 'bytes':target.stat().st_size}
                print(f'[{number}/{len(missing)}] {rel}', file=sys.stderr, flush=True)
        after = input_report(matrix,root)
        if after['missing_file_count']: raise ValueError('required inputs still missing after acquisition')
        result = {'status':'complete','repo_id':OFFICIAL_REPO,'revision':info.sha,
                  'data_root':str(root),'download_bytes':total,'downloaded':acquired,
                  'retained_sha256':retained,'missing_file_count':after['missing_file_count']}
        write_json(output/'status.json',result)
        return {k:v for k,v in result.items() if k not in ('downloaded','retained_sha256')}
    except BaseException as exc:
        write_json(output/'status.json',{'status':'failed','revision':info.sha,'downloaded':acquired,
                                        'error_type':type(exc).__name__,'error':str(exc)})
        raise


def acquisition_provenance(output, matrix_path, data_root):
    output = Path(output)
    request = json.loads((output/'request.json').read_text())
    status = json.loads((output/'status.json').read_text())
    if (status.get('status') != 'complete'
            or status['repo_id'] != OFFICIAL_REPO or status['revision'] != request['revision']
            or status['data_root'] != str(Path(data_root).resolve())):
        raise ValueError('acquisition record does not match the matrix/data root')
    hashes = {**status['retained_sha256'], **{p:v['sha256'] for p,v in status['downloaded'].items()}}
    matrix = load_matrix(matrix_path)
    report = input_report(matrix, data_root)
    required = {f'{domain}/domain_statistics.json' for domain in report['datasets']}
    required.update(f'{domain}/{idx}/{matrix["mode"]}.{ext}'
                    for domain in report['datasets'] for idx in range(10) for ext in ('json','npz'))
    if not required <= hashes.keys():
        raise ValueError('acquisition record does not cover all inputs required by this matrix')
    for rel in sorted(required):
        sha = hashes[rel]
        path = Path(data_root)/rel
        if not path.resolve().is_relative_to(Path(data_root).resolve()) or digest(path) != sha:
            raise ValueError(f'acquired input changed: {rel}')
    return {'repo_id':OFFICIAL_REPO,'revision':status['revision'],
            'acquisition_source_matrix_sha256':request['matrix_sha256'],
            'target_matrix_sha256':digest(matrix_path),
            'acquisition_request_sha256':digest(output/'request.json'),
            'acquisition_status_sha256':digest(output/'status.json')}
