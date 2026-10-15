#!/usr/bin/env bash
# Run from the repository root in the activated server environment.
# No approval creation, download, retry, or resume.
set -euo pipefail
export FG_PREP="${1:?Usage: bash experiments/run-approved-primary.sh PREPARATION_DIRECTORY}"
command -v # A separate process session prevents terminal Ctrl+C from bypassing supervision.
# The supervisor forwards SIGINT/SIGTERM, escalates after 60s, and writes sidecars.
set +e
python -u -m fluidgym_physics.execution --output "$FG_EXEC" -- \
  python -u -m fluidgym_physics.cli run \
  --matrix "$FG_PREP/approved-primary/matrix.json" \
  --approval "$FG_PREP/approved-primary/approval.json" \
  --output "$FG_EXEC/campaign"
FG_RC=$?
set -e
if [ "$FG_RC" -ne 0 ]; then
  echo 'Stopped without retry. Inspect execution-status.json and recovered-run-statuses.json.'
  exit "$FG_RC"
fi
python -m fluidgym_physics.cli analyze --campaign "$FG_EXEC/campaign" \
  --output "$FG_EXEC/analysis" > "$FG_EXEC/analysis.log" 2>&1
echo 'Campaign and offline analysis completed.'
