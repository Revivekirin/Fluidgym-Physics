"""Exercise the actual bash gate; replace only CUDA execution/analysis processes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from fluidgym_physics.characterization import digest, load_matrix, write_json
from fluidgym_physics.review import primary_draft, approve_matrix

ROOT=Path(__file__).resolve().parents[1]


def setup(tmp_path):
    (tmp_path/'experiments').mkdir()
    full=tmp_path/'experiments/characterization.v1.json'
    full.write_bytes((ROOT/'experiments/characterization.v1.json').read_bytes())
    prep=tmp_path/'prep'; (prep/'primary').mkdir(parents=True)
    draft=prep/'primary/matrix.json'; write_json(draft,primary_draft(load_matrix(full)))
    data=tmp_path/'input'; data.write_text('unchanged')
    source={'repo_id':'safe-autonomous-systems/fluidgym-data','revision':'a8c00235a814828441a0c5638e6f803ef62bfa31'}
    for name,matrix in [('full-preflight.json',full),('primary-preflight.json',draft)]:
        write_json(prep/name,{'status':'passed','matrix_sha256':digest(matrix),
                            'input_manifest':{str(data):{'sha256':digest(data)}},
                            'data_root':str(tmp_path/'initial_domains'),'dataset_source':source})
    approve_matrix(draft,prep/'primary-preflight.json',prep/'approved-primary',True)
    bin=tmp_path/'bin'; bin.mkdir()
    python=bin/'python'
    python.write_text(f'''#!{sys.executable}
import os,sys,json
if sys.argv[1:]==['-']:
    os.execv({sys.executable!r},[{sys.executable!r},'-'])
with open(os.environ['CALL_LOG'],'a') as f:
    f.write(json.dumps(sys.argv[1:])+'\\n')
if 'fluidgym_physics.execution' in sys.argv:
    raise SystemExit(int(os.environ.get('FAKE_RUN_EXIT','0')))
''')
    python.chmod(0o755)
    gpu=bin/'nvidia-smi'; gpu.write_text('#!/bin/sh\nexit 0\n'); gpu.chmod(0o755)
    env={**os.environ,'PATH':str(bin)+os.pathsep+os.environ['PATH'],
         'CALL_LOG':str(tmp_path/'calls.jsonl')}
    env.pop('FG_EXEC',None)
    return prep,data,env


def invoke(tmp_path,prep,env):
    return subprocess.run(['bash',str(ROOT/'experiments/run-approved-primary.sh'),str(prep)],
                          cwd=tmp_path,env=env,text=True,capture_output=True,timeout=30)


def test_launcher_checks_then_creates_unique_output(tmp_path):
    prep,_,env=setup(tmp_path)
    for _ in range(2):
        result=invoke(tmp_path,prep,env)
        assert result.returncode==0,result.stderr
        assert 'checks passed' in result.stdout
    calls=[json.loads(s) for s in (tmp_path/'calls.jsonl').read_text().splitlines()]
    assert len(calls)==4
    outputs=[]
    for call in calls[::2]:
        assert 'fluidgym_physics.execution' in call
        output=Path(call[call.index('--output')+1])
        assert output.is_dir()
        assert str(prep/'approved-primary/approval.json') in call
        outputs.append(output)
    assert outputs[0]!=outputs[1]


def test_launcher_rejects_changed_input_before_process_launch(tmp_path):
    prep,data,env=setup(tmp_path)
    data.write_text('changed')
    result=invoke(tmp_path,prep,env)
    assert result.returncode!=0
    assert not (tmp_path/'calls.jsonl').exists()
    assert not list(prep.glob('execution-*'))


def test_launcher_does_not_analyze_failed_campaign(tmp_path):
    prep,_,env=setup(tmp_path)
    env['FAKE_RUN_EXIT']='1'
    result=invoke(tmp_path,prep,env)
    assert result.returncode==1
    calls=(tmp_path/'calls.jsonl').read_text().splitlines()
    assert len(calls)==1
