# FluidGym-Physics

Physics-first inspection and characterization of the **official**, pinned FluidGym benchmark. No RL algorithms, solver edits, parameter shifts, or implicit dataset downloads. Downstream RL lives in `Fluidgym-RL`.

```bash
git submodule update --init --recursive
pip install -e '.[dev]'
fluidgym-physics verify-upstream
fluidgym-physics inspect-config --env-id CylinderJet2D-easy-v0
fluidgym-physics inventory
fluidgym-physics plan --matrix experiments/characterization.v1.json
python -m pytest -q
```

The source inventory covers all 39 registrations. The draft characterization matrix schedules 15 2D variants and explicitly defers 24 3D variants: 150 independent runs, 156,900 steps, approximately 7.49 GiB output and an **uncalibrated 4.11–181.38 GPU-hour planning range**. The matrix is not authorized for execution. Review its assumptions/caps on the target GPU first; no per-environment pilot approvals are required.

The reusable runner preflights all local data, records full input/code/backend provenance, guards numerical failures, and keeps benchmark and extended continuous trajectories separate. Offline analysis provides family-specific diagnostics, repeatability/variability comparisons and plots. No physical campaign results have been collected by this implementation.

The user reports **25 passing tests on the CUDA server, including three real-environment tests**. Those artifacts are not in this checkout; this is nominal runtime evidence, not comprehensive physical characterization. See [implementation status](docs/IMPLEMENTATION_STATUS.md).

- [Complete physics inventory](docs/ENVIRONMENT_PHYSICS_INVENTORY.md) and [machine-readable source values](docs/environment_inventory.v1.json)
- [Workflow, matrix, resource estimates, commands and limitations](docs/CHARACTERIZATION_WORKFLOW.md)
- [Controlled-shift feasibility assessment](docs/SHIFT_FEASIBILITY_ASSESSMENT.md)

Core inventory/planning uses only the Python standard library. Analysis/test extras add NumPy/matplotlib/pytest. Runtime requires the exact editable upstream checkout, supported Python >=3.10,<3.14, torch 2.9.*, CUDA/PISOtorch, and explicitly prepared local datasets. Output directories and completed artifacts are never overwritten by the tools.
