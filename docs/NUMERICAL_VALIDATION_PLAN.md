# Numerical validation plan

The earlier document described a CPU-only authoring state and separate C0/C1/C2 pilots. It is superseded by [the integrated characterization workflow](CHARACTERIZATION_WORKFLOW.md) and [versioned matrix](../experiments/characterization.v1.json).

Evidence distinction: the user reports 25 passing tests including three real-environment tests on a CUDA server. No server artifacts were provided here. Nominal runtime verification does not constitute long-time physical characterization.

The matrix runner preflights the entire campaign, checks loaded transport coefficients, captures solver False returns, checks native fields and measured solver-clock progress each step, preserves failed/incomplete runs, and enforces reviewed resource caps. It never concatenates reset episodes or silently repairs numerical failures. No separate environment pilots are requested. Full matrix/budget review precedes any campaign launch.

Cylinder observations arrive at .25 nominal time intervals. The solver clock, not `env.time_passed`, validates the interval. Drag/lift are outer-solver-step averages, so their spectra include temporal averaging. A benchmark episode has only 80 samples; no shedding peak is reported from benchmark trajectories. Extended runs retain 2000 samples after discard (500 nominal time units), giving nominal frequency-bin spacing .002. Candidate peaks still require enough resolved cycles and stationarity review; no zero-padding is used to claim improved physical resolution.

RBC uses native volume-weighted Nu, temperature and energy diagnostics. Airfoil uses its own force ratio. Neither receives cylinder-specific spectral interpretation. Native residual histories, divergence, wall/boundary flux audits and grid/time-convergence remain unresolved measurements and must not be represented as passed checks.
