# Numerical validation plan (nothing here has been executed)

## Signal facts derived from source (not yet measured)
- Control/sampling interval Δt_s = `step_length` = 0.25 convective units (D/U); sampling frequency 4; Nyquist 2.0 (in 1/(D/U), i.e. St units with U=D=1).
- Reported Cd/Cl are **means over 25 solver sub-steps** (box-filter, ~0.25 wide). The filter attenuates frequency f by sinc(π f Δt_s); at St≈0.2 that is ≈0.97 — negligible for the fundamental, relevant for harmonics.
- One episode = 80 samples = 20 time units. Frequency resolution Δf = 1/20 = 0.05 (St units) — **coarse**: at St≈0.2 it is 25 % of the peak. Frequency estimates need either (a) zero-padding/interpolation with documented bias, (b) multi-episode concatenation only if the flow is stationary across episode boundaries (it is not guaranteed: resets load new domains), or (c) a longer uncontrolled rollout via the stepping API (`enable_actions=False`, raises episode_length) — requires explicit approval, see C2.
- Transient: whether loaded initial domains are already periodic is **[?]**; default plan is to discard the first ≥ 5 time units and report sensitivity to that choice.
- Aliasing: harmonics above 2.0 are not an issue for the cylinder wake (fundamental ≈ 0.2-0.3, expected, not verified).
- No claim about bifurcation, chaos or regime change may be made from a frequency shift alone.

## Capability checklist (what can be measured with today's API)
| Quantity | Available? | Basis |
|---|---|---|
| Cd(t), Cl(t) per env step | Yes, via `info["drag"|"lift"]` (means) | cylinder_env_base.py:771-774 |
| Instantaneous (per solver step) Cd/Cl | Not exposed; needs calling `env._get_drag_and_lift()` after private stepping, which changes semantics | [SRC] |
| Mean drag, lift RMS | Yes once Cd/Cl series exist | derived |
| Shedding frequency / St | Derivable from Cl(t); resolution limits above | derived |
| Velocity/pressure field | Yes: `env.get_velocity()`, `get_pressure()` (resampled grid, cylinder masked) | fluid_env.py:643-709 |
| Vorticity | Yes: `env.get_vorticity()`; rendering range ±10 | cylinder_env_base.py:406-421 |
| Solver diagnostics (residuals, sub-step counts, pressure-solver fallbacks) | Not exposed by the env API [?]; `Simulation` has attributes to inspect, not yet read | |
| POD/DMD-ready snapshots | Fields are accessible at env-step cadence; storage/size untested | |

## Validation commands (expected artifact contract; DO NOT RUN without authorisation)
- **C0 – domain data (network, small):** place the HuggingFace initial-domain data for `cylinder_2D_Re100_Res24` into `config.initial_domains_path` explicitly (not via constructor). Artifact: directory listing + SHA-256 manifest `results/domains_Re100_Res24.manifest.json`.
- **C1 – nominal smoke (CUDA, seconds):** `pytest -m cuda tests/test_cuda_nominal.py -rA`; artifacts: pytest report + `results/provenance_<ts>.json` with `execution_level=runtime_cuda`, `effective_values.verification=runtime`.
- **C2 – smallest real CFD experiment (CUDA, minutes):** one uncontrolled (zero-action) episode on domain idx 0, test mode, seed 0, `randomize=False`, logging per step: Cd, Cl, `time_passed`, sim sub-step count if accessible, domain viscosity vs env viscosity. Artifact: `results/uncontrolled_Re100_idx0_seed0.csv` (+ provenance JSON). Two repetitions to quantify run-to-run reproducibility (tolerance is *measured*, not assumed).
