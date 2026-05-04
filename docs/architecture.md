# InferEdgeAIGuard Architecture

InferEdgeAIGuard is the validation reasoning layer in the InferEdge ecosystem. It does not run inference or convert models. It reads result JSON produced by validation workflows and explains anomaly signals before a result is trusted.

## Ecosystem Positioning

```text
Forge -> Runtime -> Lab -> AIGuard
```

- Forge: creates deployment artifacts such as optimized runtime files.
- Runtime: executes inference on the target edge environment.
- Lab: analyzes Runtime results, records reports/API bundles, and owns deployment decisions.
- AIGuard: reasons over the result data and reports optional anomaly, evidence, suspected cause, and recommendation.

The boundary is intentional:

- InferEdgeLab = analysis, report/API/job workflow, and final decision ownership
- InferEdgeAIGuard = optional rule/evidence diagnosis

## Internal Layers

### Output Detector

Analyzes YOLO detection output JSON directly.

- bbox collapse
- confidence saturation
- detection count mismatch

### Compare Reasoning

Analyzes Lab compare result JSON.

- unreliable comparison from shape or run_config mismatch
- latency improvement without accuracy validation
- risky latency/accuracy tradeoff
- large cross-precision latency delta

### Structured Result Reasoning

Analyzes one Lab structured result.

- missing or invalid latency metric
- p99 instability
- missing runtime artifact provenance
- missing resolved input shape provenance
- quantized result without accuracy

### Forge/Runtime Provenance Reasoning

Compares Forge metadata/manifest provenance against Runtime result provenance.

- artifact hash mismatch
- source model hash mismatch
- Forge worker/runtime summary vs Runtime worker_response provenance mismatch
- runtime artifact path mismatch
- backend/target/precision/shape mismatch
- insufficient provenance for review

This layer is rule + evidence based. It does not execute artifacts or guess missing values. It records the mismatched field, expected Forge value, observed Runtime value, and source documents so Lab can optionally surface the guard_analysis evidence in report/deployment decision flows. Worker provenance fixtures cover the newer Forge summary -> Lab worker request -> Runtime worker response path without requiring any cross-repo runtime dependency.

### History Reasoning

Analyzes repeated Lab structured result lists.

- mean latency instability
- p99 tail latency instability
- outlier run
- mixed experiment group
- partial or missing accuracy logging

### Unified CLI/API Entry Point

The `reason` command auto-routes input JSON:

- list -> run history reasoning
- Lab compare result dict -> compare reasoning
- Lab structured result dict -> structured result reasoning

This shape is suitable for a future single API endpoint, while the current project remains CLI-first.

## Lab Deployment Decision Contract

InferEdgeLab 4.2 can include AIGuard output as optional `guard_analysis` evidence when it builds a deployment decision. Lab remains the decision owner; AIGuard only supplies rule-based evidence.

The stable MVP contract is:

```json
{
  "status": "ok",
  "mode": "compare_reasoning",
  "anomalies": [],
  "suspected_causes": [],
  "recommendations": [],
  "confidence": 0.5
}
```

`status` is the only field Lab requires for deployment decision mapping:

| AIGuard status | Lab deployment effect |
|---|---|
| `ok` | Lab may classify favorable evidence as `deployable` or neutral evidence as `deployable_with_note`. |
| `warning` | Lab maps the result to `review_required`. |
| `error` | Lab maps the result to `blocked`. |
| `skipped` | Lab maps the result to `unknown`. |

The remaining fields are evidence fields for reviewers and reports. They must not replace Lab judgement, runtime profiling, or Forge artifact metadata.

The Python schema helper `validate_guard_analysis` validates this contract without importing InferEdgeLab. This keeps AIGuard optional while making the cross-repo handoff explicit and testable.

## Future Direction

Potential extensions:

- `/reason` API endpoint that accepts compare/result/history JSON
- broader JSON/Markdown report integration with Lab and Studio surfaces
- dashboard or SaaS layer on top of saved reasoning reports

Current scope remains result-based validation reasoning. It does not include model conversion, device execution, ground truth evaluation, model graph analysis, or training.
