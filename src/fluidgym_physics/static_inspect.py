"""Source-level (AST) extraction of requested CylinderJet2D settings.

Nothing here imports torch/fluidgym, so it runs on CPU-only machines. Everything returned is
"requested/source-declared"; effective solver values need runtime inspection (see runtime.py).
"""
from __future__ import annotations

import ast
from pathlib import Path

from .errors import UnsupportedEnvironmentError
from .upstream import UPSTREAM_DIR

_PKG = "src/fluidgym"
_JET_FILE = f"{_PKG}/envs/cylinder/jet_cylinder_env_2d.py"
_INIT_FILE = f"{_PKG}/__init__.py"
_BASE_FILE = f"{_PKG}/envs/cylinder/cylinder_env_base.py"


def _literal(node: ast.AST):
    if isinstance(node, ast.Attribute) and node.attr.startswith("float"):
        return node.attr  # torch.float32 -> "float32"
    return ast.literal_eval(node)


def jet2d_default_config(upstream: Path = UPSTREAM_DIR) -> dict:
    tree = ast.parse((upstream / _JET_FILE).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "CYLINDER_JET_2D_DEFAULT_CONFIG":
            assert isinstance(node.value, ast.Dict)
            return {k.value: _literal(v) for k, v in zip(node.value.keys, node.value.values)}
    raise UnsupportedEnvironmentError("CYLINDER_JET_2D_DEFAULT_CONFIG not found upstream")


def registered_jet2d_variants(upstream: Path = UPSTREAM_DIR) -> dict[str, dict]:
    """Return {env_id: {reynolds_number, resolution}} for CylinderJet2D-* register() calls."""
    tree = ast.parse((upstream / _INIT_FILE).read_text())
    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "register":
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            env_id = ast.literal_eval(kw["id"]) if "id" in kw else None
            if env_id and env_id.startswith("CylinderJet2D-"):
                out[env_id] = {
                    "reynolds_number": ast.literal_eval(kw["reynolds_number"]),
                    "resolution": ast.literal_eval(kw["resolution"]),
                }
    return out


def base_class_constants(upstream: Path = UPSTREAM_DIR) -> dict:
    """Class-level numeric constants of CylinderEnvBase (geometry, smoothing, sensors)."""
    wanted = {"H", "L", "cylinder_diameter", "_U_mean", "cylinder_offset_y", "_n_sensors_x_y",
              "_action_smoothing_alpha", "_vortex_street_refinement_base", "_initial_domain_steps"}
    tree = ast.parse((upstream / _BASE_FILE).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CylinderEnvBase")
    found = {}
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and getattr(stmt.target, "id", "") in wanted and stmt.value:
            found[stmt.target.id] = ast.literal_eval(stmt.value)
    return found


def nominal_source_summary(env_id: str, upstream: Path = UPSTREAM_DIR) -> dict:
    variants = registered_jet2d_variants(upstream)
    if env_id not in variants:
        raise UnsupportedEnvironmentError(
            f"{env_id!r} is not a registered CylinderJet2D variant; known: {sorted(variants)}"
        )
    cfg = {**jet2d_default_config(upstream), **variants[env_id]}
    consts = base_class_constants(upstream)
    return {
        "provenance": "source-declared (AST); NOT runtime-verified",
        "requested": cfg,
        "class_constants": consts,
        # Derived exactly as upstream writes it (viscosity = U_mean/Re; n_sim_steps = max(1,int(step_length/dt)))
        "derived_from_source": {
            "nominal_viscosity": consts["_U_mean"] / cfg["reynolds_number"],
            "n_sim_steps_nominal": max(1, int(cfg["step_length"] / cfg["dt"])),
            "sim_time_per_env_step": cfg["step_length"],
            "sim_time_per_episode": cfg["step_length"] * cfg["episode_length"],
            "initial_domain_id": f"cylinder_2D_Re{int(cfg['reynolds_number'])}_Res{cfg['resolution']}",
        },
    }
