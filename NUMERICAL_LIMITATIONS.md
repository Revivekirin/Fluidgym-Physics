# Numerical limitations

Status (2026-10-14): campaign evidence pending. No observed server numerical failure or successful rollout is asserted by this report.

- Full preflight validates inputs/runtime prerequisites without CFD; it does not establish numerical stability or measured execution cost.
- Primary planning estimates are 2.392 GiB output and 1.2125–48.5 sequential GPU hours, using uncalibrated timing assumptions. Actual wall time, GPU memory and output size are unavailable.
- Proposed primary limits in the source workflow are 72 wall hours, 20 GiB output, 5 GiB disk reserve and 20 GiB torch allocation. The actual reviewed artifact must be checked. Torch allocation is not total device memory usage; external GPU telemetry is needed for that distinction.
- In-process budget checks occur at step boundaries. An external wall-time limit must be verified before launch.
- Native solver residual histories, divergence diagnostics and fallback-event counts are not supplied by the existing recording pipeline. Finite-field and solver-progress checks cannot replace these diagnostics or certify numerical convergence.
- Extended trajectories and discard-window comparisons alone do not prove stationarity. Difficulty variants mix physical, discretization and task changes and cannot establish grid convergence by direct comparison.
- Deterministic repeat agreement and variability across randomized initial domains answer different questions; neither is currently measured here.

Subsequent controlled physical shifts remain a research proposal. After nominal results are available, assess parameter access, initial-domain compatibility, observable adequacy and numerical validity for each family. Reynolds/Rayleigh changes require independently justified controls and compatible initial conditions; easy/medium/hard contrasts alone do not isolate their effects. No shift method is selected or implemented.
