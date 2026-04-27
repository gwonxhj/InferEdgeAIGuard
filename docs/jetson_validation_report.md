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
| `real_device/jetson/history/yolov8n_fp16_history.json` | Jetson TensorRT FP16 repeated-run history evidence |

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

## Run History Reasoning Evidence

입력 파일:

- `real_device/jetson/history/yolov8n_fp16_history.json`

관련 report:

- `reports/jetson/yolov8n_fp16_history_reasoning.json`
- `reports/jetson/yolov8n_fp16_history_reasoning.md`

핵심 결과:

- `run_count`: `5`
- `status`: `warning`
- anomaly: `partial_accuracy_missing`
- suspected cause: `inconsistent_accuracy_logging`

같은 Jetson TensorRT FP16 조건의 repeated run history에서 accuracy logging이 일관되지 않았습니다. 일부 run에는 유효한 accuracy metric이 있고 일부 run에는 accuracy가 `null`로 남아 있기 때문에, 단순히 latency만 보고 history를 신뢰하면 안 됩니다.

AIGuard는 이 문제를 `partial_accuracy_missing`으로 감지했습니다. 이 evidence는 AIGuard가 latency anomaly뿐 아니라 validation pipeline의 logging consistency 문제도 감지할 수 있음을 보여줍니다.

## Research Value

이번 evidence는 fixture에서는 발견하기 어려운 real-device pattern을 실제 Jetson result에서 발견한 사례입니다.

AIGuard rule은 이 real evidence를 기반으로 확장되었습니다. 이는 "결과를 그대로 믿지 않고 의심 신호를 정의하고 검출한다"는 프로젝트 목표와 맞습니다.

특히 accuracy가 존재하고 shape/run_config도 맞는 상황에서도, cross-precision optimization 관점에서 기대 speedup이 관찰되지 않으면 별도 anomaly로 다루어야 함을 보여줍니다.

또한 repeated-run history에서는 latency instability가 아니라 accuracy logging consistency 문제가 포착되었습니다. 이는 AIGuard가 단순 성능 수치뿐 아니라 validation evidence 자체의 신뢰성도 점검한다는 점을 보여줍니다.

## Limitation

이번 evidence는 기존 Jetson 결과 JSON을 재사용했습니다.

FP16 repeated-run history evidence는 추가되었지만, 새로 같은 조건에서 통제된 방식으로 재측정한 controlled history는 아직 아닙니다. 따라서 반복 실행 안정성 자체에 대한 결론은 추가 측정으로 보강해야 합니다.

## Next Step

- Jetson에서 같은 조건의 FP16 또는 INT8 result를 controlled repeated run으로 다시 수집
- `reason-history`로 latency instability와 logging consistency를 함께 분석
- 필요 시 TensorRT engine build option 및 precision fallback 확인
- accuracy/task metric logging 경로를 점검해 repeated run 간 metric 누락을 줄이기
