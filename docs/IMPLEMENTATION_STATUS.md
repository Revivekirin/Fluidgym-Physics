# Implementation status

| Item | State |
|---|---|
| Git repo, submodule pin, `UPSTREAM.lock`, verification (commit, `src` tree hash, dirty flag) | Implemented; **PASSED** (CPU) |
| Strict config schema (requested) + effective-value schema (separate, default unverified) | Implemented; **PASSED** (CPU) |
| AST-based source summary (registry, defaults, constants, derived viscosity / n_sim_steps) | Implemented; **PASSED** (CPU). Source-declared only |
| Provenance record + JSON-schema + no-overwrite writer | Implemented; **PASSED** (CPU) |
| Runtime nominal env construction (no implicit download), effective-value readback | Written; **NOT RUN** (no CUDA/torch/PISOtorch) |
| CUDA tests (3) | **SKIPPED** here, never executed |
| Comparison with Fluidgym-RL pinned FluidGym revision | **NOT RUN** (repo not accessible here); recorded as UNKNOWN in the lock |
| Drag/lift/spectral statistics code | **Not implemented** (needs verified series; see validation plan) |
| Shift interventions, sweeps, POD/DMD/SINDy/Koopman | Intentionally not implemented |

Test result of the last run in the authoring sandbox: `22 passed, 3 skipped` (`python -m pytest -q`). No physical validation exists; none of the PASSED tests exercises CFD.
