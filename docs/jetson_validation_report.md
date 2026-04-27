# Jetson Validation Report for InferEdgeAIGuard

## Purpose

이 문서는 fixture 기반 validation 이후 실제 Jetson에서 생성된 InferEdgeLab structured result를 AIGuard로 분석한 real-device validation evidence입니다.

사용한 장비는 Jetson Orin Nano 계열 Jetson 환경으로 기록합니다. 수집된 structured result에는 TensorRT 10.3.0, Linux 5.15.148-tegra, aarch64 환경 정보가 포함되어 있습니다.

## Input Evidence

| File | Description |
|---|---|
| `real_device/jetson/results/yolov8n_fp32_result.json` | Jetson TensorRT FP32 structured result |
| `real_device/jetson/results/yolov8n_fp16_result.json` | Jetson TensorRT FP16 structured result |
| `real_device/jetson/compare_fp32_fp16.json` | FP32 vs FP16 cross-precision compare evidence |

## Structured Result Reasoning

FP32 structured result는 `status=ok`입니다.

FP16 structured result도 `status=ok`입니다.

두 결과 모두 `runtime_artifact_path`, `resolved_input_shapes`, `run_config`, `system`, `accuracy`가 존재합니다. 따라서 단일 structured result 관점에서는 provenance와 필수 latency metadata가 충분하며, AIGuard가 false positive 없이 정상 real-device structured result를 통과시킨 evidence로 볼 수 있습니다.

## Compare Reasoning

핵심 수치:

- FP32 `mean_ms`: `13.489712210016478`
- FP16 `mean_ms`: `13.352749789987683`
- `latency_delta_pct`: 약 `-1.0153%`
- FP32 `map50`: `0.7977`
- FP16 `map50`: `0.7791`

FP16이 FP32보다 아주 약간 빠르지만, cross-precision candidate로 기대할 만한 speedup은 관찰되지 않았습니다. accuracy는 FP32/FP16 모두 존재하므로 `accuracy_missing_warning`은 아닙니다.

이 real-device pattern은 새 rule인 `insufficient_precision_speedup`으로 포착됩니다.

의심 원인:

- `precision_speedup_not_observed`
- `runtime_or_engine_optimization_issue`
- TensorRT engine이 실제 FP16 path를 충분히 활용하지 못했을 가능성
- operator fallback 또는 measurement variance 가능성

## AIGuard Output

관련 report:

- `reports/jetson/yolov8n_fp32_reasoning.md`
- `reports/jetson/yolov8n_fp16_reasoning.md`
- `reports/jetson/compare_reasoning.md`

## Research Value

이번 evidence는 fixture에서는 발견하기 어려운 real-device pattern을 실제 Jetson result에서 발견한 사례입니다.

AIGuard rule은 이 real evidence를 기반으로 확장되었습니다. 이는 "결과를 그대로 믿지 않고 의심 신호를 정의하고 검출한다"는 프로젝트 목표와 맞습니다.

특히 accuracy가 존재하고 shape/run_config도 맞는 상황에서도, cross-precision optimization 관점에서 기대 speedup이 관찰되지 않으면 별도 anomaly로 다루어야 함을 보여줍니다.

## Limitation

이번 evidence는 기존 Jetson 결과 JSON을 재사용했습니다.

새로 동일 조건을 반복 측정한 history evidence는 아직 아닙니다. 따라서 repeated-run stability에 대한 real-device 판단은 다음 단계에서 보강해야 합니다.

## Next Step

- Jetson에서 FP16 또는 INT8 result를 3회 이상 반복 수집
- run history JSON 생성
- `reason-history`로 instability 여부 분석
- 필요 시 TensorRT engine build option 및 precision fallback 확인
