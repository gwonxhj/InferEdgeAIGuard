# InferEdgeAIGuard

Optional deterministic diagnosis evidence layer  
(provenance mismatch · suspicious result signals · guard_analysis)

Language: English | [한국어](README.ko.md)

**GitHub description:** Optional deterministic diagnosis layer for provenance mismatch and suspicious inference result evidence.

## Summary

- Optional deterministic diagnosis layer for the InferEdge validation pipeline
- Reads Lab compare/result/history JSON and Runtime/Forge provenance evidence
- Detects suspicious inference signals, provenance mismatch, and weak validation evidence
- Emits `guard_analysis` as optional evidence for Lab reports/API bundles
- Supports review decisions without replacing InferEdgeLab as the decision owner

## What Makes InferEdgeAIGuard Different?

InferEdgeAIGuard is not an LLM guessing layer.

It is a rule/evidence based diagnosis layer that:

- checks latency, accuracy, provenance, output pattern, and run-history signals
- explains suspected causes with deterministic evidence
- preserves warnings/errors in a structured `guard_analysis` contract
- stays optional so Lab remains the final deployment decision owner

## InferEdge Pipeline Role

InferEdgeAIGuard is the optional rule + evidence based diagnosis layer of the larger InferEdge validation pipeline:

```text
ONNX model
-> InferEdgeForge build
-> metadata / manifest / worker runtime summary
-> InferEdgeRuntime validation / result export
-> InferEdgeLab compare / API / job workflow / deployment_decision
-> optional InferEdgeAIGuard provenance diagnosis
-> deploy / review / blocked decision
```

In that pipeline, AIGuard consumes evidence produced by Forge, Runtime, and Lab. It can compare Forge worker/runtime summary provenance with Runtime worker_response provenance, inspect Lab result/compare context, and emit optional `guard_analysis` for Lab to preserve in reports and API bundles.

Implemented today:

- deterministic detector-based reasoning for Lab compare/result/history JSON
- evidence schema, severity/verdict mapping, explanation builder, and JSON/Markdown report persistence
- output-level bbox validity, bbox collapse, confidence distribution, detection count drift, NaN/Inf, and score range detectors
- baseline-vs-candidate comparison for output quality drift and suspicious speed/quality trade-offs
- initial temporal consistency evidence for detection count variance, bbox center movement, class flip rate, and track-free temporal instability signals
- portfolio demo diagnosis bundle covering normal/pass, bbox collapse/blocked, score saturation/blocked, temporal instability/review_required, and provenance mismatch cases
- artifact and source model provenance mismatch detection
- Forge summary vs Runtime worker_response provenance mismatch coverage
- `guard_analysis` schema compatibility with Lab deployment decision handoff

Planned later:

- production service or worker packaging
- broader detector coverage as new Runtime/Forge evidence fields become stable
- deeper integration with future SaaS job execution infrastructure

AIGuard is not an LLM guessing layer and does not make the final deployment decision. InferEdgeLab remains the final `deployment_decision` owner; AIGuard supplies optional evidence that can support review or block decisions.

## Why This Exists

Edge AI에서는 latency 숫자가 좋아 보여도 validation evidence가 충분하지 않을 수 있습니다.

- latency가 개선된 것처럼 보여도 accuracy가 기록되지 않았을 수 있습니다.
- FP16/INT8 candidate인데 FP32 대비 기대한 speedup이 없을 수 있습니다.
- 반복 실행 history에서 일부 run만 accuracy가 기록될 수 있습니다.
- 이런 문제는 단순 benchmark 숫자만 보면 놓치기 쉽습니다.

AIGuard는 inference result를 그대로 믿지 않고, result-level evidence에서 의심 신호와 suspected cause를 설명합니다.

## Current Capabilities

### Output-level failure detection

YOLO detection output JSON을 직접 분석합니다.

- bbox collapse
- confidence saturation
- detection count mismatch
- 단일 output, FP32/candidate pair, batch directory 분석 지원

### Compare result reasoning

`reason-compare` 또는 unified `reason` 명령으로 Lab compare result JSON을 분석합니다.

- latency improvement + accuracy missing
- latency improvement + accuracy drop 또는 risky tradeoff
- shape/run_config mismatch
- cross-precision large latency delta

### Structured result reasoning

`reason-result` 또는 unified `reason` 명령으로 단일 Lab structured result JSON을 분석합니다.

- missing latency metric
- invalid latency value
- p99 latency instability
- missing `runtime_artifact_path`
- missing `resolved_input_shapes`
- quantized result without accuracy

### Forge/Runtime provenance reasoning

Forge metadata/manifest와 Runtime result JSON의 provenance를 비교하는 rule-based detector를 제공합니다.

- artifact sha256 mismatch
- source model sha256 mismatch
- Forge worker/runtime summary vs Runtime worker_response provenance mismatch
- runtime artifact path mismatch
- backend/target/precision/shape mismatch
- insufficient Forge/Runtime provenance

이 detector는 실제 artifact를 실행하지 않고, Forge가 기록한 build provenance와 Runtime이 기록한 profiling/worker response provenance가 같은 산출물을 가리키는지 evidence 기반으로 확인합니다. 명확한 hash mismatch는 `error` guard_analysis로 이어질 수 있고, path/config/shape mismatch 또는 provenance 누락은 `warning` evidence로 남깁니다.

### Run history reasoning

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

## Quick Smoke Commands

- `python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json`
  - Expected: `accuracy_missing_warning`, `likely_quantization_effect`
- `python -m inferedge_aiguard.cli reason --input real_device/jetson/compare_fp32_fp16.json`
  - Expected: `insufficient_precision_speedup`
- `python -m inferedge_aiguard.cli reason --input real_device/jetson/history/yolov8n_fp16_history.json`
  - Expected: `partial_accuracy_missing`

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

## Lab Deployment Decision Handoff

InferEdgeLab 4.2의 deployment decision layer는 AIGuard를 optional evidence로 유지합니다. AIGuard가 실행되면 Lab은 `guard_analysis.status`를 읽어 최종 deployment decision에 반영합니다.

Stable MVP mapping:

| `guard_analysis.status` | Lab deployment decision impact |
|---|---|
| `ok` | favorable Lab judgement can become `deployable`; neutral judgement can become `deployable_with_note` |
| `warning` | `review_required` |
| `error` | `blocked` |
| `skipped` | `unknown` |

AIGuard output remains rule + evidence based. It should include reviewer-facing evidence such as `mode`, `anomalies`, `suspected_causes`, `recommendations`, and `confidence`, but it must not overwrite Lab judgement.

The schema helper `validate_guard_analysis` locks this handoff shape inside AIGuard without requiring a runtime dependency on InferEdgeLab.

## Validation Evidence

InferEdgeAIGuard includes a fixture-based validation report that demonstrates how the reasoning layer detects suspicious compare results, structured result issues, and repeated-run instability.

| Evidence | Path | Purpose |
|---|---|---|
| Fixture validation report | `docs/validation_report.md` | Lab-like fixture 기반 reasoning 검증 |
| Jetson validation report | `docs/jetson_validation_report.md` | Real-device evidence |
| Portfolio summary | `docs/portfolio_summary.md` | 면접/포트폴리오 설명용 |
| Jetson compare evidence | `real_device/jetson/compare_fp32_fp16.json` | FP32 vs FP16 speedup 검증 |
| Jetson history evidence | `real_device/jetson/history/yolov8n_fp16_history.json` | repeated-run logging consistency 검증 |

- Portfolio summary: [docs/portfolio_summary.md](docs/portfolio_summary.md)
- Validation report: [docs/validation_report.md](docs/validation_report.md)
- Jetson validation plan: [docs/jetson_validation_plan.md](docs/jetson_validation_plan.md)
- Jetson validation report: [docs/jetson_validation_report.md](docs/jetson_validation_report.md)
- GitHub publication notes: [docs/github_publication_notes.md](docs/github_publication_notes.md)
- Saved evidence reports: `reports/validation/`
- Real-device Jetson reports: `reports/jetson/`
- Real-device Jetson inputs: `real_device/jetson/`
- Inputs: `examples/lab_compat/`

Fixture-based validation, Jetson real-device validation, and run-history reasoning evidence are available now.
The execution checklist/history remains in [docs/jetson_validation_plan.md](docs/jetson_validation_plan.md), and the current Jetson FP32/FP16 evidence is summarized in [docs/jetson_validation_report.md](docs/jetson_validation_report.md).

Jetson run history reasoning evidence도 추가되어, AIGuard가 repeated FP16 run에서 accuracy logging이 일관되지 않은 문제를 `partial_accuracy_missing`으로 감지할 수 있음을 보여줍니다.

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

## Limitations

InferEdgeAIGuard는 result-based validation reasoning layer입니다.

- heuristic/rule-based reasoning이며, actual root cause를 확정하지 않고 suspected cause를 제공합니다.
- 모델 내부 구조 분석
- weight/graph 분석 중심 진단
- ground truth accuracy 평가기
- TensorRT/Jetson 실행기
- 모델 변환기
- ML 학습 또는 calibration 자동화
- controlled repeated-run 실험은 추가 예정
- SaaS/API는 future work

즉, AIGuard는 실행기나 변환기가 아니라 Lab/Runtime이 남긴 결과를 해석하는 reasoning layer입니다.

## Tests

```bash
python -m pytest -q
```
