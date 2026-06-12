#!/usr/bin/env bash
set -euo pipefail

AIGUARD_DIR="${AIGUARD_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUTPUT_DIR="${OUTPUT_DIR:-$AIGUARD_DIR/reports/runtime_intelligence_optional_stale_drop}"
LAB_DIR="${LAB_DIR:-$AIGUARD_DIR/../InferEdgeLab}"
LAB_SOURCE_TRACEABILITY_GATE="${LAB_SOURCE_TRACEABILITY_GATE:-$LAB_DIR/scripts/check_runtime_intelligence_source_traceability.py}"

usage() {
  cat <<'EOF'
InferEdgeAIGuard Runtime Intelligence optional stale-drop producer smoke

Usage:
  bash scripts/smoke_runtime_intelligence_optional_stale_drop.sh [--output-dir <path>] [--lab-dir <path>]
  bash scripts/smoke_runtime_intelligence_optional_stale_drop.sh --help

This smoke verifies that AIGuard can regenerate the curated optional stale-drop
guard_analysis fixture from committed source artifacts. When a sibling Lab
checkout is available, it also runs Lab's source traceability gate against the
generated AIGuard optional-present alignment metadata.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --output-dir)
      if [[ $# -lt 2 ]]; then
        echo "--output-dir requires a value" >&2
        exit 2
      fi
      OUTPUT_DIR="$2"
      shift
      ;;
    --lab-dir)
      if [[ $# -lt 2 ]]; then
        echo "--lab-dir requires a value" >&2
        exit 2
      fi
      LAB_DIR="$2"
      LAB_SOURCE_TRACEABILITY_GATE="$LAB_DIR/scripts/check_runtime_intelligence_source_traceability.py"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "$AIGUARD_DIR"
mkdir -p "$OUTPUT_DIR"

PYTHON_CMD=(python)
EXPECTED_JSON="examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json"
GENERATED_JSON="$OUTPUT_DIR/aiguard_runtime_operation_guard_analysis_optional_stale_drop.generated.json"
HANDOFF_JSON="$OUTPUT_DIR/edgeenv_lab_handoff_source_traceability.json"
ALIGNMENT_JSON="$OUTPUT_DIR/aiguard_edgeenv_handoff_alignment_optional_present.generated.json"
ALIGNMENT_MD="$OUTPUT_DIR/aiguard_edgeenv_handoff_alignment_optional_present.generated.md"
SUMMARY_MD="$OUTPUT_DIR/aiguard_optional_stale_drop_producer_smoke_summary.md"
LAB_SUMMARY_MD="$OUTPUT_DIR/lab_source_traceability_summary.md"

echo "== AIGuard Runtime Intelligence optional stale-drop producer smoke =="
echo "Output: $OUTPUT_DIR"

"${PYTHON_CMD[@]}" -m inferedge_aiguard.cli build-runtime-intelligence-optional-stale-drop \
  --edgeenv-regression examples/runtime_intelligence/edgeenv_runtime_regression_with_optional_stale_drop_context.json \
  --remote-dispatch examples/runtime_intelligence/remote_dispatch_fallback_recovered_result.json \
  --orchestration-summary examples/runtime_intelligence/orchestrator_multi_workload_sustained_summary.json \
  --save-json "$GENERATED_JSON" >/dev/null

"${PYTHON_CMD[@]}" - "$EXPECTED_JSON" "$GENERATED_JSON" <<'PY'
import json
import sys
from pathlib import Path

expected = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
generated = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if generated != expected:
    raise SystemExit("generated optional stale-drop guard_analysis differs from committed fixture")
PY

"${PYTHON_CMD[@]}" - "$HANDOFF_JSON" <<'PY'
import json
import sys
from pathlib import Path

reproduction_command = [
    "python",
    "-m",
    "inferedge_aiguard.cli",
    "build-runtime-intelligence-optional-stale-drop",
    "--edgeenv-regression",
    "examples/runtime_intelligence/edgeenv_runtime_regression_with_optional_stale_drop_context.json",
    "--remote-dispatch",
    "examples/runtime_intelligence/remote_dispatch_fallback_recovered_result.json",
    "--orchestration-summary",
    "examples/runtime_intelligence/orchestrator_multi_workload_sustained_summary.json",
    "--save-json",
    "examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json",
]
source_artifact = {
    "repository": "InferEdgeAIGuard",
    "path": "examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json",
    "schema_version": "inferedge-aiguard-diagnosis-v1",
    "role": "aiguard-optional-stale-drop-full-evidence-source",
    "context_role": "read_only_cross_repo_traceability",
    "reproduction_command": reproduction_command,
}
handoff = {
    "schema_version": "edgeenv.runtime-intelligence-lab-handoff.v1",
    "role": "edgeenv-runtime-intelligence-lab-handoff",
    "edgeenv_report_summary": {
        "producer_lineage_guard_alignment_present": True,
        "producer_lineage_guard_alignment_run_ids": [
            "edgeenv-smoke-candidate",
        ],
    },
    "lab_bundle_alignment": {
        "external_aiguard_required_evidence_types": [
            "runtime_telemetry_context_coverage",
            "edgeenv_orchestrator_producer_lineage",
            "edgeenv_orchestrator_operation_risk_rollup",
            "edgeenv_orchestrator_task_event_rollup",
            "edgeenv_orchestrator_operation_timeline_summary",
            "runtime_history_seed_run_config_traceability",
            "runtime_queue_overload",
            "runtime_thermal_instability",
            "remote_execution_recovered_by_fallback",
        ],
        "optional_aiguard_evidence_types": [
            "stale_frame_risk",
            "edgeenv_orchestrator_stale_drop_summary",
        ],
        "optional_aiguard_source_traceability": {
            "context_role": "read_only_optional_source_traceability",
            "edgeenv_does_not_generate_guard_analysis": True,
            "lab_is_final_decision_owner": True,
            "optional_present_source_artifact": source_artifact,
        },
        "boundary_flags": {
            "aiguard_guard_analysis_is_external": True,
            "edgeenv_does_not_generate_guard_analysis": True,
            "aiguard_is_final_decision_owner": False,
            "lab_is_final_decision_owner": True,
            "production_observability_platform": False,
        },
    },
}
Path(sys.argv[1]).write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
PY

"${PYTHON_CMD[@]}" -m inferedge_aiguard.cli check-edgeenv-handoff-alignment \
  --edgeenv-handoff "$HANDOFF_JSON" \
  --guard-analysis "$GENERATED_JSON" \
  --save-json "$ALIGNMENT_JSON" \
  --save-md "$ALIGNMENT_MD" >/dev/null

"${PYTHON_CMD[@]}" - "$ALIGNMENT_JSON" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("status") != "passed":
    raise SystemExit("generated AIGuard optional-present alignment did not pass")
if "optional_present_source_artifact" not in payload:
    raise SystemExit("generated AIGuard optional-present alignment is missing source artifact traceability")
PY

LAB_GATE_STATUS="skipped"
if [[ -f "$LAB_SOURCE_TRACEABILITY_GATE" ]]; then
  "${PYTHON_CMD[@]}" "$LAB_SOURCE_TRACEABILITY_GATE" \
    --edgeenv-handoff "$HANDOFF_JSON" \
    --aiguard-alignment "$ALIGNMENT_JSON" \
    --summary-out "$LAB_SUMMARY_MD"
  LAB_GATE_STATUS="passed"
fi

cat > "$SUMMARY_MD" <<EOF
# AIGuard Optional Stale-Drop Producer Smoke

- Status: passed
- generated_guard_analysis_matches_committed_fixture: true
- generated_alignment_status: passed
- optional_present_source_artifact: InferEdgeAIGuard/examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json
- optional_present_reproduction_command: python -m inferedge_aiguard.cli build-runtime-intelligence-optional-stale-drop --edgeenv-regression examples/runtime_intelligence/edgeenv_runtime_regression_with_optional_stale_drop_context.json --remote-dispatch examples/runtime_intelligence/remote_dispatch_fallback_recovered_result.json --orchestration-summary examples/runtime_intelligence/orchestrator_multi_workload_sustained_summary.json --save-json examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json
- lab_source_traceability_gate: $LAB_GATE_STATUS
- ownership: aiguard_is_final_decision_owner=false, lab_is_final_decision_owner=true
EOF

echo "AIGuard optional stale-drop producer smoke passed."
