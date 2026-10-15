"""Conservative offline reconstruction, never replacement of raw timestamps."""
import numpy as np

PIN = '50071140b73a2a917fb96d33522a769f903f8c27'


def validated_axis(records, run, provenance, campaign_provenance):
    raw = [r['elapsed_solver_time'] for r in records]
    info = {'basis':'recorded_solver_clock', 'validated_uniform':False}
    def fallback(reason):
        return raw, {**info, 'reason':reason}
    if (campaign_provenance.get('upstream', {}).get('commit') != PIN
            or campaign_provenance.get('upstream', {}).get('dirty') is True):
        return fallback('missing pinned upstream evidence')
    if not run['env_id'].startswith(('CylinderJet2D-', 'RBC2D-')) or 'wide' in run['env_id']:
        return fallback('environment outside validated source trace')
    eff = provenance.get('effective', {})
    dt, count = (.01,25) if run['env_id'].startswith('Cylinder') else (.05,20)
    if eff.get('dt') != dt or eff.get('n_sim_steps') != count:
        return fallback('effective integration schedule missing or mismatched')
    reset = provenance.get('solver_time_at_reset')
    if reset is None or not np.isfinite(reset) or float(np.float32(reset)) != reset:
        return fallback('reset clock not a finite float32 value')
    clock = np.float32(reset)
    previous_total = None
    for i,r in enumerate(records,1):
        if (r.get('step') != i or r.get('solver_clock_dtype') != 'float32'
                or r.get('solver_steps_this_env_step') != count):
            return fallback('missing timing evidence or adaptive subdivision observed')
        total = r.get('solver_total_step')
        if total is None or (previous_total is not None and total-previous_total != count):
            return fallback('inconsistent internal step counter')
        previous_total = total
        for _ in range(count):
            clock = np.float32(clock + np.float32(dt))
        if r.get('solver_time') != float(clock) or r['elapsed_solver_time'] != float(clock)-reset:
            return fallback('native float32 clock replay mismatch')
    # Each successful adaptive call must perform >=1 accepted substep. Exactly
    # count accepted substeps for count calls means no subdivision in this record.
    interval = count * float(np.float32(dt))
    axis = (np.arange(1,len(records)+1,dtype=np.float64)*interval).tolist()
    info.update(basis='validated_uniform_native_dt_schedule', validated_uniform=True,
                interval=interval, nominal_interval=count*dt,
                native_dt=float(np.float32(dt)), internal_steps_per_control=count,
                max_recorded_clock_difference=float(np.max(np.abs(np.array(raw)-axis))),
                nominal_relative_dt_error=abs(float(np.float32(dt))/dt-1),
                validation='complete count sequence and exact float32 clock replay; pinned source trace',
                uncertainty='Reconstructed elapsed schedule, not an independent timer; no residual/fallback history. No interpolation/resampling.')
    return axis, info
