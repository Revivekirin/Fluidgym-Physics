"""Read every registration without importing FluidGym or executing upstream code."""
from __future__ import annotations

import ast
import math
from pathlib import Path

from .upstream import UPSTREAM_DIR, read_lock, verify_upstream


def _value(node, names):
    if isinstance(node, ast.Name):
        return names[node.id]
    if isinstance(node, ast.Attribute):
        if ast.unparse(node) in ("np.pi", "torch.pi"):
            return math.pi
        if ast.unparse(node) == "torch.float32":
            return "float32"
    if isinstance(node, ast.BinOp):
        a, b = _value(node.left, names), _value(node.right, names)
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            return a / b
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            if k is None:
                result.update(_value(v, names))
            else:
                result[_value(k, names)] = _value(v, names)
        return result
    return ast.literal_eval(node)  # Unsupported expressions fail closed.


def registrations(upstream: Path = UPSTREAM_DIR) -> dict:
    pkg = upstream / "src/fluidgym"
    defaults, sources = {}, {}
    for path in sorted((pkg / "envs").rglob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name.endswith("_DEFAULT_CONFIG"):
                    defaults[name] = _value(node.value, defaults)
                    sources[name] = f"{path.relative_to(upstream)}:{node.lineno}"
    result = {}
    for node in ast.parse((pkg / "__init__.py").read_text()).body:
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == "register"):
            continue
        kw = {k.arg: k.value for k in node.value.keywords}
        env_id = _value(kw.pop("id"), {})
        entry = kw.pop("entry_point").id
        default = kw.pop("defaults").id
        overrides = {k: _value(v, {}) for k, v in kw.items()}
        config = {**defaults[default], **overrides}
        ndims = 2 if "2D" in env_id else 3
        family = ("cylinder" if env_id.startswith("Cylinder") else
                  "rbc" if env_id.startswith("RBC") else
                  "airfoil" if env_id.startswith("Airfoil") else "tcf")
        result[env_id] = {"entry_point": entry, "family": family, "ndims": ndims,
                          "config": config, "variant_overrides": overrides,
                          "sources": [f"src/fluidgym/__init__.py:{node.lineno}", sources[default]]}
        result[env_id].update(derived(result[env_id]))
    return result


def derived(item):
    c, f, d = item["config"], item["family"], item["ndims"]
    cells = None
    if f == "cylinder":
        r = c["resolution"]
        domain = f"cylinder_{d}D_Re{int(c['reynolds_number'])}_Res{r}"
        shape = [int(4 * r / 4.1 * 22), 4 * r, 4 * r][:d]
    elif f == "rbc":
        n, r = c["n_heaters"], c["resolution"]
        domain = f"rbc_{d}d_Ra{c['rayleigh_number']}_Pr{c['prandtl_number']}_NH{n}_HW{r}"
        shape = [20 * n, round(20 * n / (math.pi * c['aspect_ratio'])), 20 * n][:d]
        x = n * r
        cells = x * round(2 * x / (math.pi * c["aspect_ratio"])) * (x if d == 3 else 1)
    elif f == "airfoil":
        domain = f"airfoil_{d}D_Re{int(c['reynolds_number'])}"
        shape = [600, 150, 150][:d]
    else:
        x = c["resolution_x_z"]
        domain = f"channel_flow3D_L{c['L']:.2f}_Re{int(c['reynolds_number_wall'])}_Res{x}_Ref1"
        shape = [2*x, int(2*x/c['L']*2), int(2*x/c['L']*c['D'])]
        # grid.py converts y=65 to y_half=32 and generates 64 cells.
        cells = x * (2 * (c["resolution_y"] // 2)) * x
    channels = d + 1 + (f == "rbc")  # velocity, pressure, optional temperature
    return {"initial_domain_id": domain, "render_shape_xyz": shape,
            "native_cells_source_estimate": cells,
            "snapshot_bytes_float32": math.prod(shape) * channels * 4,
            "snapshot_fields": ["velocity", "pressure"] + (["temperature"] if f == "rbc" else [])}


def inventory():
    verify_upstream()
    return {"schema_version": 1, "upstream_commit": read_lock().commit,
            "evidence": "source-declared; loaded grids and effective solver settings require runtime checks",
            "environments": registrations()}
