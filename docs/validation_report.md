# InferEdgeAIGuard Validation Report

## Purpose

이 문서는 InferEdgeAIGuard가 Lab-like inference result를 기반으로 어떤 anomaly를 감지하는지 보여주는 validation evidence입니다.

중요하게도, 이 report는 Jetson 실측 결과가 아닙니다. repo 내부의 realistic fixture인 `examples/lab_compat`를 사용한 fixture-based validation입니다. 목적은 AIGuard의 reasoning layer가 compare/result/history 입력에서 문제 신호를 설명 가능하게 감지하는지 확인하는 것입니다.

## Validation Inputs

| Case | Input | Reasoning Mode | Purpose |
|---|---|---|---|
| Case 1 | `examples/lab_compat/lab_compare_realistic.json` | `compare_reasoning` | Cross-precision latency-only improvement 검증 |
| Case 2 | `examples/lab_compat/lab_result_realistic.json` | `structured_result_reasoning` | 단일 INT8 structured result의 provenance/accuracy/latency 확인 |
| Case 3 | `examples/lab_compat/lab_history_realistic.json` | `run_history_reasoning` | repeated run latency instability 확인 |

## Case 1: Lab Compare Result Reasoning

- 입력: `examples/lab_compat/lab_compare_realistic.json`
- 기대 anomaly:
  - `accuracy_missing_warning`
  - `likely_quantization_effect`

해석:

INT8 candidate가 큰 latency 개선을 보이지만 accuracy validation이 누락되어 있습니다. 따라서 latency-only improvement를 그대로 신뢰하면 안 됩니다. 또한 cross precision에서 큰 latency delta가 관찰되므로 quantization/runtime effect 가능성을 별도 확인해야 합니다.

관련 report:

- `reports/validation/lab_compare_realistic.md`
- `reports/validation/lab_compare_realistic.json`

## Case 2: Lab Structured Result Reasoning

- 입력: `examples/lab_compat/lab_result_realistic.json`
- 기대 anomaly:
  - `latency_instability`
  - `accuracy_missing_warning`

해석:

`runtime_artifact_path`와 `resolved_input_shapes`가 존재하므로 runtime provenance 누락은 아닙니다. 하지만 `p99_ms`가 `mean_ms` 대비 크고, INT8 결과인데 accuracy가 없으므로 결과 신뢰성에 warning이 필요합니다.

관련 report:

- `reports/validation/lab_result_realistic.md`
- `reports/validation/lab_result_realistic.json`

## Case 3: Run History Reasoning

- 입력: `examples/lab_compat/lab_history_realistic.json`
- 기대 anomaly:
  - `mean_latency_instability`
  - `p99_latency_instability`
  - `latency_outlier_run`
  - `quantized_history_accuracy_missing`

해석:

같은 INT8 TensorRT 조건에서 반복 run 중 latency outlier가 있고, p99 tail latency도 크게 흔들립니다. 또한 모든 run에서 accuracy가 빠져 있어 반복 실험의 안정성과 정확도 검증이 모두 부족합니다.

관련 report:

- `reports/validation/lab_history_realistic.md`
- `reports/validation/lab_history_realistic.json`

## Summary

| Case | Status | Key Anomalies | Trust Decision |
|---|---|---|---|
| Case 1 | warning | `accuracy_missing_warning`, `likely_quantization_effect` | Accuracy validation required |
| Case 2 | warning | `latency_instability`, `accuracy_missing_warning` | Repeat profiling and add accuracy |
| Case 3 | warning | latency instability, outlier run, accuracy missing | Unstable history; repeat validation |

## Current Limitation

이 report는 fixture 기반 validation입니다. 아직 실제 Jetson measurement에서 수집한 Lab result는 아닙니다. 다음 단계에서 Jetson/InferEdgeLab 실제 result를 수집하면 evidence strength가 올라갑니다.

## Next Step

- Jetson Orin Nano 또는 사용 가능한 edge device에서 Lab structured result 생성
- AIGuard `reason` CLI로 실제 result 분석
- fixture-based validation과 real-device validation 비교
- 실행 계획: [docs/jetson_validation_plan.md](jetson_validation_plan.md)
