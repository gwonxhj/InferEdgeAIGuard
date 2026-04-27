# InferEdgeAIGuard Compare Reasoning Report

## Aggregate Summary

| Metric | Value |
| --- | --- |
| status | warning |
| confidence | 0.7 |

## Anomalies

| Type | Severity | Message |
| --- | --- | --- |
| accuracy_missing_warning | medium | Latency appears improved, but accuracy or task metric validation is missing. |
| likely_quantization_effect | low | Cross-precision comparison shows a large latency delta. |

## Suspected Causes

- missing_accuracy_validation
- precision_or_runtime_change

## Recommendations

- Add accuracy or task metric validation before accepting latency-only improvement.
- Verify that the observed latency delta is expected for the target engine/device/precision.

## Raw CLI Summary

```text
InferEdgeAIGuard compare reasoning summary
- status: warning
- confidence: 0.7
- anomalies:
  - type=accuracy_missing_warning | severity=medium | message=Latency appears improved, but accuracy or task metric validation is missing.
  - type=likely_quantization_effect | severity=low | message=Cross-precision comparison shows a large latency delta.
- suspected_causes: [missing_accuracy_validation, precision_or_runtime_change]
- recommendations: [Add accuracy or task metric validation before accepting latency-only improvement., Verify that the observed latency delta is expected for the target engine/device/precision.]
```
