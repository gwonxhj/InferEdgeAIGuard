# InferEdgeAIGuard Compare Reasoning Report

## Aggregate Summary

| Metric | Value |
| --- | --- |
| status | warning |
| confidence | 0.7 |

## Anomalies

| Type | Severity | Message |
| --- | --- | --- |
| insufficient_precision_speedup | medium | Cross-precision candidate shows less than 10% latency improvement, so the expected precision speedup was not observed. |

## Suspected Causes

- precision_speedup_not_observed
- runtime_or_engine_optimization_issue

## Recommendations

- Verify that the TensorRT engine was actually built and executed with the expected reduced precision.
- Check runtime_artifact_path, engine build settings, and operator precision fallback.
- Repeat profiling to rule out measurement variance or device load effects.

## Raw CLI Summary

```text
InferEdgeAIGuard compare reasoning summary
- status: warning
- confidence: 0.7
- anomalies:
  - type=insufficient_precision_speedup | severity=medium | message=Cross-precision candidate shows less than 10% latency improvement, so the expected precision speedup was not observed.
- suspected_causes: [precision_speedup_not_observed, runtime_or_engine_optimization_issue]
- recommendations: [Verify that the TensorRT engine was actually built and executed with the expected reduced precision., Check runtime_artifact_path, engine build settings, and operator precision fallback., Repeat profiling to rule out measurement variance or device load effects.]
```
