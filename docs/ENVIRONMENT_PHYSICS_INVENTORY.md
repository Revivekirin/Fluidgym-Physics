# Physics inventory at the pinned revision

Evidence: inspected official source at `50071140b73a2a917fb96d33522a769f903f8c27`; not a characterization result. Paths below are relative to `third_party/fluidgym/src/fluidgym`. The machine-readable companion `environment_inventory.v1.json` contains **all 39 registrations**, merged defaults, explicit variant overrides, initial-domain identifiers, output shapes, and source locations. `fluidgym-physics inventory` regenerates it without importing CUDA libraries. Tests compare the checked-in inventory to the source.

## Registration and difficulty coverage

Each row represents easy/medium/hard registrations, in that order. Wide/both/large are separate task or geometry choices, not extra difficulty levels.

| Registry family | Physical parameters easy / medium / hard | Discretization changes | Task differences |
|---|---|---|---|
| CylinderJet2D | Re 100 / 250 / 500 | angular resolution 24 / 32 / 32 | scalar paired jets |
| CylinderRot2D | Re 100 / 250 / 500 | 24 / 32 / 32 | scalar cylinder wall speed |
| CylinderJet3D | Re 100 / 250 / 500 | 24 / 32 / 48, also spanwise resolution | 8 spanwise jet actuators |
| RBC2D | Ra 80,000 / 400,000 / 800,000; Pr .7 | CFL .8 / .5 / .5; 96×61 cells | 12 heaters, L/H=π |
| RBC2D-wide | same Ra, Pr | same CFL; 192×61 cells | 24 heaters, L/H=2π |
| RBC3D | Ra 6,000 / 8,000 / 10,000; Pr .7 | CFL .5 throughout; 64×41×64 cells | 8×8 heaters, horizontal size π×π |
| RBC3D-wide | same Ra, Pr | CFL .5; 128×41×128 cells | 16×16 heaters, horizontal size 2π×2π |
| TCFSmall3D-bottom | Reτ 180 / 330 / 550 | nominal resolution_y=65 generates 64 wall-normal cells; 64×64×64; time scale changes with Reτ | L=π, D=π/2, bottom wall actuation |
| TCFSmall3D-both | same | same | both walls actuated |
| TCFLarge3D-bottom | same | 128×64×128 cells | L=2π, D=π, bottom wall |
| TCFLarge3D-both | same | same | both walls |
| Airfoil2D | Re 1000 / 3000 / 5000 | same grid construction arguments | 3 suction-side jets, 10° angle |
| Airfoil3D | same | 96 spanwise cells; hard uses tail growth 1.001 instead of 1.01 | 4 spanwise agents, 3 jets each |

Loaded grids are authoritative: source construction formulas are not evidence that existing datasets contain those exact grids. Runtime provenance records block shapes and checks loaded transport coefficients. Harder registered variants are not clean single-factor interventions when resolution, CFL, reference statistics, or initial-domain ensembles also change.

## Governing models and numerics

All families solve incompressible viscous flow with PISO pressure/velocity coupling: ∇·u=0, ∂t u+u·∇u=−∇p+ν∇²u+f. RBC additionally advects/diffuses temperature, ∂t T+u·∇T=κ∇²T, with vertical buoyancy source T. These equations describe the modeled terms; they do not certify discretization error or physical regime.

`simulation/simulation.py:Simulation` wraps the CUDA PISOtorch backend. Family `_get_simulation` methods choose adaptive subdivisions, two correctors, finite-difference velocity correction, and linear-solver tolerances. `simulation/pict/PISOtorch_simulation.py` contains the actual integration and solver counters. One environment step makes `max(1,int(step_length/dt))` calls; adaptive substeps target each call's dt. `FluidEnv.time_passed` is only `_n_steps*step_length`, so the runner independently checks `Simulation.total_time`.

| Family | dt; env interval; benchmark steps | Solver details |
|---|---|---|
| Cylinder | .01; .25; 80 (20 time units) | nonorthogonal; pressure tolerance 1e-5 (2D), 5e-7 (3D); CFL .8 |
| RBC | .05; 1; 200 (200 free-fall units) | orthogonal wall-refined grid; pressure tolerance 1e-5; CFL above |
| Airfoil | .05; .25; 300 (2D), 200 (3D) | nonorthogonal; advection tol 1e-6, pressure 1e-7 / 1e-8; 2 advection and 4 pressure nonorthogonal corrections; double fallback enabled |
| TCF | interval .6 in wall units, converted by `_t_wall_to_t`; dt=interval/10; 1000 steps | nonorthogonal; CFL .1, advection/pressure tol 1e-6; default C_smag=0 and no Van Driest damping |

Airfoil stores the requested CFL but does not forward it to `Simulation`; all registered airfoil values currently equal the solver default .8. Read actual solver CFL, not only the environment attribute. `single_step` catches a linear-solver error and returns False; family loops ignore that return. The runner intercepts it and aborts, without changing any solver source or algorithm. Residual histories, fallback event counts, and a validated native divergence norm are explicitly unavailable in the output schema. Finite fields and valid clocks are necessary, not sufficient, numerical validation.

## Cylinder jet and rotation

Sources: `envs/cylinder/cylinder_env_base.py`, `grid.py`, `jet_cylinder_env_2d.py`, `rotating_cylinder_env_2d.py`, `jet_cylinder_env_3d.py`, `envs/util/forces.py`, `profiles.py`.

Geometry: H=4.1, L=22, cylinder diameter 1, vertical offset .05; 3D span D=4. Five connected curvilinear blocks with wake refinement; angular resolution is not total cell count. Inlet uses a parabolic profile with discrete mean 1; ν=1/Re. Channel/cylinder walls use closed boundaries; outlet uses advective updates. 3D span is periodic. `simulation/extensions/domain_structs.cpp` establishes periodic defaults and closes paired boundaries when necessary; inspect saved boundary metadata for the realized domain.

Jet actuation applies a scalar to paired profiles around the top/bottom cylinder, angular half-width 10°. Rotation applies tangential wall velocity. Both use smoothing c←c+.1(a−c) per outer solver call, with hidden persistent control state. CylinderJet3D has eight spanwise actuator locations and optional local observations/rewards. Zero actions characterize the nominal uncontrolled plant; they do not identify actuator response or mass-flux effectiveness.

2D observations contain velocity (151,2) and pressure (151,) on a resampled grid. 3D defaults to two sensor slices per jet (16 slices with eight jets); local_2d_obs/local_obs_window change the observation task. Public velocity, pressure and vorticity are resampled; velocity/vorticity mask the cylinder. They are not native finite-volume state arrays. Native velocity and pressure remain accessible per block.

Drag/lift include pressure and viscous forces and are averaged over outer solver calls within each environment step. Reward: Cd_ref−Cd−λ|Cl| with λ=1. Cd_ref is the saved drag mean. 3D computes spanwise forces and optionally local reward mixtures. The 3D global drag/lift are spanwise sums divided by span D; additional `all_cds`/`all_cls` arrays and MARL local rewards require separate adapters.

Diagnostics: mean drag, signed lift mean, lift RMS and standard deviation, contiguous block means, discard sensitivity; a Hann lift periodogram only for sufficiently long cylinder records. Frequencies become St=fD/U with D=U=1. An accepted candidate peak is not evidence of a bifurcation, chaos, or turbulence. Step averaging filters high frequencies.

## Rayleigh–Bénard convection

Sources: `envs/rbc/rbc_env_base.py`, `rbc_env_2d.py`, `rbc_env_3d.py`, `simulation/helpers.py:get_cell_size`.

H=1, hot plate T=1, cold plate T=0; periodic horizontal directions, closed top/bottom velocity boundaries. Free-fall scaling gives ν=√(Pr/Ra), κ=1/√(RaPr), buoyancy coefficient 1. Grid width is n_heaters×resolution; height round(2×width/(aspect_ratio×π)); 3D extrudes the width in z. Wall refinement base 1.02, uniform_grid=False. Wide variants double horizontal extent and heater count, not heater width or Ra.

Bottom temperature controls are mean-centered, limited with heater_limit=.75, and spatially blended. The nonlinear clipping/blending should not be presumed exactly mean preserving for arbitrary actions without checking boundary fields. Zero action yields uniform T=1. Sensors measure velocity, pressure and temperature at eight vertical positions and four horizontal positions per heater: 48×8 or 96×8 points in 2D, and 32×8×32 or 64×8×64 in 3D. Global 2D is the default; 3D defaults to MARL, with local reward weight .0015 (2D .2).

Global Nu = 1+√(RaPr)⟨u_y T⟩_V using native volume weights. It is an end-of-step bulk flux measurement, not an instantaneous wall-gradient measurement or a solver-step average. Global reward is Nu_ref−Nu; 2D uses the saved Nu median, 3D the mean. Local rewards mix local Nu with the global reward. Wall heat flux, top/bottom flux agreement, and resolved thermal boundary-layer adequacy are not yet measured.

Diagnostics: native Nu, native volume-mean temperature and kinetic energy, temperature extrema, block/time statistics. No cylinder lift spectra, cylinder Strouhal numbers, or unweighted resampled-grid heat transport. Temperature extrema are reported rather than silently clipped. A volume average of resampled fields would not reproduce the native nonuniform-grid weighting.

## Airfoil

Sources: `envs/airfoil/airfoil_env_base.py`, dimensional subclasses, `coords.py`, `grid.py`.

NACA0012 sharp trailing edge, chord 1, angle 10°, mean inlet .3, H=1.4, downstream L=4.5 with upstream extent to x=−1.5; span 1.4 in 3D. ν=.3/Re. Six connected body-fitted blocks, near-surface normal resolution 96 at resolution_div=1, stretched tail; 3D hard changes tail refinement. Inlet parabolic, channel and airfoil walls closed, two advective outflow boundaries, span periodic.

Three suction-side synthetic jet sites; smoothing .1 per outer call. 3D adds spanwise actuation. Velocity/pressure sensors are generated around the airfoil/wake and sampled from the resampled fields; the candidate grid comprises a coarse wake x=1.5:0.125:2.6 with eight y points, a fine wake x=1.05:0.05:1.45 with eight y points, and a 10×8 near-airfoil grid; mask filtering determines the final count, which is recorded from runtime observations. Exact sensor count is determined by the source coordinate generation and verified from runtime shapes rather than assumed equal to the cylinder's 151. Public velocity, pressure, vorticity are available; render grid 600×150 (×150 in 3D), much larger than a sparse observation.

Reward Cl/Cd−mean_ref(Cl)/mean_ref(Cd), using step-averaged forces (spanwise totals in 3D). Ratio of reference means is not mean instantaneous Cl/Cd. Diagnostics include separate drag and lift and instantaneous step-level ratio; near-zero drag yields an explicit unavailable ratio. No cylinder-specific D/U scaling is applied. Separation location and wall stress distributions require additional validated measurements and are not inferred from force ratios.

## Turbulent channel flow (3D deferred)

Sources: `envs/tcf/tcf_env.py`, `grid.py`, `simulation/pict/data/TCF_tools.py`.

Channel half-height δ=1, height 2, periodic streamwise/spanwise directions, closed wall-normal boundaries. Reτ selects an empirical centerline-Re conversion; ν=δ/Re_center and uτ=Reτ/Re_center. Dynamic streamwise forcing is set from mean wall shear. This is not a freely prescribed pressure gradient independent of wall stress. Grid stretching concentrates cells near the walls. No explicit LES viscosity by default (C_smag=0); this is not proof of adequate resolution at Reτ=550.

Bottom or both walls receive wall-normal blowing/suction, mean corrected and scaled by uτ. Actor patches are 2×2 cells. Observations include streamwise/wall-normal velocity fluctuations (spatial mean removed) and pressure near y+=15, with local windows in default MARL mode. Public full velocity/pressure/vorticity are available. Native wall stresses are exposed as step-averaged total/bottom/top info metrics. Reward 1−τ_bottom/τ_ref for bottom control, 1−τ_total/τ_ref for both; reference is the corresponding saved mean. A future adapter should use wall stress, mean velocity profiles, bulk flux, and Reynolds stresses with native volume weights; no cylinder spectrum defaults.

## Initial domains, statistics and unresolved measurements

Every family loads `<initial_domains>/<id>/<idx>/<mode>.json` and `.npz`, ten indices and train/val/test splits, plus `domain_statistics.json`. Optional `<mode>_uncontrolled_episode.csv` is used when present. JSON identifies NPZ tensor indices, geometry, transport coefficients and boundary state. The inventory records exact IDs: cylinder includes Re/resolution; RBC includes Ra/Pr/heater count/width; airfoil only dimensionality/Re; TCF includes L/Reτ/x-resolution/refinement. Several physical/grid choices are absent from these identifiers, so dataset reuse after parameter changes would need a separate audit.

`FluidEnv.init` uses seeds 100/200/300 plus index; some families continue trajectories across split generation instead of independently regenerating. Airfoil3D fresh generation defaults to initializing velocity from a randomly selected 2D train domain, with shape-mismatch fallback; loading an existing 3D domain does not invoke that generation path. Existing datasets' actual generation lineage and reference aggregation windows are not fully established by their filenames. Statistics and optional baseline CSVs are checksummed, but their physical adequacy must be assessed from data. The runner never calls init or download.

Randomized reset selects a domain and perturbs it (RBC also translates/flips). Different seeds are independent RNG streams, not proof of statistically independent flow states. Selected index, mode, checksummed inputs, and reset solver time are recorded. Deterministic runs use index 0 without perturbation twice. Every run resets exactly once. No reset episodes are concatenated. Airfoil randomized warm-up depends on episode_length; extended trajectories retain the nominal reset horizon and extend the termination counter only afterward.

Missing measurements: calibrated GPU timing/memory, native divergence and residual histories, boundary mass/heat flux audits, grid/time convergence, dataset statistical stationarity, actuator transfer response, and long-time ensemble convergence. These omissions prevent regime and controlled-shift claims, even after a nominal trajectory passes finite-value checks.
