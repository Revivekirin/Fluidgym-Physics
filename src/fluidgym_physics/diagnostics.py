"""Physical diagnostics with explicit measurement definitions; no regime classifiers."""
from __future__ import annotations

import math


def finite(value, label='value'):
    import numpy as np
    if isinstance(value, dict):
        for k, v in value.items(): finite(v, f'{label}.{k}')
    else:
        if hasattr(value, 'isfinite'):
            valid = bool(value.isfinite().all().item())
        else:
            valid = np.isfinite(np.asarray(value)).all()
        if not valid:
            raise ValueError(f'non-finite {label}')


def scalar(value):
    if hasattr(value, 'detach'): value = value.detach().cpu().numpy()
    import numpy as np
    a = np.asarray(value)
    if a.size != 1: raise ValueError('expected scalar measurement')
    result = float(a.reshape(-1)[0])
    if not math.isfinite(result): raise ValueError('non-finite measurement')
    return result


def physical_metrics(family, info):
    keys = {'cylinder':('drag','lift'), 'airfoil':('drag','lift'), 'rbc':('nusselt',),
            'tcf':('wall_stress','wall_stress_bottom','wall_stress_top')}[family]
    out = {k:scalar(info[k]) for k in keys}  # Missing metrics are errors, never fabricated zeros.
    if family == 'airfoil':
        out['lift_to_drag'] = out['lift']/out['drag'] if abs(out['drag']) > 1e-12 else None
    return out


def summarize(times, values):
    import numpy as np
    t, x = np.asarray(times), np.asarray(values)
    finite(t); finite(x)
    if len(t) < 4 or x.shape != t.shape or not np.all(np.diff(t) > 0):
        raise ValueError('need >=4 finite samples at strictly increasing times')
    # Equal-weight statistics only with verified uniform sampling.
    if not np.allclose(np.diff(t), np.median(np.diff(t)), rtol=1e-4, atol=1e-6):
        raise ValueError('nonuniform sampling: resampling/weighted analysis required')
    blocks = np.array_split(x, 4)
    return {'mean':float(x.mean()), 'std':float(x.std()), 'rms':float(np.sqrt(np.mean(x*x))),
            'min':float(x.min()), 'max':float(x.max()), 'samples':len(x),
            'block_means':[float(b.mean()) for b in blocks],
            'half_mean_difference':float(x[len(x)//2:].mean()-x[:len(x)//2].mean())}


def cylinder_spectrum(times, lifts):
    """Hann periodogram; candidate peak only, never proof of a flow regime."""
    import numpy as np
    summarize(times, lifts)
    t, x = np.asarray(times), np.asarray(lifts)
    dt = float(np.median(np.diff(t)))
    n = len(t)
    window = np.hanning(n)
    power = abs(np.fft.rfft((x-x.mean())*window))**2 * dt / (window**2).sum()
    power[1:-1 if n % 2 == 0 else None] *= 2
    frequencies = np.fft.rfftfreq(n, dt)
    idx = int(np.argmax(power[1:])+1)
    frequency = float(frequencies[idx])
    cycles = frequency*n*dt
    reasons = []
    if n < 256: reasons.append('fewer than 256 retained samples')
    if cycles < 10: reasons.append('fewer than ten candidate cycles')
    if np.std(x) <= 1e-12: reasons.append('no resolved fluctuation')
    if idx == len(frequencies)-1: reasons.append('peak at Nyquist edge')
    return {'frequency':frequencies.tolist(), 'psd':power.tolist(),
            'resolution':1/(n*dt), 'nyquist':0.5/dt,
            'candidate_strouhal_D1_U1':None if reasons else frequency,
            'withheld_reasons':reasons,
            'interpretation':'Step-averaged lift spectrum. Stationarity and convergence require review.'}
