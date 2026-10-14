# Nominal characterization workflow v1

## Architecture and implementation scope

The existing package has small modules for strict nominal CylinderJet2D configuration, AST inspection, pinned-upstream verification, CUDA construction/effective readback, and JSON provenance. Those interfaces remain available. The complete workflow adds:

- `inventory.py`: safe AST evaluation of all registered defaults/overrides, without importing upstream.
- `characterization.py`: strict matrix validation, deterministic run expansion, hashes, exclusive JSON writes, and budget calculation.
- `runner.py`: whole-matrix preflight, one continuous trajectory per run, numerical failure guards, immutable output namespaces.
- `diagnostics.py` and `analysis.py`: family-specific metrics and offline plots/statistics, with no reset concatenation.

No upstream source, physical parameters, action distributions, or RL algorithms are changed. A fresh environment per run also avoids hidden actuator-state carryover across resets. Legacy `NominalEnvConfig` remains CylinderJet2D-specific; the matrix is the configuration boundary for the broader workflow.

## Reviewable matrix and budget

`experiments/characterization.v1.json` is **draft_not_authorized**. It includes all 15 registered 2D variants (6 cylinder, 6 RBC including wide, 3 airfoil) and names all 24 deferred 3D variants. Each 2D variant gets two protocols × five initializations = 10 runs:

| Protocol | Cylinder | RBC | Airfoil |
|---|---:|---:|---:|
| Benchmark | 80 steps / 20 time units | 200 / 200 | 300 / 75 |
| Extended continuous | 2400 / 600 | 1200 / 1200 | 2400 / 600 |
| Extended discard | 400 / 100 | 200 / 200 | 400 / 100 |
| Snapshot interval | 20 steps / 5 | 20 / 20 | 20 / 5 |

All scalar observations are measured each environment step. Sparse field snapshots support qualitative evolution and later spatial analyses; their cadence is not suitable for all temporal spectral analyses. Initial and every 20th-step snapshots contain public velocity/pressure and RBC temperature, uncompressed NPZ, with actual dtype/shape recorded. No full observations are stored each step; observation finiteness is checked. Scalar logs contain reward, physical observables, solver time/counter, nominal reported time, wall cost and peak allocated GPU memory.

Initializations: seed 0, randomize=False twice for deterministic repeatability; seeds 11/22/33, randomize=True for variability. Randomized runs can select the same saved index but receive different perturbations; index is recorded. They are not claimed to be statistically independent realizations. Dataset split is test. Zero action is used throughout with official action processing enabled. No controller is fitted.

Extended runs reset with the official constructor horizon, then change only the private `_episode_length` termination counter (the public property has no setter); they are physics-only runs and not official benchmark scores. This ordering matters because airfoil randomized warm-up depends on the horizon. No solver or physical parameter changes at extension. The two horizons and extension mechanism are recorded. Benchmark runs preserve the registered horizon and default processing; the nonrandomized pair is a repeatability diagnostic rather than standard randomized benchmark evaluation. Benchmark and extended results are never pooled.

Totals: **150 runs, 156,900 environment steps, approximately 7.49 GiB output**. Planning timing scenarios are **0.05–2 seconds/step for cylinder/RBC and 0.1–5 for airfoil**, plus a factor 1.5 margin: **4.11–181.38 GPU-hours sequentially**. These are explicit assumptions, not measured GPU timings or confidence bounds. Compilation, unusually expensive adaptive stepping, and reset costs can exceed the margin. Existing datasets are excluded from output storage and are measured in the preflight manifest.

Proposed caps: 240 wall hours, 100 GiB output, 5 GiB free disk reserve, 20 GiB torch peak allocated GPU memory. These are reviewable stopping limits, not assertions of required VRAM. Caps are checked at environment-step boundaries; one in-flight solver step/constructor/reset or snapshot can exceed a cap. An external job wall timeout is required for a hung CUDA call. The runner never retries, restarts a failed trajectory, reduces fidelity, or silently shortens the requested horizon. Actual per-step wall cost/peak memory becomes available as part of the authorized integrated run, not separate environment pilots.

## 3D estimates before scheduling

These source-derived costs concern float32 public velocity+pressure (+temperature for RBC) snapshots. They exclude solver workspaces, gradients, geometry, initialization archives, rendering scratch memory, and analysis copies.

| Family | Native cells (source estimate) | One output snapshot | 121 snapshots/run |
|---|---:|---:|---:|
| CylinderJet3D easy / medium / hard | block-dependent; inspect saved grids | 72 / 172 / 579 MiB | 8.6 / 20.3 / 68.5 GiB |
| RBC3D standard / wide | 167,936 / 671,744 | 24.9 / 99.6 MiB | 2.94 / 11.77 GiB |
| TCF small / large | 262,144 / 1,048,576 | 10.1 / 40.5 MiB | 1.20 / 4.79 GiB |
| Airfoil3D | six blocks × 96 spanwise cells; hard refines tail | 206 MiB | 24.3 GiB |

For cylinder, extrusion alone multiplies native work/storage by about 24/32/48 compared with the corresponding 2D mesh; hard additionally changes the cross-section. Airfoil extrusion contributes about ×96 before hard-tail changes. RBC's cell estimates are exact construction formulas, but runtime costs also depend on substeps and solver iterations. Native float32 primary fields alone require cells×(dimensions+pressure+temperature)×4 bytes; total GPU memory is much larger and cannot be inferred from this lower bound. No credible hardware-specific 3D time upper bound is available here. All 3D cases are inventory-only and the runner rejects scheduling them in v1. Their spanwise metrics/MARL contracts need dedicated adapters before activation.

## Commands

Install the analysis/test extras in an appropriate environment. CUDA runtime requires the locked upstream's supported Python range (>=3.10,<3.14), torch 2.9.*, CUDA extension and an editable install from `third_party/fluidgym`; a PyPI FluidGym installation at another path is rejected.

```bash
pip install -e '.[dev]'
fluidgym-physics verify-upstream
fluidgym-physics inventory
fluidgym-physics plan --matrix experiments/characterization.v1.json
python -m pytest -q
```

On the CUDA host, preflight can check dependencies, import identity, compiled-backend hash and all required local data without constructing environments or advancing CFD:

```bash
fluidgym-physics preflight --matrix experiments/characterization.v1.json
```

Dataset placement is an explicit separate operation. The runner never downloads or regenerates it. Preflight requires all ten selected-mode domain JSON/NPZ pairs and reference statistics for each unique dataset; shared cylinder jet/rotation datasets are hashed once. Optional baseline CSVs are hashed when present. Input hashes are rechecked immediately before each run. Invalid loaded fields/coefficients abort after reset; file existence alone is not physical validation.

After review and authorization of the full matrix and budget, save a reviewed matrix version with `review_status: reviewed`, run `plan` to obtain its SHA-256, and supply that exact digest:

```bash
fluidgym-physics run --matrix experiments/characterization.reviewed.json \
  --reviewed-sha256 <SHA-256-from-plan> --output results/campaign-unique-id
fluidgym-physics analyze --campaign results/campaign-unique-id \
  --output results/analysis-unique-id
```

The review gate reflects the user's campaign execution policy. There is no per-environment approval/pilot loop. Do not mark the matrix reviewed merely to test the CLI. A new campaign output directory is mandatory; existing results are never overwritten or resumed. Abrupt process death leaves an incomplete run without terminal status, excluded by analysis. Normal failures write terminal failure artifacts and stop the entire matrix. Complete-run manifests cover requests, runtime provenance, scalar trajectories and field snapshots. Analysis verifies hashes and writes into a new directory.

## Analysis and evidence limits

`analysis.json` records per-run statistics and separate deterministic max-absolute differences and randomized per-run means. PNGs show each time series, extended cylinder PSDs and cross-run means. Four contiguous block means and later-window sensitivity make drift visible; there is no automatic stationarity or convergence claim. No IID error bars are applied to autocorrelated samples. Long horizons improve resolution but do not guarantee enough independent samples, particularly for convection.

The runner checks native velocity/pressure/temperature each step, loaded domain/block viscosity, RBC diffusivity, finite observations/rewards/metrics, solver clock increments and termination semantics. A Python guard promotes solver False returns to exceptions. Residual histories, solver fallback event counts and native divergence are marked missing, not zero. Snapshot arrays are resampled and not a conservative native-state restart format.

No physical trajectories are committed with this implementation. Synthetic tests exercise analysis and failure handling, not fluid mechanics. Aggregate physical findings and regime conclusions remain pending the reviewed CUDA campaign.
