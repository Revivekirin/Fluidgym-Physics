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
    sub.add_parser("inventory")
    for name in ("plan", "input-report", "preflight", "run"):
        command = sub.add_parser(name)
        command.add_argument("--matrix", required=True)
        if name == "input-report":
            command.add_argument("--data-root", required=True)
        if name == "run":
            command.add_argument("--output", required=True)
            command.add_argument("--reviewed-sha256", required=True)
    command = sub.add_parser("analyze")
    command.add_argument("--campaign", required=True)
    command.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        if args.cmd == "verify-upstream":
            print(json.dumps(verify_upstream(), indent=2))
        elif args.cmd == "inspect-config":
            print(json.dumps(nominal_source_summary(args.env_id), indent=2))
        elif args.cmd == "inventory":
            from .inventory import inventory
            print(json.dumps(inventory(), indent=2))
        elif args.cmd in ("plan", "input-report", "preflight", "run"):
            from .characterization import load_matrix, estimate, digest
            verify_upstream()
            matrix = load_matrix(args.matrix)
            if args.cmd == "plan":
                result = {"matrix_sha256": digest(args.matrix), **estimate(matrix)}
            elif args.cmd == "input-report":
                from .runner import input_report
                result = input_report(matrix, args.data_root)
            elif args.cmd == "preflight":
                from .runner import preflight
                result = preflight(matrix)
            else:
                from .runner import run_matrix
                result = run_matrix(args.matrix, args.output, args.reviewed_sha256)
            print(json.dumps(result, indent=2))
        else:
            from .analysis import analyze
            print(json.dumps(analyze(args.campaign, args.output), indent=2))
    except (FluidGymPhysicsError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
