# Campaign execution report

Status (2026-10-14): readiness verification blocked pending operator-provided server evidence. This is a gate report, not an executed-campaign report.

The researcher reports completed official acquisition, full and primary preflight, and primary budget review. These server artifacts are not available in this local workspace. The operator manages the remote server; no remote operation or CFD was performed in this session.

Local upstream verification passed at `50071140b73a2a917fb96d33522a769f903f8c27`, source tree `8a8476b966e496341676ea36384589028f4dc450`, with a clean upstream checkout. This does not establish the server checkout or imported package identity. Local Python has neither FluidGym nor torch installed; this Mac is not the target CUDA execution environment.

## Gate evidence still required

- Exact preparation directory and successful full/primary preflight artifacts, bound to their matrix hashes.
- Server upstream identity and imported FluidGym path.
- Acquisition revision, required-file manifest, current SHA-256 hashes and exact data root.
- Exact reviewed primary matrix and approval artifact, if present. Approval existence is unknown, not established absent. Do not regenerate an existing valid approval.
- Available GPU/VRAM, free disk on the output filesystem, and the external scheduler wall-time limit or timeout command. Runner checks at step boundaries cannot stop a hung native solver call.

Primary scope remains six environments, 60 nominal zero-action runs and 58,200 environment steps. No matrix, solver, physical parameter or approval artifact was changed. Runs launched here: zero. Server successful/failed/skipped counts are unknown; planned runs must not be reported as observed failures or skips.

Next operator command, from the server repository:

```bash
find results -type f \( -name '*preflight*.json' -o -name approval.json -o -name preparation.json -o -name '*plan*.json' \) -print
```

Provide those paths before choosing the exact preparation directory. If readiness passes and repository approval is confirmed absent, the explicit approval command is:

```bash
python -m fluidgym_physics.cli approve-matrix \
  --matrix "$FG_PREP/primary/matrix.json" \
  --preflight "$FG_PREP/primary-preflight.json" \
  --output "$FG_PREP/approved-primary" --accept-budget
```

Here `FG_PREP` must identify the verified preparation directory. This command is conditional operator authorization, not an instruction to replace an existing approval. Campaign execution remains blocked until all gates are verified.
