# Nominal physics characterization

Status (2026-10-14): no campaign trajectories available for analysis in this workspace. No physical results or figures have been fabricated.

The preserved primary scope is `CylinderJet2D-easy-v0`, `CylinderJet2D-medium-v0`, `CylinderJet2D-hard-v0`, `RBC2D-easy-v0`, `RBC2D-medium-v0`, and `RBC2D-hard-v0`.

The planned 60 runs retain benchmark and extended continuous protocols separately, two deterministic repeats and three randomized initializations per environment/protocol. Cylinder contributes 37,200 steps; RBC contributes 21,000. These are planned counts, not measured completion.

Pending completed, integrity-checked trajectories:

- Cylinder: drag/lift time series, long-horizon statistics, supported spectral features, discard sensitivity and variability across initializations.
- RBC: recorded Nusselt number, temperature extrema/mean and volume kinetic energy, with separate protocol statistics.
- Both: deterministic repeat comparisons, initial-domain identities, actual solver time, runtime, GPU allocation peaks and run statuses.

The existing offline analysis pipeline should run against the verified campaign into a new output directory. Its output must be inspected before interpreting the metrics. Independent resets must remain separate trajectories. No stationarity, grid convergence, bifurcation, chaos or robustness conclusion is supported at this stage.
