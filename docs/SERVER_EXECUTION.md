# Server preparation and execution reference

The primary campaign is now complete; see [final characterization](FINAL_NOMINAL_CHARACTERIZATION.md). The commands below document reproduction on a CUDA server, not a request to repeat completed acquisition, approval or CFD. Preserve valid existing approval artifacts.

Preparation scope: preserve `experiments/characterization.v1.json`, the original 15-variant draft. Acquire its missing official test inputs and preflight the full matrix. Only after a successful full preflight, generate a separate **unreviewed** six-environment primary matrix. No command in the preparation sequence approves or launches CFD.

The primary study contains exactly:

- `CylinderJet2D-easy-v0`, `CylinderJet2D-medium-v0`, `CylinderJet2D-hard-v0`
- `RBC2D-easy-v0`, `RBC2D-medium-v0`, `RBC2D-hard-v0`

CylinderRot2D (3), RBC2D-wide (3), Airfoil2D (3) remain future 2D expansion targets. All 24 registered 3D variants remain deferred. `prepare-primary` requires a successful full-matrix preflight file and unchanged input hashes. It preserves all five initialization controls, both protocols, discard horizons, snapshot cadences, zero-action nominal physics, and family-specific diagnostics. Schema v2 explicitly validates both the six required IDs and the nine future 2D targets; arbitrary subsets or CylinderJet-only matrices are rejected. The original v1 file is never rewritten.

## Preparation commands (reference; no CFD)

Synchronize this repository's code to the server first. Use the existing activated `fluidgym-test` environment with the pinned editable upstream. `huggingface_hub` is already an upstream dependency; the optional `.[data]` extra also declares it. There is no need to reinstall torch or rebuild FluidGym for these Python-only changes.

From `/nfs4/jhkim/repos/Fluidgym-Physics`:

```bash
FG_MATRIX=experiments/characterization.v1.json
FG_DATA_ROOT=/home/jhkim/.local/share/FluidGym/initial_domains
FG_PREP="results/preparation-$(date -u +%Y%m%dT%H%M%SZ)"

python -m fluidgym_physics.cli verify-upstream

python -m fluidgym_physics.cli fetch-inputs \
  --matrix "$FG_MATRIX" --data-root "$FG_DATA_ROOT" \
  --output "$FG_PREP/acquisition" --max-download-gib 20

python -m fluidgym_physics.cli preflight \
  --matrix "$FG_MATRIX" --data-root "$FG_DATA_ROOT" \
  --acquisition "$FG_PREP/acquisition" --output "$FG_PREP/full-preflight.json"

python -m fluidgym_physics.cli prepare-primary \
  --matrix "$FG_MATRIX" --preflight "$FG_PREP/full-preflight.json" \
  --output "$FG_PREP/primary"

python -m fluidgym_physics.cli preflight \
  --matrix "$FG_PREP/primary/matrix.json" --data-root "$FG_DATA_ROOT" \
  --acquisition "$FG_PREP/acquisition" --output "$FG_PREP/primary-preflight.json"

python -m fluidgym_physics.cli plan \
  --matrix "$FG_PREP/primary/matrix.json" --output "$FG_PREP/primary-plan.json"
```

Stop on any failing command; do not substitute a missing/failed preflight record. Save the value of FG_PREP if using another shell later. Output files/directories refuse overwrites; use a new preparation directory for another attempt. `--data-root` configures the upstream data parent for that preflight/run process and must end in `initial_domains`. The same explicit path is used for acquisition and preflight, avoiding HOME/NFS configuration differences.

`fetch-inputs` is the **only** network data acquisition command. It uses `safe-autonomous-systems/fluidgym-data`, resolves one full dataset commit SHA, checks all required paths in that revision, checks remote file sizes and local free space, and fetches only missing mandatory statistics/test JSON/test NPZ files. Existing nonempty files must match the selected remote revision; they are not replaced. Empty existing files or conflicting files cause a failure for explicit inspection, not silent repair. No train/val data, optional baseline CSVs, 3D data, initial-state generation, or solver steps are requested.

A staging directory on the data filesystem prevents interrupted transfers from appearing as valid inputs. Downloaded files are verified against LFS SHA-256 or Git blob hashes, then published without replacing existing files. Acquisition records contain the dataset revision, retained/downloaded hashes and failure/completion status. A download cap of 20 GiB applies to the missing payload; free space must cover twice that payload plus a 2 GiB reserve. Actual download bytes are computed from remote metadata, not the CFD output estimate.

If acquisition is interrupted, keep its record and start a new acquisition output directory with `--revision <revision-from-old-request.json>`. Already published valid files are verified and retained. Do not remove data or change the pinned dataset revision automatically to bypass an error. The preflight `--acquisition` option carries official dataset revision/hashes into provenance and supports the primary subset of the full acquired matrix.

Hugging Face APIs used: [dataset metadata](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api) and [revision-pinned downloads](https://huggingface.co/docs/huggingface_hub/package_reference/file_download).

## Budget for review (not measured GPU performance)

| Scope | Environments | Runs | Environment steps | Estimated output | Sequential GPU-hour scenario |
|---|---:|---:|---:|---:|---:|
| Original complete matrix | 15 | 150 | 156,900 | 7.491 GiB | 4.1125–181.375 |
| Primary CylinderJet2D + RBC2D | 6 | 60 | 58,200 | 2.392 GiB | 1.2125–48.5 |

Primary counts: cylinder 3×5×(80+2400)=37,200 steps; RBC 3×5×(200+1200)=21,000. Each environment retains two deterministic repeats (seed 0, no randomization) and three randomized initializations (seeds 11/22/33), for both benchmark and extended continuous protocols.

Timing assumptions remain .05–2 seconds/environment-step with a 1.5× margin for the primary matrix. These were uncalibrated planning scenarios. The completed primary campaign took 18h 15m 45.7s; that observation is not a guarantee for other hardware or matrices. Input dataset size and solver workspaces are excluded from output storage. Primary proposed caps: **72 wall hours, 20 GiB output, 5 GiB free disk reserve, 20 GiB torch peak allocation**. Memory cap is not a demonstrated hardware requirement. Preflight records target GPU memory; clock/cap checks occur at step boundaries and cannot interrupt a hung CUDA call. Numerical checks do not certify grid convergence or long-time physical adequacy.

Review `primary/matrix.json`, `primary/preparation.json`, `primary-plan.json` and `primary-preflight.json` before authorization. Generated draft matrices remain `draft_not_authorized` until explicitly approved. The completed primary campaign used a separately approved copy; the original full matrix remains unapproved. Full preflight has no rollout and therefore does not provide measured per-step GPU costs.

## Approval and supervised execution

The completed primary campaign already has an approval artifact. Do not regenerate it or rerun the campaign for document reproduction. For a newly authorized preparation, `approve-matrix --accept-budget` writes a separate reviewed matrix and approval bound to the preflight input manifest:

```bash
python -m fluidgym_physics.cli approve-matrix \
  --matrix "$FG_PREP/primary/matrix.json" \
  --preflight "$FG_PREP/primary-preflight.json" \
  --output "$FG_PREP/approved-primary" --accept-budget
```

Only when a further execution is explicitly authorized, the supervised launcher uses the existing approval, checks inputs and creates a unique execution directory:

```bash
bash experiments/run-approved-primary.sh "$FG_PREP"
```

Use the server's persistent terminal/job system. The launcher supplies process supervision and a wall-time limit; an external scheduler is needed to protect against supervisor or host failure. It never resumes a failed trajectory by concatenation. Offline analysis can be run independently against an existing campaign into a fresh output directory:

```bash
python -m fluidgym_physics.cli analyze \
  --campaign "$FG_EXEC/campaign" --output "$FG_EXEC/analysis-new"
```
