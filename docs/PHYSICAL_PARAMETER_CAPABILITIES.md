# Physical parameter capabilities (read-only vs mutable)

> Historical CylinderJet2D source audit. Current evidence: the user reports 25 passing CUDA-server tests (three real-environment tests); artifacts are not present here. Earlier “not run” statements describe the original authoring host only. See ENVIRONMENT_PHYSICS_INVENTORY.md and CHARACTERIZATION_WORKFLOW.md for the current complete scope. `env.time_passed` is nominal step-count time, not measured solver time; the new runner checks `env._sim.total_time`. Reset episodes must never be concatenated.

Legend: **R** readable from a live env (private attribute, read-only here) · **C** settable only at construction · **Fixed** hard-coded upstream. None of the "R" paths has been executed yet (no CUDA in sandbox).

| Quantity | Where | Status |
|---|---|---|
| Reynolds number | ctor arg `reynolds_number`; `env._reynolds_number` (cylinder_env_base.py:165) | R, C (but selects initial-domain directory, see audit) |
| Kinematic viscosity (force calc) | `env._viscosity = U_mean/Re` (186-188) | R |
| Kinematic viscosity (solver) | `env._domain.viscosity` (stored in domain, `domain_io.py:86,203`) | R (after reset); **may differ from the line above if a saved domain was made at a different Re** [?] |
| Inlet velocity | profile built in `profiles.py:get_inflow_profile`, mean fixed to 1.0; `_U_mean` is a class constant (128) | Fixed (amplitude); `_U_mean` only enters viscosity, Cd normalisation and outflow speed |
| Geometry (H, L, D) | class constants 124-129 | Fixed |
| Grid resolution | ctor `resolution` → `_circle_resolution_angular` | R, C |
| dt, adaptive CFL, step_length, episode_length | ctor args; `env.dt`, `env.step_length`, `env.n_sim_steps`, `env._adaptive_cfl` | R, C |
| Effective sub-step size | inside `Simulation` adaptive stepping | **Not exposed**; need `env.time_passed` / sim internals logged per step [?] |
| Jet geometry/profile | `_jet_angle=10`, `get_jet_profile` | Fixed |
| Action smoothing alpha | `_action_smoothing_alpha=0.1` (122) | Fixed (class attr) |
| Hidden actuator state | `__last_control` (name-mangled `_CylinderEnvBase__last_control`) | R via `get_state().additional_info["last_control"]` (847-857) |
| Solver tolerances / corrector steps | `_get_simulation` literals (303-332) | Fixed |

This phase implements **read** access only (`runtime.read_effective_values`). Any physical override is rejected by `NominalEnvConfig` (`UnsupportedParameterError`).
