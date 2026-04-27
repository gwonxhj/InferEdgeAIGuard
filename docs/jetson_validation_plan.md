# Jetson Validation Plan for InferEdgeAIGuard

## Purpose

이 문서는 fixture 기반 validation 이후 real-device Jetson validation을 수행하기 위한 계획입니다.

목표는 Jetson에서 생성한 InferEdgeLab structured result, compare result, run history result를 AIGuard로 분석해 실제 장비 기반 evidence를 확보하는 것입니다. 이 문서는 실행 기록이 아니라 실행 계획입니다.

## Scope

포함 범위:

- Jetson Orin Nano 우선
- 가능하면 Jetson AGX Orin 또는 Xavier는 선택 확장
- `resnet18.onnx` 또는 기존 InferEdgeLab/Forge에서 사용한 경량 ONNX 모델 우선
- FP32 baseline vs TensorRT FP16 또는 INT8 candidate 비교
- single structured result reasoning
- compare reasoning
- run history reasoning

제외 범위:

- 모델 학습
- SaaS
- UI
- 대규모 benchmark suite
- 실제 accuracy dataset 기반 평가
- Forge/Runtime 전체 자동 통합

## Required Inputs

| Item | Example | Purpose |
|---|---|---|
| ONNX model | `resnet18.onnx` | baseline/candidate artifact source |
| Runtime artifact | `resnet18.engine` | TensorRT candidate artifact |
| Lab structured result | `result_fp32.json`, `result_fp16.json` | AIGuard `reason-result` input |
| Lab compare result | `compare_fp32_fp16.json` | AIGuard `reason-compare` input |
| Repeated history | `history_fp16.json` | AIGuard `reason-history` input |

## Expected Lab Result Fields

InferEdgeLab structured result에는 다음 필드가 필요합니다.

필수:

- `model`
- `engine`
- `device`
- `precision`
- `batch`
- `height`
- `width`
- `mean_ms`
- `p99_ms`
- `run_config`
- `system`
- `extra.runtime_artifact_path`
- `extra.resolved_input_shapes`

선택:

- `accuracy`
- `extra.primary_input_name`
- `extra.runtime_version`
- `extra.engine_path`

## Jetson Collection Workflow

1. Jetson 환경 확인

   - device name
   - Python version
   - TensorRT availability
   - CUDA/TensorRT runtime availability
   - input model/artifact path

2. FP32 or ONNXRuntime baseline profiling

   Lab 또는 기존 EdgeBench/InferEdgeLab CLI로 structured result를 저장합니다.

   예: `results/jetson/fp32_result.json`

3. TensorRT FP16 또는 INT8 candidate profiling

   TensorRT engine 기반 structured result를 저장합니다.

   예: `results/jetson/fp16_result.json` 또는 `results/jetson/int8_result.json`

4. Compare result 생성

   Lab compare 또는 compare-latest로 baseline/candidate 비교 JSON을 생성합니다.

   예: `results/jetson/compare_fp32_fp16.json`

5. Repeated run history 생성

   같은 model/engine/device/precision/shape 조건으로 3회 이상 반복하고 history JSON list로 저장합니다.

   예: `results/jetson/history_fp16.json`

6. AIGuard 실행

```bash
python -m inferedge_aiguard.cli reason-result \
  --input results/jetson/fp16_result.json \
  --save-json reports/jetson/fp16_reasoning.json \
  --save-md reports/jetson/fp16_reasoning.md
```

```bash
python -m inferedge_aiguard.cli reason-compare \
  --input results/jetson/compare_fp32_fp16.json \
  --save-json reports/jetson/compare_reasoning.json \
  --save-md reports/jetson/compare_reasoning.md
```

```bash
python -m inferedge_aiguard.cli reason-history \
  --input results/jetson/history_fp16.json \
  --save-json reports/jetson/history_reasoning.json \
  --save-md reports/jetson/history_reasoning.md
```

또는 unified reason 명령을 사용할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason --input results/jetson/compare_fp32_fp16.json
```

## Evidence to Collect

| Evidence | File | Why it matters |
|---|---|---|
| structured reasoning JSON | `reports/jetson/fp16_reasoning.json` | 단일 result 신뢰성 판단 |
| structured reasoning MD | `reports/jetson/fp16_reasoning.md` | 포트폴리오/리포트용 |
| compare reasoning JSON | `reports/jetson/compare_reasoning.json` | FP32 대비 candidate 의심 신호 |
| compare reasoning MD | `reports/jetson/compare_reasoning.md` | 설명 가능한 비교 리포트 |
| history reasoning JSON | `reports/jetson/history_reasoning.json` | repeated-run 안정성 |
| history reasoning MD | `reports/jetson/history_reasoning.md` | 반복 실험 리포트 |

## Success Criteria

- Jetson에서 생성한 Lab structured result를 AIGuard가 정상 파싱한다.
- `reason-result`가 `ok`, `warning`, `error` 중 하나를 안정적으로 출력한다.
- `reason-compare`가 latency/accuracy/config/provenance 기반 anomaly를 설명한다.
- `reason-history`가 3회 이상 repeated run에서 instability 또는 stable status를 판단한다.
- `reports/jetson`에 JSON/Markdown evidence가 남는다.
- fixture validation과 real-device validation의 차이를 docs 또는 report에서 설명할 수 있다.

## Failure Handling

| Situation | Likely AIGuard Signal | Response |
|---|---|---|
| TensorRT engine path가 result에 기록되지 않음 | `missing_runtime_artifact` | runtime artifact path 또는 engine path를 result metadata에 기록한다. |
| `resolved_input_shapes` 누락 | `missing_resolved_input_shapes` | 실제 runtime input shape를 `extra.resolved_input_shapes`에 저장한다. |
| `p99_ms`가 비정상적으로 큼 | `latency_instability` 또는 `p99_latency_instability` | warmup/runs/device load를 확인하고 profiling을 반복한다. |
| accuracy 없음 | `accuracy_missing_warning` 또는 `quantized_history_accuracy_missing` | task metric 또는 accuracy validation을 함께 저장한다. |
| `run_config` mismatch | `unreliable_comparison` with `run_config_mismatch` | baseline/candidate의 warmup, runs, batch, shape 설정을 맞춘다. |
| shape mismatch | `unreliable_comparison` with `input_shape_mismatch` | batch/height/width 또는 resolved input shape를 맞춘 뒤 비교한다. |
| repeated run 수가 부족함 | `insufficient_history` | 최소 3회 이상 반복 run을 수집한다. |

## Next Step

- Jetson에서 실제 Lab result를 1세트 생성한다.
- 가능하면 FP32 baseline + TensorRT FP16 candidate부터 시작한다.
- INT8은 calibration/accuracy 이슈가 커서 FP16 validation 이후 진행한다.
- 실제 결과 파일이 준비되면 `reports/jetson`을 생성하고 `docs/jetson_validation_report.md`로 확장한다.
- 실제 FP32/FP16 validation report: [docs/jetson_validation_report.md](jetson_validation_report.md)
