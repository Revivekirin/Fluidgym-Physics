"""Sequential nominal experiments. No downloads, regeneration, or solver-source edits."""
from __future__ import annotations

import contextlib
import importlib.metadata
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from .characterization import digest, estimate, load_matrix, runs, write_json
from .diagnostics import finite, physical_metrics, scalar
from .errors import MissingInitialDomainError, UpstreamIntegrityError
from .inventory import registrations
from .execution import capture_signals, emit_progress, termination_reason
from .provenance import collect_platform
from .upstream import REPO_ROOT, UPSTREAM_DIR, verify_upstream


def _input_paths(root, item, mode, randomize):
    directory = Path(root) / item['initial_domain_id']
    files = [directory / 'domain_statistics.json']
    for idx in range(10) if randomize else [0]:
        files.extend(directory / str(idx) / f'{mode}.{ext}' for ext in ('json','npz'))
        optional = directory / str(idx) / f'{mode}_uncontrolled_episode.csv'
        if optional.exists(): files.append(optional)
    return files


def local_inputs(root, item, mode, randomize):
    files = _input_paths(root, item, mode, randomize)
    missing = [str(p) for p in files if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise MissingInitialDomainError('Missing local inputs; no download/generation allowed: '+', '.join(missing))
    return files


def input_report(matrix, root):
    """Whole-matrix local availability report; no CUDA imports or network access."""
    root = Path(root).expanduser().resolve()
    reg = registrations()
    datasets = {}
    for row in matrix['environments']:
        item = reg[row['env_id']]
        domain_id = item['initial_domain_id']
        if domain_id not in datasets:
            paths = _input_paths(root, item, matrix['mode'], True)
            missing = [str(p.relative_to(root)) for p in paths
                       if not p.is_file() or p.stat().st_size == 0]
            datasets[domain_id] = {
                'env_ids': [], 'missing_files': missing,
                'present_bytes': sum(p.stat().st_size for p in paths if p.is_file()),
                'availability': 'missing_or_empty' if missing else 'present_not_validated',
            }
        datasets[domain_id]['env_ids'].append(row['env_id'])
    return {'schema_version': 1, 'data_root': str(root), 'mode': matrix['mode'],
            'dataset_count': len(datasets),
            'missing_file_count': sum(len(d['missing_files']) for d in datasets.values()),
            'datasets': datasets,
            'note': 'Availability only. Preflight checks archive structure and hashes. No downloads or CFD.'}


def validate_input_file(path):
    """Validate JSON/NPZ structure without constructing an environment or moving data to CUDA."""
    import zipfile
    path = Path(path)
    if path.suffix != '.json':
        return
    data = json.loads(path.read_text())
    if path.name == 'domain_statistics.json':
        if not {'velocity_magnitude','pressure'} <= data.keys():
            raise ValueError(f'incomplete reference statistics: {path}')
        required = {'mean','min','max','p5','p25','p50','p75','p95'}
        for key, stats in data.items():
            if not isinstance(stats, dict) or not required <= stats.keys():
                raise ValueError(f'incomplete statistics for {key}: {path}')
            finite(list(stats.values()), str(path))
        return
    if not {'spatialDims','viscosity','blocks','data_info'} <= data.keys() or not data['blocks']:
        raise ValueError(f'incomplete domain metadata: {path}')
    with zipfile.ZipFile(path.with_suffix('.npz')) as archive:
        names = set(archive.namelist())
        expected = {f'{i}.npy' for i in range(len(data['data_info']))}
        if names != expected:
            raise ValueError(f'domain tensor index/archive mismatch: {path}')
        bad = archive.testzip()
        if bad is not None: raise ValueError(f'corrupt compressed tensor: {bad}')
    for block in data['blocks']:
        if not {'velocity','pressure','boundaries'} <= block.keys():
            raise ValueError(f'incomplete domain block: {path}')


def _installed_upstream():
    spec = importlib.util.find_spec('fluidgym')
    expected = (UPSTREAM_DIR / 'src/fluidgym/__init__.py').resolve()
    actual = Path(spec.origin).resolve() if spec is not None and spec.origin else None
    if actual != expected:
        raise UpstreamIntegrityError(
            'FluidGym import does not resolve to the verified pinned checkout. '
            f'Python: {sys.executable}; actual: {actual or "not found"}; expected: {expected}. '
            'From the Fluidgym-Physics repository root, using the active CUDA environment, run: '
            'MAX_JOBS=1 python -m pip install --no-build-isolation --no-deps -e ./third_party/fluidgym. '
            'This builds the CUDA extension using the existing torch/toolchain. '
            'If the path still differs, check PYTHONPATH and whether the CLI uses the same Python.'
        )


def preflight(matrix, data_root=None):
    upstream = verify_upstream()
    if not (3,10) <= sys.version_info[:2] < (3,14):
        raise ValueError('Pinned FluidGym requires Python >=3.10,<3.14 for runtime')
    _installed_upstream()
    from .runtime import _require_cuda
    torch = _require_cuda()
    if not torch.__version__.split('+')[0].startswith('2.9.'):
        raise ValueError('UPSTREAM.lock requires torch 2.9.*')
    import fluidgym
    if data_root is not None:
        root = Path(data_root).expanduser().resolve()
        if root.name != 'initial_domains':
            raise ValueError('--data-root must end in initial_domains (upstream data layout)')
        fluidgym.config.update('local_data_path', str(root.parent))
    reg = registrations()
    report = input_report(matrix, fluidgym.config.initial_domains_path)
    if report['missing_file_count']:
        summary = '; '.join(f"{name}: {len(d['missing_files'])} missing/empty files"
                            for name, d in report['datasets'].items() if d['missing_files'])
        raise MissingInitialDomainError(
            f"Missing inputs across the full matrix at {report['data_root']}: {summary}. "
            'No download/generation performed. Use input-report --matrix <matrix.json> '
            '--data-root <initial_domains-directory> for the complete file list.'
        )
    paths = set()
    for row in matrix['environments']:
        paths.update(local_inputs(fluidgym.config.initial_domains_path, reg[row['env_id']], matrix['mode'], True))
    for p in sorted(paths):
        validate_input_file(p)
    manifest = {str(p.resolve()):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(paths)}
    # Preserve exact implementation files, including uncommitted modifications.
    code = {str(p.relative_to(REPO_ROOT)):digest(p) for base in ('src','experiments')
            for p in (REPO_ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    props = torch.cuda.get_device_properties(torch.cuda.current_device())
    packages = {}
    for name in ('torch','numpy','gymnasium','fluidgym','fluidgym-physics'):
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = 'not-installed-as-distribution'
    try:
        driver = subprocess.check_output(['nvidia-smi','--query-gpu=name,uuid,driver_version,memory.total',
                                          '--format=csv,noheader'], text=True).strip()
    except (OSError, subprocess.CalledProcessError): driver = None
    # Exact compiled backend is part of provenance, not just its Python package version.
    from fluidgym.simulation.extensions import PISOtorch
    binary = Path(PISOtorch.__file__).resolve()
    return {'status':'passed','data_root':str(Path(fluidgym.config.initial_domains_path).resolve()),
            'upstream':upstream,'platform':collect_platform(),'packages':packages,
            'gpu':{'name':props.name,'total_memory':props.total_memory,'cuda':torch.version.cuda,
                   'driver_query':driver}, 'backend':{'path':str(binary),'sha256':digest(binary)},
            'input_manifest':manifest,'implementation_sha256':code,'source_inventory':reg,
            'installed_packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata.get('Name')},
            'torch_determinism':{'algorithms_enabled':torch.are_deterministic_algorithms_enabled(),
                                 'cudnn_deterministic':torch.backends.cudnn.deterministic,
                                 'cudnn_benchmark':torch.backends.cudnn.benchmark},
            'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO_ROOT,text=True).strip(),
            'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=REPO_ROOT,text=True)}


@contextlib.contextmanager
def solver_failure_guard():
    from fluidgym.simulation import Simulation
    original = Simulation.single_step
    def checked(sim, *args, **kwargs):
        result = original(sim, *args, **kwargs)
        if not result:
            raise RuntimeError('upstream Simulation.single_step returned failure')
        return result
    with patch.object(Simulation, 'single_step', checked):
        yield


def effective(env, item):
    """Read actual solver rather than env.time_passed (which is only step*interval)."""
    c = item['config']
    result = {'dt':scalar(env.dt),'step_length':scalar(env.step_length),
              'n_sim_steps':int(env.n_sim_steps),'env_cfl':scalar(env._adaptive_cfl),
              'solver_cfl':scalar(env._sim.adaptive_CFL),
              'domain_viscosity':scalar(env._domain.viscosity),
              'render_shape':list(env.render_shape[:item['ndims']]),
              'block_velocity_shapes':[list(b.velocity.shape) for b in env._domain.getBlocks()],
              'solver_pressure_tol':scalar(env._sim.pressure_tol),
              'solver_residuals':None,'fallback_event_counts':None}
    expected_viscosity = ((c['prandtl_number']/c['rayleigh_number'])**0.5 if item['family']=='rbc'
                          else (0.3 if item['family']=='airfoil' else 1.0)/c['reynolds_number'])
    for key in ('dt','step_length'):
        if not math.isclose(result[key], c[key], rel_tol=1e-6): raise ValueError(f'effective {key} mismatch')
    for value in (result['domain_viscosity'], scalar(env._kinematic_viscosity if item['family']=='rbc' else env._viscosity)):
        if not math.isclose(value, expected_viscosity, rel_tol=1e-5):
            raise ValueError('loaded/force viscosity inconsistent with nominal parameters')
    if not math.isclose(result['solver_cfl'], c['adaptive_cfl'], rel_tol=1e-6):
        raise ValueError('effective solver CFL differs from registry')
    if item['family']=='rbc':
        result['scalar_diffusivity'] = scalar(env._domain.passiveScalarViscosity)
        if not math.isclose(result['scalar_diffusivity'], (c['rayleigh_number']*c['prandtl_number'])**-0.5, rel_tol=1e-5):
            raise ValueError('loaded thermal diffusivity mismatch')
    result['reference'] = ({'nusselt':scalar(env.nu_ref)} if item['family']=='rbc' else
                           {'lift_drag_ratio':scalar(env._cl_cd_ref)} if item['family']=='airfoil' else
                           {'drag':scalar(env._cd_ref)})
    if result['render_shape'] != item['render_shape_xyz']:
        raise ValueError('source/runtime output shape mismatch')
    for block in env._domain.getBlocks():
        if item['family']=='rbc' and block.hasPassiveScalarViscosity():
            import torch
            expected_scalar = (c['rayleigh_number']*c['prandtl_number'])**-0.5
            if not torch.allclose(block.passiveScalarViscosity, torch.full_like(block.passiveScalarViscosity, expected_scalar),rtol=1e-5,atol=1e-10):
                raise ValueError('block scalar diffusivity overrides nominal value')
        if block.hasViscosity():
            import torch
            if not torch.allclose(block.viscosity, torch.full_like(block.viscosity,expected_viscosity),rtol=1e-5,atol=1e-10):
                raise ValueError('block viscosity overrides nominal value')
    return result


def check_native_fields(env, family):
    for i, block in enumerate(env._domain.getBlocks()):
        finite(block.velocity, f'block{i}.velocity')
        finite(block.pressure, f'block{i}.pressure')
        if family == 'rbc': finite(block.passiveScalar, f'block{i}.temperature')


def snapshot(env, item, path):
    import numpy as np
    arrays = {name:getattr(env, f'get_{name}')().detach().cpu().numpy()
              for name in item['snapshot_fields']}
    finite(arrays, 'snapshot')
    with Path(path).open('xb') as stream:
        np.savez(stream, **arrays)
    return {k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in arrays.items()}


def validate_step(previous, current, expected_delta, terminated, truncated, final,
                  *, clock_dtype=None, solver_steps=None):
    if not math.isfinite(current) or current <= previous:
        raise ValueError('solver time failed to advance')
    tolerance = max(2e-4 * abs(expected_delta), 1e-6)
    rounding_bound = 0.0
    if clock_dtype is not None:
        import numpy as np
        dtype = np.dtype(clock_dtype)
        if dtype.kind != 'f' or solver_steps is None or solver_steps <= 0:
            raise ValueError('invalid solver clock dtype or step count')
        # Upstream end_step adds one native scalar per solver step. Each addition
        # rounds by at most half an ULP; use the largest endpoint spacing.
        spacing = max(abs(float(np.spacing(dtype.type(previous)))),
                      abs(float(np.spacing(dtype.type(current)))))
        rounding_bound = solver_steps * spacing / 2
        if rounding_bound >= expected_delta / (2 * solver_steps):
            raise ValueError('solver clock resolution insufficient to validate integration interval')
        tolerance += rounding_bound
    if abs(current-previous-expected_delta) > tolerance:
        raise ValueError(
            'solver time increment differs from nominal integration interval: '
            f'previous={previous!r}, current={current!r}, '
            f'actual_delta={current-previous!r}, expected_delta={expected_delta!r}, '
            f'tolerance={tolerance!r}, rounding_bound={rounding_bound!r}, '
            f'clock_dtype={clock_dtype}, solver_steps={solver_steps}')
    if terminated or bool(truncated) != bool(final):
        raise ValueError('unexpected termination/truncation; trajectories are never reset/concatenated')
    return tolerance


def _tree_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def check_budget(root, budget, started, output_bytes=None):
    if time.monotonic()-started > budget['max_wall_hours']*3600:
        raise RuntimeError('campaign wall-time cap reached')
    if (output_bytes if output_bytes is not None else _tree_bytes(root)) > budget['max_output_gib']*2**30:
        raise RuntimeError('campaign storage cap reached')
    if shutil.disk_usage(root).free < budget['minimum_free_gib']*2**30:
        raise RuntimeError('disk reserve reached')


def execute_run(run, item, directory, provenance, campaign, budget, started):
    import fluidgym
    import torch
    directory.mkdir()  # Independent immutable namespace; retries need a new campaign.
    write_json(directory/'request.json', run)
    env = None
    completed = 0
    begin = time.monotonic()
    last_output = None
    emit_progress(directory,run,completed,begin,'starting')
    try:
        # Recheck checksums immediately before use; files may have changed since campaign preflight.
        for path in local_inputs(fluidgym.config.initial_domains_path,item,run['mode'],run['randomize']):
            if digest(path) != provenance['input_manifest'][str(path.resolve())]['sha256']:
                raise ValueError(f'input changed after preflight: {path}')
        kwargs = {'randomize_initial_state':run['randomize']}
        with solver_failure_guard(), torch.no_grad(), patch(
                'fluidgym.util.data_utils.download_initial_domains',
                side_effect=MissingInitialDomainError('implicit download blocked by runner')):
            env = fluidgym.make(run['env_id'], **kwargs)
            if env.initial_domain_id != item['initial_domain_id']:
                raise ValueError('source/runtime initial-domain identity mismatch')
            getattr(env, run['mode'])()
            selected = []
            original_load = env._load_initial_domain
            def tracked_load(*args, **kw):
                selected.append({'idx':kw.get('idx'), 'mode':str(kw.get('mode'))})
                return original_load(*args, **kw)
            with patch.object(env, '_load_initial_domain', tracked_load):
                obs, info = env.reset(seed=run['seed'], randomize=run['randomize'])
            # Airfoil randomization uses episode_length. Preserve official reset semantics,
            # then extend only the task termination counter (no solver/physical setting).
            nominal_horizon = item['config']['episode_length']
            if env.episode_length != nominal_horizon:
                raise ValueError('constructor horizon differs from official benchmark')
            if run['protocol'] == 'extended':
                env._episode_length = run['steps']
            finite(obs,'reset observations')
            check_native_fields(env,item['family'])
            eff = effective(env,item)
            torch.cuda.synchronize()
            t0 = scalar(env._sim.total_time)
            emit_progress(directory,run,completed,begin,'reset_complete')
            tprev = t0
            solver_step_prev = int(env._sim.total_step)
            shape = snapshot(env,item,directory/'fields_000000.npz')
            write_json(directory/'provenance.json', {'schema_version':1,'execution_level':'runtime_cuda',
                       'campaign_provenance':'../provenance.json','effective':eff,'initial_domains':selected,
                       'solver_time_at_reset':t0,'snapshot_layout':shape,
                       'official_reset_horizon':nominal_horizon,'rollout_horizon':env.episode_length,
                       'observation_shapes':{k:list(v.shape) for k,v in obs.items()},
                       'action_shape':list(env.action_space.shape),
                       'horizon_extension':'_episode_length only, after official reset' if run['protocol']=='extended' else None,
                       'missing_measurements':['solver residual histories','fallback events','native divergence norm'],
                       'notes':['Native fields checked every env step; this is not a proof of numerical convergence.',
                                'Public fields are resampled; not native conservative snapshots.']})
            action = torch.zeros(env.action_space.shape,device=env.cuda_device,dtype=env._dtype)
            torch.cuda.reset_peak_memory_stats()
            baseline_bytes = _tree_bytes(campaign)
            with (directory/'trajectory.jsonl').open('x', buffering=1) as stream:
                for step in range(1,run['steps']+1):
                    check_budget(campaign,budget,started,baseline_bytes+stream.tell())
                    tick=time.monotonic()
                    obs,reward,term,trunc,info = env.step(action)
                    finite(obs,'observations'); finite(reward,'reward'); finite(info,'info')
                    check_native_fields(env,item['family'])
                    now=scalar(env._sim.total_time)
                    solver_steps = int(env._sim.total_step) - solver_step_prev
                    if solver_steps <= 0:
                        raise ValueError('solver step counter failed to advance')
                    clock_dtype = getattr(env._sim.total_time, 'dtype', None)
                    clock_tolerance = validate_step(
                        tprev,now,eff['dt']*eff['n_sim_steps'],term,trunc,step==run['steps'],
                        clock_dtype=clock_dtype, solver_steps=solver_steps)
                    metrics=physical_metrics(item['family'],info)
                    if item['family']=='rbc':
                        temperature=env._domain.getBlock(0).passiveScalar
                        from fluidgym.simulation.helpers import get_cell_size
                        block=env._domain.getBlock(0)
                        weights=get_cell_size(block).expand_as(temperature)
                        if not bool((weights>0).all()): raise ValueError('nonpositive cell volumes')
                        velocity=block.getVelocity(False)
                        metrics.update(temperature_min=scalar(temperature.min()),temperature_max=scalar(temperature.max()),
                            temperature_volume_mean=scalar((temperature*weights).sum()/weights.sum()),
                            kinetic_energy_volume_mean=scalar((0.5*(velocity*velocity).sum(dim=1,keepdim=True)*weights).sum()/weights.sum()))
                    torch.cuda.synchronize()
                    peak=torch.cuda.max_memory_allocated()
                    if peak > budget['max_gpu_allocated_gib']*2**30: raise RuntimeError('GPU allocation cap reached')
                    record={'step':step,'solver_time':now,'elapsed_solver_time':now-t0,
                            'solver_time_increment':now-tprev,
                            'solver_time_increment_tolerance':clock_tolerance,
                            'solver_clock_dtype':str(clock_dtype),
                            'solver_steps_this_env_step':solver_steps,
                            'reported_env_time':scalar(env.time_passed),'solver_total_step':int(env._sim.total_step),
                            'wall_seconds':time.monotonic()-tick,'reward':scalar(reward),
                            'gpu_peak_allocated_bytes':peak,**metrics}
                    stream.write(json.dumps(record,allow_nan=False)+'\n')
                    completed=step; tprev=now; solver_step_prev=int(env._sim.total_step)
                    last_output = str(directory/'trajectory.jsonl')
                    if step == 1 or step % 25 == 0 or step == run['steps']:
                        emit_progress(directory,run,completed,begin,'running',last_output)
                    if step % run['snapshot_stride']==0:
                        snapshot_path=directory/f'fields_{step:06d}.npz'
                        snapshot(env,item,snapshot_path)
                        baseline_bytes += snapshot_path.stat().st_size
            check_budget(campaign,budget,started)
        files={p.name:digest(p) for p in directory.iterdir() if p.is_file()}
        write_json(directory/'status.json',{'status':'complete','steps':completed,'wall_seconds':time.monotonic()-begin,
                                          'sha256':files})
    except BaseException as exc:
        write_json(directory/'status.json',{'status':'failed','steps':completed,'error_type':type(exc).__name__,
                                          'error':str(exc),'wall_seconds':time.monotonic()-begin,
                                          'termination_reason':termination_reason(exc), 'last_successful_output':last_output})
        raise
    finally:
        if env is not None:
            close=getattr(env,'close',None)
            if close is not None: close()


@capture_signals()
def run_matrix(matrix_path, output, reviewed_sha256=None, data_root=None, approval_path=None):
    path, output = Path(matrix_path), Path(output)
    m=load_matrix(path)
    approval = None
    if approval_path is not None:
        from .review import check_approval
        approval = check_approval(approval_path, path)
        reviewed_sha256 = approval['reviewed_matrix_sha256']
        if data_root is None: data_root = approval['data_root']
    if digest(path)!=reviewed_sha256 or m['review_status']!='reviewed':
        raise ValueError('Review full matrix/budget, set review_status=reviewed and supply exact matrix SHA-256')
    budget=m['budget']; est=estimate(m)
    if est['wall_hours_scenario'][1] > budget['max_wall_hours'] or est['output_gib_estimate'] > budget['max_output_gib']:
        raise ValueError('planning estimate exceeds campaign caps; review budget first')
    if output.exists(): raise FileExistsError('campaign output already exists; no resume/overwrite')
    provenance=preflight(m, data_root=data_root)  # Entire matrix checked before the first reset.
    if approval is not None:
        check_approval(approval_path,path,provenance)
    output.mkdir(parents=True)
    started=time.monotonic()
    write_json(output/'matrix.json',m)
    if approval is not None: write_json(output/'approval.json',approval)
    write_json(output/'provenance.json',{**provenance,'matrix_sha256':digest(path),'estimate':est})
    try:
        reg=registrations()
        for run in runs(m):
            check_budget(output,budget,started)
            execute_run(run,reg[run['env_id']],output/run['run_id'],provenance,output,budget,started)
        verify_upstream()
        write_json(output/'status.json',{'status':'complete','wall_seconds':time.monotonic()-started,
                   'sha256':{p.name:digest(p) for p in output.iterdir() if p.is_file()}})
    except BaseException as exc:
        write_json(output/'status.json',{'status':'failed','error':str(exc),'error_type':type(exc).__name__,
                                          'termination_reason':termination_reason(exc),'wall_seconds':time.monotonic()-started})
        raise
    return {'output':str(output),'status':'complete'}
