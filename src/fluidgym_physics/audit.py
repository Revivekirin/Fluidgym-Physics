"""Read-only campaign integrity audit; never imports the CFD runtime."""
import argparse
import csv
import json
from pathlib import Path

from .characterization import digest, load_matrix, runs, write_json
from .review import check_approval, primary_draft
from .upstream import REPO_ROOT, verify_upstream


def verify_recorded_hashes(directory, status):
    errors=[]; count=0
    for name, sha in status.get('sha256',{}).items():
        path=Path(directory)/name
        if not path.is_file():
            errors.append(f'missing: {path}')
        else:
            if digest(path)!=sha: errors.append(f'hash mismatch: {path}')
            count+=1
    return count, errors


def validate_snapshot(path, layout):
    import numpy as np
    ranges={}
    with np.load(path,allow_pickle=False) as archive:
        if set(archive.files)!=set(layout): raise ValueError(f'field names: {path}')
        for key in archive.files:
            a=archive[key]; spec=layout[key]
            if list(a.shape)!=spec['shape'] or str(a.dtype)!=spec['dtype']:
                raise ValueError(f'field layout: {path}/{key}')
            if not np.isfinite(a).all(): raise ValueError(f'nonfinite field: {path}/{key}')
            ranges[key]=[float(a.min()),float(a.max())]
    return ranges


def audit(execution, output):
    import numpy as np
    import matplotlib.image as mpimg
    execution, output = Path(execution), Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    campaign = execution/'campaign'
    errors=[]; verified=0; snapshots=0; steps=0; rows=[]
    def check(condition, message):
        if not condition: errors.append(message)
    def read(path):
        return json.loads(path.read_text())
    def hashes(directory, status):
        nonlocal verified
        count, issues = verify_recorded_hashes(directory,status)
        verified+=count; errors.extend(issues)
    matrix=load_matrix(campaign/'matrix.json')
    expected=primary_draft(load_matrix(REPO_ROOT/'experiments/characterization.v1.json'))
    expected['review_status']='reviewed'
    check(matrix==expected, 'primary matrix differs from preserved protocol')
    provenance=read(campaign/'provenance.json')
    approval=check_approval(campaign/'approval.json',campaign/'matrix.json',provenance)
    upstream=verify_upstream()
    check(provenance['upstream']['commit']==upstream['commit'] and not provenance['upstream']['dirty'], 'upstream mismatch')
    check(provenance['upstream']['src_tree']==upstream['src_tree'], 'source tree mismatch')
    check(provenance['matrix_sha256']==digest(campaign/'matrix.json'),'provenance matrix mismatch')
    top=read(campaign/'status.json'); hashes(campaign,top)
    expected_runs={r['run_id']:r for r in runs(matrix)}
    actual={p.name for p in campaign.iterdir() if p.is_dir()}
    check(actual==set(expected_runs),'run directory set mismatch')
    for name, request in expected_runs.items():
        directory=campaign/name
        try:
            status=read(directory/'status.json'); hashes(directory,status)
            check(status['status']=='complete',f'noncomplete: {name}')
            check(read(directory/'request.json')==request,f'request mismatch: {name}')
            records=[json.loads(line) for line in (directory/'trajectory.jsonl').read_text().splitlines()]
            check(len(records)==request['steps']==status['steps'],f'step count mismatch: {name}')
            check([r['step'] for r in records]==list(range(1,request['steps']+1)),f'discontinuous: {name}')
            for r in records:
                check(all(np.isfinite(v) for v in r.values() if isinstance(v,(float,int))),f'nonfinite scalar: {name}/{r["step"]}')
            check(all(b['solver_time']>a['solver_time'] and b['solver_total_step']>a['solver_total_step'] for a,b in zip(records,records[1:])),f'nonmonotone solver: {name}')
            rp=read(directory/'provenance.json')
            wanted={f'fields_{i:06d}.npz' for i in range(0,request['steps']+1,request['snapshot_stride'])}
            check(set(status['sha256']) == wanted | {'request.json','provenance.json','progress.jsonl','trajectory.jsonl'},f'hash manifest coverage: {name}')
            check({p.name for p in directory.glob('fields_*.npz')}==wanted,f'snapshot cadence: {name}')
            ranges={}
            for filename in sorted(wanted):
                for key, (lo,hi) in validate_snapshot(directory/filename,rp['snapshot_layout']).items():
                    low,high=ranges.get(key,(float('inf'),float('-inf')))
                    ranges[key]=[min(low,lo),max(high,hi)]
                snapshots+=1
            steps+=len(records)
            rows.append({'run_id':name,'status':status['status'],'steps':len(records),
                         'wall_seconds':status['wall_seconds'],'initial_domains':rp['initial_domains'],
                         'field_ranges':ranges,'peak_torch_bytes':max(r['gpu_peak_allocated_bytes'] for r in records),
                         'final_solver_clock_error':records[-1]['elapsed_solver_time']-records[-1]['reported_env_time']})
        except (OSError,ValueError,KeyError) as exc:
            errors.append(f'{name}: {exc}')
    analysis=read(execution/'analysis/analysis.json')
    check({r['run_id'] for r in analysis['trajectories']}==set(expected_runs),'analysis run set mismatch')
    check(not analysis['excluded'],'analysis exclusions present')
    figures=list((execution/'analysis').glob('*.png'))
    for f in figures:
        try:
            a=mpimg.imread(f); check(a.size>0 and bool(np.isfinite(a).all()),f'bad image: {f}')
        except (OSError,ValueError) as exc: errors.append(f'bad image {f}: {exc}')
    figure_names={'aggregate.png'}|{name+'.png' for name in expected_runs}
    figure_names|={r['run_id']+'__spectrum.png' for r in analysis['trajectories'] if r.get('spectrum') and r['spectrum'].get('frequency')}
    check({p.name for p in figures}==figure_names,'figure set mismatch')
    termination=read(execution/'execution-status.json')
    check(termination['reason']=='SUCCESS' and termination['child_returncode']==0,'supervisor not successful')
    recovery=read(execution/'recovered-run-statuses.json')
    check({r['run_id'] for r in recovery['runs']}==set(expected_runs),'recovery set mismatch')
    for r in recovery['runs']:
        check(r['terminal']==read(campaign/r['run_id']/'status.json'),f'recovery mismatch {r["run_id"]}')
    with (execution/'gpu.csv').open() as f:
        gpu=[{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(f)]
    from datetime import datetime
    timestamps=[datetime.strptime(r['timestamp'],'%Y/%m/%d %H:%M:%S.%f').timestamp() for r in gpu]
    gaps=np.diff(timestamps)
    check(bool(np.all(gaps>0)), 'nonmonotone GPU timestamps')
    memory=[float(r['memory.used [MiB]'].split()[0]) for r in gpu]
    check(all(0 <= m <= float(r['memory.total [MiB]'].split()[0]) for m,r in zip(memory,gpu)), 'invalid GPU memory')
    check(all(0 <= float(r['utilization.gpu [%]'].split()[0]) <= 100 for r in gpu), 'invalid GPU utilization')
    check(len({r['uuid'] for r in gpu}) == 1 and gpu[0]['uuid'] in provenance['gpu']['driver_query'], 'GPU identity mismatch')
    available_inputs={p:item for p,item in provenance['input_manifest'].items() if Path(p).is_file()}
    for p,item in available_inputs.items(): check(digest(p)==item['sha256'],f'input mismatch {p}')
    local_code={name:('match' if digest(REPO_ROOT/name)==sha else 'differs') if (REPO_ROOT/name).is_file() else 'absent'
                for name,sha in provenance['implementation_sha256'].items()}
    report={'execution':str(execution.resolve()),'errors':errors,'verified_file_hashes':verified,
            'runs':rows,'steps':steps,'snapshots':snapshots,'figures_decoded':len(figures),
            'termination':termination,'dataset_source':approval['dataset_source'],
            'external_inputs_recorded':len(provenance['input_manifest']),'external_inputs_locally_rehashed':len(available_inputs),
            'external_limitations':['Original server dataset files, compiled CUDA binary and original approval preflight/acquisition files are not assumed present. Manifest binding verified; absent external bytes cannot be rehashed.'],
            'current_code_comparison':local_code,
            'gpu':{'samples':len(gpu),'peak_device_mib':max(memory),'min_device_mib':min(memory),
                   'max_gap_seconds':float(max(gaps)),'duration_seconds':timestamps[-1]-timestamps[0],
                   'monitor_status':read(execution/'telemetry-status.json'),
                   'monitor_error_text':(execution/'gpu-monitor-errors.log').read_text()},
            'artifact_sha256':{str(p.relative_to(execution)):digest(p) for p in execution.rglob('*') if p.is_file() and not p.name.startswith('fields_')}}
    write_json(output/'integrity.json',report)
    return report




def characterize(execution, output):
    """Supplemental descriptive comparisons and field plates from saved data only."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from .diagnostics import summarize
    from .time_axis import validated_axis
    execution,output=Path(execution),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    campaign=execution/'campaign'
    analysis=json.loads((execution/'analysis/analysis.json').read_text())
    prov=json.loads((campaign/'provenance.json').read_text())
    summary=[]; field_repeats=[]; phase=[]
    datasets={}
    colors={'repeat-a':'black','repeat-b':'grey','ic-1':'tab:red','ic-2':'tab:blue','ic-3':'tab:green'}
    for row in analysis['trajectories']:
        name=row['run_id']; d=campaign/name
        request=json.loads((d/'request.json').read_text()); rp=json.loads((d/'provenance.json').read_text())
        records=[json.loads(s) for s in (d/'trajectory.jsonl').read_text().splitlines()]
        t,axis=validated_axis(records,request,rp,prov); t=np.array(t)
        keys=list(row['metrics'])
        windows={}
        # Same physically recorded observables; no new classifier or regime metric.
        for key in keys:
            values=np.array([r[key] for r in records]); n=len(values)
            windows[key]={'early':summarize(t[:n//4],values[:n//4]),
                          'last_quarter':summarize(t[3*n//4:],values[3*n//4:])}
        summary.append({'run_id':name,'initial_domains':rp['initial_domains'],'time_axis':axis,
                        'windows':windows,'original_metrics':row['metrics']})
        datasets[name]=(t,records,request)
    eids=sorted({r['env_id'] for r in analysis['trajectories']})
    for eid in eids:
        keys=['drag','lift'] if eid.startswith('Cylinder') else ['nusselt','kinetic_energy_volume_mean','temperature_volume_mean']
        fig,axes=plt.subplots(len(keys),2,figsize=(12,3*len(keys)),squeeze=False)
        for j,protocol in enumerate(['benchmark','extended']):
            for label in ['repeat-a','ic-1','ic-2','ic-3']:
                name=f'{eid}__{protocol}__{label}'; t,records,request=datasets[name]
                for i,key in enumerate(keys):
                    axes[i,j].plot(t,[r[key] for r in records],lw=.65,color=colors[label],label=label)
                    axes[i,j].set_ylabel(key); axes[i,j].set_xlabel('elapsed time (validated schedule if available; otherwise solver clock)')
                if request['discard_steps']:
                    for ax in axes[:,j]: ax.axvline(t[request['discard_steps']-1],color='grey',ls='--',lw=.7)
            axes[0,j].set_title(protocol); axes[0,j].legend(fontsize=7)
            a=campaign/f'{eid}__{protocol}__repeat-a'; b=campaign/f'{eid}__{protocol}__repeat-b'
            differences={}
            for f in a.glob('fields_*.npz'):
                with np.load(f) as aa,np.load(b/f.name) as bb:
                    for key in aa.files: differences[key]=max(differences.get(key,0),float(np.max(np.abs(aa[key]-bb[key]))))
            field_repeats.append({'env_id':eid,'protocol':protocol,'max_absolute_array_difference':differences})
        fig.suptitle(eid);fig.tight_layout();fig.savefig(output/f'{eid}__protocols.png',dpi=140);plt.close(fig)
        if eid.startswith('RBC'):
            fig,axes=plt.subplots(4,2,figsize=(11,8),squeeze=False)
            for i,label in enumerate(['repeat-a','ic-1','ic-2','ic-3']):
                d=campaign/f'{eid}__extended__{label}'
                with np.load(d/'fields_001200.npz') as a:
                    temp=a['temperature'];v=a['velocity'];speed=np.sqrt((v*v).sum(axis=0))
                    im=axes[i,0].imshow(temp,origin='lower',vmin=0,vmax=1,cmap='coolwarm')
                    axes[i,0].quiver(np.arange(0,temp.shape[1],12),np.arange(0,temp.shape[0],8),v[0,::8,::12],v[1,::8,::12],color='black',width=.002)
                    fig.colorbar(im,ax=axes[i,0],fraction=.02)
                    im=axes[i,1].imshow(speed,origin='lower',vmin=0,vmax=.7,cmap='viridis');fig.colorbar(im,ax=axes[i,1],fraction=.02)
                    axes[i,0].set_ylabel(label)
            axes[0,0].set_title('Temperature + velocity arrows');axes[0,1].set_title('Speed (resampled fields)')
            fig.suptitle(eid+' final extended snapshots; image indices, not native mesh');fig.tight_layout()
            fig.savefig(output/f'{eid}__fields.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,6))
    for i,level in enumerate(['easy','medium','hard']):
        d=campaign/f'CylinderJet2D-{level}-v0__extended__repeat-a'
        with np.load(d/'fields_002400.npz') as a:
            speed=np.sqrt((a['velocity']**2).sum(axis=0))
            for j,(value,title,cmap) in enumerate([(speed,'speed','viridis'),(a['pressure'],'pressure','coolwarm')]):
                im=axes[i,j].imshow(value,origin='lower',cmap=cmap,aspect='auto');fig.colorbar(im,ax=axes[i,j],fraction=.02)
                axes[i,j].set_title(f'{level}: {title} (individual color scale)')
    fig.suptitle('Cylinder final snapshots: resampled image indices, different instantaneous phases')
    fig.tight_layout();fig.savefig(output/'cylinder_fields.png',dpi=150);plt.close(fig)
    name='CylinderJet2D-easy-v0__extended__repeat-a';_,base,_=datasets[name]
    ref=np.array([r['lift'] for r in base[400:]])
    for label in ['ic-1','ic-2','ic-3']:
        _,other,_=datasets['CylinderJet2D-easy-v0__extended__'+label]
        x=np.array([r['lift'] for r in other[400:]])
        # Bounded alignment within about half a measured easy shedding period.
        candidates=[]
        for lag in range(-7,8):
            a,b=(ref[-lag:],x[:lag]) if lag<0 else (ref[:-lag],x[lag:]) if lag else (ref,x)
            candidates.append((float(np.corrcoef(a,b)[0,1]),lag))
        corr,lag=max(candidates)
        phase.append({'initialization':label,'zero_lag_correlation':float(np.corrcoef(ref,x)[0,1]),
                      'best_correlation':corr,'lag_samples':lag,'search_lags':[-7,7],
                      'interpretation':'Descriptive lag alignment on validated uniform easy lift; not evidence of distinct dynamics.'})
    result={'runs':summary,'field_repeatability':field_repeats,'easy_lift_phase_alignment':phase}
    write_json(output/'physical-comparison.json',result)
    return result


def plot_rbc_evolution(campaign, output):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    campaign,output=Path(campaign),Path(output)
    fig,axes=plt.subplots(4,4,figsize=(14,8))
    for i,(level,label) in enumerate([(x,y) for x in ['medium','hard'] for y in ['repeat-a','ic-1']]):
        for j,step in enumerate([0,200,600,1200]):
            with np.load(campaign/f'RBC2D-{level}-v0__extended__{label}'/f'fields_{step:06d}.npz') as a:
                t=a['temperature']; v=a['velocity']
                axes[i,j].imshow(t,origin='lower',vmin=0,vmax=1,cmap='coolwarm',aspect='auto')
                axes[i,j].quiver(np.arange(0,t.shape[1],20),np.arange(0,t.shape[0],12),v[0,::12,::20],v[1,::12,::20],width=.003)
                axes[i,j].set_title(f'{level}/{label}: step {step}',fontsize=9)
    fig.suptitle('RBC temperature [0,1] and velocity: initial structure and persistence; resampled image indices')
    fig.tight_layout(); fig.savefig(output/'rbc_evolution.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--execution',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--physical-output')
    args=parser.parse_args()
    result=audit(args.execution,args.output)
    if args.physical_output:
        characterize(args.execution,args.physical_output)
        plot_rbc_evolution(Path(args.execution)/'campaign',args.physical_output)
    print(json.dumps({k:result[k] for k in ('errors','verified_file_hashes','steps','snapshots','figures_decoded','gpu')},indent=2))
