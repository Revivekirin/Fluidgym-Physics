# Campaign execution report

## Current time-axis and termination audit — 2026-10-15

See [Time-axis and execution validation](docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md) for the current source trace, reconstruction conditions, uncertainty, termination classifications and exact offline/next-launch commands. This supersedes earlier blanket FFT withholding: easy extended spectra are permitted only if the full raw record passes the new fixed-native-dt replay/count validation. Raw trajectories are not available locally, so no new physical spectrum or peak has been calculated here. All six targets are adaptive-capable; medium variable counts and unknown timing retain restrictions. The second campaign termination remains UNKNOWN. Progress/signal supervision is corrected without changing solver physics or the approved matrix. No CFD was launched and no approval was generated.


## Latest execution assessment — 2026-10-15

This section supersedes older pending-launch/analysis statuses below. Second attempt: `execution-20261015T010803Z-Rk5NDa`. Server offline analysis completed with 15 analyzed runs and one excluded incomplete run. Completed scope: CylinderJet2D-easy benchmark and extended (10 runs), CylinderJet2D-medium benchmark (5 runs). Completed trajectories contain 12,800 environment steps; the incomplete medium extended trajectory last showed 580 additional recorded steps, for 13,380 recorded steps in this attempt. Forty-four planned runs were not started. This is not a completed 60-run campaign.

Campaign/run terminal status for the incomplete trajectory and wrapper exit/wall-time files are absent. A later successful process listing showed no campaign processes; GPU snapshot showed none. Termination cause and total wall time are unknown; Ctrl+C and Killed were observed but do not establish OOM. Do not merge this attempt with the earlier failed attempt or resume its incomplete trajectory. The latest five supplied medium benchmark status files report completion; analysis verified completed-run hashes server-side. Locally only the operator transcript is available.

The previously supplied medium final record reports torch peak allocation 67,819,520 bytes (64.68 MiB). This is a sampled record's allocator peak, not a measured whole-campaign device-memory peak. Complete GPU telemetry and launcher timing are still unavailable. No new CFD was launched during this analysis update.


## Clock validation correction — 2026-10-15

CPU reproduction of pinned upstream scalar accumulation (`numpy.float32(1)` plus 25 additions of `numpy.float32(.01)` per environment step) exactly matches all supplied clock values at steps 249–253. It predicts step 254 clock 64.49536895751953 and increment 0.25005340576171875, exceeding the old 0.00005 increment tolerance. The observed failure is explained by float32 clock accumulation, not evidence of solver divergence. The rejected value itself was not saved, so the predicted step-254 value is a reproduction, not a recovered measurement.

The runner now adds a bounded rounding allowance: actual solver-step count times half the maximum endpoint ULP of the actual clock dtype. It retains the original baseline tolerance, monotonic/finite time checks and termination checks, rejects nonpositive solver-step progress, and fails if the rounding bound reaches half the average nominal substep interval. This validates the recorded clock within finite precision; it does not establish solver accuracy. New trajectory records expose clock dtype, increment, tolerance and internal step count. Official solver source, physical parameters, data and approved matrix are unchanged. CPU regression tests cover the full 2,400-step cylinder horizon, missed/extra integration and insufficient clock resolution. No new CFD has been executed locally.

The failed campaign remains immutable and excluded from complete-run statistics. Any subsequent campaign must execute all 60 runs in a fresh directory using the existing approval; no continuation or concatenation of the failed trajectory is supported.


## Server execution update — 2026-10-15

This update supersedes the pending-launch status below. Operator-supplied evidence identifies `results/preparation-20261014T115019Z/execution-20261014T130118Z-LYojRC`. Runner exit code: 2; wrapper wall time: 511 seconds. Five CylinderJet2D-easy benchmark runs completed (80 steps each). The first extended run (`repeat-a`) failed after 253 recorded steps with `solver time increment differs from nominal integration interval`. Thus 5 runs completed, 1 failed, and 54 were not started under fail-fast execution. There are 653 recorded validated steps; the next env.step returned before validation failed, so this is not the total solver work performed. Completed run wall times were 62.1201, 61.4181, 61.8394, 62.0062 and 62.1328 seconds; failed run wall time was 195.4805 seconds.

No trajectory has been retried, resumed, joined, or overwritten. Actual rejected clock values were not recorded by the original error message. A diagnostic-only runner change now includes previous/current time, actual/expected increment and unchanged tolerances. It does not resolve or reclassify the observed failure. Await trajectory/provenance and offline analysis before deciding whether a numerical validity change is justified. No new campaign launch is recommended yet.


Status (2026-10-14): preflight, input-hash verification and repository approval reported successful; server launch pending. This is a gate report, not an executed-campaign report.

The researcher reports completed official acquisition, full and primary preflight, and primary budget review. These server artifacts are not available in this local workspace. The operator manages the remote server; no remote operation or CFD was performed in this session.

Local upstream verification passed at `50071140b73a2a917fb96d33522a769f903f8c27`, source tree `8a8476b966e496341676ea36384589028f4dc450`, with a clean upstream checkout. This does not establish the server checkout or imported package identity. Local Python has neither FluidGym nor torch installed; this Mac is not the target CUDA execution environment.

## Operator-provided server evidence

The operator supplied server output on 2026-10-14 (GPU snapshot at 21:02:10). Server upstream verification matches the locked commit and source tree above and reports `dirty: false`. Python resolves to `/nfs4/jhkim/conda_envs/fluidgym-test/bin/python`; FluidGym resolves to `/nfs4/jhkim/repos/Fluidgym-Physics/third_party/fluidgym/src/fluidgym/__init__.py`.

The GPU snapshot reports an RTX 3090 with 24,576 MiB total memory, 1 MiB used, 0% utilization and no running processes; driver 535.171.04. The displayed CUDA 12.2 value is driver capability, not proof of the installed torch CUDA runtime or extension compatibility. The repository filesystem `/nfs4` has 912G available. These are point-in-time resource observations, not reservations or a guarantee against user quotas. `/usr/bin/timeout` exists; no actual external timeout invocation or scheduler wall limit has yet been verified.

The subsequent operator transcript identifies `results/preparation-20261014T115019Z`. Both saved preflights report `passed`, and the supplied verification script completed its matrix equality and current input SHA-256 checks without an assertion failure. Evidence is the operator transcript; the server artifacts themselves have not been copied into this workspace.

| Check | Observed value |
|---|---|
| Full matrix SHA-256 | `73ac299057f82a11cf4dc1a5e7a5d815af097fdd2641975e52e91e6f219d80d6` |
| Primary draft SHA-256 | `0f15afbbd926d6bd03195ecaea8db8131cdd8a7358c020384f661c211d6b8bc1` |
| Current manifest files verified | Full: 262; primary: 136 |
| Official dataset | `safe-autonomous-systems/fluidgym-data` |
| Dataset revision recorded in both preflights | `a8c00235a814828441a0c5638e6f803ef62bfa31` |
| Data root | `/home/jhkim/.local/share/FluidGym/initial_domains` |
| Primary protocol | Equal to `primary_draft(full)`; six required environments, 60 runs, 58,200 steps |
| Planning estimate | 2.392069 GiB; 1.2125–48.5 hours, unmeasured |
| Budget | 72 hours, 20 GiB output, 5 GiB reserve, 20 GiB torch allocation |

The source matrix and plan remain `draft_not_authorized`. Subsequently, the operator explicitly ran `approve-matrix --accept-budget` and supplied its successful `status: approved` output. The reviewed copy is `results/preparation-20261014T115019Z/approved-primary/matrix.json`, and its approval is the adjacent `approval.json`. No approval was generated locally; do not regenerate this artifact.

`experiments/run-approved-primary.sh` now provides the server launch wrapper. It checks the existing approval, original protocol, both saved preflights and current input hashes before invoking the existing runner, which repeats runtime preflight and approval/input validation before any reset. It creates an exclusive execution directory, records external timeout settings, wall time, exit code and five-second device-wide GPU samples, and runs existing offline analysis only after campaign success. It never retries a failed campaign. The external limit sends TERM at 71h59m and KILL 60 seconds later. GPU telemetry includes other processes and is sampled, so it does not replace per-run torch allocation peaks. Shell syntax was checked locally with `bash -n`; the CUDA launch has not been tested or executed here.

## Gate evidence still required

- Revalidate the existing repository approval and current inputs at launch using the wrapper; no new approval is required.
- External scheduler wall-time limit or timeout command, and fresh resource checks at launch on the chosen output filesystem. Runner checks at step boundaries cannot stop a hung native solver call.

Primary scope remains six environments, 60 nominal zero-action runs and 58,200 environment steps. No matrix, solver, physical parameter or approval artifact was changed. Runs launched here: zero. Server successful/failed/skipped counts are unknown; planned runs must not be reported as observed failures or skips.

After copying the launch wrapper to the server, the operator command from a persistent server terminal in the activated environment is:

```bash
bash experiments/run-approved-primary.sh results/preparation-20261014T115019Z
```

The wrapper refuses failed readiness checks before launching CFD. Actual campaign results remain pending operator execution and returned artifacts.

Current audit validation: full CPU suite 97 passed / 3 CUDA-dependent skipped; final focused time-axis and subprocess suite 16 passed. Shell syntax and diff whitespace checks passed. See docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md for source trace, exact commands, and remaining supervisor/NFS/SIGKILL limits. No CFD launched.

Launcher correction: the two reported `FG_EXEC: unbound variable` attempts failed before invoking the Python runner. The removed preflight/approval verification block and unique-directory initialization have been restored. Three actual-launcher CPU regression tests pass (downstream CFD replaced by a stub); no new CFD or approval creation occurred. See the validation audit for the exact editing failure and coverage gap.
