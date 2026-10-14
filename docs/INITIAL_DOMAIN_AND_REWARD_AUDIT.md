# Initial-domain and reward audit

> Historical CylinderJet2D source audit. Current evidence: the user reports 25 passing CUDA-server tests (three real-environment tests); artifacts are not present here. Earlier “not run” statements describe the original authoring host only. See ENVIRONMENT_PHYSICS_INVENTORY.md and CHARACTERIZATION_WORKFLOW.md for the current complete scope. `env.time_passed` is nominal step-count time, not measured solver time; the new runner checks `env._sim.total_time`. Reset episodes must never be concatenated.

## Initial domains
- Count/modes: `N_INITIAL_DOMAINS = 10` (`fluid_env.py:58`); modes train/val/test with generation seeds `MODE_SEEDS=[100,200,300]` (61) and per-domain seed `mode_seed + i` (`init`, ~1140-1156). **[SRC]**
- Identity: `initial_domain_id = cylinder_{ndims}D_Re{int(Re)}_Res{res}` (`cylinder_env_base.py:822-828`). **Viscosity is not a separate key**: any change of Re maps to a different directory; any other physical change (e.g. inlet, actuator) would silently reuse the same files. **[SRC]**
- Storage: `config.initial_domains_path / <id> / <idx> / <mode>` (`fluid_env.py:1044-1046`); download source: HuggingFace dataset repo named in `config.hf_intial_domains_repo_id` (`data_utils.py:48-64`). **[SRC]**
- Selection: `idx ~ np_rng.integers(0,10)` if `randomize` else 0 (522-524). With `randomize=True` a Gaussian perturbation (σ=0.025 for u and p) is added, then `n_steps` solver steps run (364-404). `n_steps` is computed in units of *env steps* (`int(period/step_length)`, St assumed 0.3 → period 3.33 → max_n_steps = 25, n_steps ∈ [13, 25]) but the loop calls `self._sim.single_step()` (one *solver* step, nominal dt = 0.01), so the warm-up after noise injection is nominally only ≈0.13–0.25 time units, far shorter than the shedding period the code comment intends. Noise is therefore largely *not* relaxed before the episode starts. **[SRC; effective duration depends on adaptive sub-stepping → [?]]**
- Generation (`init`, ~1114-1190): `_initial_domain_steps=400` plus random extra steps (cylinder_env_base.py:138). We never call `init()`; missing domains raise `MissingInitialDomainError`.
- Whether the saved states are in a fully developed shedding state at the nominal Re, and their phase diversity: **[?]** requires reading the stored fields.

## Reference statistics
- `_load_domain_statistics` (`fluid_env.py:1205-1221`; cylinder override 830-840) reads a JSON per initial-domain id: velocity magnitude, pressure, `drag`, `lift`, vorticity magnitude. `cd_ref = stats["drag"].mean` (271-275). **[SRC]**
- How the drag statistic was generated (uncontrolled episodes? which modes, how many, transient excluded?): from `init`/`_save_uncontrolled_episode` (~1223-1245), not yet traced. **[?]**
- Consequence for later work: the reference is a *property of the stored data for that Re/resolution*; it is not recomputed if physics are changed at runtime.

## Reward
`r = cd_ref − Cd_step − λ|Cl_step|`, λ = `lift_penalty` = 1.0, where Cd_step/Cl_step are means over the 25 solver sub-steps (cylinder_env_base.py:762-769). The reward therefore (i) is not scale-free across Re, (ii) contains no explicit control-effort term; only smoothing limits actuation. **[SRC]**

## Observation vs internal state
Agent sees 151 sensor points of resampled velocity/pressure only; the full state is the domain's block fields + `__last_control`. Observations are not a Markov state (shedding phase is partially observable through the sensors; the hidden actuator state is not observed at all). **[SRC + reasoning]**
