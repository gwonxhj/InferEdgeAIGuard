# InferEdgeAIGuard Structured Result Reasoning Report

## Aggregate Summary

| Metric | Value |
| --- | --- |
| status | warning |
| confidence | 0.7 |

## Anomalies

| Type | Severity | Message |
| --- | --- | --- |
| latency_instability | medium | p99 latency is much higher than mean latency. |
| accuracy_missing_warning | medium | Quantized precision result is missing accuracy or task metric validation. |

## Suspected Causes

- runtime_jitter_or_outlier_latency
- missing_accuracy_validation

## Recommendations

- Repeat profiling and inspect warmup/runs/device load before trusting the result.
- Add accuracy or task metric validation before accepting quantized inference results.

## Raw CLI Summary

```text
InferEdgeAIGuard structured result reasoning summary
- status: warning
- confidence: 0.7
- anomalies:
  - type=latency_instability | severity=medium | message=p99 latency is much higher than mean latency.
  - type=accuracy_missing_warning | severity=medium | message=Quantized precision result is missing accuracy or task metric validation.
- suspected_causes: [runtime_jitter_or_outlier_latency, missing_accuracy_validation]
- recommendations: [Repeat profiling and inspect warmup/runs/device load before trusting the result., Add accuracy or task metric validation before accepting quantized inference results.]
```
