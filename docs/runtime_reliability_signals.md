# Runtime Reliability Signals

InferEdgeAIGuard can read InferEdgeOrchestrator's
`inferedge-orchestration-summary-v1` output and InferEdge Runtime's additive
`inferedge-runtime-result-v1` operation evidence fields, then convert the
deterministic signals into the existing `inferedge-aiguard-diagnosis-v1` guard
analysis contract.

This is an optional evidence path. AIGuard does not become the deployment
decision owner; InferEdgeLab still owns the final deployment decision.

## Input

Expected input:

- `schema_version: inferedge-orchestration-summary-v1`
- `agent_runtime_summary.totals`
- `policy_decision_log` or `policy_decisions`
- optional `drop_events` / `overload_events`
- optional `sustained_runtime_summary`
- optional `queue_depth_timeline`
- optional `latency_timeline`
- optional `multi_workload_sustained_summary`
- optional `tegrastats_timeline`
- optional embedded `runtime_result` / `runtime_results`

The summary is produced by InferEdgeOrchestrator's 3-agent scheduling and
sustained workload demos. It connects Forge `agent_manifest.json` and Runtime
`result.agent` metadata to runtime policy evidence. AIGuard interprets only the
deterministic signals that are present in the summary; it does not infer real
hardware bottlenecks unless those signals are provided by runtime telemetry.

Runtime result input is also supported directly when the JSON includes:

- `schema_version: inferedge-runtime-result-v1`
- optional `runtime_health_snapshot`
- optional `runtime_error_classification`
- optional `runtime_events`

AIGuard treats these fields as Runtime-provided operation evidence. It does not
guess a root cause from missing logs.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | Meaning |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | Agent tasks miss latency budgets under load |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | Work is being dropped to protect the system |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | Fallback path is used too often |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | Scheduler had to intervene because backlog grew |
| `sustained_overload_risk` | `max_total_queue_depth` | `>= 3` | `>= 8` | Sustained queue depth indicates multi-agent overload pressure |
| `profiled_workload_pressure` | `profiled_workload_risk_count` | `>= 1` | `>= 3` | Sustained workload profiles show which runtime loops are under pressure |
| `thermal_resource_pressure` | `max_temperature_c` | `>= 70.0` | `>= 85.0` | Tegrastats indicates thermal/resource pressure during sustained execution |
| `runtime_backend_unavailable` | `engine_available` | `0` | n/a | Runtime could not confirm backend/engine availability |
| `runtime_latency_budget_overrun` | `latency_budget_exceeded` | `true` | n/a | Runtime exceeded the latency budget or missed a deadline |
| `runtime_error_classification` | `runtime_error_severity` | present | n/a | Runtime classified an execution warning/error with a retry hint |
| `runtime_thermal_memory_evidence_missing` | `thermal_memory_evidence_available` | `false` on Jetson | n/a | Jetson result lacks thermal/memory context for sustained review |

These thresholds are intentionally deterministic and local-first. They are
review signals, not production SLOs.

## Sustained Scenario Fields

When Orchestrator emits sustained demo telemetry, AIGuard also preserves:

- `scenario_mode` from `run.scenario_mode` or `sustained_runtime_summary`
- `max_total_queue_depth` from `sustained_runtime_summary` or
  `queue_depth_timeline`
- `policy_decision_reasons` from `decision_reason`, `reason`, or `decision`
- `queue_depth_sample_count`
- `latency_sample_count`

This lets the report explain not only that work was dropped, but also why the
scheduler intervened and whether queue depth kept growing under sustained
multi-agent load.

## Multi-Workload Sustained Fields

When Orchestrator emits `multi_workload_sustained_summary`, AIGuard preserves
and reasons over:

- `workload_profiles` for Vision / Voice-Command / Safety-Monitor profiles
- `runtime_loop` such as `yolo_detection_loop`, `whisper_command_burst`, or
  `safety_monitor_loop`
- `ingress_profile` such as `frame_queue`, `fastapi_concurrent_request`, or
  `periodic_monitor`
- per-workload `dropped`, `deadline_missed`, `fallback_used`, and
  `max_queue_backlog`
- `observed_runtime_signals` such as executed/drop/deadline/fallback counts,
  policy decision reasons, max total queue depth, `local_profile_adapter_count`,
  `local_profile_elapsed_ms`, and `local_profile_kinds`

If any workload profile shows dropped work, deadline misses, fallback usage, or
queue backlog, AIGuard emits `profiled_workload_pressure`. When Orchestrator
uses lightweight local CPU profile adapters, AIGuard preserves adapter count,
elapsed profile time, implementation, work units, and profile kinds in the raw
context. This explains which
runtime loop was affected instead of only reporting an aggregate drop or
deadline miss rate.

## Tegrastats Fields

When Orchestrator includes `tegrastats_timeline.summary`, AIGuard records:

- `tegrastats_sample_count`
- `max_temperature_c`
- `max_gpu_percent`
- `max_ram_used_mb`

`thermal_resource_pressure` is emitted only when temperature evidence is
present. This keeps synthetic local demos compatible while allowing Jetson
sustained runs to explain thermal/resource degradation signals.

## Runtime Operation Fields

When Runtime emits additive health/error/event fields, AIGuard preserves and
reasons over:

- `runtime_health_snapshot.engine_available`
- `runtime_health_snapshot.latency_budget_ms`
- `runtime_health_snapshot.latency_budget_exceeded`
- `runtime_health_snapshot.deadline_missed`
- `runtime_health_snapshot.thermal_memory_evidence_available`
- `runtime_error_classification.category`
- `runtime_error_classification.severity`
- `runtime_error_classification.retry_hint`
- `runtime_events[].latency_budget_exceeded`
- `runtime_events[].deadline_missed`

These fields are interpreted as operation evidence. For example, a Runtime
result with `engine_available: false`, `latency_budget_exceeded: true`, and a
`retry_hint` produces deterministic guard evidence such as
`runtime_backend_unavailable`, `runtime_latency_budget_overrun`, and
`runtime_error_classification`.

## CLI

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
```

Runtime operation results can be analyzed directly:

```bash
python -m inferedge_aiguard.cli reason-runtime \
  --input reports/runtime_result.json
```

The unified `reason` command also auto-routes Orchestrator summaries:

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

It also auto-routes Runtime results that include `schema_version:
inferedge-runtime-result-v1` or the additive Runtime operation fields.

Remote dispatch starter results can also be analyzed directly:

```bash
python -m inferedge_aiguard.cli reason-remote-dispatch \
  --input reports/remote_dispatch_result.json
```

The unified `reason` command auto-routes `schema_version:
inferedge-remote-dispatch-result-v1` as well. AIGuard interprets worker
selection status and explicit HTTP/SSH starter execution status as
`remote_execution_plan_only`, `remote_execution_starter_success`, or
`remote_execution_failed` evidence. This remains starter evidence, not a claim
of production remote execution.

## Output

The output uses the existing diagnosis report schema:

```json
{
  "schema_version": "inferedge-aiguard-diagnosis-v1",
  "guard_verdict": "blocked",
  "severity": "high",
  "primary_reason": "drop_rate indicates runtime reliability risk under orchestrated multi-agent load.",
  "evidence": [
    {
      "type": "excessive_drop_rate",
      "metric_name": "drop_rate",
      "observed_value": 0.58,
      "threshold": 0.2,
      "severity": "high",
      "status": "failed"
    },
    {
      "type": "sustained_overload_risk",
      "metric_name": "max_total_queue_depth",
      "observed_value": 6,
      "threshold": 3,
      "severity": "medium",
      "status": "failed"
    },
    {
      "type": "profiled_workload_pressure",
      "metric_name": "profiled_workload_risk_count",
      "observed_value": 2,
      "threshold": 1,
      "severity": "medium",
      "status": "failed"
    },
    {
      "type": "thermal_resource_pressure",
      "metric_name": "max_temperature_c",
      "observed_value": 76.2,
      "threshold": 70.0,
      "severity": "medium",
      "status": "failed"
    }
  ]
}
```

## Boundary

- AIGuard explains runtime reliability risk.
- Orchestrator records scheduling and policy evidence.
- Lab remains the final deployment decision owner.
- This does not add production queue/cloud orchestration or an LLM agent
  framework.
