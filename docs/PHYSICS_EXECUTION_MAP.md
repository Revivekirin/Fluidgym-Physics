# CylinderJet2D physics execution map

Upstream: commit `50071140b73a2a917fb96d33522a769f903f8c27` (v0.1.2-7). `UP/` = `third_party/fluidgym/src/fluidgym/`.
Labels: **[SRC]** verified by reading source · **[RUN]** verified at runtime · **[ASM]** assumption · **[?]** unresolved.
As of this document **no [RUN] claim exists**: the authoring sandbox had no torch/CUDA/PISOtorch.

| Stage | Where (file : function : lines) | Claim |
|---|---|---|
| Registry | `UP/__init__.py` : `register(...)` : 28-50; `UP/registry.py` : `EnvRegistry.register/make` | **[SRC]** easy = Re 100/res 24, medium = Re 250/res 32, hard = Re 500/res 32; all share `CYLINDER_JET_2D_DEFAULT_CONFIG`. |
| Defaults | `UP/envs/cylinder/jet_cylinder_env_2d.py` : `CYLINDER_JET_2D_DEFAULT_CONFIG` : 8-23 | **[SRC]** dt=0.01, adaptive_cfl=0.8, step_length=0.25, episode_length=80, lift_penalty=1.0, float32, load_initial_domain/statistics=True, randomize_initial_state=True. |
| Constructor | `jet_cylinder_env_2d.py` : `CylinderJetEnv2D.__init__` : 93-128 → `cylinder_env_base.py` : `CylinderEnvBase.__init__` : 145-201 → `fluid_env.py` : `FluidEnv.__init__` : ~138-258 | **[SRC]** chain stores Re/resolution first (165-167), then FluidEnv, then builds `_viscosity = U_mean/Re` (186-188). |
| Implicit download | `fluid_env.py` : `__init__` : ~234-238 → `UP/util/data_utils.py` : `prepare_initial_domains` : 23-46 | **[SRC]** constructor downloads initial domains from HuggingFace if the local directory is empty. Our runtime wrapper pre-checks and refuses (see `runtime.py`). |
| Geometry constants | `cylinder_env_base.py` : 124-132 | **[SRC]** H=4.1, L=22.0, D_cyl=1.0, U_mean=1.0, cylinder_offset_y=0.05, 151 sensors. Blockage D/H ≈ 0.24. |
| Domain build (fresh path) | `cylinder_env_base.py` : `_get_domain` : 247-268 → `UP/envs/cylinder/grid.py` : `make_vortex_street_domain` : ~302-360 | **[SRC]** 5 blocks (left, top, right, bottom, vortex street); viscosity enters `PISOtorch.Domain(ndims, viscosity, ...)` (grid.py:301-307). Only used when `load_initial_domain=False`. |
| Initial-domain selection | `fluid_env.py` : `_set_initial_state` : 507-552 | **[SRC]** default path: `domain = _load_initial_domain(mode, idx)` with idx ∈ [0,10) from `np_rng` if randomize else 0 (522-524). `_get_domain()` is NOT called on this path (552). |
| Reset | `fluid_env.py` : `reset` : 862-917 | **[SRC]** raises if CUDA unavailable (~887); reseeds three RNGs (844-860); `_set_initial_state`; zero-action applied (~913); `_n_steps=0`. |
| Solver init | `cylinder_env_base.py` : `_get_simulation` : 303-332 | **[SRC]** PISO-style `Simulation`, `substeps="ADAPTIVE"`, `adaptive_CFL`, `corrector_steps=2`, `pressure_tol=1e-5` (2D), FD velocity corrector, non-orthogonal grid, output resampled to `render_shape`. |
| Inlet BC | `grid.py` : 309-323; `UP/envs/util/profiles.py` : `get_inflow_profile` : 35-92 | **[SRC]** parabolic profile, *discrete mean normalised to 1.0* (profiles.py ~74), amplitude NOT tied to `_U_mean`. |
| Outlet BC | `grid.py` : 351-354; `cylinder_env_base.py` : `_get_prep_fn` : 277-301 | **[SRC]** `+x` boundary of vortex-street block uses an advective (convective) outflow updated in a PRE hook with `char_vel=[U_mean,0]`, tol 5e-6. |
| Walls / cylinder | `grid.py` : 326-353 | **[SRC]** top/bottom channel walls and cylinder surface are closed (no-slip-type) boundaries; wall-type (no-slip vs slip) semantics are in the C++ extension **[?]**. |
| Actuation | `jet_cylinder_env_2d.py` : `_get_boundary_velocities` : 136-183, `_apply_action` : 185-188; `profiles.py` : `get_jet_profile` : 6-31 | **[SRC]** two jets at the top/bottom of the cylinder, half-width `_jet_angle`=10° (91, 150); parabolic profile, max normalised to 1; **the same scalar control multiplies both jets' fixed velocity fields**. Net mass flux (zero-net-mass-flux?) and sign symmetry **[?]**, needs runtime check. |
| Action smoothing / hidden state | `cylinder_env_base.py` : `_step_impl` : 746-753; `_action_smoothing_alpha=0.1` : 122 | **[SRC]** per *sim* step `c ← c + 0.1(a − c)`; `__last_control` persists across env steps, is zeroed in `_additional_initialization` (360), saved in `get_state` (847-857). Jet response time ≈ 10 sim steps ≈ 0.1 time units **[ASM: nominal dt]**. |
| Time integration per env step | `fluid_env.py` : `_n_sim_steps` : 840-842; `_step_impl` loop 746-758 | **[SRC]** n = max(1, int(step_length/dt)) = 25 (checked in Python, 0.25/0.01 → 25.0). Each `single_step()` may itself subdivide adaptively (`simulation.py:210`); the *effective* sim time per env step is therefore **[?]** until `time_passed` is logged. |
| State update | `simulation.py` : `single_step` : 210 | **[SRC]** advances `domain` block velocity/pressure in place (internal state). Detailed PISO loop not traced. |
| Observation | `cylinder_env_base.py` : `_get_global_obs` : 542-546 → `UP/envs/util/obs_extraction.py` : `extract_global_2d_obs` : 10-50; sensors 451-516 | **[SRC]** velocity (151,2) + pressure (151,) taken from a *resampled uniform grid* (`render_shape`) by nearest-index lookup, not from native cells. Observation space 212-232. |
| Drag / lift | `cylinder_env_base.py` : `_get_drag_and_lift` : 657-698; `UP/envs/util/forces.py` : `compute_forces_2d` : 193-… | **[SRC]** pressure + viscous wall stress from first-cell velocity gradients (finite-difference), uses `self._viscosity`; Cd = F/(0.5·U_mean²·D). |
| Reward | `cylinder_env_base.py` : 762-769 | **[SRC]** reward = `cd_ref − mean_over_substeps(Cd) − lift_penalty·|mean(Cl)|`; `cd_ref` = mean drag from the stats file (271-275), 0.0 if stats not loaded. |
| Termination | `fluid_env.py` : `step` : 749-801 | **[SRC]** `terminated` is always False (`_step_impl` returns False, cylinder_env_base.py:776); truncation at `_n_steps ≥ episode_length`=80 → 20 convective time units. |
| Internal vs exposed | `fluid_env.py` : `get_velocity/get_pressure/get_vorticity` : 643-709; cylinder overrides 406-434 | **[SRC]** full resampled fields are accessible via public getters (cylinder masked to 0); native-cell fields via `env._domain.getBlocks()`. |

## Open points that matter for later physics work
1. **[SRC→?]** When initial domains are loaded, the solver viscosity comes from the *saved domain* (`domain_io.py` 86, 203), while `env._viscosity` (used for forces) is recomputed from Re. Equality of the two is untested: `EffectiveSolverValues.mismatches` encodes this check.
2. `_randomize_domain` (364-404) hard-codes St=0.3 and sizes the warm-up in env-step units but executes solver single-steps (≈25× shorter than intended); see INITIAL_DOMAIN_AND_REWARD_AUDIT. Real St in this confined geometry is unverified.
3. Reported drag/lift in `info` are means over the 25 sub-steps (762-763): **low-pass filtered**, not instantaneous.
