# FluidGym-Physics

Physics-first inspection of the **official** FluidGym benchmark (initial target `CylinderJet2D-easy-v0`). No RL, no solver changes, no parameter shifts.

## Setup
```bash
git clone --recurse-submodules <this repo>        # upstream pinned in third_party/fluidgym (see UPSTREAM.lock)
pip install -e ".[dev]"                            # core package is stdlib-only
fluidgym-physics verify-upstream                   # commit + src tree + clean-tree check
fluidgym-physics inspect-config --env-id CylinderJet2D-easy-v0   # source-declared values (no torch/GPU)
python -m pytest -q                                # CPU tests; CUDA tests are skipped without a GPU
```
CUDA host only (not yet run): install upstream deps (torch 2.9.*, PISOtorch extension per upstream README), fetch initial domains explicitly (docs/NUMERICAL_VALIDATION_PLAN.md C0), then `pytest -m cuda`.

## Guarantees
- Upstream is never modified; mismatch/dirty tree → `UpstreamIntegrityError`.
- Constructor-time HuggingFace downloads are blocked by pre-check (`MissingInitialDomainError`).
- Requested ≠ effective: `NominalEnvConfig` vs `EffectiveSolverValues` (unverified until read from a live env).

See `docs/` for the execution map, capability tables, audits, validation plan, shift feasibility and status.
