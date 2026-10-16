# Numerical uncertainty and limitations

Campaign `execution-20261015T045202Z-NoMY5u`; final offline review, 2026-10-16. Labels distinguish **Measured**, **Inference**, and **Unresolved**. This document supersedes partial-campaign conclusions for this completed attempt, while retaining those attempts as historical evidence.

## What was verified

**Measured.** Sixty complete run directories match the approved request matrix and have 58,200 contiguous scalar records and 2,970 expected snapshots. Recorded hashes (3,213 files) match. All snapshots decode without pickle and match declared field names, shapes and float32 dtypes, with finite values. All 66 original figures decode. Top-level terminal status, approval/matrix/input-manifest binding, source commit/tree and supervisor recovery status agree. No corrupt or missing recorded output was found. The original matrix, original campaign and analysis were not edited.

**Measured.** The server input manifest contains 136 paths. None of those original `/home/jhkim/...` data paths is available locally. Original acquisition files/preflight, native CUDA binary and their bytes are also not provided. **Unresolved:** independent byte-level validation of those external dependencies. The recorded source/input hashes and approval chain are evidence of the execution record, not a new download verification or cryptographic authentication of the entire server.

**Measured.** Local offline reanalysis reproduces comparisons exactly and scalar statistics within 3.47e-18 (two lift half-window differences). PSD floating-point arrays differ by at most 8.53e-14 absolute. **Inference:** this scale is consistent with numerical FFT implementation differences, not a scientifically material spectrum change. No uncertainty interval is inferred from that difference.

## Three different clocks

**Measured/source-traced.** All target environments configure adaptive internal stepping. Cylinder requests 25 solver calls of dt .01 per control step; RBC requests 20 of dt .05. The native solver accumulates accepted substep times into a float32 clock. `reported_env_time` instead counts nominal control intervals. Neither the nominal counter nor a rounded cumulative clock alone establishes the exact sum of native adaptive timesteps.

**Measured.** All easy Cylinder trajectories pass exact float32 clock replay and one accepted internal step per requested solver call over every recorded step. Their analysis axis is `step * 25 * float(float32(.01))`. At 2,400 steps this is 599.999986589, nominal time is 600, and the accumulated float32 elapsed clock can be about 600.27557 depending on reset time. Raw timestamps are retained. No interpolation or data-dependent peak optimization is applied.

**Measured.** Maximum absolute final recorded-clock minus nominal-time differences in each environment are: Cylinder easy .275567, medium .371941, hard .431328; RBC easy .585353, medium .400367, hard .400367. **Unresolved:** for adaptive cases these differences cannot be partitioned exactly into accumulation rounding, native timestep conversion and residual target-time truncation because individual accepted dt values were not recorded. They are not measurements of physical trajectory error.

**Measured.** All five easy extended lift spectra yield the same bin near St .274, with bin resolution .002 and Nyquist near 2. **Inference:** this is a supported candidate shedding scale in the retained data. **Unresolved:** asymptotic stationarity, spectral confidence bounds, aliasing of unresolved faster fluctuations and discretization convergence. Force records are averages across the 25 solver calls, so they are not instantaneous lift samples. Retained windows cover about 137 candidate cycles but temporal samples are correlated.

**Measured.** Medium/hard Cylinder timing is adaptive and does not pass the fixed-native-dt reconstruction; their spectra are withheld. RBC is analyzed through physically relevant heat/energy/temperature observables, not an indiscriminate cylinder shedding metric. Future recorded accepted-dt sums in float64 could resolve timing without replacing the native solver clock or changing fidelity; implementation and overhead would need validation in a separately authorized task.

## Statistical and spatial limits

**Measured.** Uniform easy time axes use equal-weight sample moments. Nonuniform records use duration-weighted piecewise-linear interpolant moments and equal-duration block means. Weighted RMS/SD describe that interpolant and may smooth sample-to-sample excursions; they are not an unbiased instantaneous turbulence measure. Comparison reports label the estimators. Window spans run from the first retained sample to the last, not from the nominal start of the discarded boundary. No effective sample size or confidence interval is claimed.

**Measured.** Scalars repeat exactly in all 12 deterministic pairs on one RTX 3090 setup. RBC resampled fields repeat exactly; Cylinder resampled fields differ by up to 9.54e-7. **Unresolved:** cause of those small field differences (e.g. resampling/native nondeterminism), and cross-device reproducibility. Torch deterministic algorithms and cuDNN deterministic mode were disabled in recorded provenance. Same-seed repetitions do not increase the independent-initial-condition sample size.

**Measured.** Initial domain identities are 0, 1, 7 and 8; repeat-a/b reuse 0. The three randomized cases are not exhaustive samples of the ten supplied test domains. Benchmark and extended runs use matched initialization controls and can share early trajectory evolution; they must not be split naively across training/test sets as independent data.

**Measured.** Saved fields are public resampled pressure/velocity and RBC temperature, at every 20 control steps. They are not native conservative fields, native wall gradients or exact restart checkpoints. Observations were checked for finiteness but their per-step sensor tensors were not saved. Vorticity was not saved. The official vorticity routine needs native block velocity gradients before resampling; differentiating these images is not an equivalent measurement. No native divergence, boundary heat-flux closure, momentum/energy balance or solver-residual time series is available.

**Inference.** Visible RBC roll structure explains a plausible link to Nu/energy separation, but finite trajectories cannot establish multiple attractors, ergodicity, transition rates or bifurcation. Difficulty contrasts change parameters and sometimes resolution/CFL; they are not controlled causal studies or grid-convergence tests.

## Execution evidence and historical interruptions

**Measured.** Completed campaign: SUCCESS, 65,745.713 seconds, no KILL escalation, 13,147 device telemetry samples, peak 476 MiB, maximum intersample gap 5.099 seconds. PyTorch peak allocation reaches 137.358 MiB; these values exclude different memory categories and device-wide sampling can miss short peaks. The monitor error file is empty. Wall time includes initialization/output and is not native kernel-only integration cost.

**Measured.** Earlier `execution-20261014T130118Z-LYojRC` failed on a Python clock-increment validation exception (511 seconds; five complete runs and one partial). Float32 replay explains why the former fixed tolerance rejected it. **Unresolved:** earlier `execution-20261015T010803Z-Rk5NDa` termination cause remains UNKNOWN, despite observed Ctrl+C/Killed and eventual absence of processes. It is not proven OOM or solver instability. Two subsequent launcher attempts failed before CFD on unbound FG_EXEC; the gate was restored and actual-launcher tests added. These histories are not merged into the completed attempt.

## Reproducibility

Read-only audit, into a fresh output directory:

```bash
python -m fluidgym_physics.audit \
  --execution results/execution-20261015T045202Z-NoMY5u \
  --output results/final-nominal-audit-new \
  --physical-output docs/figures/nominal-review-new
```

Offline analysis, also into a fresh directory:

```bash
python -m fluidgym_physics.cli analyze \
  --campaign results/execution-20261015T045202Z-NoMY5u/campaign \
  --output results/final-nominal-reanalysis-new
```

Neither command executes CFD. CPU corruption tests cover changed/missing hashes and invalid snapshot dtype/shape/keys/nonfinite values. Real artifacts were all decoded and hashed. No extra scientific metric was invented to compensate for missing native measurements.

## Final validation record

**Measured.** Final audit returned zero errors after manifest-coverage and GPU UUID/range checks. CPU tests: **106 passed, 3 CUDA-dependent skipped**. No new CFD ran. All 30 benchmark trajectories exactly match their corresponding extended prefixes for physical/time records (wall time and allocator peaks excluded); these are not independent training/test samples. Reanalysis differences and generated-figure hashes are recorded in [reanalysis-and-figures.json](evidence/final-nominal-20261015/reanalysis-and-figures.json).
