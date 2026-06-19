# InferEdgeAIGuard

Optional deterministic diagnosis evidence layer  
(provenance mismatch · suspicious result signals · guard_analysis)

언어: [English](README.md) | 한국어

## 요약

- InferEdge validation pipeline의 optional deterministic diagnosis layer입니다.
- Lab compare/result/history JSON과 Runtime/Forge provenance evidence를 읽습니다.
- suspicious inference signal, provenance mismatch, 약한 validation evidence를 감지합니다.
- Lab report/API bundle에 보존 가능한 `guard_analysis`를 optional evidence로 출력합니다.
- InferEdgeLab의 최종 decision owner 역할을 대체하지 않고 review decision을 보조합니다.

## InferEdgeAIGuard의 차별점

InferEdgeAIGuard는 LLM 추측 기반 진단 도구가 아닙니다.

이 레포는 rule/evidence 기반으로:

- latency, accuracy, provenance, output pattern, run-history signal을 점검하고
- suspected cause를 deterministic evidence와 함께 설명하며
- warning/error를 structured `guard_analysis` contract로 보존하고
- Lab이 최종 deployment decision owner로 남도록 optional evidence 역할만 수행합니다.

InferEdge는 Forge build provenance, Runtime execution/result export, Lab analysis/deployment decision, optional AIGuard diagnosis evidence를 연결하는 end-to-end Edge AI inference validation pipeline입니다.

```text
ONNX model
-> InferEdgeForge build/provenance
-> InferEdge-Runtime C++ execution/result export
-> InferEdgeLab compare/API/job/deployment_decision
-> optional InferEdgeAIGuard guard_analysis

Experiment hygiene / comparability layer:
InferEdgeEnv -> v0.1.5 v1-complete local-first run evidence registry / comparability checker
```

## 이 레포의 역할

- Lab result, Runtime profiling/provenance, Forge metadata/manifest evidence를 읽어 suspicious inference result를 진단합니다.
- artifact/source hash mismatch, backend/target/precision/shape mismatch, insufficient provenance 등을 rule/evidence 기반으로 감지합니다.
- `guard_analysis`를 optional evidence로 출력해 Lab report/API/deployment decision 흐름에 보존될 수 있게 합니다.
- 최종 deployment decision owner는 InferEdgeLab입니다. AIGuard는 최종 판단을 덮어쓰지 않습니다.

## 역할 경계 한눈에 보기

| 영역 | AIGuard가 하는 일 | AIGuard가 하지 않는 일 |
| --- | --- | --- |
| Lab deployment decision | Lab report/API bundle에 보존 가능한 optional `guard_analysis` evidence를 생성합니다. | InferEdgeLab의 `deployment_decision`을 대체하거나 덮어쓰지 않습니다. |
| EdgeEnv regression evidence | EdgeEnv runtime regression report를 deterministic anomaly evidence로 설명합니다. | comparability를 재계산하거나 registry를 소유하거나 deployment를 결정하지 않습니다. |
| Orchestrator operation context | queue/deadline/fallback/remote-dispatch starter signal을 warning/review evidence로 해석합니다. | scheduler, cloud control plane, production remote execution proof가 되지 않습니다. |
| Root-cause explanation | 관측 metric, threshold, severity, suspected cause, recommendation을 기록합니다. | LLM 기반 root-cause 확정이나 automatic remediation을 수행하지 않습니다. |

## 중요한 경계

AIGuard는 다음을 하지 않습니다.

- root cause를 확정하지 않습니다.
- 자동 해결 시스템이 아닙니다.
- LLM 추측 기반 진단 도구가 아닙니다.
- 의료/안전/법적 판단 자동화 도구가 아닙니다.
- production SaaS worker가 아닙니다.

대신 deterministic rule과 evidence를 사용해 reviewer가 확인해야 할 suspected cause와 anomaly signal을 좁혀줍니다.

## 빠른 실행

예시 reasoning:

```bash
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json
python -m inferedge_aiguard.cli reason --input real_device/jetson/compare_fp32_fp16.json
```

테스트:

```bash
python3 -m pytest -q
```

프로젝트 Python에 pytest가 없다면 사용 가능한 venv/Poetry 환경에서 동일하게 실행하면 됩니다.

## 다른 InferEdge 레포와의 관계

- **InferEdgeForge:** build artifact와 source/artifact hash, backend/target/precision/shape provenance를 제공합니다.
- **InferEdge-Runtime:** 실행/profiling result JSON과 runtime provenance를 제공합니다.
- **InferEdgeLab:** AIGuard `guard_analysis`를 optional evidence로 보존하고 최종 deployment decision을 생성합니다.
- **InferEdgeEnv:** `v0.1.5` v1-complete 상태의 experiment hygiene / comparability layer로, benchmark run evidence를 local artifact와 SQLite registry로 고정하고 비교 가능성을 판정합니다.
- **InferEdgeOrchestrator:** queue/deadline/fallback/remote dispatch starter context를 supplemental operation evidence로 제공합니다.

포트폴리오 경계: InferEdgeLab은 validation / decision layer이고, InferEdgeEnv는 `v0.1.5` v1-complete experiment hygiene / comparability layer입니다. AIGuard는 optional diagnosis evidence를 제공하고, Env는 benchmark evidence가 신뢰 가능하고 비교 가능한 형태인지 관리합니다.

## 현재 범위와 future work

현재는 fixture와 real-device evidence 기반의 deterministic diagnosis layer입니다.
Lab optional contract, provenance mismatch detector, bbox/score evidence detectors, baseline comparison, initial temporal consistency evidence, Orchestrator runtime reliability signal, remote dispatch starter evidence, sustained workload profile pressure, optional tegrastats thermal/resource signal, JSON/Markdown report 저장, portfolio diagnosis demo bundle이 구현되어 있습니다.
Local Studio는 Lab에서 demo evidence를 불러와 normal/pass, bbox collapse/blocked, score saturation/blocked, temporal instability/review_required, temporal profile continuity/blocked 계열 사례를 표시할 수 있습니다.

## Runtime Reliability Signal

InferEdgeOrchestrator의 `inferedge-orchestration-summary-v1` summary를 읽어
multi-agent scheduling evidence를 `guard_analysis`로 변환할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

현재 분석하는 signal:

- `repeated_deadline_miss`
- `excessive_drop_rate`
- `fallback_overuse`
- `queue_backlog_risk`
- `sustained_overload_risk`
- `profiled_workload_pressure`
- `thermal_resource_pressure`

EdgeEnv runtime regression report도 deterministic runtime anomaly evidence로
해석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input reports/edgeenv_runtime_regression.json
python -m inferedge_aiguard.cli reason \
  --input reports/edgeenv_runtime_regression.json
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input examples/runtime_intelligence/edgeenv_runtime_regression_with_orchestrator_feed.json \
  --save-json examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
python -m inferedge_aiguard.cli check-edgeenv-handoff-alignment \
  --edgeenv-handoff reports/edgeenv_runtime_intelligence_lab_handoff.json \
  --guard-analysis examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
```

이 경로는 EdgeEnv가 생성한 same-condition regression과
`runtime_telemetry_context` coverage를 `runtime_latency_regression`,
`runtime_throughput_regression`, `runtime_memory_regression`,
`runtime_telemetry_context_coverage`, `runtime_telemetry_replay_context`
evidence로 변환합니다. AIGuard는 comparability 계산이나 final deployment
decision을 소유하지 않습니다.
candidate telemetry gap과 baseline/candidate execution sequence inversion은
EdgeEnv replay context에서 온 warning evidence로 보존되며, AIGuard가 이를
comparability decision으로 재판정하지 않습니다.
AIGuard는 EdgeEnv가 보존한 Orchestrator `edgeenv_mapping_hint`도 raw context에
유지합니다. `coverage_summary_owner=edgeenv`,
`coverage_summary_path=runtime_telemetry_context.history.telemetry_coverage`,
`operation_context_role=supplemental`은 ownership marker이며, AIGuard가
coverage/regression 또는 Lab deployment policy를 소유한다는 의미가 아닙니다.
EdgeEnv가 Orchestrator `operation_risk_rollup`을 보존하면 AIGuard는
`edgeenv_orchestrator_operation_risk_rollup` evidence로 compact risk level,
primary reason, affected task group, queue/deadline/fallback/drop/scheduler-delay
marker를 설명합니다. 이는 Lab review용 deterministic warning context이며
final deployment decision이 아닙니다.
EdgeEnv가 Orchestrator `latency_budget_protection` block을 보존하면 AIGuard는
`edgeenv_orchestrator_latency_budget_protection` evidence로 protected
high-priority task, latency-budget risk task, deadline/scheduler/queue reason,
per-task budget context를 설명합니다. 이는 runtime operation warning context이며
AIGuard가 scheduler나 final decision owner가 된다는 의미가 아닙니다.
EdgeEnv가 Orchestrator `policy_pressure` block을 보존하면 AIGuard는
`edgeenv_orchestrator_policy_pressure_summary` evidence로 limited task,
protected task, fallback task, decision reason count, pressure marker를
설명합니다. 이는 scheduler pressure를 Lab review context로 보존하는 것이며
AIGuard가 scheduler나 final decision owner가 된다는 의미가 아닙니다.
EdgeEnv가 Orchestrator `scheduler_fairness_summary` block을 보존하면 AIGuard는
`edgeenv_orchestrator_scheduler_fairness_summary` evidence로 protected
high-priority task, starvation-risk task, scheduler-delay task, degraded task,
per-task fairness context를 설명합니다. 이는 Lab review용 supplemental
operation context이며 AIGuard가 scheduler나 final decision owner가 된다는
의미가 아닙니다.
EdgeEnv가 Runtime의 `runtime_telemetry_history_seed`를 보존하면 AIGuard는
`inferedge-runtime-telemetry-history-seed-v1`, `registry_owner=edgeenv`,
`decision_owner=lab` marker를 raw context에 유지합니다. EdgeEnv가 seed
`run_config` snapshot도 보존하면 AIGuard는 이를 replay/comparability context로
함께 유지하되 새 diagnosis verdict로 승격하지 않습니다. 이는 replay evidence
traceability를 위한 보존이며 AIGuard가 registry나 deployment decision을 소유한다는
의미가 아닙니다.
`tests/fixtures/edgeenv_regression/`에는 EdgeEnv의 committed replay fixtures를
mirror한 작은 CLI smoke 입력이 있습니다.
`examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json`는
Lab Runtime Intelligence bundle에 넣을 수 있는 precomputed
`guard_analysis` artifact 예시입니다. 파일명은 Lab bundle의 AIGuard artifact
role과 맞추며, AIGuard는 deterministic evidence만 생성하고 deployment
decision은 만들지 않습니다.
`examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json`는
optional stale-drop evidence가 실제로 present인 동반 예시입니다. 이 artifact는
`edgeenv_orchestrator_stale_drop_summary`와 `stale_frame_risk` full evidence
item을 모두 보존하지만, optional evidence를 required deployment decision
evidence로 승격하지 않습니다.
아래 명령은 committed source fixtures에서 optional-present artifact를 재생성합니다.

```bash
python -m inferedge_aiguard.cli build-runtime-intelligence-optional-stale-drop \
  --edgeenv-regression examples/runtime_intelligence/edgeenv_runtime_regression_with_optional_stale_drop_context.json \
  --remote-dispatch examples/runtime_intelligence/remote_dispatch_fallback_recovered_result.json \
  --orchestration-summary examples/runtime_intelligence/orchestrator_multi_workload_sustained_summary.json \
  --save-json examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis_optional_stale_drop.json
```

producer smoke는 위 재생성 경로를 감싸서 generated artifact가 committed
fixture와 같은지 비교합니다. sibling InferEdgeLab checkout이 있으면 생성된
optional-present alignment metadata로 Lab source traceability gate도 함께
실행합니다. alignment summary는 `optional_present_source_artifact`와
`read_only_cross_repo_traceability` context로 fixture 출처를 노출하므로,
Lab이 source를 검증하되 AIGuard가 deployment decision owner가 되지는
않습니다.

```bash
bash scripts/smoke_runtime_intelligence_optional_stale_drop.sh \
  --output-dir reports/runtime_intelligence_optional_stale_drop
```

`check-edgeenv-handoff-alignment`는 EdgeEnv handoff의
`external_aiguard_required_evidence_types`가 실제 `guard_analysis.evidence`
type set으로 충족되는지 확인합니다. 또한
`lab_bundle_alignment.optional_aiguard_evidence_types`가 있으면 이를
`read_only_optional_guard_context`로 보존하고, 현재 guard analysis에 이미
포함된 optional evidence와 아직 없는 optional evidence를 나눠 표시합니다.
AIGuard does not validate optional evidence as required; optional 항목 누락은
required evidence failure가 아닙니다. 이어서
`edgeenv_report_summary.producer_lineage_guard_alignment_run_ids`를
AIGuard의 `edgeenv_orchestrator_producer_lineage` raw context와 대조해
EdgeEnv producer summary와 AIGuard deterministic evidence가 같은
producer-lineage marker를 가리키는지 확인합니다. 이 gate는 누락 evidence와
ownership boundary flag mismatch를 찾기 위한 smoke이며, AIGuard가 Lab의
final deployment decision을 대신한다는 의미가 아닙니다.
EdgeEnv가
`edgeenv_report_summary.orchestrator_policy_pressure_summary_run_ids`도
노출하면 같은 gate는 AIGuard의
`edgeenv_orchestrator_policy_pressure_summary` raw context와 비교해
policy-pressure handoff traceability가 같은 run을 가리키는지 확인합니다.

이 기능은 AIGuard를 final deployment decision owner로 바꾸지 않습니다. AIGuard는
runtime reliability risk를 설명하는 optional evidence provider이고, 최종 판단은
InferEdgeLab이 담당합니다.

## Remote Dispatch Starter Diagnosis Boundary

Orchestrator `inferedge-remote-dispatch-result-v1` 결과는 AIGuard에서
deterministic warning/review evidence로 해석할 수 있습니다.

- 해석 대상: worker selection, explicit HTTP/SSH starter status, bounded
  fallback recovery, compact runtime event summary,
  `operation_boundary=remote dispatch starter evidence only`
- 생성 가능한 evidence: `remote_execution_plan_only`,
  `remote_execution_starter_success`, `remote_execution_failed`,
  `remote_execution_recovered_by_fallback`,
  `remote_runtime_event_summary_mismatch`
- 해석하지 않는 것: production remote execution 완료, long-lived worker
  readiness, secure tunnel operation, production retry/failover, cloud
  orchestration

Orchestrator는 operation evidence producer이고, AIGuard는 optional
deterministic diagnosis provider이며, 최종 deployment decision owner는
InferEdgeLab입니다.

## Detector Validation Matrix

AIGuard detector는 deterministic evidence provider입니다. `guard_verdict`는 Lab의 최종 `deployment_decision`이 아니라, Lab이 참고할 수 있는 optional diagnosis evidence입니다.

| Case | Signal | Expected `guard_verdict` | Meaning |
|---|---|---|---|
| normal | bbox/score/count 안정 | `pass` | AIGuard 기준 배포 위험 evidence 없음 |
| bbox collapse | near-zero area bbox 증가 | `blocked` | decoder/postprocess/quantization 문제 가능 |
| score saturation | score가 0 또는 1 근처에 몰림 | `blocked` | score calibration 또는 postprocess 문제 가능 |
| temporal instability | frame 간 detection count 또는 bbox 이동이 불안정 | `review_required` | runtime output 안정성 검토 필요 |
| provenance mismatch | Forge/Runtime source 또는 artifact identity 불일치 | `blocked` / `error` | 검토 중인 artifact와 evidence가 다를 수 있음 |

### Detector Verdict Matrix

아래 표는 AIGuard가 어떤 수치 근거로 pass/review/block 성격의 `guard_verdict`를 만드는지 보여주는 요약입니다. 이 표는 Lab의 최종 deployment policy가 아니며, Lab은 latency, accuracy, contract, runtime evidence와 함께 AIGuard evidence를 참고합니다.

| Detector family | Primary evidence | Pass | Review | Block |
|---|---|---|---|---|
| bbox validity | `invalid_bbox_rate` | `<= 0.05` | `> 0.05` | `> 0.20` |
| bbox collapse | `bbox_collapse_ratio` | `<= 0.05` | `> 0.05` 또는 baseline factor `> 5x` | severe collapse 또는 baseline factor `> 10x` |
| confidence score range | `score_range_violation_count` | `0` | n/a | `> 0` |
| confidence saturation | `saturation_ratio` | `< 0.70` | `>= 0.70` | `>= 0.85` and quality drift |
| detection disappearance | `detection_count_drop_pct`, `zero_detection_frame_ratio`, `max_zero_detection_streak` | stable count | drop `>= 50%` 또는 zero-frame streak `>= 2` | drop `>= 80%`, zero-frame ratio `> 0.30`, 또는 zero-frame streak `>= 3` |
| per-class detection drift | `per_class_detection_drop_pct`, dropped class IDs | class count 안정 | baseline class 하나가 `>= 50%` 감소 | baseline class 하나가 `100%` 감소 |
| baseline deviation | invalid/collapse/saturation factor | near baseline | factor `> 5x` | factor `> 10x` |
| temporal consistency | count CV, bbox jump, class flip, disappearance streak | stable sequence | count CV `> 1.0`, class flip `> 0.30`, 큰 center jump, zero-frame streak `>= 2` | zero-frame ratio `> 0.30` 또는 zero-frame streak `>= 3` |
| provenance consistency | source/artifact/backend identity | exact handoff match | warning mismatch | error mismatch |
| runtime reliability | deadline miss, drop/fallback, queue backlog | stable scheduling | deadline/drop/fallback threshold 초과 | excessive drop/fallback 또는 repeated deadline miss |

구현된 detector hardening에는 candidate zero-detection collapse를 잡는 `detection_disappearance`, 반복 zero-detection frame streak를 잡는 `sequence_disappearance`, 총 detection 수가 유지되어도 특정 class가 사라지는 `per_class_detection_drift`, fixed-bin score histogram / mean score / std score / saturation delta를 baseline과 비교하는 `calibration_drift`, saved baseline profile의 sample count와 histogram/class coverage를 기록하는 `profile_stability` audit metadata가 포함됩니다.
`calibration_drift`가 포함됩니다. `profile_stability` audit metadata는 Lab deployment decision이 아니라 saved baseline profile 검토용 metadata입니다.

전체 detector별 threshold, expected verdict, report field는 [Detector Validation Matrix](docs/detector_validation_matrix.ko.md)에 정리되어 있습니다. 대표/canonical 문서는 [English matrix](docs/detector_validation_matrix.md)입니다.
Orchestrator summary 기반 runtime reliability mapping은 [docs/runtime_reliability_signals.ko.md](docs/runtime_reliability_signals.ko.md)에 정리되어 있습니다.

Future work:

- 더 넓은 detector coverage
- production service/worker packaging
- future SaaS job execution infrastructure와의 깊은 통합
