"""CPU tests of source-declared contracts (AST only). These are NOT physical validation."""
import pytest
from fluidgym_physics.errors import UnsupportedEnvironmentError
from fluidgym_physics.static_inspect import (
    base_class_constants, nominal_source_summary, registered_jet2d_variants)


def test_registered_variants():
    v = registered_jet2d_variants()
    assert v == {
        "CylinderJet2D-easy-v0": {"reynolds_number": 100, "resolution": 24},
        "CylinderJet2D-medium-v0": {"reynolds_number": 250, "resolution": 32},
        "CylinderJet2D-hard-v0": {"reynolds_number": 500, "resolution": 32},
    }


def test_easy_nominal_summary():
    s = nominal_source_summary("CylinderJet2D-easy-v0")
    r, d = s["requested"], s["derived_from_source"]
    assert (r["dt"], r["step_length"], r["episode_length"], r["adaptive_cfl"]) == (0.01, 0.25, 80, 0.8)
    assert d["nominal_viscosity"] == pytest.approx(0.01)
    assert d["n_sim_steps_nominal"] == 25
    assert d["sim_time_per_episode"] == pytest.approx(20.0)
    assert d["initial_domain_id"] == "cylinder_2D_Re100_Res24"
    assert "NOT runtime-verified" in s["provenance"]


def test_class_constants():
    c = base_class_constants()
    assert c["_action_smoothing_alpha"] == 0.1 and c["H"] == 4.1 and c["L"] == 22.0
    assert c["_n_sensors_x_y"] == 151 and c["cylinder_diameter"] == 1.0


def test_unknown_env():
    with pytest.raises(UnsupportedEnvironmentError):
        nominal_source_summary("CylinderJet2D-extreme-v0")
