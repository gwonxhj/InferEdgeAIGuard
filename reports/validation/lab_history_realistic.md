# InferEdgeAIGuard Run History Reasoning Report

## Aggregate Summary

| Metric | Value |
| --- | --- |
| status | warning |
| confidence | 0.7 |
| run_count | 3 |

## History Metrics

| Metric | Value |
| --- | --- |
| run_count | 3 |
| mean_ms_values | 5.0, 5.2, 10.1 |
| p99_ms_values | 7.1, 7.5, 18.4 |
| min_mean_ms | 5 |
| max_mean_ms | 10.1 |
| mean_latency_ratio | 2.02 |
| min_p99_ms | 7.1 |
| max_p99_ms | 18.4 |
| p99_latency_ratio | 2.59155 |
| accuracy_present_count | 0 |
| accuracy_missing_count | 3 |

## Anomalies

| Type | Severity | Message |
| --- | --- | --- |
| mean_latency_instability | medium | Mean latency varies significantly across repeated runs. |
| p99_latency_instability | medium | p99 latency varies significantly across repeated runs. |
| latency_outlier_run | medium | One or more runs have mean latency far above the history median. |
| quantized_history_accuracy_missing | medium | Repeated quantized runs are missing accuracy or task metric validation. |

## Suspected Causes

- runtime_jitter_or_unstable_device_load
- tail_latency_jitter
- single_run_outlier
- missing_accuracy_validation

## Recommendations

- Repeat profiling after controlling device load, warmup, and run count.
- Inspect tail latency outliers and increase repeated runs.
- Inspect the outlier run and repeat profiling to confirm whether it is reproducible.
- Add accuracy validation for repeated quantized runs before accepting the performance trend.

## Raw CLI Summary

```text
InferEdgeAIGuard run history reasoning summary
- status: warning
- confidence: 0.7
- run_count: 3
- anomalies:
  - type=mean_latency_instability | severity=medium | message=Mean latency varies significantly across repeated runs.
  - type=p99_latency_instability | severity=medium | message=p99 latency varies significantly across repeated runs.
  - type=latency_outlier_run | severity=medium | message=One or more runs have mean latency far above the history median.
  - type=quantized_history_accuracy_missing | severity=medium | message=Repeated quantized runs are missing accuracy or task metric validation.
- suspected_causes: [runtime_jitter_or_unstable_device_load, tail_latency_jitter, single_run_outlier, missing_accuracy_validation]
- recommendations: [Repeat profiling after controlling device load, warmup, and run count., Inspect tail latency outliers and increase repeated runs., Inspect the outlier run and repeat profiling to confirm whether it is reproducible., Add accuracy validation for repeated quantized runs before accepting the performance trend.]
```
