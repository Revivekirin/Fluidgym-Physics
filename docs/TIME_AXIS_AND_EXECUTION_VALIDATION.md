# Time-axis and termination audit — 2026-10-15

No CFD was launched. The approved matrix, approvals, data and pinned solver are unchanged. Upstream verification reports clean commit `50071140b73a2a917fb96d33522a769f903f8c27` and source tree `8a8476b966e496341676ea36384589028f4dc450`.

## Actual stepping path

Pinned source locations:

- `third_party/fluidgym/src/fluidgym/envs/fluid_env.py`: `_n_sim_steps` uses `max(1, int(step_length / dt))`; `step` increments the control-step counter only after the family implementation returns.
- `envs/cylinder/cylinder_env_base.py`: simulation construction uses `substeps="ADAPTIVE"`; `_step_impl` calls `single_step` 25 times and averages drag/lift measured after those calls. They are control-interval averages, not instantaneous measurements.
- `envs/rbc/rbc_env_base.py`: simulation construction also uses adaptive substeps; `_step_impl` calls `single_step` 20 times before measuring Nusselt number.
- `simulation/simulation.py:single_step`: `substeps == -1` selects `_PISO_adaptive_step`; solver exceptions return failure. The runner's existing guard rejects a false return.
- `simulation/pict/PISOtorch_simulation.py:_PISO_adaptive_step`: starts with the requested target duration, partitions it according to velocity/CFL, subtracts substep durations and converts each duration to native tensor dtype. Iteration stops at zero or `np.isclose(remaining, 0)`; the remaining-time threshold and float conversion prevent treating all adaptive sums as exactly nominal without additional evidence.
- `PISOtorch_simulation.py:end_step`: increments the internal step counter once and adds `ntonp(time_step)[0]` to `total_time`. With float32 operands this accumulated clock rounds at every addition. It is not an independently precise measurement of elapsed integration time.

| Target variants | Requested solver call dt | Calls/control step | Requested control interval | CFL | Internal integration |
|---|---:|---:|---:|---:|---|
| CylinderJet2D easy/medium/hard | .01 | 25 | .25 | .8 | Adaptive-capable, not universally fixed |
| RBC2D easy | .05 | 20 | 1 | .8 | Adaptive-capable |
| RBC2D medium/hard | .05 | 20 | 1 | .5 | Adaptive-capable |

`reported_env_time` is the intended task schedule, not evidence that adaptive substeps exactly covered it. Observed easy records report 25 accepted internal steps/control step; medium records report varying counts (e.g. 27–49), proving subdivision occurs there. No runtime RBC timing evidence is available.

## Conservative offline reconstruction

`time_axis.validated_axis` checks every record, not a tail excerpt. Requirements: pinned source identity in campaign provenance; a target family and matching effective dt/call count; finite float32 reset clock; complete sequential control-step indices; float32 clock dtype; exactly one internal accepted step per requested solver call throughout; consistent cumulative internal step counts; and exact replay of every native float32 accumulated timestamp and elapsed timestamp. Failed checks retain original solver-clock times and withhold the extended FFT.

A successful adaptive call must make at least one accepted internal step. Having exactly 25 (or 20) accepted steps over that many successful calls, together with replay, supports no subdivision in that record. The uniform analysis axis is control-step index times `calls * float(float32(dt))`. It is explicitly labeled `validated_uniform_native_dt_schedule`. It is derived from the native dt schedule, not renamed nominal task time, and no measured samples are interpolated/resampled. Raw timestamps remain unchanged. The report includes the interval, nominal interval, native dt, maximum accumulated-clock disagreement, relative nominal dt error and validation basis.

For Cylinder dt, native dt is 0.009999999776482582. Over 2,400 control steps the reconstructed elapsed time is 599.9999865889549, versus nominal 600. Starting at clock 1, float32 accumulation ends at 601.275390625 (elapsed 600.275390625). This exact CPU reproduction explains a 0.275404036 difference without changing the integration itself. Nominal/native dt relative difference is about 2.24e-8. FFT frequency units use the reconstructed interval and remain those of the dimensionless solver schedule. This does not quantify spatial/temporal discretization error, solver residuals, or clock-dependent boundary effects.

### Existing partial results

The supplied tail excerpts and summary JSON do not contain full raw time/lift sequences. Therefore existing easy extended FFTs are **conditionally justified only after all-record validation**. They have not been computed locally and no peak is reported. Medium extended is incomplete and excluded; its variable subdivision cannot use this reconstruction. The completed server run artifacts should be analyzed offline into a new directory, using the commands below. Synthetic full-horizon replay/FFT tests do not substitute for this server artifact validation.

Even validated FFTs remain control-interval-averaged lift spectra; window length, frequency resolution, aliasing and stationarity limitations remain. Existing rules requiring enough samples/cycles and withholding flat/Nyquist-edge candidates remain in force.

## Execution audit and corrections

The original shell ran `timeout` in the foreground with all runner output redirected. Its only trap cleaned up GPU telemetry. It neither handled launcher INT/TERM explicitly nor guaranteed recording after signal delivery. Thus a silent terminal did not imply a stalled solver; an interrupted shell could lose exit/timing records. We cannot infer which signal ended the historical campaign.

The launcher now starts an external Python supervisor. The CFD child is in a separate POSIX session/process group. The supervisor catches INT/TERM, records the request before forwarding it to that group, allows 60 seconds for cleanup, then sends KILL if necessary. At the 72-hour budget it initiates TERM after 71h59m, escalating at 72h. It prints a heartbeat every 30 seconds with the last persisted run/environment/protocol/seed/randomization/step/output information; an unchanged heartbeat is not proof of solver progress. The runner appends flushed progress on start/reset, first step, every 25 completed steps, and final step. No native solver stepping is modified.

Runner INT/TERM handlers raise a distinct exception so the existing run/campaign exception path writes terminal status, reason and completed steps where Python can execute. Native CUDA calls may defer handling. The external supervisor remains able to signal the process group. It records child return code, reason, elapsed time, kill escalation and launch command. Known signals, timeout, Python exceptions with runner evidence, and unknown nonzero exits are distinguished. SIGKILL indicates the signal only, not whether OOM, a user, or another actor caused it.

Missing per-run terminal statuses are classified in a new `recovered-run-statuses.json` sidecar after the child exits. Existing run files are never edited, and no missing terminal record becomes a completed trajectory. Device-wide `gpu.csv`, monitoring errors/status and per-run PyTorch allocator peaks are distinct evidence. The monitor has its own session and bounded cleanup. Analysis runs only after successful supervision.

Limits: SIGKILL of the supervisor, machine loss, blocked filesystem writes or uninterruptible kernel I/O cannot guarantee a final record. Whole-job hard limits require an external scheduler/cgroup for protection against supervisor failure. The supervisor provides the application-external 72-hour limit while it is alive; it is not a cluster scheduler. Heartbeat and status I/O themselves may block on failed NFS. Atomic durable storage and automatic recovery of old attempts are not claimed. No retry/resume is implemented.

## Historical termination classifications

| Attempt | Evidence | Classification |
|---|---|---|
| `execution-20261014T130118Z-LYojRC` | runner exit 2; ValueError in run/campaign status; 511 seconds | PYTHON_EXCEPTION, overly strict accumulated-clock check; not evidence of divergence |
| `execution-20261015T010803Z-Rk5NDa` | 15 complete, medium extended at step 580 with no terminal status; no campaign/launcher exit records; later no active process | UNKNOWN interruption; SIGINT, SIGKILL and OOM not established |

Second attempt: 12,800 completed-run steps plus 580 recorded incomplete steps; 44 runs not started. First attempt: 400 completed-run steps plus 253 recorded incomplete steps. These independent attempts are not combined into a trajectory or a completed matrix. Device-wide peak and total runtime of the second attempt are unavailable. Existing residual histories, fallback-event counts and divergence diagnostics remain missing.

## Commands (operator-run; no commands here were executed against CFD)

Synchronize changed Python modules and launcher to the server, keep the existing activated environment, and run offline reanalysis first:

```bash
cd /nfs4/jhkim/repos/Fluidgym-Physics
FG_EXEC=results/preparation-20261014T115019Z/execution-20261015T010803Z-Rk5NDa
python -m fluidgym_physics.cli analyze \
  --campaign "$FG_EXEC/campaign" \
  --output "$FG_EXEC/analysis-validated-time-v1"
```

This reads immutable existing trajectories, validates hashes/time evidence and either produces labeled spectra or explicit withholding reasons. If the output exists, choose a fresh name. Send `analysis.json` and figures for review; do not claim spectral results from the previous summary alone.

For the **next campaign only**, after this task's changes and tests have been reviewed, in a persistent server terminal:

```bash
cd /nfs4/jhkim/repos/Fluidgym-Physics
bash experiments/run-approved-primary.sh results/preparation-20261014T115019Z
```

The launcher uses the existing approval, revalidates the same matrix/inputs, generates a new exclusive execution directory and never resumes partial trajectories. Do not rerun approve-matrix. The six environments, 60 runs and 58,200 steps are unchanged. No launch is part of this task.

## Validation results

- Full CPU suite: **97 passed, 3 skipped** (26.62 seconds). Skipped tests require the real CUDA environment.
- After removing the signal-sensitive shell `tee` pipe and testing process-group delivery, focused time-axis/subprocess suite: **16 passed** (18.11 seconds).
- Coverage: full 2,400-step float32 Cylinder replay, 1,200-step RBC synthetic replay, synthetic known-frequency spectrum, exact-record offline reconstruction with raw hashes unchanged, missing/mismatched timing evidence, variable substep rejection, child success, unknown nonzero exit, evidenced Python exception, SIGINT/SIGTERM group forwarding, timeout with forced KILL, child SIGKILL, partial-JSON recovery, spawn failure, and signaling descendant processes.
- `bash -n experiments/run-approved-primary.sh` and `git diff --check` passed.
- Original full matrix SHA-256 remains `73ac299057f82a11cf4dc1a5e7a5d815af097fdd2641975e52e91e6f219d80d6`; pinned upstream is clean. No approval artifact was created.
- No GPU integration, real long-run supervisor reliability, or physical PSD from the server trajectories was tested locally. Synthetic tests validate bookkeeping/analysis, not CFD accuracy.

The shell `tee` process substitution was removed: otherwise terminal SIGINT could kill tee and break the supervisor's output pipe. The supervisor now writes launcher.log directly and independently displays progress. Its status/progress files are not a guarantee against filesystem loss.
