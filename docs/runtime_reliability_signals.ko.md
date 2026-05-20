# Runtime Reliability Signals

InferEdgeAIGuard는 InferEdgeOrchestrator의
`inferedge-orchestration-summary-v1` 결과와 InferEdge Runtime의 additive
`inferedge-runtime-result-v1` operation evidence 필드를 읽고, deterministic
signal을 기존 `inferedge-aiguard-diagnosis-v1` guard analysis contract로
변환할 수 있습니다.

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
- optional `multi_workload_sustained_summary`
- optional `tegrastats_timeline`
- optional embedded `runtime_result` / `runtime_results`

이 summary는 InferEdgeOrchestrator의 3-agent scheduling 및 sustained
workload demo에서 생성되며, Forge `agent_manifest.json`과 Runtime
`result.agent` metadata를 runtime policy evidence로 이어줍니다. AIGuard는
summary에 존재하는 deterministic signal만 해석하며, 실제 hardware
bottleneck은 runtime telemetry로 제공된 경우에만 근거로 사용합니다.

Runtime result도 아래 필드가 있으면 직접 입력으로 분석할 수 있습니다.

- `schema_version: inferedge-runtime-result-v1`
- optional `runtime_health_snapshot`
- optional `runtime_error_classification`
- optional `runtime_events`

AIGuard는 이 필드를 Runtime이 제공한 operation evidence로만 해석합니다.
누락된 log를 바탕으로 root cause를 추측하지 않습니다.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | 의미 |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | 부하 상황에서 agent task가 latency budget을 놓침 |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | 시스템 보호를 위해 workload가 많이 drop됨 |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | fallback path가 과도하게 사용됨 |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | backlog 때문에 scheduler가 개입함 |
| `sustained_overload_risk` | `max_total_queue_depth` | `>= 3` | `>= 8` | sustained queue depth가 multi-agent overload 압력을 보여줌 |
| `profiled_workload_pressure` | `profiled_workload_risk_count` | `>= 1` | `>= 3` | sustained workload profile 중 어떤 runtime loop가 압력을 받는지 표시 |
| `thermal_resource_pressure` | `max_temperature_c` | `>= 70.0` | `>= 85.0` | sustained 실행 중 tegrastats가 thermal/resource pressure를 보여줌 |
| `runtime_backend_unavailable` | `engine_available` | `0` | n/a | Runtime이 backend/engine availability를 확인하지 못함 |
| `runtime_latency_budget_overrun` | `latency_budget_exceeded` | `true` | n/a | Runtime이 latency budget을 초과했거나 deadline을 놓침 |
| `runtime_error_classification` | `runtime_error_severity` | present | n/a | Runtime이 retry hint와 함께 execution warning/error를 분류함 |
| `runtime_thermal_memory_evidence_missing` | `thermal_memory_evidence_available` | `false` on Jetson | n/a | Jetson 결과에 sustained review용 thermal/memory context가 없음 |

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

## Multi-Workload Sustained Fields

Orchestrator가 `multi_workload_sustained_summary`를 내보내면 AIGuard는
다음 값을 보존하고 해석합니다.

- Vision / Voice-Command / Safety-Monitor의 `workload_profiles`
- `yolo_detection_loop`, `whisper_command_burst`, `safety_monitor_loop` 같은
  `runtime_loop`
- `frame_queue`, `fastapi_concurrent_request`, `periodic_monitor` 같은
  `ingress_profile`
- workload별 `dropped`, `deadline_missed`, `fallback_used`,
  `max_queue_backlog`
- executed/drop/deadline/fallback count, policy decision reason, max total
  queue depth, `local_profile_adapter_count`, `local_profile_elapsed_ms`,
  `local_profile_kinds` 같은 `observed_runtime_signals`

workload profile 중 drop, deadline miss, fallback, queue backlog가 관측되면
AIGuard는 `profiled_workload_pressure` evidence를 생성합니다. Orchestrator가
lightweight local CPU profile adapter를 사용하면 AIGuard는 adapter count,
elapsed profile time, implementation, work units, profile kinds를 raw context에
보존합니다. 이를 통해
aggregate drop rate만 보여주는 대신 어떤 runtime loop가 영향을 받았는지
설명할 수 있습니다.

## Tegrastats Fields

Orchestrator가 `tegrastats_timeline.summary`를 포함하면 AIGuard는 다음 값을
기록합니다.

- `tegrastats_sample_count`
- `max_temperature_c`
- `max_gpu_percent`
- `max_ram_used_mb`

`thermal_resource_pressure`는 temperature evidence가 있을 때만 생성합니다.
따라서 synthetic local demo와 호환성을 유지하면서도 Jetson sustained run에서는
thermal/resource degradation signal을 설명할 수 있습니다.

## Runtime Operation Fields

Runtime이 additive health/error/event 필드를 내보내면 AIGuard는 다음 값을
보존하고 해석합니다.

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

이 필드는 operation evidence로 해석됩니다. 예를 들어 Runtime result에
`engine_available: false`, `latency_budget_exceeded: true`, `retry_hint`가
있으면 AIGuard는 `runtime_backend_unavailable`,
`runtime_latency_budget_overrun`, `runtime_error_classification` 같은
deterministic guard evidence를 생성합니다.

## CLI

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
```

Runtime operation result도 직접 분석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-runtime \
  --input reports/runtime_result.json
```

unified `reason` 명령도 Orchestrator summary를 자동 라우팅합니다.

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

`schema_version: inferedge-runtime-result-v1` 또는 Runtime operation 필드가
있는 Runtime result도 unified `reason` 명령이 자동 라우팅합니다.

Remote dispatch starter result도 직접 분석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-remote-dispatch \
  --input reports/remote_dispatch_result.json
```

unified `reason` 명령은 `schema_version: inferedge-remote-dispatch-result-v1`도
자동 라우팅합니다. AIGuard는 worker selection 상태와 explicit HTTP/SSH starter
execution 상태를 `remote_execution_plan_only`,
`remote_execution_starter_success`, `remote_execution_failed` evidence로
해석합니다. 이는 starter evidence이며 production remote execution을 완료했다는
의미가 아닙니다.

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

## 경계

- AIGuard는 runtime reliability risk를 설명합니다.
- Orchestrator는 scheduling/policy evidence를 기록합니다.
- Lab은 final deployment decision owner입니다.
- production queue/cloud orchestration 또는 LLM agent framework를 추가하지
  않습니다.
