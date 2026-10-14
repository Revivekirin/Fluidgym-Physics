import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fluidgym_physics.acquisition import fetch_inputs, acquisition_provenance, _verify_file
from fluidgym_physics.characterization import digest, load_matrix, write_json
from fluidgym_physics.runner import input_report
from fluidgym_physics.review import approve_matrix, check_approval, object_digest

MATRIX=Path(__file__).resolve().parents[1]/'experiments/characterization.v1.json'
SHA='a'*40


@pytest.fixture
def hub(tmp_path,monkeypatch):
    root=tmp_path/'initial_domains'
    report=input_report(load_matrix(MATRIX),root)
    payloads={f'initial_domains/{r}':r.encode() for d in report['datasets'].values() for r in d['missing_files']}
    siblings=[]
    for name,data in payloads.items():
        siblings.append(SimpleNamespace(rfilename=name,size=len(data),lfs=None,
            blob_id=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()))
    calls=[]
    class API:
        def __init__(self,endpoint): assert endpoint=='https://huggingface.co'
        def dataset_info(self,repo,revision,files_metadata):
            assert repo=='safe-autonomous-systems/fluidgym-data' and files_metadata
            return SimpleNamespace(sha=SHA,siblings=siblings)
    def download(**kw):
        assert kw['revision']==SHA and kw['repo_type']=='dataset'
        calls.append(kw)
        path=Path(kw['local_dir'])/kw['filename'];path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(payloads[kw['filename']]);return str(path)
    monkeypatch.delenv('HF_ENDPOINT',raising=False)
    monkeypatch.setitem(sys.modules,'huggingface_hub',SimpleNamespace(HfApi=API,hf_hub_download=download))
    return root,payloads,siblings,calls


def test_fetch_pins_revision_preserves_existing_and_records_provenance(tmp_path,hub):
    root,payloads,_,calls=hub
    name=next(iter(payloads)); existing=root/name.removeprefix('initial_domains/')
    existing.parent.mkdir(parents=True);existing.write_bytes(payloads[name])
    before=existing.stat().st_mtime_ns
    out=tmp_path/'acquisition'
    result=fetch_inputs(MATRIX,root,out)
    assert result['status']=='complete' and result['missing_file_count']==0
    assert len(calls)==251 and existing.stat().st_mtime_ns==before
    source=acquisition_provenance(out,MATRIX,root)
    assert source['revision']==SHA
    assert input_report(load_matrix(MATRIX),root)['missing_file_count']==0
    assert not list(root.glob('.fluidgym-fetch-*'))
    with pytest.raises(FileExistsError): fetch_inputs(MATRIX,root,out)
    existing.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'): acquisition_provenance(out,MATRIX,root)


@pytest.mark.parametrize('case',['missing_remote','budget','existing_mismatch','empty_existing'])
def test_fetch_fails_before_any_transfer(tmp_path,hub,case):
    root,payloads,siblings,calls=hub
    kwargs={}
    if case=='missing_remote': siblings.pop()
    if case=='budget': kwargs['max_download_gib']=1e-12
    if case in ('existing_mismatch','empty_existing'):
        path=root/next(iter(payloads)).removeprefix('initial_domains/')
        path.parent.mkdir(parents=True);path.write_bytes(b'wrong' if case=='existing_mismatch' else b'')
    with pytest.raises((ValueError,FileExistsError)):
        fetch_inputs(MATRIX,root,tmp_path/'acquisition',**kwargs)
    assert not calls and not (tmp_path/'acquisition').exists()


def test_download_failure_preserves_failure_record_and_is_retryable(tmp_path,hub,monkeypatch):
    root,payloads,siblings,calls=hub
    module=sys.modules['huggingface_hub'];original=module.hf_hub_download
    def fails(**kw):
        if len(calls)==2: raise OSError('network interruption')
        return original(**kw)
    monkeypatch.setattr(module,'hf_hub_download',fails)
    out=tmp_path/'failed'
    with pytest.raises(OSError,match='network interruption'): fetch_inputs(MATRIX,root,out)
    status=json.loads((out/'status.json').read_text())
    assert status['status']=='failed' and len(status['downloaded'])==2
    monkeypatch.setattr(module,'hf_hub_download',original)
    result=fetch_inputs(MATRIX,root,tmp_path/'retry',revision=SHA)
    assert result['status']=='complete' and len(calls)==252


def test_lfs_hash_checked(tmp_path):
    path=tmp_path/'tensor';path.write_bytes(b'abc')
    meta=SimpleNamespace(size=3,rfilename='tensor',lfs=SimpleNamespace(sha256=digest(path)))
    assert _verify_file(path,meta)==digest(path)
    path.write_bytes(b'abd')
    with pytest.raises(ValueError,match='SHA-256 mismatch'): _verify_file(path,meta)


def _report(tmp_path):
    data=tmp_path/'input';data.write_text('fixed')
    report={'status':'passed','matrix_sha256':digest(MATRIX),'data_root':str(tmp_path),
            'input_manifest':{str(data):{'bytes':data.stat().st_size,'sha256':digest(data)}}}
    file=tmp_path/'preflight.json';write_json(file,report)
    return file,report,data


def test_review_requires_explicit_acceptance_and_valid_preflight(tmp_path):
    file,report,data=_report(tmp_path)
    with pytest.raises(ValueError,match='accept-budget'): approve_matrix(MATRIX,file,tmp_path/'reviewed')
    report['status']='failed';file.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='preflight'): approve_matrix(MATRIX,file,tmp_path/'reviewed',True)
    report['status']='passed';file.write_text(json.dumps(report));data.write_text('changed')
    with pytest.raises(ValueError,match='input changed'): approve_matrix(MATRIX,file,tmp_path/'reviewed',True)
    assert not (tmp_path/'reviewed').exists()


def test_approval_binds_exact_matrix_and_inputs(tmp_path):
    file,report,data=_report(tmp_path)
    out=tmp_path/'reviewed';approve_matrix(MATRIX,file,out,True)
    assert load_matrix(out/'matrix.json')['review_status']=='reviewed'
    assert load_matrix(MATRIX)['review_status']=='draft_not_authorized'
    check_approval(out/'approval.json',out/'matrix.json',report)
    with pytest.raises(FileExistsError): approve_matrix(MATRIX,file,out,True)
    report['input_manifest'][str(data)]['sha256']='0'*64
    with pytest.raises(ValueError,match='manifest changed'): check_approval(out/'approval.json',out/'matrix.json',report)
    with (out/'matrix.json').open('a') as stream: stream.write(' ')
    with pytest.raises(ValueError,match='does not match'): check_approval(out/'approval.json',out/'matrix.json')


def test_plan_output_and_cli_preflight_artifact(tmp_path,monkeypatch,capsys):
    from fluidgym_physics.cli import main
    import fluidgym_physics.runner as runner
    plan=tmp_path/'plan.json'
    assert main(['plan','--matrix',str(MATRIX),'--output',str(plan)])==0
    assert json.loads(plan.read_text())['runs']==150
    assert main(['plan','--matrix',str(MATRIX),'--output',str(plan)])==2
    _,report,_=_report(tmp_path)
    monkeypatch.setattr(runner,'preflight',lambda matrix,data_root=None:report)
    out=tmp_path/'new-preflight.json'
    assert main(['preflight','--matrix',str(MATRIX),'--data-root',str(tmp_path),'--output',str(out)])==0
    assert json.loads(out.read_text())['status']=='passed'


def test_primary_prepared_only_after_full_preflight_remains_draft(tmp_path):
    from fluidgym_physics.review import prepare_primary
    from fluidgym_physics.characterization import PRIMARY_ENV_IDS, estimate, runs
    file,report,data=_report(tmp_path)
    source_hash=digest(MATRIX)
    out=tmp_path/'primary'
    report['status']='failed';file.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='full-matrix preflight'): prepare_primary(MATRIX,file,out)
    assert not out.exists()
    report['status']='passed';file.write_text(json.dumps(report))
    result=prepare_primary(MATRIX,file,out)
    primary=load_matrix(out/'matrix.json')
    assert primary['review_status']==result['status']=='draft_not_authorized'
    assert [r['env_id'] for r in primary['environments']]==list(PRIMARY_ENV_IDS)
    assert len(primary['deferred_2d'])==9 and len(primary['deferred_3d'])==24
    assert primary['protocols']==load_matrix(MATRIX)['protocols']
    assert primary['replicates']==load_matrix(MATRIX)['replicates']
    assert len(list(runs(primary)))==60
    assert estimate(primary)['environment_steps']==58200
    assert estimate(primary)['wall_hours_scenario']==[1.2125,48.5]
    assert estimate(primary)['output_gib_estimate']==pytest.approx(2.3920691013)
    assert digest(MATRIX)==source_hash
    assert not (out/'approval.json').exists()
    with pytest.raises(FileExistsError): prepare_primary(MATRIX,file,out)


@pytest.mark.parametrize('mutation',[
    lambda m:m['environments'].pop(),
    lambda m:m['environments'][3].update(env_id='RBC2D-wide-easy-v0'),
    lambda m:m['deferred_2d'].pop(),
    lambda m:m.update(scope='cylinder_only'),
])
def test_primary_cannot_silently_drop_rbc_or_change_scope(tmp_path,mutation):
    from fluidgym_physics.review import primary_draft
    matrix=primary_draft(load_matrix(MATRIX));mutation(matrix)
    path=tmp_path/'primary.json';write_json(path,matrix)
    with pytest.raises(ValueError): load_matrix(path)


def test_full_acquisition_can_provenance_primary_subset(tmp_path,hub):
    from fluidgym_physics.review import primary_draft
    root,_,_,_=hub
    out=tmp_path/'acquisition';fetch_inputs(MATRIX,root,out)
    primary=tmp_path/'primary.json';write_json(primary,primary_draft(load_matrix(MATRIX)))
    source=acquisition_provenance(out,primary,root)
    assert source['revision']==SHA
    assert source['acquisition_source_matrix_sha256']==digest(MATRIX)
    assert source['target_matrix_sha256']==digest(primary)


def test_run_rejects_changed_inputs_after_approval_before_cfd(tmp_path,monkeypatch):
    import fluidgym_physics.runner as runner
    file,report,data=_report(tmp_path)
    reviewed=tmp_path/'reviewed';approve_matrix(MATRIX,file,reviewed,True)
    report['input_manifest'][str(data)]['sha256']='f'*64
    monkeypatch.setattr(runner,'preflight',lambda matrix,data_root=None:report)
    monkeypatch.setattr(runner,'execute_run',lambda *a,**kw:pytest.fail('CFD must not be invoked'))
    output=tmp_path/'campaign'
    with pytest.raises(ValueError,match='manifest changed'):
        runner.run_matrix(reviewed/'matrix.json',output,approval_path=reviewed/'approval.json')
    assert not output.exists()


def test_prepare_primary_cli_creates_only_draft_artifacts(tmp_path,capsys):
    from fluidgym_physics.cli import main
    file,_,_=_report(tmp_path)
    out=tmp_path/'primary'
    assert main(['prepare-primary','--matrix',str(MATRIX),'--preflight',str(file),'--output',str(out)])==0
    assert json.loads(capsys.readouterr().out)['status']=='draft_not_authorized'
    assert sorted(p.name for p in out.iterdir())==['matrix.json','preparation.json']
