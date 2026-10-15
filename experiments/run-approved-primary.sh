#!/usr/bin/env bash
# Run from the repository root in the activated server environment.
# No approval creation, download, retry, or resume.
set -euo pipefail
export FG_PREP="${1:?Usage: bash experiments/run-approved-primary.sh PREPARATION_DIRECTORY}"
command -v nvidia-smi >/dev/null
python - <<'PY'
import json, os, shutil
from pathlib import Path
from fluidgym_physics.characterization import load_matrix, digest
from fluidgym_physics.review import check_approval, primary_draft
from fluidgym_physics.upstream import verify_upstream
p = Path(os.environ['FG_PREP'])
verify_upstream()
full_path = Path('experiments/characterization.v1.json')
draft_path = p/'primary/matrix.json'
reviewed_path = p/'approved-primary/matrix.json'
expected = primary_draft(load_matrix(full_path))
assert load_matrix(draft_path) == expected, 'Unexpected primary protocol'
expected['review_status'] = 'reviewed'
assert load_matrix(reviewed_path) == expected, 'Reviewed protocol differs'
reports = []
for name, matrix in [('full-preflight.json', full_path), ('primary-preflight.json', draft_path)]:
    report = json.loads((p/name).read_text())
    assert report['status'] == 'passed' and report['matrix_sha256'] == digest(matrix)
    assert report['input_manifest'] and report['dataset_source']
    for filename, item in report['input_manifest'].items():
        assert digest(filename) == item['sha256'], f'Changed input: {filename}'
    reports.append(report)
assert reports[0]['dataset_source']['revision'] == reports[1]['dataset_source']['revision']
assert reports[1]['dataset_source']['revision'] == 'a8c00235a814828441a0c5638e6f803ef62bfa31'
assert reports[1]['dataset_source']['repo_id'] == 'safe-autonomous-systems/fluidgym-data'
approval = check_approval(p/'approved-primary/approval.json', reviewed_path, reports[1])
assert approval['source_matrix_sha256'] == digest(draft_path)
assert approval['preflight_sha256'] == digest(p/'primary-preflight.json')
assert approval['dataset_source'] == reports[1]['dataset_source']
assert expected['budget']['max_wall_hours'] == 72, 'External timeout requires the reviewed 72-hour cap'
required = expected['budget']['max_output_gib'] + expected['budget']['minimum_free_gib']
assert shutil.disk_usage(p).free >= required * 1024**3, 'Insufficient free disk'
print('Saved preflights, current inputs, protocol, approval and disk checks passed.')
PY

FG_EXEC=$(mktemp -d "$FG_PREP/execution-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
printf 'Execution directory: %s\n' "$FG_EXEC"

# A separate process session prevents terminal Ctrl+C from bypassing supervision.
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
