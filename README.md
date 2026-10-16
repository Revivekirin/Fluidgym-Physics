# FluidGym-Physics

Physics-first inspection and characterization of the **official**, pinned FluidGym benchmark. Downstream RL lives separately in `Fluidgym-RL`. This repository does not implement RL algorithms or physical dynamics shifts, modify upstream solver physics, or implicitly download datasets.

The primary nominal campaign `execution-20261015T045202Z-NoMY5u` completed **60 runs and 58,200 environment steps** across CylinderJet2D and RBC2D easy/medium/hard, with separate benchmark and extended continuous protocols. The offline audit checked all 2,970 field snapshots and 3,213 recorded output hashes with no missing or corrupt campaign output. Recorded campaign wall time was **18h 15m 45.7s**. Original server input files and the compiled CUDA binary are not present locally; verification of their recorded provenance is distinct from rehashing their bytes.

## Final results

- [Final nominal characterization](docs/FINAL_NOMINAL_CHARACTERIZATION.md): completion, physical metrics, repeatability and evidence.
- [Physical observation comparison](docs/PHYSICAL_OBSERVATION_COMPARISON.md): Cylinder/RBC time series, fields and initialization sensitivity.
- [Numerical uncertainty and limitations](docs/NUMERICAL_UNCERTAINTY_AND_LIMITATIONS.md): validated time axes, telemetry and unresolved diagnostics.
- [Controlled-shift design requirements](docs/CONTROLLED_SHIFT_DESIGN_REQUIREMENTS.md): future intervention candidates and required validation; no shift is selected or implemented.

## Reproduction and technical references

```bash
git submodule update --init --recursive
pip install -e '.[dev]'
fluidgym-physics verify-upstream
fluidgym-physics inventory
python -m pytest -q
```

- [Complete physics inventory](docs/ENVIRONMENT_PHYSICS_INVENTORY.md) and [machine-readable source values](docs/environment_inventory.v1.json): all 39 registrations.
- [Characterization workflow](docs/CHARACTERIZATION_WORKFLOW.md): protocols, diagnostics and deferred 3D resource estimates.
- [Server preparation and execution reference](docs/SERVER_EXECUTION.md): explicit acquisition, preflight and approval mechanism.
- [Time-axis and execution validation](docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md): stepping, reconstruction and process supervision.

The original `experiments/characterization.v1.json` remains an unapproved 15-variant expansion matrix (150 runs, 156,900 steps). It is separate from the completed, approved six-environment primary matrix. Existing results and approvals are retained; a further CFD campaign requires authorization.

Core inventory/planning uses the Python standard library. Analysis/test extras add NumPy, matplotlib and pytest. CUDA execution requires the exact editable pinned upstream checkout, Python >=3.10,<3.14, torch 2.9.*, CUDA/PISOtorch and explicitly prepared local datasets. Output directories are exclusive; independent trajectories are never concatenated or resumed. See the final reports for scientific limitations and recorded validation results.
