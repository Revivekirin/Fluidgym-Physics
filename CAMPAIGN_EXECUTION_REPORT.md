# Campaign execution report

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
