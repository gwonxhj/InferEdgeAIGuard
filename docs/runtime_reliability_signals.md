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

The summary is produced by InferEdgeOrchestrator's 3-agent scheduling demo and
connects Forge `agent_manifest.json` and Runtime `result.agent` metadata to
runtime policy evidence.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | Meaning |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | Agent tasks miss latency budgets under load |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | Work is being dropped to protect the system |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | Fallback path is used too often |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | Scheduler had to intervene because backlog grew |

These thresholds are intentionally deterministic and local-first. They are
review signals, not production SLOs.

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
