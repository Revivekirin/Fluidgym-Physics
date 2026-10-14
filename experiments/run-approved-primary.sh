#!/usr/bin/env bash
# Run from the repository root in the activated server environment.
# No approval creation, download, retry, or resume.
set -euo pipefail
export FG_PREP="${1:?Usage: bash experiments/run-approved-primary.sh PREPARATION_DIRECTORY}"
command -v timeout >/dev/null
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
exec > >(tee "$FG_EXEC/launcher.log") 2>&1
nvidia-smi > "$FG_EXEC/gpu-before.txt"
df -h "$FG_PREP" > "$FG_EXEC/disk-before.txt"
timeout --version > "$FG_EXEC/timeout-version.txt"
printf '%s\n' 'timeout --signal=TERM --kill-after=60s 259140s' > "$FG_EXEC/external-wall-limit.txt"
# TERM after 71h59m, forced termination 60s later: total 72h.
nvidia-smi --query-gpu=timestamp,uuid,memory.used,memory.total,utilization.gpu --format=csv -l 5 > "$FG_EXEC/gpu.csv" 2> "$FG_EXEC/gpu-monitor-errors.log" &
FG_MONITOR=$!
trap 'kill "$FG_MONITOR" 2>/dev/null || true; wait "$FG_MONITOR" 2>/dev/null || true' EXIT
FG_STARTED=$(date +%s)
date -u +%FT%TZ > "$FG_EXEC/started-utc.txt"
set +e
timeout --signal=TERM --kill-after=60s 259140s \
  python -u -m fluidgym_physics.cli run \
  --matrix "$FG_PREP/approved-primary/matrix.json" \
  --approval "$FG_PREP/approved-primary/approval.json" \
  --output "$FG_EXEC/campaign" > "$FG_EXEC/run.log" 2>&1
FG_RC=$?
set -e
printf '%s\n' "$FG_RC" > "$FG_EXEC/runner-exit-code.txt"
printf '%s\n' "$(( $(date +%s) - FG_STARTED ))" > "$FG_EXEC/runner-wall-seconds.txt"
date -u +%FT%TZ > "$FG_EXEC/finished-utc.txt"
kill "$FG_MONITOR" 2>/dev/null || true
wait "$FG_MONITOR" 2>/dev/null || true
trap - EXIT
printf 'Runner exit code: %s; results: %s\n' "$FG_RC" "$FG_EXEC"
if [ "$FG_RC" -ne 0 ]; then
  echo 'Stopped without retry. Inspect logs/status before offline analysis of completed runs.'
  exit "$FG_RC"
fi
python -m fluidgym_physics.cli analyze --campaign "$FG_EXEC/campaign" \
  --output "$FG_EXEC/analysis" > "$FG_EXEC/analysis.log" 2>&1
echo 'Campaign and offline analysis completed.'
