# Implementation status

Updated 2026-10-14. Source pin: `50071140b73a2a917fb96d33522a769f903f8c27`, src tree `8a8476b966e496341676ea36384589028f4dc450`. The initially absent submodule was initialized and verified without modifying upstream source.

| Item | Current evidence |
|---|---|
| Pinned integrity, legacy CylinderJet2D config/source inspection/provenance | Reused; CPU checks pass. Legacy factory now checks import identity, exact required data files and propagates randomization preference. |
| Existing nominal CUDA tests | User reports **25 passing tests including three real-environment tests** on the server. No raw report, GPU metadata or trajectory artifacts were available locally; not independently reproduced here. |
| Complete source inventory | 39 registered variants inspected; checked-in JSON matches AST extraction. Family physics, numerical/task co-changes, fields, rewards and data dependencies documented. |
| Versioned complete matrix | Draft: 15 2D variants × two protocols × five initializations; all 24 3D variants explicitly deferred. Not reviewed/authorized for execution. |
| Resource estimates | 156,900 steps, about 7.49 GiB output, uncalibrated 4.11–181.38 GPU-hour scenario range including 1.5× margin. 3D snapshot/cell estimates documented; measured runtime/VRAM unavailable. |
| Integrated runner | Implemented with whole-matrix preflight, local archive checks/hashes, code/backend/package provenance, solver-return and field/clock checks, resource caps, exclusive run outputs and failure artifacts. Real execution of this new runner is pending the reviewed CUDA campaign. |
| Benchmark/extended separation | One reset per trajectory; official reset horizon retained, termination counter extended only afterward. No episode concatenation or solver-source changes. |
| Physical analysis/plots | Implemented for cylinder forces/qualified lift PSD, RBC Nu/temperature/native kinetic energy, airfoil forces/ratio. Synthetic tests pass. Physical results are not yet available. |
| Local tests | **51 passed, 3 skipped** in the temporary Python 3.14 CPU test environment. CUDA tests skipped because torch/CUDA unavailable. Runtime preflight enforces upstream Python >=3.10,<3.14; this CPU result is not CUDA compatibility evidence. |
| Fluidgym-RL pin comparison | Still unknown; repository not inspected as part of this scope. |
| Dynamics shifts, RL, solver changes | None implemented. Feasibility assessment updated without choosing a shift method. |

Tests exercise all CPU CLI entry points, inventory coverage, strict matrix rejection, missing/invalid local inputs, review gate, artifact no-overwrite/hash checks, known synthetic spectra and withholding, nonuniform clocks, family metric contracts, effective coefficient mismatch, solver-return failure, single-reset trajectory execution/failure artifacts, and offline aggregation. Fake environments and synthetic signals validate software contracts only.

The earlier source maps remain as historical CylinderJet2D audits with prominent evidence updates. The current authoritative workflow is [CHARACTERIZATION_WORKFLOW.md](CHARACTERIZATION_WORKFLOW.md); the family inventory is [ENVIRONMENT_PHYSICS_INVENTORY.md](ENVIRONMENT_PHYSICS_INVENTORY.md).

Outstanding scientific evidence: real new-runner execution, dataset stationarity/lineage, calibrated compute budget, numerical residual/divergence/flux audits, grid/time convergence, sufficiently sampled physical variability and controlled interventions. No comprehensive physical characterization or aggregate physical finding is claimed.

## Subsequent server report: import-path blocker

The supplied server log reports **51 passed, 3 errors** under Python 3.12. All three errors occur in the shared CUDA fixture at `_installed_upstream`, before environment construction or stepping. The preflight command stops at the same check. The original message omitted the actual import path, so the log alone cannot distinguish an absent package from a wheel or another checkout. This does not invalidate the earlier reported 25-test nominal run; the new provenance guard adds an installation requirement.

The error now reports interpreter, actual/expected import paths and the editable-install command. The workflow documents installing upstream separately using the existing CUDA toolchain, without replacing dependencies or downloading datasets. Server installation repair and subsequent runtime verification remain pending.

## Subsequent server report: local datasets

The server now resolves FluidGym to the pinned submodule and passes the import check. Preflight stops on missing/empty Re250 cylinder statistics and all ten test JSON/NPZ pairs at `/home/jhkim/.local/share/FluidGym/initial_domains`. The old fail-fast listing does not establish availability of later datasets. Added a CUDA-free `input-report` command and whole-matrix missing-input summary, deduplicating 15 environment rows into 12 dataset directories. No data was downloaded or regenerated; runtime characterization remains pending.
