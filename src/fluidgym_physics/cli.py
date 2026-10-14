"""Thin CLI wrappers; all logic lives in the library modules."""
from __future__ import annotations

import argparse
import json
import sys

from .errors import FluidGymPhysicsError
from .static_inspect import nominal_source_summary
from .upstream import verify_upstream


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fluidgym-physics")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-upstream")
    s = sub.add_parser("inspect-config")
    s.add_argument("--env-id", default="CylinderJet2D-easy-v0")
    args = p.parse_args(argv)
    try:
        if args.cmd == "verify-upstream":
            print(json.dumps(verify_upstream(), indent=2))
        else:
            print(json.dumps(nominal_source_summary(args.env_id), indent=2))
    except FluidGymPhysicsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
