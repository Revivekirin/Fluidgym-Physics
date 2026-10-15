# Numerical limitations

## Current time-axis and termination audit — 2026-10-15

See [Time-axis and execution validation](docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md) for the current source trace, reconstruction conditions, uncertainty, termination classifications and exact offline/next-launch commands. This supersedes earlier blanket FFT withholding: easy extended spectra are permitted only if the full raw record passes the new fixed-native-dt replay/count validation. Raw trajectories are not available locally, so no new physical spectrum or peak has been calculated here. All six targets are adaptive-capable; medium variable counts and unknown timing retain restrictions. The second campaign termination remains UNKNOWN. Progress/signal supervision is corrected without changing solver physics or the approved matrix. No CFD was launched and no approval was generated.


## Partial-analysis evidence — 2026-10-15

Server analysis now succeeds for 15 completed runs; one incomplete run is excluded. All five easy extended spectra remain withheld for nonuniform solver-time sampling. Equal-weight and time-weighted interpolant statistics coexist and must be distinguished when comparing amplitudes. Available drag/lift repeat pairs agree exactly; full-field repeatability and cross-hardware determinism were not tested. No RBC or hard-cylinder physical conclusions are possible. No complete campaign runtime, device-memory peak, residual history, fallback counts or divergence history is available. Earlier sections are historical records, not evidence that the campaign is complete.


## Clock validation correction — 2026-10-15

CPU reproduction of pinned upstream scalar accumulation (`numpy.float32(1)` plus 25 additions of `numpy.float32(.01)` per environment step) exactly matches all supplied clock values at steps 249–253. It predicts step 254 clock 64.49536895751953 and increment 0.25005340576171875, exceeding the old 0.00005 increment tolerance. The observed failure is explained by float32 clock accumulation, not evidence of solver divergence. The rejected value itself was not saved, so the predicted step-254 value is a reproduction, not a recovered measurement.

The runner now adds a bounded rounding allowance: actual solver-step count times half the maximum endpoint ULP of the actual clock dtype. It retains the original baseline tolerance, monotonic/finite time checks and termination checks, rejects nonpositive solver-step progress, and fails if the rounding bound reaches half the average nominal substep interval. This validates the recorded clock within finite precision; it does not establish solver accuracy. New trajectory records expose clock dtype, increment, tolerance and internal step count. Official solver source, physical parameters, data and approved matrix are unchanged. CPU regression tests cover the full 2,400-step cylinder horizon, missed/extra integration and insufficient clock resolution. No new CFD has been executed locally.

The failed campaign remains immutable and excluded from complete-run statistics. Any subsequent campaign must execute all 60 runs in a fresh directory using the existing approval; no continuation or concatenation of the failed trajectory is supported.


## Observed validation failure — 2026-10-15

The first CylinderJet2D-easy extended run failed its solver-clock increment check after 253 recorded steps. The validator uses relative tolerance 2e-4 and absolute tolerance 1e-6 against the nominal integration interval. Pinned upstream accumulates `total_time` by adding `ntonp(time_step)[0]` in `PISOtorch_simulation.py:end_step`. Finite-precision accumulation is a possible explanation, not a demonstrated root cause; the offending clock values are missing. Solver instability is likewise not established by this message alone. No tolerance or official solver change has been made. GPU telemetry and completed-run physical statistics have not yet been supplied. A diagnostic-only error-message improvement will expose rejected values in future execution, but does not justify rerunning now.


Status (2026-10-14): campaign evidence pending. No observed server numerical failure or successful rollout is asserted by this report.

- Full preflight validates inputs/runtime prerequisites without CFD; it does not establish numerical stability or measured execution cost.
- Primary planning estimates are 2.392 GiB output and 1.2125–48.5 sequential GPU hours, using uncalibrated timing assumptions. Actual wall time, GPU memory and output size are unavailable.
- Proposed primary limits in the source workflow are 72 wall hours, 20 GiB output, 5 GiB disk reserve and 20 GiB torch allocation. The actual reviewed artifact must be checked. Torch allocation is not total device memory usage; external GPU telemetry is needed for that distinction.
- In-process budget checks occur at step boundaries. An external wall-time limit must be verified before launch.
- Native solver residual histories, divergence diagnostics and fallback-event counts are not supplied by the existing recording pipeline. Finite-field and solver-progress checks cannot replace these diagnostics or certify numerical convergence.
- Extended trajectories and discard-window comparisons alone do not prove stationarity. Difficulty variants mix physical, discretization and task changes and cannot establish grid convergence by direct comparison.
- Deterministic repeat agreement and variability across randomized initial domains answer different questions; neither is currently measured here.

Subsequent controlled physical shifts remain a research proposal. After nominal results are available, assess parameter access, initial-domain compatibility, observable adequacy and numerical validity for each family. Reynolds/Rayleigh changes require independently justified controls and compatible initial conditions; easy/medium/hard contrasts alone do not isolate their effects. No shift method is selected or implemented.

## Offline sampling handling — 2026-10-15

The partial-campaign analysis stopped with `nonuniform sampling: resampling/weighted analysis required`. The analysis now preserves recorded solver times and uses duration-weighted piecewise-linear interpolant moments for nonuniform time series, including equal-duration block means and half-window comparisons. This is an explicitly labeled descriptive estimator between sampled observables, not a reconstruction of instantaneous CFD fields or a correction to the solver clock. Uniform series retain equal-weight sample moments; these estimator labels must be considered when comparing runs. Nonuniform cylinder spectra are withheld with a reason; no FFT frequency or Strouhal estimate is fabricated. Raw artifacts and validation tolerances are unchanged. Failed analysis output remains immutable; rerun offline analysis into a new directory. No CFD rerun is needed for this fix.

Current audit validation: full CPU suite 97 passed / 3 CUDA-dependent skipped; final focused time-axis and subprocess suite 16 passed. Shell syntax and diff whitespace checks passed. See docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md for source trace, exact commands, and remaining supervisor/NFS/SIGKILL limits. No CFD launched.
