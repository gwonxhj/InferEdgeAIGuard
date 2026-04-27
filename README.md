# InferEdgeAIGuard

InferEdgeAIGuard는 Edge AI inference 결과를 신뢰하기 전에 latency, accuracy, runtime provenance, output pattern, repeated-run history를 기반으로 anomaly와 suspected cause를 설명하는 validation reasoning layer입니다.

InferEdge ecosystem에서 역할은 다음처럼 나뉩니다.

- InferEdgeLab: measurement + comparison
- InferEdgeAIGuard: anomaly reasoning + explanation + suspected cause + recommendation

전체 흐름은 다음을 기준으로 합니다.

```text
Forge -> Runtime -> Lab -> AIGuard
```

- Forge: deployment artifact 생성
- Runtime: edge device inference 실행
- Lab: latency, accuracy, structured result, compare result 생성
- AIGuard: 결과 신뢰성 분석, anomaly detection, root-cause reasoning

AIGuard는 Lab 결과를 덮어쓰지 않습니다. Lab이 측정하고 비교한 JSON 결과 위에 "이 결과를 믿어도 되는가?", "어떤 anomaly signal이 있는가?", "어떤 원인을 의심해야 하는가?"를 덧붙이는 계층입니다.

## What AIGuard Analyzes

### A. Output-level failure detection

YOLO detection output JSON을 직접 분석합니다.

- bbox collapse
- confidence saturation
- detection count mismatch
- 단일 output, FP32/candidate pair, batch directory 분석 지원

### B. Lab compare result reasoning

`reason-compare` 또는 unified `reason` 명령으로 Lab compare result JSON을 분석합니다.

- latency improvement + accuracy missing
- latency improvement + accuracy drop 또는 risky tradeoff
- shape/run_config mismatch
- cross-precision large latency delta

### C. Lab structured result reasoning

`reason-result` 또는 unified `reason` 명령으로 단일 Lab structured result JSON을 분석합니다.

- missing latency metric
- invalid latency value
- p99 latency instability
- missing `runtime_artifact_path`
- missing `resolved_input_shapes`
- quantized result without accuracy

### D. Run history reasoning

`reason-history` 또는 unified `reason` 명령으로 repeated Lab structured result list JSON을 분석합니다.

- repeated-run mean latency instability
- p99 tail latency instability
- latency outlier run
- mixed experiment group
- partial or missing accuracy logging

## CLI Overview

| Command | Input | Purpose |
|---|---|---|
| `analyze` | YOLO output JSON | Single output failure detection |
| `compare` | FP32/candidate output JSON | Output-level pair comparison |
| `batch-analyze` | Directory of output JSON | Batch output failure rate |
| `batch-compare` | FP32/candidate directories | Batch output comparison |
| `reason-compare` | Lab compare result JSON | Compare result reasoning |
| `reason-result` | Lab structured result JSON | Single result reasoning |
| `reason-history` | Lab structured result list JSON | Multi-run stability reasoning |
| `reason` | Compare/result/history JSON | Unified auto-routing reasoning |

## Unified Reason CLI

`reason` 명령은 입력 JSON 타입을 보고 적절한 reasoning 경로로 자동 라우팅합니다.

- JSON이 list이면 `reason-history`와 동일하게 run history reasoning을 수행합니다.
- JSON이 Lab compare result dict로 보이면 `reason-compare`와 동일하게 adapter 정규화 후 compare reasoning을 수행합니다.
- JSON이 Lab structured result dict로 보이면 `reason-result`와 동일하게 단일 result reasoning을 수행합니다.

```bash
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_result_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_history_realistic.json
```

저장도 같은 entrypoint에서 가능합니다.

```bash
python -m inferedge_aiguard.cli reason \
  --input examples/lab_compat/lab_history_realistic.json \
  --save-json reports/reason.json \
  --save-md reports/reason.md
```

이 구조는 향후 API나 SaaS로 확장할 때 단일 endpoint로 연결하기 좋습니다. 현재 단계에서는 SaaS/API 서버를 구현하지 않고 CLI entrypoint와 JSON/Markdown report 저장만 제공합니다.

명시적 명령이 필요하면 기존 `reason-compare`, `reason-result`, `reason-history`도 그대로 사용할 수 있습니다.

## Quick Examples

YOLO output 하나를 분석합니다.

```bash
python -m inferedge_aiguard.cli analyze --input examples/single/fp32_normal.json
```

FP32 baseline과 candidate output을 비교합니다.

```bash
python -m inferedge_aiguard.cli compare \
  --base examples/single/fp32_normal.json \
  --candidate examples/single/int8_count_mismatch.json
```

여러 YOLO output을 batch 분석합니다.

```bash
python -m inferedge_aiguard.cli batch-analyze --input-dir examples/single
```

FP32/candidate directory를 파일명 기준으로 batch 비교합니다.

```bash
python -m inferedge_aiguard.cli batch-compare \
  --base-dir examples/fp32 \
  --candidate-dir examples/int8
```

## Lab Compatibility Examples

`examples/lab_compat`는 실제 InferEdgeLab 출력에 더 가까운 compatibility fixture입니다. 실제 Lab repo를 import하지 않고도 unified `reason` CLI가 Lab-style JSON을 올바른 reasoning 경로로 라우팅하는지 검증합니다.

- `lab_compare_realistic.json`: cross precision FP32 vs INT8 compare result 형태
- `lab_result_realistic.json`: 단일 TensorRT INT8 structured result 형태
- `lab_history_realistic.json`: repeated TensorRT INT8 structured result history 형태

```bash
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_result_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_history_realistic.json
```

이 단계는 실제 Lab repo import가 아니라 JSON 호환성 검증 단계입니다.

## Output JSON Schema

YOLO output-level detector는 다음 형식을 기준으로 합니다.

```json
{
  "model": "yolov8n",
  "precision": "fp32",
  "image_id": "sample_001",
  "detections": [
    {
      "class_id": 0,
      "confidence": 0.91,
      "bbox": [12.0, 24.0, 120.0, 80.0]
    }
  ]
}
```

- `bbox`는 `[x, y, w, h]` 형식입니다.
- `confidence`는 `0.0` 이상 `1.0` 이하의 숫자여야 합니다.
- `detections`는 빈 배열일 수 있습니다.

## Failure Definition

현재 output-level detector는 3개입니다.

- bbox collapse: bbox `w` 또는 `h`가 `threshold` 이하로 작아진 detection 감지
- confidence saturation: confidence가 0.0 또는 1.0 근처로 과도하게 몰리는 현상 감지
- detection count mismatch: FP32 baseline 대비 candidate detection 수가 크게 달라지는 현상 감지

각 detector는 `affected_count`, `total_count`, `ratio`, `threshold` 계열 필드를 함께 반환합니다. severity는 고정 문자열이 아니라 failure ratio 기반으로 산정됩니다.

## Summary Metadata

모든 summary 결과에는 실험 재현성을 위한 metadata가 포함됩니다.

- `guard_version`: 실험에 사용한 InferEdgeAIGuard 버전
- `created_at`: summary 생성 시각의 UTC ISO-8601 문자열
- `detector_config`: failure 판단에 사용된 threshold/config snapshot

`--save-json`은 summary dict를 그대로 저장하므로 후속 분석, 표 작성, 논문/포트폴리오 실험 로그 누적에 적합합니다. `--save-md`는 사람이 읽기 쉬운 실험 리포트를 남길 때 사용합니다.

## Research Framing

- RQ1: Quantized/cross-runtime inference results show what kinds of failure/anomaly patterns?
- RQ2: Can output/result-level signals identify suspicious inference results without trusting the model output?
- RQ3: Can rule-based reasoning reduce manual debugging effort for Edge AI validation?

InferEdgeAIGuard는 ground truth 정답을 직접 판단하기보다, result-level signal을 통해 "검증자가 더 살펴봐야 할 inference result"를 빠르게 좁히는 연구형 도구입니다.

## What This Project Does Not Do

InferEdgeAIGuard는 result-based validation reasoning layer입니다. 다음을 직접 구현하지 않습니다.

- 모델 내부 구조 분석
- weight/graph 분석 중심 진단
- ground truth accuracy 평가기
- TensorRT/Jetson 실행기
- 모델 변환기
- ML 학습 또는 calibration 자동화
- SaaS 제품 구현

즉, AIGuard는 실행기나 변환기가 아니라 Lab/Runtime이 남긴 결과를 해석하는 reasoning layer입니다.

## Tests

```bash
python -m pytest -q
```
