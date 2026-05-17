# Runtime Reliability Signals

InferEdgeAIGuard는 InferEdgeOrchestrator의
`inferedge-orchestration-summary-v1` 결과를 읽고 scheduling telemetry를
기존 `inferedge-aiguard-diagnosis-v1` guard analysis contract로 변환할 수
있습니다.

이 경로는 optional evidence입니다. AIGuard는 deployment decision owner가
아니며, 최종 deployment decision은 계속 InferEdgeLab이 담당합니다.

## 입력

예상 입력:

- `schema_version: inferedge-orchestration-summary-v1`
- `agent_runtime_summary.totals`
- `policy_decision_log` 또는 `policy_decisions`
- optional `drop_events` / `overload_events`
- optional `sustained_runtime_summary`
- optional `queue_depth_timeline`
- optional `latency_timeline`

이 summary는 InferEdgeOrchestrator의 3-agent scheduling demo에서 생성되며,
Forge `agent_manifest.json`과 Runtime `result.agent` metadata를 runtime
policy evidence로 이어줍니다.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | 의미 |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | 부하 상황에서 agent task가 latency budget을 놓침 |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | 시스템 보호를 위해 workload가 많이 drop됨 |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | fallback path가 과도하게 사용됨 |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | backlog 때문에 scheduler가 개입함 |
| `sustained_overload_risk` | `max_total_queue_depth` | `>= 3` | `>= 8` | sustained queue depth가 multi-agent overload 압력을 보여줌 |

이 threshold는 local-first deterministic review signal입니다. production SLO로
해석하지 않습니다.

## Sustained Scenario Fields

Orchestrator가 sustained demo telemetry를 내보내면 AIGuard는 다음 값도
보존합니다.

- `run.scenario_mode` 또는 `sustained_runtime_summary`의 `scenario_mode`
- `sustained_runtime_summary` 또는 `queue_depth_timeline` 기반
  `max_total_queue_depth`
- `decision_reason`, `reason`, `decision` 기반 `policy_decision_reasons`
- `queue_depth_sample_count`
- `latency_sample_count`

따라서 report는 workload가 drop되었다는 사실뿐 아니라, scheduler가 왜
개입했는지와 sustained multi-agent load에서 queue depth가 얼마나 커졌는지도
설명할 수 있습니다.

## CLI

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
```

unified `reason` 명령도 Orchestrator summary를 자동 라우팅합니다.

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

## 출력

출력은 기존 diagnosis report schema를 사용합니다.

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

## 경계

- AIGuard는 runtime reliability risk를 설명합니다.
- Orchestrator는 scheduling/policy evidence를 기록합니다.
- Lab은 final deployment decision owner입니다.
- production queue/cloud orchestration 또는 LLM agent framework를 추가하지
  않습니다.
