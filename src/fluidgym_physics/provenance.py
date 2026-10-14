"""Structured experiment provenance record (JSON) with a hand-written, versioned schema."""
from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .upstream import inspect_checkout, read_lock

SCHEMA_VERSION = 1

PROVENANCE_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "fluidgym-physics provenance",
    "type": "object",
    "required": ["schema_version", "created_utc", "upstream", "requested_config",
                 "effective_values", "execution_level", "platform"],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "created_utc": {"type": "string"},
        "upstream": {"type": "object", "required": ["url", "commit", "dirty"]},
        "requested_config": {"type": "object"},
        "effective_values": {"type": "object"},
        "execution_level": {"enum": ["static_source", "runtime_cpu", "runtime_cuda"]},
        "platform": {"type": "object"},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass
class ProvenanceRecord:
    requested_config: dict
    effective_values: dict
    execution_level: str
    upstream: dict
    platform: dict
    created_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    schema_version: int = SCHEMA_VERSION
    notes: list[str] = field(default_factory=list)

    def validate(self) -> None:
        req = PROVENANCE_JSON_SCHEMA["required"]
        d = asdict(self)
        missing = [k for k in req if k not in d]
        if missing:
            raise ValueError(f"provenance missing {missing}")
        if self.execution_level not in ("static_source", "runtime_cpu", "runtime_cuda"):
            raise ValueError(f"bad execution_level {self.execution_level!r}")
        for k in ("url", "commit", "dirty"):
            if k not in self.upstream:
                raise ValueError(f"upstream provenance missing {k!r}")

    def write(self, path: Path) -> Path:
        """Refuses to overwrite an existing record."""
        self.validate()
        path = Path(path)
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(asdict(self), stream, indent=2, sort_keys=True, allow_nan=False)
        return path


def collect_platform() -> dict:
    return {"python": sys.version.split()[0], "os": platform.platform(), "machine": platform.machine()}


def build_record(requested_config: dict, effective_values: dict, execution_level: str,
                 notes: list[str] | None = None) -> ProvenanceRecord:
    info = inspect_checkout()
    lock = read_lock()
    return ProvenanceRecord(
        requested_config=requested_config,
        effective_values=effective_values,
        execution_level=execution_level,
        upstream={"url": lock.url, "commit": info["commit"], "src_tree": info["src_tree"],
                  "dirty": info["dirty"], "locked_commit": lock.commit},
        platform=collect_platform(),
        notes=notes or [],
    )
