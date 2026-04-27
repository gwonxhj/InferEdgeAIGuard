# InferEdgeAIGuard Run History Reasoning Report

## Aggregate Summary

| Metric | Value |
| --- | --- |
| status | warning |
| confidence | 0.7 |
| run_count | 5 |

## History Metrics

| Metric | Value |
| --- | --- |
| run_count | 5 |
| mean_ms_values | 12.409211830017739, 13.352749789987683, 13.71496924999974, 13.609172769988618, 13.352749789987683 |
| p99_ms_values | 16.95117583997444, 16.816976569712097, 17.07734356033143, 17.01069448038197, 16.816976569712097 |
| min_mean_ms | 12.4092 |
| max_mean_ms | 13.715 |
| mean_latency_ratio | 1.10522 |
| min_p99_ms | 16.817 |
| max_p99_ms | 17.0773 |
| p99_latency_ratio | 1.01548 |
| accuracy_present_count | 1 |
| accuracy_missing_count | 4 |

## Anomalies

| Type | Severity | Message |
| --- | --- | --- |
| partial_accuracy_missing | medium | Accuracy is logged for only part of the run history. |

## Suspected Causes

- inconsistent_accuracy_logging

## Recommendations

- Ensure accuracy or task metrics are consistently logged across repeated runs.

## Raw CLI Summary

```text
InferEdgeAIGuard run history reasoning summary
- status: warning
- confidence: 0.7
- run_count: 5
- anomalies:
  - type=partial_accuracy_missing | severity=medium | message=Accuracy is logged for only part of the run history.
- suspected_causes: [inconsistent_accuracy_logging]
- recommendations: [Ensure accuracy or task metrics are consistently logged across repeated runs.]
```
