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
- optional `worker_health_snapshot`
- optional `runtime_event_summary`
- optional `runtime_event_timeline`
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
- optional `runtime_operation_summary`

AIGuard는 이 필드를 Runtime이 제공한 operation evidence로만 해석합니다.
누락된 log를 바탕으로 root cause를 추측하지 않습니다.

Remote dispatch starter result도 아래 필드가 있으면 직접 입력으로 분석할 수
있습니다.

- `schema_version: inferedge-remote-dispatch-result-v1`
- optional `worker_selection_evidence`
- optional `remote_execution_plan`
- optional `remote_execution_result`
- optional `fallback_execution_result`
- optional `remote_operation_summary`
- optional `remote_runtime_event_summary`

AIGuard는 이 입력을 Orchestrator가 생산한 starter evidence로 해석합니다.
worker-selection, explicit HTTP/SSH starter status, bounded fallback recovery,
compact event-summary consistency는 설명할 수 있지만, production remote
execution 완료, long-lived worker readiness, secure tunnel operation,
production retry/failover, cloud orchestration을 확인하지 않습니다. 최종
deployment decision owner는 Lab입니다.

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
| `worker_health_degradation` | `degraded_or_constrained_worker_count` | `>= 1` | degraded worker `>= 3` 또는 constrained worker 존재 | worker health snapshot이 degraded/constrained runtime loop를 설명함 |
| `scheduler_delay_pattern` | `scheduler_delay_event_count` | `>= 1` | `>= 3` | runtime event timeline에서 task가 scheduler cycle을 넘겨 지연됨 |
| `queue_pressure_context` | `queue_pressure_reason_count` | concerning reason `>= 1` | n/a | queue pressure reason이 backlog가 overload threshold에 가까운지/넘었는지 설명함 |
| `worker_operation_risk_summary` | `worker_operation_risk_count` | `>= 1` | `>= 3` | worker operation risk summary가 latency/fallback/drop/queue-pressure risk label을 식별함 |
| `device_local_operation_context` | `device_local_event_count` | device-local task가 있으면 `>= 1` | n/a | device-local starter가 local producer source와 runtime event coverage를 기록했는지 설명함 |
| `runtime_backend_unavailable` | `engine_available` | `0` | n/a | Runtime이 backend/engine availability를 확인하지 못함 |
| `runtime_latency_budget_overrun` | `latency_budget_exceeded` | `true` | n/a | Runtime이 latency budget을 초과했거나 deadline을 놓침 |
| `runtime_error_classification` | `runtime_error_severity` | present | n/a | Runtime이 retry hint와 함께 execution warning/error를 분류함 |
| `runtime_operation_health` | `runtime_operation_summary_risk_count` | risk label 또는 review action `>= 1` | n/a | Runtime이 operation summary risk label, evidence gap, review action을 제공함 |
| `runtime_thermal_memory_evidence_missing` | `thermal_memory_evidence_available` | `false` on Jetson | n/a | Jetson 결과에 sustained review용 thermal/memory context가 없음 |
| `runtime_telemetry_context_coverage` | `runtime_telemetry_evidence_gap_count` | `>= 1` | n/a | EdgeEnv telemetry context의 baseline/candidate coverage, history entry, 또는 `telemetry_coverage.missing_fields`에 gap이 있음 |
| `runtime_history_seed_run_config_traceability` | `runtime_history_seed_run_config_count` | Runtime history seed는 보존됐지만 run_config marker가 부족하면 warning | n/a | EdgeEnv가 보존한 Runtime history seed run_config marker를 replay/comparability traceability evidence로 설명함 |
| `edgeenv_orchestrator_producer_lineage` | `device_local_producer_context_count` | 보존된 Orchestrator context에 device-local producer metadata가 없으면 warning | n/a | EdgeEnv가 보존한 device-local Orchestrator producer lineage를 traceability evidence로 설명함 |
| `remote_execution_plan_only` | `execution_requested` | `false` | n/a | remote dispatch가 worker를 선택했지만 plan-only starter boundary 안에 머무름 |
| `remote_execution_starter_success` | `remote_execution_status` | pass evidence only | n/a | explicit HTTP/SSH starter가 structured success response를 반환함 |
| `remote_execution_failed` | `remote_execution_status` / `error_category` | starter execution 실패 시 | n/a | explicit starter execution failure를 remote operation review evidence로 설명함 |
| `remote_execution_recovered_by_fallback` | `fallback_recovered` | primary failure 이후 `true` | n/a | bounded fallback이 starter path를 회복했지만 primary worker path는 review evidence로 남음 |
| `remote_runtime_event_summary_mismatch` | `remote_runtime_event_summary_consistent` | `false` | n/a | compact remote event summary가 producer events 또는 operation summary와 맞지 않음 |

이 threshold는 local-first deterministic review signal입니다. production SLO로
해석하지 않습니다.

EdgeEnv가 `runtime_telemetry.coverage`를 보존하면 AIGuard는 coverage ratio,
missing field name, `missing_telemetry_is_failure`를 evidence `raw_context`에
남깁니다. coverage field 누락은 deterministic warning context일 뿐이며,
AIGuard가 final deployment decision으로 승격하지 않습니다.

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

## Orchestrator Operation Telemetry Fields

Orchestrator가 Phase 2 operation telemetry를 내보내면 AIGuard는 다음 값을
보존하고 해석합니다.

- `worker_health_snapshot.health_state_counts`
- `worker_health_snapshot.degraded_workers`
- `worker_health_snapshot.constrained_workers`
- worker별 `health_reasons`, `drop_rate`, `deadline_miss_rate`,
  `fallback_rate`, `queue_pressure_ratio`, `runtime_loop`, `ingress_profile`
- worker별 `primary_health_reason`, `operation_risk_summary`,
  `device_local_validation`, `producer_stage`, `producer_sources`,
  `producer_event_count`
- `queue_state_summary.queue_pressure_reason`
- `queue_state_summary.max_pressure_task`
- `queue_state_summary.device_local_producer_sources`
- `queue_state_summary.producer_sources_by_task`
- `runtime_event_summary.policy_decision_reason_counts`
- `runtime_event_summary.drop_reason_counts`
- `runtime_event_summary.reason_counts`
- `runtime_event_summary.queue_pressure_reason_counts`
- `runtime_event_summary.fallback_decision_count`
- `runtime_event_summary.scheduler_delay_event_count`
- `runtime_event_summary.producer_sources`
- `runtime_event_summary.producer_event_count`
- `runtime_event_summary.device_local_event_count`
- `runtime_event_timeline[].scheduler_delay_cycles`
- `runtime_event_timeline[].queue_wait_ms`

`worker_health_degradation`은 Orchestrator가 하나 이상의 worker를 degraded
또는 constrained로 표시했을 때 생성됩니다. degraded worker는 warning
evidence이며, constrained worker 또는 높은 degraded count는 severity를 높입니다.
이렇게 해도 AIGuard는 evidence provider로 남고, 최종 판단은 Lab이 담당합니다.

`scheduler_delay_pattern`은 scheduler delay event가 관측된 경우에만 생성됩니다.
policy/drop reason count도 raw context에 보존하므로 backlog, load shedding,
fallback 등 어떤 scheduler reason과 연결되는지 설명할 수 있습니다.

`queue_pressure_context`는 Orchestrator가 threshold exceeded 또는 elevated
pressure 같은 concerning queue pressure reason을 기록했을 때 생성됩니다.
AIGuard는 pressure reason, max pressure task, policy reason count, drop reason
count를 review evidence로 보존하지만 root cause를 추측하지 않습니다.

`worker_operation_risk_summary`는 Orchestrator가
`latency_or_fallback_risk`, `drop_or_queue_pressure_risk` 같은 non-healthy
operation risk label을 기록했을 때 생성됩니다. 이는 `worker_health_degradation`
을 보완하며 Lab report가 바로 읽을 수 있는 worker별 risk label을 보존합니다.

`device_local_operation_context`는 device-local task가 있을 때 생성됩니다.
Orchestrator가 producer source와 device-local runtime event coverage를 기록하면
passed evidence가 되고, device-local task는 있는데 producer/event coverage가
없으면 warning evidence가 됩니다. 이는 local starter evidence이며 long-running
device operation 완료 증명이 아닙니다.

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
- `runtime_error_classification.retryable`
- `runtime_error_classification.retry_hint`
- `runtime_events[].retryable`
- `runtime_events[].latency_budget_exceeded`
- `runtime_events[].deadline_missed`
- `runtime_operation_summary.health_reason`
- `runtime_operation_summary.risk_labels`
- `runtime_operation_summary.evidence_gaps`
- `runtime_operation_summary.recommended_action`
- `runtime_operation_summary.decision_owner`
- `runtime_operation_summary.scheduler_owner`

이 필드는 operation evidence로 해석됩니다. 예를 들어 Runtime result에
`engine_available: false`, `latency_budget_exceeded: true`, retryable
`retry_hint`가 있으면 AIGuard는 `runtime_backend_unavailable`,
`runtime_latency_budget_overrun`, `runtime_error_classification` 같은
deterministic guard evidence를 생성합니다. AIGuard는 `retryable`을 Lab
review를 위한 Runtime-side failure evidence로 보존할 뿐, 직접 retry를
수행하거나 production worker behavior를 주장하지 않습니다.
`runtime_operation_summary`가 있으면 AIGuard는 Runtime이 제공한
`risk_labels`, `evidence_gaps`, `recommended_action`을
`runtime_operation_health` warning evidence로 보존합니다. 최종 deployment
decision owner는 계속 Lab입니다.

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

EdgeEnv runtime regression report도 직접 분석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input reports/edgeenv_runtime_regression.json
```

unified `reason` 명령도 EdgeEnv regression report를 자동 라우팅합니다.

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/edgeenv_runtime_regression.json
```

Runtime Intelligence chain smoke에서는 Lab이 optional evidence로 ingest하는
precomputed artifact도 같은 명령으로 만들 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input examples/runtime_intelligence/edgeenv_runtime_regression_with_orchestrator_feed.json \
  --save-json examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
python -m inferedge_aiguard.cli check-edgeenv-handoff-alignment \
  --edgeenv-handoff reports/edgeenv_runtime_intelligence_lab_handoff.json \
  --guard-analysis examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
```

이 경로는 EdgeEnv가 이미 계산한 same-condition regression과
`runtime_telemetry_context` coverage를 `runtime_latency_regression`,
`runtime_throughput_regression`, `runtime_memory_regression`,
`runtime_telemetry_context_coverage`, `runtime_telemetry_replay_context`,
`edgeenv_orchestrator_producer_lineage`
evidence로 변환합니다. AIGuard는 comparability를 다시 계산하지 않으며,
non-comparable 또는 same-condition이 아닌 report는
`edgeenv_comparability_guardrail` skipped evidence로 남깁니다.
EdgeEnv가 baseline 또는 candidate telemetry context 아래에
`orchestrator_operation_context`를 보존한 경우, AIGuard는 그 nested context의
queue depth, thermal, throttling hint를 supplemental operation evidence로
읽습니다. 이 feed는 Orchestrator verdict, EdgeEnv comparability gate, Lab
deployment decision으로 취급하지 않습니다.
EdgeEnv가 `candidate_context.producer`를 보존한 경우에는
`edgeenv_orchestrator_producer_lineage` evidence로 device-local producer
source, per-task source mapping, task stage mapping, event/task count를
설명합니다. 이 항목은 traceability evidence이며 deployment decision이나
comparability gate가 아닙니다.
보존된 Orchestrator context에
`downstream_guard_alignment.producer_lineage_evidence_type=edgeenv_orchestrator_producer_lineage`
가 포함되어 있으면 AIGuard는 이 marker도 검증해 producer-lineage reasoning을
queue/thermal operation evidence 후보와 분리합니다.
AIGuard는 producer `edgeenv_mapping_hint`도 deterministic raw context에
보존합니다. 여기에는 `coverage_summary_owner=edgeenv`,
`coverage_summary_path=runtime_telemetry_context.history.telemetry_coverage`,
`operation_context_role=supplemental` 같은 ownership marker가 포함됩니다.
이 필드는 소유권 경계를 설명하기 위한 것이며 AIGuard가 EdgeEnv coverage를
다시 계산하거나 Lab deployment policy를 소유한다는 뜻이 아닙니다.
EdgeEnv가 Orchestrator producer marker를 제공하면 AIGuard는
`source_repository=InferEdgeOrchestrator`,
`artifact_role=orchestrator-supplemental-operation-context`,
`producer_contract=inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1`도
raw context에 그대로 유지합니다. 이는 Lab artifact bundle의 traceability를
위한 것이며 AIGuard가 Orchestrator feed producer가 된다는 뜻이 아닙니다.
nested candidate context에 producer lineage block이 포함되어 있으면,
AIGuard는 `candidate_context.producer`와 `producer_sources`,
`device_local_producer_sources`, `producer_sources_by_task`,
`producer_stage_by_task`, `producer_event_count`,
`operation_context_role=supplemental` 같은 device-local marker를
`raw_context.edgeenv_regression`에 보존합니다. 이는 device-local input
override provenance를 Lab이 추적할 수 있게 하기 위한 것이며, AIGuard가
registry나 comparability owner가 된다는 뜻이 아닙니다.
candidate telemetry gap과 baseline/candidate execution sequence inversion은
EdgeEnv replay context에서 온 warning evidence로 보존되며, AIGuard가 이를
comparability decision으로 재판정하지 않습니다.
EdgeEnv가 `runtime_telemetry_context.history.telemetry_coverage`를 제공하면
AIGuard는 해당 producer-side replay summary를 우선 사용해 missing field
run을 `runtime_telemetry_field_gap` suspected cause로 설명합니다. 이 summary가
없을 때만 per-run `runtime_telemetry.coverage`로 fallback하며, Lab-owned
deployment policy를 대체하지 않습니다.
EdgeEnv가 Runtime의 `runtime_telemetry_history_seed`를 보존하면 AIGuard는
`inferedge-runtime-telemetry-history-seed-v1`, `registry_owner=edgeenv`,
`decision_owner=lab` marker를 deterministic raw context에 유지합니다. EdgeEnv가
seed `run_config` snapshot도 보존하면 AIGuard는 이를 replay/comparability
context로 함께 유지하고 `runtime_history_seed_run_config_traceability`
evidence로 shape, input/preprocess, power mode, Jetson clocks, warmup/repeat
run marker 보존 여부를 설명합니다. 이는 replay traceability 보존이며
AIGuard가 registry나 deployment decision을 소유한다는 뜻이 아닙니다.
`tests/fixtures/edgeenv_regression/`에는 EdgeEnv의 committed replay fixtures를
mirror한 작은 CLI smoke 입력이 있습니다.
`examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json`는
Lab bundle naming에 맞춘 precomputed `guard_analysis` artifact 예시입니다.
AIGuard는 이 artifact에서 runtime anomaly evidence만 제공하고, Lab-owned
deployment decision을 생성하지 않습니다.
`check-edgeenv-handoff-alignment`는 EdgeEnv의
`external_aiguard_required_evidence_types`가 `guard_analysis.evidence`에
존재하는지 검증합니다. 또한 AIGuard가 external evidence provider이고 Lab이
final decision owner라는 handoff boundary flag도 함께 확인합니다. EdgeEnv가
`edgeenv_report_summary.producer_lineage_guard_alignment_run_ids`를 제공하면,
같은 gate는 이를 AIGuard의 `edgeenv_orchestrator_producer_lineage` raw
context와 대조해 producer-lineage marker handoff가 조용히 어긋나지 않게
합니다. 이는 artifact alignment를 위한 deterministic smoke gate이며 새
deployment decision 경로가 아닙니다.

Remote dispatch starter result도 직접 분석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-remote-dispatch \
  --input reports/remote_dispatch_result.json
```

unified `reason` 명령은 `schema_version: inferedge-remote-dispatch-result-v1`도
자동 라우팅합니다. AIGuard는 worker selection 상태와 explicit HTTP/SSH starter
execution 상태를 `remote_execution_plan_only`,
`remote_execution_starter_success`, `remote_execution_failed` evidence로
해석합니다. Orchestrator가 additive `fallback_execution_result`를 제공하면
`remote_execution_recovered_by_fallback` 또는
`remote_fallback_execution_failed`도 생성합니다. fallback이 성공해도 primary
worker path가 불안정했다는 뜻이므로 review evidence로 남깁니다. 이는 starter
evidence이며 production remote execution을 완료했다는 의미가 아닙니다.

Orchestrator가 additive `remote_runtime_event_summary`를 제공하면 AIGuard는 이를
deterministic raw context에 보존하고 compact event/status/error/fallback/final
status count가 원본 `runtime_events` 및 `remote_operation_summary`와 일치하는지
확인합니다. 또한 Lab-facing `runtime_event_count` alias와
`operation_boundary: remote dispatch starter evidence only` marker를 top-level
raw context와 compact summary 안에 그대로 보존해 downstream에서도 starter
boundary가 보이게 합니다. `remote_dispatch_runtime_event_compact_summary`가
아닌 non-starter `evidence_role`은 production remote-operation proof가 아니라
compact-summary mismatch로 취급합니다. 불일치하면 downstream
Lab report가 오래된 compact summary를 신뢰하지 않도록
`remote_runtime_event_summary_mismatch` warning evidence로 남깁니다.
같은 summary가 EdgeEnv가 보존한 `orchestrator_operation_context`를 통해
전달되는 경우에도 AIGuard는
`evidence_role=remote_dispatch_runtime_event_compact_summary`,
`operation_boundary=remote dispatch starter evidence only`,
`production_remote_execution=false`를 traceability/raw-context marker로만
유지합니다. 이는 deterministic warning context를 위한 것이며 production
remote execution proof도 아니고 Lab의 final deployment-decision ownership을
바꾸지도 않습니다.

### Remote Dispatch Diagnosis Boundary

Remote dispatch evidence는 production remote operation보다 좁은 범위입니다.

- 구현된 signal: worker-selection evidence, plan-only mode, explicit starter
  status, bounded fallback recovery, compact event summary,
  `operation_boundary=remote dispatch starter evidence only`
- 구현하지 않은 signal: production remote execution, long-lived worker
  lifecycle, Cloudflare/Zero Trust operation, production retry/failover, cloud
  control plane behavior
- ownership: Orchestrator는 operation evidence를 생산하고, AIGuard는 optional
  deterministic warning context를 출력하며, 최종 deployment decision은 Lab이
  소유합니다.

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
