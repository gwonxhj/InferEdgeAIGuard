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

포트폴리오 경계: InferEdgeLab은 validation / decision layer이고, InferEdgeEnv는 `v0.1.5` v1-complete experiment hygiene / comparability layer입니다. AIGuard는 optional diagnosis evidence를 제공하고, Env는 benchmark evidence가 신뢰 가능하고 비교 가능한 형태인지 관리합니다.

## 현재 범위와 future work

현재는 fixture와 real-device evidence 기반의 deterministic diagnosis layer입니다.
Lab optional contract, provenance mismatch detector, bbox/score evidence detectors, baseline comparison, initial temporal consistency evidence, Orchestrator runtime reliability signal, sustained workload profile pressure, optional tegrastats thermal/resource signal, JSON/Markdown report 저장, portfolio diagnosis demo bundle이 구현되어 있습니다.
Local Studio는 Lab에서 demo evidence를 불러와 normal/pass, bbox collapse/blocked, score saturation/blocked, temporal instability/review_required, provenance mismatch 계열 사례를 표시할 수 있습니다.

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
`tests/fixtures/edgeenv_regression/`에는 EdgeEnv의 committed replay fixtures를
mirror한 작은 CLI smoke 입력이 있습니다.

이 기능은 AIGuard를 final deployment decision owner로 바꾸지 않습니다. AIGuard는
runtime reliability risk를 설명하는 optional evidence provider이고, 최종 판단은
InferEdgeLab이 담당합니다.

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
| detection disappearance | `detection_count_drop_pct`, `zero_detection_frame_ratio` | stable count | drop `>= 50%` | drop `>= 80%` 또는 zero-frame ratio `> 0.30` |
| baseline deviation | invalid/collapse/saturation factor | near baseline | factor `> 5x` | factor `> 10x` |
| temporal consistency | count CV, bbox jump, class flip | stable sequence | count CV `> 1.0`, class flip `> 0.30`, 큰 center jump | zero-frame ratio `> 0.30` |
| provenance consistency | source/artifact/backend identity | exact handoff match | warning mismatch | error mismatch |
| runtime reliability | deadline miss, drop/fallback, queue backlog | stable scheduling | deadline/drop/fallback threshold 초과 | excessive drop/fallback 또는 repeated deadline miss |

다음 후보 detector는 deterministic evidence 기반 roadmap입니다: per-class detection drift, detection disappearance hardening, calibration drift, baseline profile stability.

전체 detector별 threshold, expected verdict, report field는 [docs/detector_validation_matrix.md](docs/detector_validation_matrix.md)에 정리되어 있습니다.
Orchestrator summary 기반 runtime reliability mapping은 [docs/runtime_reliability_signals.ko.md](docs/runtime_reliability_signals.ko.md)에 정리되어 있습니다.

Future work:

- 더 넓은 detector coverage
- production service/worker packaging
- future SaaS job execution infrastructure와의 깊은 통합
