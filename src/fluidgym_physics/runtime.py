"""Runtime (CUDA-only) nominal environment construction and read-only inspection.

NOT EXECUTED in the authoring sandbox (no torch/CUDA). Written from source reading; must be run on the
CUDA server. torch/fluidgym are imported lazily so the rest of the package stays CPU-importable.
"""
from __future__ import annotations

from pathlib import Path

from .config import EffectiveSolverValues, NominalEnvConfig
from .errors import CudaUnavailableError, MissingInitialDomainError
from .static_inspect import nominal_source_summary


def _require_cuda():
    import torch  # lazy

    if not torch.cuda.is_available():
        raise CudaUnavailableError("FluidGym reset() raises without CUDA (fluid_env.py reset); run on a CUDA host")
    return torch


def check_initial_domains_present(cfg: NominalEnvConfig) -> Path:
    """Upstream's constructor calls prepare_initial_domains(), which downloads from HuggingFace when the
    directory is empty (util/data_utils.py:23-46). We therefore refuse to construct unless data is local."""
    import fluidgym.config as fg_config  # lazy

    domain_id = nominal_source_summary(cfg.env_id)["derived_from_source"]["initial_domain_id"]
    d = Path(fg_config.initial_domains_path) / domain_id
    if not (d.exists() and any(d.iterdir())):
        raise MissingInitialDomainError(
            f"initial domains for {domain_id} not found at {d}; not downloading automatically. "
            "Fetch them explicitly (see docs/NUMERICAL_VALIDATION_PLAN.md, command C0)."
        )
    return d


def make_nominal_env(cfg: NominalEnvConfig):
    _require_cuda()
    check_initial_domains_present(cfg)
    import fluidgym  # lazy

    env = fluidgym.make(cfg.env_id)
    getattr(env, cfg.mode)()          # env.train()/val()/test()
    env.seed(cfg.seed)
    return env


def read_effective_values(env) -> EffectiveSolverValues:
    """Read-only: reads private attributes of the env; never writes. Requires reset() to have been called
    for domain_viscosity (the domain only exists after _set_initial_state)."""
    dom_visc = None
    dom = getattr(env, "_domain", None)
    if dom is not None:
        v = dom.viscosity
        dom_visc = float(v.flatten()[0].item())
    return EffectiveSolverValues(
        reynolds_number=float(env._reynolds_number),
        domain_viscosity=dom_visc,
        env_viscosity=float(env._viscosity.flatten()[0].item()),
        dt=float(env.dt),
        adaptive_cfl=float(env._adaptive_cfl),
        step_length=float(env.step_length),
        n_sim_steps=int(env.n_sim_steps),
        resolution=int(env._circle_resolution_angular),
        verification="runtime",
    )
