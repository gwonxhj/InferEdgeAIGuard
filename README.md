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

Experiment hygiene / comparability layer:
InferEdgeEnv -> v0.1.5 v1-complete local-first run evidence registry / comparability checker
```

In that pipeline, AIGuard consumes evidence produced by Forge, Runtime, and Lab. It can compare Forge worker/runtime summary provenance with Runtime worker_response provenance, inspect Lab result/compare context, and emit optional `guard_analysis` for Lab to preserve in reports and API bundles.

Implemented today:

- deterministic detector-based reasoning for Lab compare/result/history JSON
- evidence schema, severity/verdict mapping, explanation builder, and JSON/Markdown report persistence
- output-level bbox validity, bbox collapse, confidence distribution, detection count drift, NaN/Inf, and score range detectors
- baseline-vs-candidate comparison for output quality drift and suspicious speed/quality trade-offs
- initial temporal consistency evidence for detection count variance, bbox center movement, class flip rate, and track-free temporal instability signals
- runtime reliability evidence from Orchestrator `orchestration_summary` files: deadline miss, drop/fallback, queue backlog, queue pressure reasons, worker operation risk summaries, device-local producer/event coverage, sustained workload profile pressure, local profile adapter signals, and optional tegrastats thermal/resource signals
- portfolio demo diagnosis bundle covering normal/pass, bbox collapse/blocked, score saturation/blocked, temporal instability/review_required, and provenance mismatch cases
- artifact and source model provenance mismatch detection
- Forge summary vs Runtime worker_response provenance mismatch coverage
- `guard_analysis` schema compatibility with Lab deployment decision handoff

Planned later:

- production service or worker packaging
- broader detector coverage as new Runtime/Forge evidence fields become stable
- deeper integration with future SaaS job execution infrastructure

AIGuard is not an LLM guessing layer and does not make the final deployment decision. InferEdgeLab remains the final `deployment_decision` owner; AIGuard supplies optional evidence that can support review or block decisions.

Portfolio boundary: InferEdgeLab is the validation / decision layer. InferEdgeEnv is the v0.1.5 v1-complete experiment hygiene / comparability layer; it records whether benchmark evidence can be trusted and compared without replacing AIGuard diagnosis evidence or Lab deployment decisions.

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
| `reason-orchestration` | Orchestrator summary JSON | Runtime reliability reasoning |
| `reason` | Compare/result/history/orchestration JSON | Unified auto-routing reasoning |

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
- JSON이 Orchestrator `inferedge-orchestration-summary-v1` dict로 보이면 `reason-orchestration`과 동일하게 runtime reliability reasoning을 수행합니다.

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

Orchestrator runtime reliability summary도 같은 흐름으로 분석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

이 경로는 `policy_decision_log`, `decision_reason`, `queue_depth_timeline`,
deadline miss, drop/fallback 신호를 `guard_analysis` evidence로 변환합니다.
AIGuard는 runtime reliability risk를 설명하고, 최종 deployment decision은
계속 InferEdgeLab이 담당합니다.

EdgeEnv runtime regression report도 deterministic runtime anomaly evidence로
해석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input reports/edgeenv_runtime_regression.json
python -m inferedge_aiguard.cli reason \
  --input reports/edgeenv_runtime_regression.json
```

이 경로는 EdgeEnv의 comparability-first 결과를 존중하면서
`runtime_latency_regression`, `runtime_throughput_regression`,
`runtime_memory_regression`, `runtime_telemetry_context_coverage`,
`runtime_telemetry_replay_context` evidence를 생성합니다. AIGuard는
regression 계산이나 final deployment decision을 소유하지 않습니다.
candidate telemetry gap과 baseline/candidate execution sequence inversion은
EdgeEnv replay context에서 온 warning evidence로 보존되며, AIGuard가 이를
comparability decision으로 재판정하지 않습니다.
`tests/fixtures/edgeenv_regression/`에는 EdgeEnv의 committed replay fixtures를
mirror한 작은 CLI smoke 입력이 있습니다.

Remote dispatch starter 결과도 deterministic evidence로 해석할 수 있습니다.

```bash
python -m inferedge_aiguard.cli reason-remote-dispatch \
  --input reports/remote_dispatch_result.json
python -m inferedge_aiguard.cli reason \
  --input reports/remote_dispatch_result.json
```

이 경로는 `inferedge-remote-dispatch-result-v1`의 worker selection,
`remote_execution_result.status`, `error_category`, HTTP/SSH starter 성공/실패를
`remote_execution_plan_only`, `remote_execution_starter_success`,
`remote_execution_failed`, `remote_execution_recovered_by_fallback` 같은
evidence로 변환합니다. fallback이 성공해도 primary worker instability는
review evidence로 남깁니다. 이는 production remote execution 판정이 아니라
explicit starter execution evidence입니다.

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
| Runtime reliability signals | `docs/runtime_reliability_signals.md` | Orchestrator scheduling/sustained telemetry -> guard_analysis mapping |
| Jetson compare evidence | `real_device/jetson/compare_fp32_fp16.json` | FP32 vs FP16 speedup 검증 |
| Jetson history evidence | `real_device/jetson/history/yolov8n_fp16_history.json` | repeated-run logging consistency 검증 |

- Portfolio summary: [docs/portfolio_summary.md](docs/portfolio_summary.md)
- Detector validation matrix: [docs/detector_validation_matrix.md](docs/detector_validation_matrix.md)
- Runtime reliability signals: [docs/runtime_reliability_signals.md](docs/runtime_reliability_signals.md)
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

## Detector Validation Matrix

AIGuard detectors are deterministic evidence providers. They explain why a result
should pass, require review, or be blocked, but InferEdgeLab remains the final
deployment decision owner.

| Case | Signal | Expected `guard_verdict` | Meaning |
|---|---|---|---|
| normal | stable bbox, score, and detection count | `pass` | no deployment-risk evidence from AIGuard |
| bbox collapse | near-zero area boxes increase | `blocked` | decoder, postprocess, or quantization issue possible |
| score saturation | confidence scores concentrate near 0 or 1 | `blocked` | score calibration or postprocess issue possible |
| temporal instability | frame-level detection count or bbox movement is unstable | `review_required` | runtime output stability should be reviewed |
| provenance mismatch | Forge/Runtime source or artifact identity differs | `blocked` / `error` | evidence may not describe the artifact under review |

### Detector Verdict Matrix

The table below is the reviewer-facing version of the detector policy. It is
not a Lab deployment policy by itself; Lab may combine these signals with
latency, accuracy, contract, and runtime evidence before producing the final
`deployment_decision`.

| Detector family | Primary evidence | Pass | Review | Block | Report field |
|---|---|---|---|---|---|
| bbox validity | `invalid_bbox_rate` | `<= 0.05` | `> 0.05` | `> 0.20` | `evidence[].metric_name` |
| bbox collapse | `bbox_collapse_ratio` | `<= 0.05` | `> 0.05` or baseline factor `> 5x` | severe collapse or baseline factor `> 10x` | `evidence[].observed_value` |
| confidence score range | `score_range_violation_count` | `0` | n/a | `> 0` | `evidence[].severity` |
| confidence saturation | `saturation_ratio` | `< 0.70` | `>= 0.70` | `>= 0.85` with quality drift | `evidence[].observed_value` |
| detection disappearance | `detection_count_drop_pct`, `zero_detection_frame_ratio` | stable count | drop `>= 50%` | drop `>= 80%` or zero-frame ratio `> 0.30` | `candidate_summary.comparison` |
| baseline deviation | invalid/collapse/saturation factor | near baseline | factor `> 5x` | factor `> 10x` | `evidence[].increase_factor` |
| temporal consistency | count CV, bbox jump, class flip | stable sequence | count CV `> 1.0`, class flip `> 0.30`, or large center jump | zero-frame ratio `> 0.30` | `candidate_summary.temporal` |
| provenance consistency | source/artifact/backend identity | exact handoff match | warning mismatch | error mismatch | `guard_analysis.anomalies` |

Planned detector extensions are intentionally still deterministic: per-class
detection drift, stronger detection disappearance summaries, calibration drift
for score distributions, and baseline profile stability. These are documented
as roadmap items, not as implemented automatic root-cause proof.

The full matrix is maintained in [docs/detector_validation_matrix.md](docs/detector_validation_matrix.md).

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

Core output-level detector families are:

- bbox validity/collapse: invalid, NaN/Inf, out-of-bounds, or near-zero-area boxes
- confidence distribution: score range violation and saturation
- detection count drift: FP32 or known-good baseline 대비 detection 수 변화
- baseline deviation: invalid bbox, collapse, saturation factor 증가
- temporal consistency: tracking 없이 frame-level instability 감지

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
