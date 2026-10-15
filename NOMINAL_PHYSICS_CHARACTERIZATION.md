# Nominal physics characterization

## Current time-axis and termination audit — 2026-10-15

See [Time-axis and execution validation](docs/TIME_AXIS_AND_EXECUTION_VALIDATION.md) for the current source trace, reconstruction conditions, uncertainty, termination classifications and exact offline/next-launch commands. This supersedes earlier blanket FFT withholding: easy extended spectra are permitted only if the full raw record passes the new fixed-native-dt replay/count validation. Raw trajectories are not available locally, so no new physical spectrum or peak has been calculated here. All six targets are adaptive-capable; medium variable counts and unknown timing retain restrictions. The second campaign termination remains UNKNOWN. Progress/signal supervision is corrected without changing solver physics or the approved matrix. No CFD was launched and no approval was generated.


## Current measured partial results — 2026-10-15

This section supersedes earlier pending-analysis statements below, which are historical. Source: operator-supplied `analysis-completed-v2/analysis.json`, archived as `docs/evidence/execution-20261015T010803Z-Rk5NDa/analysis-transcript.json`. Raw trajectories and figures have not been transferred; server-side analysis reports 15 completed runs analyzed and one incomplete run excluded. Forty-four planned runs were not started in this attempt. The approved scope remains all six environments and 60 runs.

| Environment / protocol / initialization | Mean drag | Drag SD | Mean lift | Lift SD | Retained samples |
|---|---:|---:|---:|---:|---:|
| CylinderJet2D-easy-v0__benchmark__ic-1 | 3.32819190 | 0.02787720 | -0.07197411 | 0.86628642 | 80 |
| CylinderJet2D-easy-v0__benchmark__ic-2 | 3.32767246 | 0.02776939 | -0.07657637 | 0.86499732 | 80 |
| CylinderJet2D-easy-v0__benchmark__ic-3 | 3.32863551 | 0.02805104 | -0.08828551 | 0.86707245 | 80 |
| CylinderJet2D-easy-v0__benchmark__repeat-a | 3.32811007 | 0.02815476 | -0.03826655 | 0.86725706 | 80 |
| CylinderJet2D-easy-v0__benchmark__repeat-b | 3.32811007 | 0.02815476 | -0.03826655 | 0.86725706 | 80 |
| CylinderJet2D-easy-v0__extended__ic-1 | 3.32805480 | 0.02629603 | -0.02029187 | 0.85410704 | 2000 |
| CylinderJet2D-easy-v0__extended__ic-2 | 3.32805298 | 0.02629546 | -0.02011270 | 0.85414481 | 2000 |
| CylinderJet2D-easy-v0__extended__ic-3 | 3.32805614 | 0.02629662 | -0.01944343 | 0.85439539 | 2000 |
| CylinderJet2D-easy-v0__extended__repeat-a | 3.32808990 | 0.02630158 | -0.02151226 | 0.85418706 | 2000 |
| CylinderJet2D-easy-v0__extended__repeat-b | 3.32808990 | 0.02630158 | -0.02151226 | 0.85418706 | 2000 |
| CylinderJet2D-medium-v0__benchmark__ic-1 | 3.15777393 | 0.11849026 | -0.01964243 | 1.65975796 | 80 |
| CylinderJet2D-medium-v0__benchmark__ic-2 | 3.15776836 | 0.11861873 | -0.02723773 | 1.65856139 | 80 |
| CylinderJet2D-medium-v0__benchmark__ic-3 | 3.15830745 | 0.11949335 | -0.02482596 | 1.65898479 | 80 |
| CylinderJet2D-medium-v0__benchmark__repeat-a | 3.15862247 | 0.11865076 | -0.01817763 | 1.66064683 | 80 |
| CylinderJet2D-medium-v0__benchmark__repeat-b | 3.15862247 | 0.11865076 | -0.01817763 | 1.66064683 | 80 |

Benchmark and extended results are kept separate. Easy benchmark uses equal-weight sample moments; easy extended and medium benchmark use time-weighted piecewise-linear interpolant moments on recorded solver time. Standard deviations across these estimator types are not directly interchangeable measures of instantaneous fluctuations. Extended easy statistics retain 2,000 samples after discarding 400 of 2,400 steps. No independent episodes are concatenated.

All three available deterministic pairs (easy benchmark, easy extended, medium benchmark) have zero maximum absolute difference in the recorded drag and lift sequences. This establishes repeatability for these observed sequences on this setup, not full-field identity or cross-hardware reproducibility.

Across the three randomized easy extended runs, mean drag ranges from 3.32805298 to 3.32805614 and mean lift from -0.02029187 to -0.01944343. The similar means are descriptive observations, not proof of independent initial conditions or stationarity. For medium benchmark repeat-a, removing the first quarter of retained samples changes mean lift from -0.01817763 to 0.13308696, demonstrating window sensitivity. Easy extended repeat-a mean lift changes from -0.02151226 to -0.02111287; a smaller change alone does not establish stationarity.

All five easy extended FFTs are withheld because recorded solver-time sampling is nonuniform; no Strouhal estimate is available. Time-series PNGs and aggregate.png were generated on the server by the analysis pipeline but have not been supplied for local inspection. No time-series figure is reconstructed from summary statistics.

CylinderJet2D-medium extended repeat-a is excluded (no terminal status, previously observed 580 recorded steps). CylinderJet2D-hard and all RBC2D variants have no completed results in this attempt. RBC temperature, heat transport and convection statistics therefore remain unavailable. Complete nominal coverage and better clock/solver diagnostics are prerequisites for assessing controlled Reynolds/Rayleigh shifts; no method is selected and no robustness claim is supported.


## Partial campaign evidence — 2026-10-15

Five CylinderJet2D-easy benchmark runs completed, covering both repeat controls and three randomized initializations. First extended repeat failed after 253 recorded steps; all other variants remain unexecuted in this attempt. Only status summaries are available locally, not trajectories or analysis. Drag/lift metrics, repeatability, cross-initialization statistics and figures therefore remain pending. Different trajectory or NPZ hashes alone do not establish physical non-repeatability. RBC observables are unavailable. The failed extended run did not reach its planned 400-step discard horizon and cannot support the planned post-transient long-horizon analysis.


Status (2026-10-14): no campaign trajectories available for analysis in this workspace. No physical results or figures have been fabricated.

The preserved primary scope is `CylinderJet2D-easy-v0`, `CylinderJet2D-medium-v0`, `CylinderJet2D-hard-v0`, `RBC2D-easy-v0`, `RBC2D-medium-v0`, and `RBC2D-hard-v0`.

The planned 60 runs retain benchmark and extended continuous protocols separately, two deterministic repeats and three randomized initializations per environment/protocol. Cylinder contributes 37,200 steps; RBC contributes 21,000. These are planned counts, not measured completion.

Pending completed, integrity-checked trajectories:

- Cylinder: drag/lift time series, long-horizon statistics, supported spectral features, discard sensitivity and variability across initializations.
- RBC: recorded Nusselt number, temperature extrema/mean and volume kinetic energy, with separate protocol statistics.
- Both: deterministic repeat comparisons, initial-domain identities, actual solver time, runtime, GPU allocation peaks and run statuses.

The existing offline analysis pipeline should run against the verified campaign into a new output directory. Its output must be inspected before interpreting the metrics. Independent resets must remain separate trajectories. No stationarity, grid convergence, bifurcation, chaos or robustness conclusion is supported at this stage.
