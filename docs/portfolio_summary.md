# InferEdgeAIGuard Portfolio Summary

## 1. 프로젝트 개요

InferEdgeAIGuard는 Edge AI inference 결과를 그대로 신뢰하지 않고, latency, accuracy, runtime provenance, 반복 실행 결과를 기반으로 anomaly와 suspected cause를 설명하는 validation reasoning layer입니다.

InferEdge ecosystem에서 AIGuard는 다음 흐름의 optional diagnosis evidence 계층입니다. 최종 deployment decision은 InferEdgeLab이 소유합니다.

```text
Forge -> Runtime -> Lab -> AIGuard
```

- Forge: deployment artifact 생성
- Runtime: edge device inference 실행
- Lab: analysis/report/API/deployment decision owner
- AIGuard: evidence-based deterministic diagnosis provider

InferEdgeLab이 Runtime result를 분석하고 report/API/deployment decision을 생성한다면, InferEdgeAIGuard는 그 결과 위에서 "이 결과를 그대로 믿어도 되는가?", "어떤 의심 신호가 있는가?", "무엇을 먼저 점검해야 하는가?"를 optional `guard_analysis` evidence로 설명합니다.

## 2. 해결하려는 문제

```text
Edge AI inference에서는 다음과 같은 문제가 발생할 수 있다:
- quantization 이후 이상한 결과
- latency 개선이 없는 경우
- accuracy가 기록되지 않은 상태
- 반복 실행 결과가 불안정한 경우

하지만 대부분의 시스템은:
-> 결과를 "측정"만 하고
-> 그 결과가 정상인지 "판단하지 않는다"
```

InferEdgeAIGuard는 이 빈칸을 채웁니다. 모델 내부 weight나 graph를 분석하는 도구가 아니라, 실제 inference validation pipeline이 남긴 result-level evidence를 기반으로 failure/diagnosis signal을 정의하고 설명합니다.

## 3. 시스템이 분석하는 입력

| Layer | Input | Purpose |
|---|---|---|
| Output detector | YOLO detection output JSON | bbox collapse, confidence saturation, detection count mismatch 감지 |
| Compare reasoning | Lab compare result JSON | FP32 대비 candidate 결과가 신뢰 가능한 비교인지 판단 |
| Structured result reasoning | Lab structured result JSON | 단일 측정 결과의 provenance, latency, accuracy metadata 신뢰성 판단 |
| Run history reasoning | Lab structured result list JSON | repeated-run stability와 logging consistency 판단 |
| Unified reason CLI | compare/result/history JSON | 입력 타입 자동 판별 후 적절한 reasoning 경로로 라우팅 |

대표 명령은 하나로 정리할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason --input path/to/result.json
```

## 4. 핵심 구현 포인트

- Python 표준 라이브러리 중심의 lightweight rule engine
- InferEdgeLab JSON을 직접 import하지 않고 adapter로 schema alias 정규화
- JSON/Markdown report 저장 지원
- 단일 result, compare result, repeated-run history를 같은 CLI UX로 분석
- `guard_version`, `created_at`, `detector_config` metadata를 report에 포함해 재현성 확보

## 5. 실제로 검출한 Jetson evidence

### Case 1. FP32 vs FP16 compare에서 speedup이 거의 없음

실제 Jetson FP32/FP16 compare evidence:

- 입력: `real_device/jetson/compare_fp32_fp16.json`
- report: `reports/jetson/compare_reasoning.json`
- mode: `compare_reasoning`
- status: `warning`
- anomaly: `insufficient_precision_speedup`
- suspected causes:
  - `precision_speedup_not_observed`
  - `runtime_or_engine_optimization_issue`

핵심 수치:

| Metric | Value |
|---|---:|
| FP32 mean_ms | 13.4897 |
| FP16 mean_ms | 13.3527 |
| latency_delta_pct | -1.0153% |
| FP32 map50 | 0.7977 |
| FP16 map50 | 0.7791 |

해석:

FP16 candidate가 FP32보다 아주 약간 빠르지만, cross-precision optimization으로 기대할 만한 speedup은 관찰되지 않았습니다. accuracy는 FP32/FP16 모두 기록되어 있으므로 accuracy 누락 문제는 아닙니다. AIGuard는 이 패턴을 `insufficient_precision_speedup`으로 감지해 TensorRT engine build setting, precision fallback, runtime artifact, device load를 점검하도록 안내합니다.

### Case 2. FP16 repeated-run history에서 accuracy logging이 일관되지 않음

실제 Jetson FP16 repeated-run history evidence:

- 입력: `real_device/jetson/history/yolov8n_fp16_history.json`
- report: `reports/jetson/yolov8n_fp16_history_reasoning.json`
- mode: `run_history_reasoning`
- run_count: `5`
- status: `warning`
- anomaly: `partial_accuracy_missing`
- suspected cause: `inconsistent_accuracy_logging`

해석:

같은 Jetson TensorRT FP16 조건의 반복 실행 history에서 일부 run은 유효한 accuracy metric을 포함하고, 일부 run은 accuracy가 `null`로 남아 있습니다. 이 문제는 latency instability가 아니라 validation logging consistency 문제입니다.

AIGuard는 단순히 latency 수치만 보는 것이 아니라, 반복 실험 evidence 자체가 일관되게 기록되었는지도 검사합니다. 이는 포트폴리오 관점에서 "측정 자동화"를 넘어 "측정 결과를 신뢰할 수 있는지 판단하는 계층"을 구현했다는 증거입니다.

### Case 3. 정상 structured result는 false positive 없이 통과

실제 Jetson structured result evidence:

- `reports/jetson/yolov8n_fp32_reasoning.json`: `status=ok`
- `reports/jetson/yolov8n_fp16_reasoning.json`: `status=ok`

두 structured result에는 runtime artifact, resolved input shapes, run config, system metadata, accuracy가 존재합니다. AIGuard는 이 정상 단일 결과를 anomaly로 과탐지하지 않았습니다.

## 6. 포트폴리오에서 보여줄 수 있는 가치

이 프로젝트가 보여주는 역량은 단순 CLI 작성이 아닙니다.

- Edge AI inference validation workflow를 system layer로 설계
- Lab/Runtime 결과를 신뢰성 관점에서 해석하는 reasoning layer 구현
- 실제 Jetson evidence에서 새 anomaly pattern을 발견하고 rule로 확장
- JSON schema 변형을 adapter로 흡수하는 실험 호환성 설계
- 테스트, fixture, report, PR 단위로 단계적 개발 이력 유지

특히 `insufficient_precision_speedup`은 fixture가 아니라 real-device Jetson evidence에서 발견된 pattern입니다. 이는 프로젝트가 가짜 데모가 아니라 실제 validation 과정에서 rule을 진화시키는 구조라는 점을 보여줍니다.

## 7. 주요 산출물

| Artifact | Path |
|---|---|
| Fixture validation report | `docs/validation_report.md` |
| Detector validation matrix | `docs/detector_validation_matrix.md` |
| Jetson validation plan | `docs/jetson_validation_plan.md` |
| Jetson validation report | `docs/jetson_validation_report.md` |
| Real-device Jetson inputs | `real_device/jetson/` |
| Jetson reasoning reports | `reports/jetson/` |
| Lab compatibility fixtures | `examples/lab_compat/` |

## 8. 하지 않는 것

InferEdgeAIGuard는 다음을 직접 수행하지 않습니다.

- TensorRT 실행
- Jetson 코드 실행
- 모델 변환
- ML 학습 또는 calibration
- ground truth 기반 accuracy 평가
- 모델 내부 구조, weight, graph 분석
- SaaS/UI 구현

대신 AIGuard는 이미 생성된 inference result와 validation output을 읽고, 그 결과를 신뢰하기 전에 확인해야 할 anomaly signal과 suspected cause를 설명합니다.

## 9. Detector Validation Matrix

현재 AIGuard는 detector별 expected behavior와 pass/review/block 근거를 문서화했습니다. 이 표는 AIGuard `guard_verdict`의 설명 기준이며, 최종 deployment decision은 InferEdgeLab이 latency, accuracy, contract, runtime evidence와 함께 통합해서 판단합니다.

| Case | Signal | Expected guard_verdict | Meaning |
|---|---|---|---|
| normal | stable bbox/score/count | `pass` | 배포 위험 evidence 없음 |
| bbox collapse | near-zero area boxes 증가 | `blocked` | decoder/postprocess/quantization 문제 가능 |
| score saturation | score가 0 또는 1 근처에 몰림 | `blocked` | score calibration 또는 postprocess 문제 가능 |
| temporal instability | frame 간 detection count 변동 또는 bbox jump | `review_required` | output 안정성 검토 필요 |
| provenance mismatch | source/artifact identity 불일치 | `blocked` / `error` | evidence가 검토 대상 artifact를 설명하지 못할 수 있음 |

| Detector family | Primary evidence | Review trigger | Block trigger |
|---|---|---|---|
| bbox validity | `invalid_bbox_rate` | `> 0.05` | `> 0.20` |
| bbox collapse | `bbox_collapse_ratio` | `> 0.05` or baseline factor `> 5x` | severe collapse or baseline factor `> 10x` |
| score range | `score_range_violation_count` | n/a | `> 0` |
| score saturation | `saturation_ratio` | `>= 0.70` | `>= 0.85` with quality drift |
| detection disappearance | `detection_count_drop_pct`, `zero_detection_frame_ratio` | drop `>= 50%` | drop `>= 80%` or zero-frame ratio `> 0.30` |
| temporal consistency | count CV, bbox jump, class flip | unstable sequence signal | zero-frame ratio `> 0.30` |

세부 threshold, report field, 향후 후보 detector는 `docs/detector_validation_matrix.md`에 정리되어 있습니다. 다음 후보는 per-class detection drift, detection disappearance hardening, calibration drift, baseline profile stability입니다.

## 10. 다음 단계

- controlled repeated-run Jetson history를 현재 FP16 사례보다 넓은 조건으로 확장
- FP16/INT8 TensorRT engine build option과 precision fallback evidence 추가 정리
- 향후 API/SaaS로 확장할 경우 unified `reason` entrypoint를 optional diagnosis endpoint로 연결

현재 단계에서 InferEdgeAIGuard는 "Edge inference result를 측정하는 도구"가 아니라, 측정 결과를 검토하고 bbox/score/baseline/temporal/provenance evidence로 의심 신호를 설명하는 validation reasoning layer로 포지셔닝됩니다.

## 11. One-line Interview Pitch

InferEdgeAIGuard는 Jetson 기반 Edge AI inference 결과를 단순 측정에서 끝내지 않고, 결과의 신뢰성 문제를 rule-based reasoning으로 감지하고 설명하는 validation layer입니다.
