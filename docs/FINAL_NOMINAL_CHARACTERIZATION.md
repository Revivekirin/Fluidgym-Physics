# Final nominal characterization

Campaign: `execution-20261015T045202Z-NoMY5u`. Audit date: 2026-10-16. No CFD, upstream modification, new approval or physical intervention was performed for this analysis.

Evidence labels used throughout: **Measured** = recorded values, verified files, or a directly computed descriptive statistic; **Inference** = interpretation supported by those observations; **Unresolved** = explanation or validation not established by this campaign. None of the results establishes stationarity, grid convergence, bifurcation, chaos or physical-shift robustness.

## Completion and integrity

**Measured.** All 60 requested runs completed, with 58,200 scalar records, 2,970 field snapshots, zero failed/excluded runs and 66 existing analysis figures. The audit verified 3,213 recorded file hashes, decoded every NPZ and checked names/shapes/dtypes/finite values, checked control-step continuity and monotone solver clocks/counters, compared request manifests to the approved matrix, and decoded all 66 PNGs. No missing or corrupt campaign output was detected. Approval binds the copied matrix and the 136-file input manifest. The pinned clean source commit is `50071140b73a2a917fb96d33522a769f903f8c27`; the official dataset revision recorded in approval is `a8c00235a814828441a0c5638e6f803ef62bfa31`. All 25 implementation files recorded in campaign provenance match their local counterparts at audit time.

**Measured.** Supervisor status is SUCCESS, return code 0, no KILL escalation. Wall time is 65,745.713 seconds (18h 15m 45.7s); runner-only time is 65,739.005 seconds. Device telemetry has 13,147 samples, maximum gap 5.099 seconds, peak 476 MiB and an empty monitor-error log. Maximum recorded PyTorch allocation is 137.358 MiB. These are different memory measures; device telemetry is sampled and includes other processes.

**Unresolved.** The 136 original server input files, compiled CUDA binary and original acquisition/preflight artifacts were not copied into this workspace. Their recorded manifest/hash relationships were verified; their absent bytes cannot be independently rehashed here. This is not output corruption. Native residual histories, fallback-event counts and divergence norms remain missing.

[Machine-readable integrity evidence](evidence/final-nominal-20261015/integrity.json). A separate read-only offline reanalysis is saved under `results/final-nominal-audit-v1/reanalysis`; original outputs remain untouched. **Measured:** all comparisons match; two half-window differences vary by 3.47e-18 and differences in PSD numeric arrays are at most 8.53e-14 absolute, consistent with floating-point FFT variation across hosts (**Inference**, not evidence of changed dynamics).

## Protocol-separated reference results

**Measured.** The following means use `repeat-a`, not a pooled five-run average. Its repeat-b is a numerical repeat, not an additional independent physical realization. Benchmark has 80 Cylinder / 200 RBC samples. Extended statistics retain 2,000 Cylinder / 1,000 RBC samples after discarding 400 / 200 steps. All controls are nominal zero action.

Cylinder columns are mean drag and mean lift; RBC columns are mean Nusselt and mean volume kinetic energy.

| Environment | Protocol | Mean drag / Nu | Mean lift / kinetic energy |
|---|---|---:|---:|
| CylinderJet2D-easy | benchmark | 3.3281101 | -0.0382666 |
| CylinderJet2D-easy | extended | 3.3280897 | -0.0216431 |
| CylinderJet2D-medium | benchmark | 3.1586225 | -0.0181776 |
| CylinderJet2D-medium | extended | 3.1569571 | -0.0225866 |
| CylinderJet2D-hard | benchmark | 3.6253006 | 0.0232358 |
| CylinderJet2D-hard | extended | 3.6218428 | -0.0446644 |
| RBC2D-easy | benchmark | 4.8960839 | 0.0438840 |
| RBC2D-easy | extended | 4.8962385 | 0.0438834 |
| RBC2D-medium | benchmark | 6.9733887 | 0.0586552 |
| RBC2D-medium | extended | 6.9722043 | 0.0586619 |
| RBC2D-hard | benchmark | 7.9726871 | 0.0624928 |
| RBC2D-hard | extended | 7.9818174 | 0.0624954 |

**Measured.** All 12 deterministic pairs have zero maximum scalar-observable differences over their recorded sequences. All saved RBC field arrays also match exactly within pairs. Cylinder resampled field arrays differ by at most 9.54e-7 across inspected paired snapshots. **Inference:** scalar repeatability is strong on this setup; exact scalar agreement must not be reported as bitwise equality of every field. **Unresolved:** cross-GPU/platform reproducibility and sensitivity to native solver nondeterminism (deterministic algorithms were disabled).

## Cylinder findings

**Measured.** Easy extended lift PSD has a candidate peak at 0.274000006 in all five runs, resolution 0.00200000004 and approximately 137 candidate cycles in the retained window. Only these five extended records pass the full fixed-native-dt count/clock replay required by the analysis. Medium and hard show adaptive subdivision and do not receive FFT/Strouhal estimates. This is a supported shedding-frequency candidate, not a demonstrated asymptotic frequency or numerical convergence result.

**Measured.** Easy randomized extended mean drag spans only 3.3280580–3.3280609; zero-lag lift correlations with repeat-a are 0.846, 0.799 and 0.554. Aligning by -1, -1 and -2 samples within a predeclared ±7-sample search raises them to 0.991, 0.977 and 0.993. **Inference:** substantial pointwise differences can be explained by temporal phase while time-averaged drag stays close. This is a descriptive alignment, not a redefinition/resampling of trajectories or independent evidence of frequency stability.

**Measured.** Benchmark versus extended lift means depend on the window, especially hard (+0.02324 versus -0.04466). The extended randomized drag ranges are 3.1570092–3.1570883 (medium) and 3.6220688–3.6224953 (hard). **Unresolved:** difficulty changes combine physical and numerical/task differences; these are not causal Reynolds-number effects. The figures and per-run window tables in the comparison document retain this distinction.

## RBC findings

**Measured.** Easy extended Nu is approximately 4.89622–4.89624 across the sampled initializations. Medium `ic-1` instead has Nu 6.09898 and kinetic energy 0.0452607 versus repeat-a 6.97220 and 0.0586619. Hard `ic-1` likewise has Nu 7.21048 and energy 0.0481728 versus repeat-a 7.98182 and 0.0624954. These are about 12.5% / 22.8% lower for medium and 9.7% / 22.9% lower for hard (Nu / energy).

**Measured.** `ic-1` selects test domain index 1; repeat-a/b select 0, ic-2 selects 7 and ic-3 selects 8. Temperature/velocity plates show broader, approximately two-roll structure for medium/hard ic-1, compared with approximately four-roll structures in the other sampled initializations. The difference is visible at reset and persists at steps 200, 600 and 1,200; the scalar difference also persists across all four retained blocks and the last quarter. **Inference:** the initial-domain structure is a plausible explanation for the persistent heat-transport/energy separation. **Unresolved:** attraction basins, uniqueness, transitions, very-long-time persistence and whether these are distinct attractors. No bifurcation claim is justified.

## What this enables next

**Inference / design proposal, not execution.** First use the validated nominal sequences to test whether a representation preserves Cylinder phase and RBC spatial organization/heat transport, with splits by initial-domain identity. Next close timing/measurement gaps before attributing model error to physics. Only then design action-excitation and controlled-parameter experiments in a separately reviewed protocol. These zero-action data do not identify actuator response or validate planning performance. RL/TD-MPC implementation belongs in `Fluidgym-RL`; no algorithm or physical-shift method is selected here.

Read [physical comparisons](PHYSICAL_OBSERVATION_COMPARISON.md), [numerical uncertainty](NUMERICAL_UNCERTAINTY_AND_LIMITATIONS.md), and [intervention design requirements](CONTROLLED_SHIFT_DESIGN_REQUIREMENTS.md) for evidence, figures and remaining tests.

## Final validation record

**Measured.** Final audit returned zero errors after manifest-coverage and GPU UUID/range checks. CPU tests: **106 passed, 3 CUDA-dependent skipped**. No new CFD ran. All 30 benchmark trajectories exactly match their corresponding extended prefixes for physical/time records (wall time and allocator peaks excluded); these are not independent training/test samples. Reanalysis differences and generated-figure hashes are recorded in [reanalysis-and-figures.json](evidence/final-nominal-20261015/reanalysis-and-figures.json).
