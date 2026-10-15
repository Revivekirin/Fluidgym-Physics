"""Offline per-trajectory analysis; independent resets are never concatenated."""
from __future__ import annotations

import json
from pathlib import Path

from .characterization import digest, write_json
from .diagnostics import cylinder_spectrum, summarize
from .inventory import registrations


def analyze(campaign, output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    campaign, output = Path(campaign), Path(output)
    if output.exists(): raise FileExistsError('analysis output must be new')
    output.mkdir(parents=True)
    reg=registrations()
    campaign_provenance = json.loads((campaign/"provenance.json").read_text()) if (campaign/"provenance.json").exists() else {}
    results=[]; excluded=[]; series={}
    for directory in sorted(p for p in campaign.iterdir() if p.is_dir()):
        status_path=directory/'status.json'
        if not status_path.exists():
            excluded.append({'run':directory.name,'reason':'interrupted: no terminal status'}); continue
        status=json.loads(status_path.read_text())
        if status['status']!='complete':
            excluded.append({'run':directory.name,'reason':status}); continue
        for filename, sha in status['sha256'].items():
            if digest(directory/filename)!=sha: raise ValueError(f'corrupt artifact {directory/filename}')
        run=json.loads((directory/'request.json').read_text())
        records=[json.loads(line) for line in (directory/'trajectory.jsonl').read_text().splitlines()]
        if len(records)!=run['steps'] or [r['step'] for r in records]!=list(range(1,run['steps']+1)):
            raise ValueError('incomplete/discontinuous trajectory')
        retained=records[run['discard_steps']:]
        from .time_axis import validated_axis
        provenance = json.loads((directory/'provenance.json').read_text()) if (directory/'provenance.json').exists() else {}
        axis, axis_info = validated_axis(records, run, provenance, campaign_provenance)
        t=axis[run['discard_steps']:]
        family=reg[run['env_id']]['family']
        keys={'cylinder':['drag','lift'],'airfoil':['drag','lift','lift_to_drag'],
              'rbc':['nusselt','temperature_min','temperature_max','temperature_volume_mean','kinetic_energy_volume_mean']}[family]
        metrics={}; unavailable={}
        fig,axes=plt.subplots(len(keys),1,figsize=(9,2.6*len(keys)),squeeze=False)
        for ax,key in zip(axes[:,0],keys):
            values=[r[key] for r in retained]
            if any(v is None for v in values):
                unavailable[key]='undefined denominator in lift/drag'; continue
            metrics[key]=summarize(t,values)
            # Sensitivity to an additional quarter-window exclusion; no automatic stationarity declaration.
            start=len(values)//4
            metrics[key]['later_window_mean']=summarize(t[start:],values[start:])['mean']
            ax.plot(t,values,lw=0.6); ax.set_ylabel(key); ax.set_xlabel(axis_info['basis'])
        fig.suptitle(directory.name); fig.tight_layout()
        fig.savefig(output/f'{directory.name}.png',dpi=130); plt.close(fig)
        spectrum=None
        if family=='cylinder' and run['protocol']=='extended':
            if axis_info['validated_uniform']:
                spectrum=cylinder_spectrum(t,[r['lift'] for r in retained])
            else:
                spectrum={'frequency':[], 'psd':[], 'candidate_strouhal_D1_U1':None,
                          'withheld_reasons':['uniform integration schedule not validated: '+axis_info.get('reason','unknown')],
                          'interpretation':'No interpolation or resampling applied.'}
            spectrum['time_axis'] = axis_info
            if spectrum['frequency']:
                fig,ax=plt.subplots(figsize=(7,3))
                ax.plot(spectrum['frequency'][1:],spectrum['psd'][1:]); ax.set(xlabel='frequency (D/U units)',ylabel='lift PSD')
                fig.tight_layout(); fig.savefig(output/f'{directory.name}__spectrum.png',dpi=130); plt.close(fig)
        row={'run_id':directory.name,'env_id':run['env_id'],'protocol':run['protocol'],
             'randomize':run['randomize'],'seed':run['seed'],'metrics':metrics,
             'unavailable':unavailable,'spectrum':spectrum,'time_axis':axis_info}
        results.append(row); series[directory.name]=(run,records)
    comparisons=[]
    for eid in reg:
        for protocol in ('benchmark','extended'):
            matching=[r for r in results if r['env_id']==eid and r['protocol']==protocol]
            repeat=[r for r in matching if not r['randomize']]
            variability=[r for r in matching if r['randomize']]
            for other in repeat[1:]:
                a=series[repeat[0]['run_id']][1]; b=series[other['run_id']][1]
                if len(a)!=len(b) or not np.allclose([x['elapsed_solver_time'] for x in a],[x['elapsed_solver_time'] for x in b],rtol=1e-5,atol=1e-6):
                    raise ValueError('repeatability comparison has incompatible time axes')
                comparisons.append({'env_id':eid,'protocol':protocol,'kind':'deterministic_repeatability',
                    'runs':[repeat[0]['run_id'],other['run_id']],
                    'max_absolute_difference':{k:float(np.max(np.abs(np.array([x[k] for x in a])-np.array([x[k] for x in b]))))
                        for k in other['metrics'] if all(x[k] is not None for x in a+b)}})
            if variability:
                comparisons.append({'env_id':eid,'protocol':protocol,'kind':'randomized_initial_condition_variability',
                    'runs':[r['run_id'] for r in variability],
                    'per_run_means':{k:[r['metrics'][k]['mean'] for r in variability if k in r['metrics']]
                                     for k in variability[0]['metrics']}})
    report={'schema_version':1,'campaign':str(campaign.resolve()),'trajectories':results,
            'comparisons':comparisons,'excluded':excluded,
            'interpretation':'Descriptive statistics only. Four contiguous block means and discard sensitivity do not establish stationarity, independence, bifurcation, chaos, or turbulence.'}
    write_json(output/'analysis.json',report)
    # Compact cross-run comparison plot; never pool temporal samples across runs.
    if results:
        fig,axes=plt.subplots(3,1,figsize=(12,10))
        for ax,(family,key) in zip(axes,[('cylinder','drag'),('rbc','nusselt'),('airfoil','lift_to_drag')]):
            rows=[r for r in results if reg[r['env_id']]['family']==family and r['protocol']=='extended' and key in r['metrics']]
            ax.scatter(range(len(rows)),[r['metrics'][key]['mean'] for r in rows],s=14)
            ax.set_xticks(range(len(rows)),[r['run_id'].replace('__extended','') for r in rows],rotation=90,fontsize=5)
            ax.set_ylabel(f'per-run mean {key}')
        fig.tight_layout(); fig.savefig(output/'aggregate.png',dpi=150); plt.close(fig)
    return {'analyzed':len(results),'excluded':len(excluded),'output':str(output)}
