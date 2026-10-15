import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from fluidgym_physics.characterization import digest, estimate, load_matrix, runs, write_json
from fluidgym_physics.diagnostics import cylinder_spectrum, physical_metrics, summarize
from fluidgym_physics.inventory import inventory, registrations
from fluidgym_physics.runner import local_inputs, run_matrix, validate_step
from fluidgym_physics.errors import MissingInitialDomainError

MATRIX = Path(__file__).resolve().parents[1] / 'experiments/characterization.v1.json'


def test_inventory_covers_registry_and_snapshot():
    current = inventory()
    saved = json.loads((MATRIX.parents[1]/'docs/environment_inventory.v1.json').read_text())
    assert current == saved
    reg = current['environments']
    assert len(reg) == 39
    assert sum(i['ndims']==2 for i in reg.values()) == 15
    assert reg['RBC2D-wide-hard-v0']['native_cells_source_estimate'] == 192*61
    assert reg['TCFLarge3D-both-hard-v0']['native_cells_source_estimate'] == 128*64*128
    assert reg['Airfoil2D-easy-v0']['config']['reynolds_number'] == 1000


def test_matrix_distinct_protocols_and_replicates():
    matrix=load_matrix(MATRIX)
    expanded=list(runs(matrix))
    assert len(expanded)==150
    assert len({r['run_id'] for r in expanded})==150
    assert all(r['discard_steps']==0 for r in expanded if r['protocol']=='benchmark')
    assert all(r['steps']>r['discard_steps']>0 for r in expanded if r['protocol']=='extended')
    assert estimate(matrix)['environment_steps']==156900
    assert estimate(matrix)['timing_measured'] is False


@pytest.mark.parametrize('mutation', [
    lambda m: m['environments'][0].update(extended_steps=80),
    lambda m: m['environments'][0].update(snapshot_stride=0),
    lambda m: m['environments'][0].update(overrides={'reynolds_number':200}),
    lambda m: m['replicates'][0].update(label='../bad'),
    lambda m: m.update(action='random'),
    lambda m: m['environments'].pop(),
    lambda m: m['budget'].update(max_wall_hours=float('nan')),
])
def test_invalid_matrix_fails(tmp_path, mutation):
    matrix=json.loads(MATRIX.read_text()); mutation(matrix)
    path=tmp_path/'matrix.json'; path.write_text(json.dumps(matrix))
    with pytest.raises(ValueError): load_matrix(path)


def test_review_gate_before_cuda_or_output(tmp_path):
    with pytest.raises(ValueError, match='Review full matrix'):
        run_matrix(MATRIX,tmp_path/'campaign',digest(MATRIX))
    assert not (tmp_path/'campaign').exists()


def test_partial_dataset_rejected(tmp_path):
    item=registrations()['CylinderJet2D-easy-v0']
    directory=tmp_path/item['initial_domain_id']; directory.mkdir()
    (directory/'unrelated').write_text('not a domain')
    with pytest.raises(MissingInitialDomainError): local_inputs(tmp_path,item,'test',False)
    (directory/'0').mkdir()
    for p in ('domain_statistics.json','0/test.json','0/test.npz'):
        (directory/p).write_text('present')
    assert len(local_inputs(tmp_path,item,'test',False))==3
    with pytest.raises(MissingInitialDomainError): local_inputs(tmp_path,item,'test',True)


def test_no_overwrite(tmp_path):
    p=tmp_path/'data.json'; write_json(p,{'a':1})
    with pytest.raises(FileExistsError): write_json(p,{'a':2})
    assert json.loads(p.read_text())=={'a':1}


@pytest.mark.parametrize('current,term,trunc,final',[(0,False,False,False),(float('nan'),False,False,False),
    (0.1,False,False,False),(0.25,True,False,False),(0.25,False,True,False)])
def test_invalid_solver_progress(current,term,trunc,final):
    with pytest.raises(ValueError): validate_step(0,current,0.25,term,trunc,final)


def test_float32_clock_rounding_over_full_extended_horizon():
    clock = np.float32(1)
    for step in range(1, 2401):
        previous = float(clock)
        for _ in range(25):
            clock += np.float32(.01)
        if step == 253:
            assert float(clock) == 64.24531555175781
        if step == 254:
            with pytest.raises(ValueError, match='increment differs'):
                validate_step(previous, float(clock), .25, False, False, False)
        validate_step(previous, float(clock), .25, False, step == 2400, step == 2400,
                      clock_dtype=clock.dtype, solver_steps=25)


@pytest.mark.parametrize('start,count', [(64.,24), (64.,26), (600.,24), (600.,26)])
def test_rounding_allowance_rejects_missing_or_extra_integration(start, count):
    clock = np.float32(start)
    for _ in range(count):
        clock += np.float32(.01)
    with pytest.raises(ValueError, match='increment differs'):
        validate_step(start, float(clock), .25, False, False, False,
                      clock_dtype=clock.dtype, solver_steps=count)


def test_clock_resolution_guard():
    with pytest.raises(ValueError, match='resolution insufficient'):
        validate_step(1e6, 1e6+.25, .25, False, False, False,
                      clock_dtype=np.dtype('float32'), solver_steps=25)


def test_metrics_are_family_specific():
    assert physical_metrics('rbc',{'nusselt':2}) == {'nusselt':2}
    with pytest.raises(KeyError): physical_metrics('rbc',{'drag':2})
    assert physical_metrics('airfoil',{'drag':0,'lift':1})['lift_to_drag'] is None
    with pytest.raises(ValueError): physical_metrics('cylinder',{'drag':float('nan'),'lift':1})


def test_spectrum_known_frequency_and_short_record_withholding():
    t=np.arange(2000)*0.25
    x=np.sin(2*np.pi*0.2*t)
    result=cylinder_spectrum(t,x)
    assert result['candidate_strouhal_D1_U1']==pytest.approx(.2,abs=result['resolution'])
    assert sum(result['psd'])*result['resolution']==pytest.approx(.5,rel=.01)
    assert cylinder_spectrum(t[:80],x[:80])['candidate_strouhal_D1_U1'] is None
    assert cylinder_spectrum(t,np.ones(len(t)))['candidate_strouhal_D1_U1'] is None
    with pytest.raises(ValueError): summarize([0,1,1,2],[1,2,3,4])
    with pytest.raises(ValueError): summarize([0,1,2,4],[1,2,3,4])


def test_guard_catches_ignored_failure_and_restores(monkeypatch):
    import sys
    from fluidgym_physics.runner import solver_failure_guard
    class Simulation:
        def single_step(self): return False
    original=Simulation.single_step
    monkeypatch.setitem(sys.modules,'fluidgym.simulation',SimpleNamespace(Simulation=Simulation))
    with solver_failure_guard():
        with pytest.raises(RuntimeError,match='returned failure'): Simulation().single_step()
    assert Simulation.single_step is original


def test_analysis_preserves_runs_and_excludes_failures(tmp_path):
    from fluidgym_physics.analysis import analyze
    campaign=tmp_path/'campaign'; campaign.mkdir()
    for label,shift in [('repeat-a',0),('repeat-b',.01)]:
        d=campaign/label; d.mkdir()
        run={'env_id':'CylinderJet2D-easy-v0','protocol':'extended','randomize':False,
             'seed':0,'steps':300,'discard_steps':20}
        write_json(d/'request.json',run)
        with (d/'trajectory.jsonl').open('w') as stream:
            for i in range(1,301):
                stream.write(json.dumps({'step':i,'elapsed_solver_time':i*.25,'drag':3+shift,
                                         'lift':float(np.sin(i*.25*2*np.pi*.2))+shift})+'\n')
        write_json(d/'status.json',{'status':'complete','sha256':{p.name:digest(p) for p in d.iterdir()}})
    (campaign/'interrupted').mkdir()
    output=tmp_path/'analysis'
    assert analyze(campaign,output)['analyzed']==2
    report=json.loads((output/'analysis.json').read_text())
    assert len(report['excluded'])==1
    assert report['comparisons'][0]['max_absolute_difference']['drag']==pytest.approx(.01)
    assert (output/'aggregate.png').exists()
    with pytest.raises(FileExistsError): analyze(campaign,output)
    (campaign/'repeat-a'/'trajectory.jsonl').write_text('corrupt')
    with pytest.raises(ValueError,match='corrupt artifact'): analyze(campaign,tmp_path/'new-analysis')

@pytest.mark.parametrize('fail_at', [None, 2])
def test_runner_one_continuous_trajectory_and_failure_artifact(tmp_path, monkeypatch, fail_at):
    import contextlib
    import sys
    import time
    import fluidgym_physics.runner as runner
    item=registrations()['CylinderJet2D-easy-v0']
    item=copy.deepcopy(item)
    data=tmp_path/'inputs'/item['initial_domain_id']; (data/'0').mkdir(parents=True)
    for p in ('domain_statistics.json','0/test.json','0/test.npz'): (data/p).write_text('fixture')
    files=local_inputs(tmp_path/'inputs',item,'test',False)
    provenance={'input_manifest':{str(p.resolve()):{'sha256':digest(p)} for p in files}}
    class Env:
        action_space=SimpleNamespace(shape=(1,))
        cuda_device='fake'; _dtype='float32'
        initial_domain_id=item['initial_domain_id']
        _domain=SimpleNamespace(getBlocks=lambda:[SimpleNamespace(velocity=np.ones((1,2,3,3)),pressure=np.ones((1,1,3,3)))])
        def __init__(self): self._sim=SimpleNamespace(total_time=0,total_step=0); self.resets=0; self.closed=False; self._episode_length=80
        @property
        def episode_length(self): return self._episode_length
        def test(self): pass
        def _load_initial_domain(self, **kw): pass
        def reset(self,seed,randomize):
            assert self.episode_length==80
            self.resets+=1; self._load_initial_domain(idx=0,mode='test'); return {'velocity':np.ones(2)},{}
        @property
        def time_passed(self): return self._sim.total_time
        def step(self,action):
            self._sim.total_step+=1
            if self._sim.total_step==fail_at: raise RuntimeError('synthetic solver failure')
            self._sim.total_time+=.25
            return {'velocity':np.ones(2)},1,False,self._sim.total_step==4,{'drag':3.,'lift':.1}
        def close(self): self.closed=True
    env=Env(); kwargs_seen=[]
    def make(eid,**kw): kwargs_seen.append(kw); return env
    monkeypatch.setitem(sys.modules,'fluidgym',SimpleNamespace(make=make,config=SimpleNamespace(initial_domains_path=tmp_path/'inputs')))
    monkeypatch.setitem(sys.modules,'fluidgym.util',SimpleNamespace())
    monkeypatch.setitem(sys.modules,'fluidgym.util.data_utils',SimpleNamespace(download_initial_domains=lambda:None))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(no_grad=contextlib.nullcontext,
        zeros=lambda *a,**k:np.zeros(1),cuda=SimpleNamespace(synchronize=lambda:None,reset_peak_memory_stats=lambda:None,max_memory_allocated=lambda:0)))
    monkeypatch.setattr(runner,'solver_failure_guard',contextlib.nullcontext)
    monkeypatch.setattr(runner,'effective',lambda *a:{'dt':.01,'n_sim_steps':25})
    monkeypatch.setattr(runner,'snapshot',lambda env,item,path:write_json(path,{'synthetic':True}))
    run={'env_id':'CylinderJet2D-easy-v0','mode':'test','protocol':'extended','steps':4,'randomize':False,
         'seed':0,'snapshot_stride':2}
    budget={'max_wall_hours':1,'max_output_gib':1,'minimum_free_gib':.001,'max_gpu_allocated_gib':1}
    directory=tmp_path/'run'
    if fail_at:
        with pytest.raises(RuntimeError,match='synthetic solver failure'):
            runner.execute_run(run,item,directory,provenance,tmp_path,budget,time.monotonic())
    else: runner.execute_run(run,item,directory,provenance,tmp_path,budget,time.monotonic())
    assert env.resets==1 and env.closed
    assert kwargs_seen==[{'randomize_initial_state':False}]
    assert env.episode_length==4
    status=json.loads((directory/'status.json').read_text())
    assert status['status']==('failed' if fail_at else 'complete')
    assert status['steps']==(1 if fail_at else 4)


def test_effective_values_catch_loaded_physics_mismatch():
    from fluidgym_physics.runner import effective
    item=registrations()['CylinderJet2D-easy-v0']
    block=SimpleNamespace(velocity=np.zeros((1,2,3,3)),hasViscosity=lambda:False)
    domain=SimpleNamespace(viscosity=np.array([.01]),getBlocks=lambda:[block])
    env=SimpleNamespace(dt=.01,step_length=.25,n_sim_steps=25,_adaptive_cfl=.8,
                        _sim=SimpleNamespace(adaptive_CFL=.8,pressure_tol=1e-5),
                        _domain=domain,_viscosity=np.array([.01]),_cd_ref=3.0,
                        render_shape=tuple(item['render_shape_xyz']))
    assert effective(env,item)['reference']=={'drag':3.0}
    domain.viscosity=np.array([.02])
    with pytest.raises(ValueError,match='viscosity inconsistent'): effective(env,item)


def test_preflight_detects_broken_archive_and_statistics(tmp_path):
    from fluidgym_physics.runner import validate_input_file
    p=tmp_path/'test.json'
    p.write_text(json.dumps({'spatialDims':2,'viscosity':'0','blocks':[{'velocity':'0','pressure':'0','boundaries':[]}],
                             'data_info':{'0':{'device':'cuda:0'}}}))
    np.savez(tmp_path/'test.npz',bad=np.ones(2))
    with pytest.raises(ValueError,match='index/archive mismatch'): validate_input_file(p)
    np.savez(tmp_path/'test.npz',**{'0':np.ones(2)})
    validate_input_file(p)
    p=tmp_path/'domain_statistics.json';p.write_text('{}')
    with pytest.raises(ValueError,match='incomplete reference'): validate_input_file(p)


@pytest.mark.parametrize('args', [['verify-upstream'], ['inspect-config'], ['inventory'], ['plan','--matrix',str(MATRIX)]])
def test_cpu_cli_commands(args,capsys):
    from fluidgym_physics.cli import main
    assert main(args)==0
    assert isinstance(json.loads(capsys.readouterr().out),dict)


@pytest.mark.parametrize('origin', [None, '/different/checkout/fluidgym/__init__.py'])
def test_import_guard_explains_actual_path_and_repair(monkeypatch, origin):
    import fluidgym_physics.runner as runner
    from fluidgym_physics.errors import UpstreamIntegrityError
    monkeypatch.setattr(runner.importlib.util, 'find_spec',
                        lambda name: None if origin is None else SimpleNamespace(origin=origin))
    with pytest.raises(UpstreamIntegrityError) as exc:
        runner._installed_upstream()
    message = str(exc.value)
    assert f'actual: {origin or "not found"}' in message
    assert 'expected:' in message and 'Python:' in message
    assert '--no-build-isolation --no-deps -e ./third_party/fluidgym' in message


def test_import_guard_accepts_pinned_checkout(monkeypatch):
    import fluidgym_physics.runner as runner
    monkeypatch.setattr(runner.importlib.util, 'find_spec', lambda name: SimpleNamespace(
        origin=str(runner.UPSTREAM_DIR/'src/fluidgym/__init__.py')))
    runner._installed_upstream()


def test_input_report_covers_all_datasets_and_deduplicates(tmp_path):
    from fluidgym_physics.runner import input_report
    matrix = load_matrix(MATRIX)
    report = input_report(matrix, tmp_path)
    assert report['dataset_count'] == 12
    assert report['missing_file_count'] == 252
    dataset = report['datasets']['cylinder_2D_Re100_Res24']
    assert len(dataset['env_ids']) == 2
    for name in dataset['missing_files']:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('present, not yet validated')
    report = input_report(matrix, tmp_path)
    assert report['missing_file_count'] == 231
    assert report['datasets']['cylinder_2D_Re100_Res24']['availability'] == 'present_not_validated'
    (tmp_path/'cylinder_2D_Re100_Res24/0/test.npz').write_bytes(b'')
    assert input_report(matrix,tmp_path)['missing_file_count'] == 232


def test_input_report_cli(tmp_path,capsys):
    from fluidgym_physics.cli import main
    assert main(['input-report','--matrix',str(MATRIX),'--data-root',str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['missing_file_count'] == 252
