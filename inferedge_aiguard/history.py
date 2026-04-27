"""Rule-based reasoning over repeated InferEdgeLab structured results."""

from __future__ import annotations

from statistics import median
from typing import Any

from .detectors import summary_metadata


def analyze_run_history(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze stability and consistency across repeated structured results."""

    if not isinstance(results, list):
        raise ValueError("results must be a list of structured result dictionaries")

    anomalies: list[dict[str, Any]] = []
    explanations: list[str] = []
    suspected_causes: list[str] = []
    recommendations: list[str] = []

    def add_anomaly(
        anomaly_type: str,
        severity: str,
        message: str,
        evidence: dict[str, Any],
        suspected_cause: str,
        recommendation: str,
    ) -> None:
        anomalies.append(
            {
                "type": anomaly_type,
                "severity": severity,
                "message": message,
                "evidence": evidence,
            }
        )
        explanations.append(message)
        _append_unique(suspected_causes, suspected_cause)
        _append_unique(recommendations, recommendation)

    run_count = len(results)
    mean_ms_values = [
        float(result.get("mean_ms"))
        for result in results
        if _is_positive_number(result.get("mean_ms"))
    ]
    p99_ms_values = [
        float(result.get("p99_ms"))
        for result in results
        if _is_positive_number(result.get("p99_ms"))
    ]
    accuracy_present_count = sum(1 for result in results if _has_accuracy_value(result))
    accuracy_missing_count = run_count - accuracy_present_count

    min_mean_ms = min(mean_ms_values) if mean_ms_values else None
    max_mean_ms = max(mean_ms_values) if mean_ms_values else None
    min_p99_ms = min(p99_ms_values) if p99_ms_values else None
    max_p99_ms = max(p99_ms_values) if p99_ms_values else None
    mean_latency_ratio = (
        _ratio(max_mean_ms, min_mean_ms)
        if max_mean_ms is not None and min_mean_ms is not None
        else None
    )
    p99_latency_ratio = (
        _ratio(max_p99_ms, min_p99_ms)
        if max_p99_ms is not None and min_p99_ms is not None
        else None
    )
    history_metrics = {
        "run_count": run_count,
        "mean_ms_values": mean_ms_values,
        "p99_ms_values": p99_ms_values,
        "min_mean_ms": min_mean_ms,
        "max_mean_ms": max_mean_ms,
        "mean_latency_ratio": mean_latency_ratio,
        "min_p99_ms": min_p99_ms,
        "max_p99_ms": max_p99_ms,
        "p99_latency_ratio": p99_latency_ratio,
        "accuracy_present_count": accuracy_present_count,
        "accuracy_missing_count": accuracy_missing_count,
    }

    if run_count < 2:
        add_anomaly(
            "insufficient_history",
            "low",
            "Run history has too few repeated runs for stability analysis.",
            {"run_count": run_count},
            "not_enough_runs",
            "Collect at least 3 repeated runs before making stability conclusions.",
        )

    identity_values = _field_values(results, ("model", "engine", "device", "precision"))
    mixed_identity = {
        field: values for field, values in identity_values.items() if len(values) > 1
    }
    if mixed_identity:
        add_anomaly(
            "mixed_run_identity",
            "high",
            "Run history mixes identity fields across repeated runs.",
            mixed_identity,
            "mixed_experiment_group",
            (
                "Group run history by the same model, engine, device, precision, "
                "and shape before stability analysis."
            ),
        )

    shape_values = _field_values(results, ("batch", "height", "width"))
    mixed_shape = {field: values for field, values in shape_values.items() if len(values) > 1}
    if mixed_shape:
        add_anomaly(
            "mixed_shape_config",
            "high",
            "Run history mixes batch/height/width configuration.",
            mixed_shape,
            "mixed_input_configuration",
            "Compare repeated runs only when batch/height/width are consistent.",
        )

    if len(mean_ms_values) >= 2 and mean_latency_ratio is not None:
        if mean_latency_ratio >= 1.5:
            add_anomaly(
                "mean_latency_instability",
                "medium",
                "Mean latency varies significantly across repeated runs.",
                {
                    "min_mean_ms": min(mean_ms_values),
                    "max_mean_ms": max(mean_ms_values),
                    "ratio": mean_latency_ratio,
                },
                "runtime_jitter_or_unstable_device_load",
                "Repeat profiling after controlling device load, warmup, and run count.",
            )

    if len(p99_ms_values) >= 2 and p99_latency_ratio is not None:
        if p99_latency_ratio >= 1.5:
            add_anomaly(
                "p99_latency_instability",
                "medium",
                "p99 latency varies significantly across repeated runs.",
                {
                    "min_p99_ms": min(p99_ms_values),
                    "max_p99_ms": max(p99_ms_values),
                    "ratio": p99_latency_ratio,
                },
                "tail_latency_jitter",
                "Inspect tail latency outliers and increase repeated runs.",
            )

    indexed_mean_values = [
        (index, float(result.get("mean_ms")))
        for index, result in enumerate(results)
        if _is_positive_number(result.get("mean_ms"))
    ]
    if len(indexed_mean_values) >= 3:
        median_mean_ms = median(value for _, value in indexed_mean_values)
        outlier_indices = [
            index
            for index, value in indexed_mean_values
            if value >= median_mean_ms * 1.8
        ]
        if outlier_indices:
            add_anomaly(
                "latency_outlier_run",
                "medium",
                "One or more runs have mean latency far above the history median.",
                {
                    "outlier_indices": outlier_indices,
                    "median_mean_ms": median_mean_ms,
                },
                "single_run_outlier",
                (
                    "Inspect the outlier run and repeat profiling to confirm whether "
                    "it is reproducible."
                ),
            )

    if 0 < accuracy_present_count < run_count:
        add_anomaly(
            "partial_accuracy_missing",
            "medium",
            "Accuracy is logged for only part of the run history.",
            {
                "accuracy_present_count": accuracy_present_count,
                "accuracy_missing_count": accuracy_missing_count,
            },
            "inconsistent_accuracy_logging",
            "Ensure accuracy or task metrics are consistently logged across repeated runs.",
        )

    precisions = {
        str(result.get("precision", "")).lower()
        for result in results
        if result.get("precision") is not None
    }
    if precisions and precisions.issubset({"int8", "fp16"}) and accuracy_present_count == 0:
        add_anomaly(
            "quantized_history_accuracy_missing",
            "medium",
            "Repeated quantized runs are missing accuracy or task metric validation.",
            {"precision_values": sorted(precisions), "run_count": run_count},
            "missing_accuracy_validation",
            (
                "Add accuracy validation for repeated quantized runs before accepting "
                "the performance trend."
            ),
        )

    status = _status_from_anomalies(anomalies)
    return {
        **summary_metadata(),
        "mode": "run_history_reasoning",
        "status": status,
        "run_count": run_count,
        "anomalies": anomalies,
        "explanations": explanations,
        "suspected_causes": suspected_causes,
        "confidence": _confidence_for_status(status),
        "recommendations": recommendations,
        "history_metrics": history_metrics,
    }


def _field_values(
    results: list[dict[str, Any]], fields: tuple[str, ...]
) -> dict[str, list[Any]]:
    return {
        field: sorted({result.get(field) for result in results}, key=lambda value: str(value))
        for field in fields
    }


def _ratio(max_value: float, min_value: float) -> float | None:
    if min_value <= 0:
        return None
    return max_value / min_value


def _status_from_anomalies(anomalies: list[dict[str, Any]]) -> str:
    severities = {anomaly.get("severity") for anomaly in anomalies}
    if "high" in severities:
        return "error"
    if severities:
        return "warning"
    return "ok"


def _confidence_for_status(status: str) -> float:
    if status == "error":
        return 0.9
    if status == "warning":
        return 0.7
    return 0.5


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _has_accuracy_value(result: dict[str, Any]) -> bool:
    if "accuracy" in result and result.get("accuracy") is not None:
        return True

    metrics = result.get("metrics")
    if isinstance(metrics, dict) and metrics.get("accuracy") is not None:
        return True

    extra = result.get("extra")
    return isinstance(extra, dict) and extra.get("accuracy") is not None
