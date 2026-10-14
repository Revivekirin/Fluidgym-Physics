"""Strict typed configuration: *requested* values and *verified effective* values are separate types."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

from .errors import UnsupportedEnvironmentError, UnsupportedParameterError

SUPPORTED_ENV_IDS = ("CylinderJet2D-easy-v0", "CylinderJet2D-medium-v0", "CylinderJet2D-hard-v0")
# Nominal-only phase: any physical override is rejected rather than silently ignored.
_PHYSICAL_KEYS = ("reynolds_number", "resolution", "dt", "adaptive_cfl", "step_length",
                  "episode_length", "lift_penalty", "viscosity", "inlet_velocity")


@dataclass(frozen=True)
class NominalEnvConfig:
    env_id: str = "CylinderJet2D-easy-v0"
    seed: int = 0
    mode: str = "test"                      # train | val | test (upstream EnvMode values)
    randomize_initial_state: bool = False   # False => deterministic domain idx 0, no noise injection
    allow_download: bool = False            # we never let upstream download implicitly
    overrides: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.env_id not in SUPPORTED_ENV_IDS:
            raise UnsupportedEnvironmentError(f"{self.env_id!r} unsupported; supported: {SUPPORTED_ENV_IDS}")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("seed must be a non-negative int")
        if self.mode not in ("train", "val", "test"):
            raise ValueError("mode must be train|val|test")
        if self.allow_download:
            raise UnsupportedParameterError("allow_download=True is not supported in this phase")
        if self.overrides:
            bad = sorted(self.overrides)
            raise UnsupportedParameterError(
                f"physical/solver overrides are not implemented in this phase: {bad} "
                f"(known physical keys: {list(_PHYSICAL_KEYS)})"
            )

    @classmethod
    def from_dict(cls, d: dict) -> "NominalEnvConfig":
        allowed = {f.name for f in fields(cls)}
        unknown = set(d) - allowed
        if unknown:
            raise UnsupportedParameterError(f"unknown config keys: {sorted(unknown)}")
        return cls(**d)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EffectiveSolverValues:
    """Values read back from a constructed env/solver. None == not verified (never defaulted to requested)."""
    reynolds_number: float | None = None
    domain_viscosity: float | None = None       # viscosity stored in the loaded PISOtorch domain
    env_viscosity: float | None = None          # env._viscosity (used for force computation)
    dt: float | None = None
    adaptive_cfl: float | None = None
    step_length: float | None = None
    n_sim_steps: int | None = None
    resolution: int | None = None
    verification: str = "unverified"            # "unverified" | "runtime"

    def mismatches(self, requested: dict, rtol: float = 1e-6) -> list[str]:
        out = []
        for key in ("reynolds_number", "dt", "adaptive_cfl", "step_length", "resolution"):
            eff, req = getattr(self, key), requested.get(key)
            if eff is None or req is None:
                continue
            if abs(eff - req) > rtol * max(1.0, abs(req)):
                out.append(f"{key}: requested {req}, effective {eff}")
        if self.domain_viscosity is not None and self.env_viscosity is not None:
            if abs(self.domain_viscosity - self.env_viscosity) > 1e-9:
                out.append(f"domain_viscosity {self.domain_viscosity} != env_viscosity {self.env_viscosity}")
        return out
