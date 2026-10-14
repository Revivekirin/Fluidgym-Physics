"""Actual-CFD / GPU tests. SKIPPED on hosts without CUDA; they have never been executed by the author."""
import numpy as np
import pytest
from fluidgym_physics.config import NominalEnvConfig

pytestmark = pytest.mark.cuda


@pytest.fixture(scope="module")
def env():
    from fluidgym_physics.runtime import make_nominal_env
    return make_nominal_env(NominalEnvConfig(seed=0, randomize_initial_state=False))


def test_effective_values_match_request(env):
    from fluidgym_physics.runtime import read_effective_values
    from fluidgym_physics.static_inspect import nominal_source_summary
    env.reset(seed=0, randomize=False)
    eff = read_effective_values(env)
    assert eff.mismatches(nominal_source_summary("CylinderJet2D-easy-v0")["requested"]) == []


def test_contracts(env):
    import torch
    obs, _ = env.reset(seed=0, randomize=False)
    assert tuple(obs["velocity"].shape) == (151, 2) and tuple(obs["pressure"].shape) == (151,)
    assert env.action_space.shape == (1,)
    _, _, term, trunc, info = env.step(torch.zeros(1, device=env.cuda_device))
    assert term is False and trunc is False and {"drag", "lift"} <= set(info)


def test_determinism_same_seed(env):
    import torch
    def roll():
        obs, _ = env.reset(seed=7, randomize=False)
        out = []
        for _ in range(3):
            obs, r, *_ = env.step(torch.zeros(1, device=env.cuda_device))
            out.append(float(r))
        return np.array(out)
    a, b = roll(), roll()
    # Bitwise equality is NOT assumed (GPU solver); tolerance is a placeholder to be set from data.
    assert np.allclose(a, b, rtol=1e-4, atol=1e-6)
