"""Upstream integration: read UPSTREAM.lock and verify the checkout is the pinned, clean revision."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import UpstreamIntegrityError

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = REPO_ROOT / "UPSTREAM.lock"
UPSTREAM_DIR = REPO_ROOT / "third_party" / "fluidgym"


@dataclass(frozen=True)
class UpstreamLock:
    url: str
    commit: str
    src_tree: str
    describe: str
    pinned_deps: dict[str, str]


def read_lock(path: Path = LOCK_PATH) -> UpstreamLock:
    """Parse the simple `key = value` lock file (no TOML dependency on py3.10)."""
    if not path.exists():
        raise UpstreamIntegrityError(f"missing lock file: {path}")
    kv: dict[str, str] = {}
    deps: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key.startswith("dep."):
            deps[key[4:]] = value
        else:
            kv[key] = value
    missing = {"url", "commit", "src_tree", "describe"} - kv.keys()
    if missing:
        raise UpstreamIntegrityError(f"lock file missing keys: {sorted(missing)}")
    return UpstreamLock(kv["url"], kv["commit"], kv["src_tree"], kv["describe"], deps)


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise UpstreamIntegrityError(f"git {' '.join(args)} failed in {cwd}: {exc}") from exc


def inspect_checkout(upstream_dir: Path = UPSTREAM_DIR) -> dict[str, object]:
    if not (upstream_dir / ".git").exists():
        raise UpstreamIntegrityError(f"upstream checkout not found at {upstream_dir}")
    return {
        "commit": _git(["rev-parse", "HEAD"], upstream_dir),
        "src_tree": _git(["rev-parse", "HEAD:src"], upstream_dir),
        "describe": _git(["describe", "--tags", "--always"], upstream_dir),
        "dirty": bool(_git(["status", "--porcelain"], upstream_dir)),
        "origin_url": _git(["remote", "get-url", "origin"], upstream_dir),
    }


def verify_upstream(
    lock: UpstreamLock | None = None, upstream_dir: Path = UPSTREAM_DIR
) -> dict[str, object]:
    """Raise UpstreamIntegrityError unless the checkout matches the lock exactly and is clean."""
    lock = lock or read_lock()
    info = inspect_checkout(upstream_dir)
    problems = []
    if info["commit"] != lock.commit:
        problems.append(f"commit {info['commit']} != pinned {lock.commit}")
    if info["src_tree"] != lock.src_tree:
        problems.append(f"src tree {info['src_tree']} != pinned {lock.src_tree}")
    if info["dirty"]:
        problems.append("upstream working tree is dirty (upstream must stay unmodified)")
    if problems:
        raise UpstreamIntegrityError("; ".join(problems))
    return info
