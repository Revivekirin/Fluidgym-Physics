"""Thin CLI wrappers; all logic lives in the library modules."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    for name in ("plan", "input-report", "fetch-inputs", "preflight", "approve-matrix", "prepare-primary", "run"):
        command = sub.add_parser(name)
        command.add_argument("--matrix", required=True)
        if name in ("input-report", "fetch-inputs", "preflight", "run"):
            command.add_argument("--data-root", required=name in ("input-report", "fetch-inputs"))
        if name in ("plan", "preflight"):
            command.add_argument("--output")
        if name == "preflight":
            command.add_argument("--acquisition")
        if name == "fetch-inputs":
            command.add_argument("--output", required=True)
            command.add_argument("--revision")
            command.add_argument("--max-download-gib", type=float, default=20)
        if name in ("approve-matrix", "prepare-primary"):
            command.add_argument("--preflight", required=True)
            command.add_argument("--output", required=True)
        if name == "approve-matrix":
            command.add_argument("--accept-budget", action="store_true")
        if name == "run":
            command.add_argument("--output", required=True)
            approval = command.add_mutually_exclusive_group(required=True)
            approval.add_argument("--reviewed-sha256")
            approval.add_argument("--approval")
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
        elif args.cmd in ("plan", "input-report", "fetch-inputs", "preflight", "approve-matrix", "prepare-primary", "run"):
            from .characterization import load_matrix, estimate, digest
            verify_upstream()
            matrix = load_matrix(args.matrix)
            if args.cmd in ("plan", "preflight") and args.output and Path(args.output).exists():
                raise FileExistsError(f'refusing to overwrite {args.output}')
            if args.cmd == "plan":
                result = {"matrix_sha256": digest(args.matrix), "review_status":matrix['review_status'],
                          "env_ids":[r['env_id'] for r in matrix['environments']],
                          "budget":matrix['budget'], **estimate(matrix)}
            elif args.cmd == "input-report":
                from .runner import input_report
                result = input_report(matrix, args.data_root)
            elif args.cmd == "fetch-inputs":
                from .acquisition import fetch_inputs
                result = fetch_inputs(args.matrix, args.data_root, args.output,
                                      args.revision, args.max_download_gib)
            elif args.cmd == "prepare-primary":
                from .review import prepare_primary
                result = prepare_primary(args.matrix,args.preflight,args.output)
            elif args.cmd == "approve-matrix":
                from .review import approve_matrix
                result = approve_matrix(args.matrix, args.preflight, args.output, args.accept_budget)
            elif args.cmd == "preflight":
                from .runner import preflight
                result = {**preflight(matrix, data_root=args.data_root), "matrix_sha256":digest(args.matrix), "estimate":estimate(matrix)}
                if args.acquisition:
                    from .acquisition import acquisition_provenance
                    result['dataset_source'] = acquisition_provenance(args.acquisition,args.matrix,result['data_root'])
            else:
                from .runner import run_matrix
                result = run_matrix(args.matrix, args.output, args.reviewed_sha256, args.data_root, args.approval)
            if args.cmd in ("plan", "preflight") and args.output:
                from .characterization import write_json
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                write_json(args.output, result)
                result = {"output":args.output, "status":result.get("status", "planned"),
                          "matrix_sha256":digest(args.matrix), "estimate":estimate(matrix),
                          "budget":matrix["budget"], "review_status":matrix["review_status"]}
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
