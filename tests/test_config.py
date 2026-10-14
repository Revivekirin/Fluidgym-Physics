import pytest
from fluidgym_physics.config import EffectiveSolverValues, NominalEnvConfig
from fluidgym_physics.errors import UnsupportedEnvironmentError, UnsupportedParameterError


def test_default_ok():
    assert NominalEnvConfig().env_id == "CylinderJet2D-easy-v0"


@pytest.mark.parametrize("env_id", ["CylinderRot2D-easy-v0", "CylinderJet2D-easy-v1", ""])
def test_unsupported_env(env_id):
    with pytest.raises(UnsupportedEnvironmentError):
        NominalEnvConfig(env_id=env_id)


def test_physical_override_rejected():
    with pytest.raises(UnsupportedParameterError, match="viscosity"):
        NominalEnvConfig(overrides={"viscosity": 0.02})


def test_download_rejected():
    with pytest.raises(UnsupportedParameterError):
        NominalEnvConfig(allow_download=True)


@pytest.mark.parametrize("kw", [{"seed": -1}, {"seed": True}, {"mode": "dev"}])
def test_bad_values(kw):
    with pytest.raises(ValueError):
        NominalEnvConfig(**kw)


def test_unknown_key():
    with pytest.raises(UnsupportedParameterError):
        NominalEnvConfig.from_dict({"env_id": "CylinderJet2D-easy-v0", "re": 200})


def test_effective_defaults_are_unverified_not_requested():
    eff = EffectiveSolverValues()
    assert eff.verification == "unverified" and eff.dt is None
    assert eff.mismatches({"dt": 0.01}) == []   # unknown is not "equal"


def test_mismatch_reported():
    eff = EffectiveSolverValues(dt=0.02, domain_viscosity=0.01, env_viscosity=0.02)
    msgs = eff.mismatches({"dt": 0.01})
    assert any("dt" in m for m in msgs) and any("viscosity" in m for m in msgs)
