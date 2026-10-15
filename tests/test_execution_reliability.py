import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np
import pytest

from fluidgym_physics.time_axis import validated_axis, PIN


def clock_records(n=2400):
    clock=np.float32(1)
    records=[]
    for i in range(1,n+1):
        for _ in range(25): clock=np.float32(clock+np.float32(.01))
        records.append({'step':i,'solver_time':float(clock),'elapsed_solver_time':float(clock)-1,
                        'solver_clock_dtype':'float32','solver_steps_this_env_step':25,'solver_total_step':1+i*25})
    return records


def axis(records):
    return validated_axis(records,{'env_id':'CylinderJet2D-easy-v0'},
                          {'effective':{'dt':.01,'n_sim_steps':25},'solver_time_at_reset':1.},
                          {'upstream':{'commit':PIN}})


def test_full_horizon_replay_and_uniform_spectrum():
    from fluidgym_physics.diagnostics import cylinder_spectrum
    records=clock_records()
    times,info=axis(records)
    assert info['validated_uniform']
    assert records[-1]['solver_time']==601.275390625
    assert times[-1]==pytest.approx(599.9999865889549)
    assert info['max_recorded_clock_difference'] > .27
    x=np.sin(2*np.pi*.2*np.array(times))
    spectrum=cylinder_spectrum(times[400:],x[400:])
    assert spectrum['candidate_strouhal_D1_U1']==pytest.approx(.2,abs=spectrum['resolution'])


@pytest.mark.parametrize('field,value', [('solver_steps_this_env_step',26),('solver_time',9),
                                          ('solver_clock_dtype','float64'),('solver_total_step',999)])
def test_time_axis_rejects_insufficient_or_variable_evidence(field,value):
    records=clock_records(10); records[5][field]=value
    times,info=axis(records)
    assert not info['validated_uniform']
    assert times==[r['elapsed_solver_time'] for r in records]


def launch(tmp_path, code, wall=10, grace=.3):
    p=subprocess.Popen([sys.executable,'-m','fluidgym_physics.execution','--output',str(tmp_path),
                        '--wall-seconds',str(wall),'--grace-seconds',str(grace),'--no-telemetry',
                        '--',sys.executable,'-u','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    return p


def finish(p,tmp_path):
    stdout,stderr=p.communicate(timeout=8)
    assert not stderr,stderr
    return json.loads((tmp_path/'execution-status.json').read_text())


@pytest.mark.parametrize('code,reason', [('pass','SUCCESS'),('raise RuntimeError("test")','NONZERO_EXIT_UNKNOWN'),
    ('import os,signal; os.kill(os.getpid(),signal.SIGKILL)','SIGKILL')])
def test_child_exits(tmp_path,code,reason):
    p=launch(tmp_path,code)
    assert finish(p,tmp_path)['reason']==reason


def test_timeout_escalation_and_recovery(tmp_path):
    run=tmp_path/'campaign/run'; run.mkdir(parents=True)
    (run/'request.json').write_text('{"seed":0}')
    (run/'trajectory.jsonl').write_text('{"step":1}\n{"step":')
    p=launch(tmp_path,'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)',wall=.7)
    result=finish(p,tmp_path)
    assert result['reason']=='TIMEOUT' and result['kill_sent']
    recovery=json.loads((tmp_path/'recovered-run-statuses.json').read_text())
    assert recovery['runs'][0]['completed_steps']==1
    assert not (run/'status.json').exists()


@pytest.mark.parametrize('sig', [signal.SIGINT,signal.SIGTERM])
def test_forward_signal_and_runner_terminal_status(tmp_path,sig):
    code='''import time
from pathlib import Path
from fluidgym_physics.execution import capture_signals, termination_reason
from fluidgym_physics.characterization import write_json
p=Path(%r)
with capture_signals():
    try:
        (p/'ready').touch()
        time.sleep(60)
    except BaseException as exc:
        write_json(p/'campaign/status.json',{'status':'failed','termination_reason':termination_reason(exc)})
        raise
''' % str(tmp_path)
    (tmp_path/'campaign').mkdir()
    p=launch(tmp_path,code)
    deadline=time.monotonic()+4
    while not (tmp_path/'ready').exists():
        assert p.poll() is None
        assert time.monotonic()<deadline
        time.sleep(.02)
    os.killpg(p.pid,sig)
    result=finish(p,tmp_path)
    assert result['reason']==signal.Signals(sig).name
    assert json.loads((tmp_path/'campaign/status.json').read_text())['termination_reason']==signal.Signals(sig).name


def test_classified_python_exception(tmp_path):
    (tmp_path/'campaign').mkdir()
    code='''from pathlib import Path
from fluidgym_physics.characterization import write_json
from fluidgym_physics.execution import termination_reason
try:
    raise ValueError('test')
except BaseException as exc:
    write_json(Path(%r)/'campaign/status.json',{'status':'failed','termination_reason':termination_reason(exc)})
    raise
''' % str(tmp_path)
    assert finish(launch(tmp_path,code),tmp_path)['reason']=='PYTHON_EXCEPTION'


def test_spawn_error_is_explicit(tmp_path):
    from fluidgym_physics.execution import supervise
    with pytest.raises(FileNotFoundError):
        supervise(['/nonexistent/fluidgym-command'],tmp_path,telemetry=False)
    assert json.loads((tmp_path/'execution-status.json').read_text())['reason']=='SUPERVISOR_EXCEPTION'


def test_rbc_native_uniform_and_adaptive_restriction():
    clock=np.float32(1)
    records=[]
    for i in range(1,1201):
        for _ in range(20): clock=np.float32(clock+np.float32(.05))
        records.append({'step':i,'solver_time':float(clock),'elapsed_solver_time':float(clock)-1,
                        'solver_clock_dtype':'float32','solver_steps_this_env_step':20,'solver_total_step':1+i*20})
    args=({'env_id':'RBC2D-easy-v0'}, {'effective':{'dt':.05,'n_sim_steps':20},'solver_time_at_reset':1.},
          {'upstream':{'commit':PIN}})
    assert validated_axis(records,*args)[1]['validated_uniform']
    records[10]['solver_steps_this_env_step']=21
    assert not validated_axis(records,*args)[1]['validated_uniform']


def test_offline_reanalysis_validates_axis_without_mutating_raw(tmp_path):
    from fluidgym_physics.analysis import analyze
    from fluidgym_physics.characterization import digest, write_json
    campaign=tmp_path/'campaign'; d=campaign/'run'; d.mkdir(parents=True)
    write_json(campaign/'provenance.json',{'upstream':{'commit':PIN}})
    write_json(d/'request.json',{'env_id':'CylinderJet2D-easy-v0','protocol':'extended','randomize':False,
                               'seed':0,'steps':300,'discard_steps':20})
    write_json(d/'provenance.json',{'effective':{'dt':.01,'n_sim_steps':25},'solver_time_at_reset':1.})
    records=clock_records(300)
    for r in records:
        r.update(drag=3.,lift=float(np.sin(2*np.pi*.2*r['step']*.25)))
    (d/'trajectory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    hashes={p.name:digest(p) for p in d.iterdir()}
    write_json(d/'status.json',{'status':'complete','sha256':hashes})
    analyze(campaign,tmp_path/'analysis')
    row=json.loads((tmp_path/'analysis/analysis.json').read_text())['trajectories'][0]
    assert row['time_axis']['validated_uniform']
    assert row['spectrum']['candidate_strouhal_D1_U1'] is not None
    assert digest(d/'trajectory.jsonl')==hashes['trajectory.jsonl']


def test_timeout_signals_whole_child_group(tmp_path):
    marker=tmp_path/'descendant-stopped'
    ready=tmp_path/'descendant-ready'
    child=f'''import signal,time
from pathlib import Path
def stop(s,f):
    Path({str(marker)!r}).touch()
    raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
Path({str(ready)!r}).touch()
time.sleep(60)
'''
    parent=f'''import subprocess,sys,time
from pathlib import Path
p=subprocess.Popen([sys.executable,'-c',{child!r}])
while not Path({str(ready)!r}).exists(): time.sleep(.01)
p.wait()
'''
    p=launch(tmp_path,parent,wall=2,grace=.5)
    result=finish(p,tmp_path)
    assert result['reason']=='TIMEOUT'
    assert marker.exists()
