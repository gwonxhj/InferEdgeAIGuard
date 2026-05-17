# Runtime Reliability Signals

InferEdgeAIGuard can read InferEdgeOrchestrator's
`inferedge-orchestration-summary-v1` output and convert scheduling telemetry
into the existing `inferedge-aiguard-diagnosis-v1` guard analysis contract.

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

The summary is produced by InferEdgeOrchestrator's synthetic/dummy 3-agent
scheduling demo and connects Forge `agent_manifest.json` and Runtime
`result.agent` metadata to runtime policy evidence. AIGuard interprets the
deterministic scheduling signals that are present in the summary; it does not
infer real hardware bottlenecks unless those signals are provided by runtime
telemetry.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | Meaning |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | Agent tasks miss latency budgets under load |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | Work is being dropped to protect the system |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | Fallback path is used too often |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | Scheduler had to intervene because backlog grew |
| `sustained_overload_risk` | `max_total_queue_depth` | `>= 3` | `>= 8` | Sustained queue depth indicates multi-agent overload pressure |

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

## CLI

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
```

The unified `reason` command also auto-routes Orchestrator summaries:

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

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
