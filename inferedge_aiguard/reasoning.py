"""Rule-based reasoning over InferEdgeLab comparison results."""

from __future__ import annotations

from typing import Any


def analyze_compare_result(compare_result: dict[str, Any]) -> dict[str, Any]:
    """Analyze an InferEdgeLab compare result without modifying Lab measurements."""

    anomalies: list[dict[str, Any]] = []
    explanations: list[str] = []
    suspected_causes: list[str] = []
    recommendations: list[str] = []

    def add_anomaly(
        anomaly_type: str,
        severity: str,
        message: str,
        evidence: dict[str, Any],
        suspected_cause: str | list[str],
        recommendation: str | list[str],
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
        for cause in _as_list(suspected_cause):
            _append_unique(suspected_causes, cause)
        for item in _as_list(recommendation):
            _append_unique(recommendations, item)

    shape_match = _first_present(compare_result, "shape_match", "shape_matched")
    if shape_match is False:
        add_anomaly(
            "unreliable_comparison",
            "high",
            "Comparison is unreliable because input/output shapes do not match.",
            {"shape_match": shape_match},
            "input_shape_mismatch",
            "Re-run comparison with matching batch/height/width or resolved input shapes.",
        )

    run_config_match = _first_present(
        compare_result, "run_config_match", "run_config_matched"
    )
    if run_config_match is False:
        add_anomaly(
            "unreliable_comparison",
            "high",
            "Comparison is unreliable because run configuration does not match.",
            {"run_config_match": run_config_match},
            "run_config_mismatch",
            (
                "Ensure warmup/runs/batch/precision-related run configuration is "
                "consistent before trusting the comparison."
            ),
        )

    latency_improved = _latency_improved(compare_result)
    accuracy_missing = not any(
        key in compare_result
        for key in (
            "accuracy",
            "accuracy_delta",
            "base_accuracy",
            "new_accuracy",
            "candidate_accuracy",
        )
    )
    if latency_improved and accuracy_missing:
        add_anomaly(
            "accuracy_missing_warning",
            "medium",
            "Latency appears improved, but accuracy or task metric validation is missing.",
            _latency_evidence(compare_result),
            "missing_accuracy_validation",
            "Add accuracy or task metric validation before accepting latency-only improvement.",
        )

    if latency_improved and _accuracy_dropped(compare_result):
        add_anomaly(
            "risky_tradeoff",
            "medium",
            "Latency appears improved while accuracy appears to drop.",
            {
                **_latency_evidence(compare_result),
                "accuracy_delta": compare_result.get("accuracy_delta"),
                "base_accuracy": compare_result.get("base_accuracy"),
                "new_accuracy": compare_result.get("new_accuracy"),
                "candidate_accuracy": compare_result.get("candidate_accuracy"),
            },
            "possible_quantization_accuracy_loss",
            "Review the latency/accuracy tradeoff before accepting the candidate result.",
        )

    if _is_cross_precision(compare_result) and _large_latency_delta(compare_result):
        add_anomaly(
            "likely_quantization_effect",
            "low",
            "Cross-precision comparison shows a large latency delta.",
            {
                **_latency_evidence(compare_result),
                "comparison_mode": compare_result.get("comparison_mode"),
                "precision_pair": compare_result.get("precision_pair"),
            },
            "precision_or_runtime_change",
            (
                "Verify that the observed latency delta is expected for the target "
                "engine/device/precision."
            ),
        )

    if _has_insufficient_precision_speedup(compare_result):
        add_anomaly(
            "insufficient_precision_speedup",
            "medium",
            (
                "Cross-precision candidate shows less than 10% latency improvement, "
                "so the expected precision speedup was not observed."
            ),
            {
                "comparison_mode": compare_result.get("comparison_mode"),
                "precision_pair": compare_result.get("precision_pair"),
                "latency_delta_pct": compare_result.get("latency_delta_pct"),
                "minimum_expected_speedup_pct": 10.0,
            },
            [
                "precision_speedup_not_observed",
                "runtime_or_engine_optimization_issue",
            ],
            [
                (
                    "Verify that the TensorRT engine was actually built and executed "
                    "with the expected reduced precision."
                ),
                (
                    "Check runtime_artifact_path, engine build settings, and operator "
                    "precision fallback."
                ),
                (
                    "Repeat profiling to rule out measurement variance or device "
                    "load effects."
                ),
            ],
        )

    status = _status_from_anomalies(anomalies)
    return {
        "mode": "compare_reasoning",
        "status": status,
        "anomalies": anomalies,
        "explanations": explanations,
        "suspected_causes": suspected_causes,
        "confidence": _confidence_for_status(status),
        "recommendations": recommendations,
    }


def analyze_structured_result(result: dict[str, Any]) -> dict[str, Any]:
    """Analyze one InferEdgeLab structured measurement result."""

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

    missing_identity_fields = [
        field for field in ("model", "engine", "device", "precision") if not result.get(field)
    ]
    if missing_identity_fields:
        add_anomaly(
            "missing_identity_field",
            "high",
            "Required identity fields are missing from the structured result.",
            {"missing_fields": missing_identity_fields},
            "incomplete_result_schema",
            (
                "Ensure model, engine, device, and precision are recorded in the Lab "
                "structured result."
            ),
        )

    mean_ms = result.get("mean_ms")
    p99_ms = result.get("p99_ms")
    missing_latency_fields = [
        field for field in ("mean_ms", "p99_ms") if result.get(field) is None
    ]
    if missing_latency_fields:
        add_anomaly(
            "missing_latency_metric",
            "high",
            "Required latency metrics are missing from the structured result.",
            {"missing_fields": missing_latency_fields},
            "incomplete_latency_measurement",
            "Re-run profiling and ensure mean_ms and p99_ms are exported.",
        )

    invalid_latency = {
        field: value
        for field, value in (("mean_ms", mean_ms), ("p99_ms", p99_ms))
        if _is_number(value) and value <= 0
    }
    if invalid_latency:
        add_anomaly(
            "invalid_latency_value",
            "high",
            "Latency metrics must be positive values.",
            invalid_latency,
            "invalid_measurement_export",
            "Check timing collection and result serialization.",
        )

    if _is_number(mean_ms) and _is_number(p99_ms) and mean_ms > 0:
        p99_to_mean_ratio = p99_ms / mean_ms
        if p99_to_mean_ratio >= 2.0:
            add_anomaly(
                "latency_instability",
                "medium",
                "p99 latency is much higher than mean latency.",
                {
                    "mean_ms": mean_ms,
                    "p99_ms": p99_ms,
                    "p99_to_mean_ratio": p99_to_mean_ratio,
                },
                "runtime_jitter_or_outlier_latency",
                (
                    "Repeat profiling and inspect warmup/runs/device load before "
                    "trusting the result."
                ),
            )

    extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
    if not extra.get("runtime_artifact_path"):
        add_anomaly(
            "missing_runtime_artifact",
            "medium",
            "runtime_artifact_path is missing from result.extra.",
            {"runtime_artifact_path": extra.get("runtime_artifact_path")},
            "missing_runtime_provenance",
            "Record runtime_artifact_path so the measured engine/artifact can be traced.",
        )

    if not extra.get("resolved_input_shapes"):
        add_anomaly(
            "missing_resolved_input_shapes",
            "medium",
            "resolved_input_shapes is missing from result.extra.",
            {"resolved_input_shapes": extra.get("resolved_input_shapes")},
            "missing_shape_provenance",
            "Record resolved_input_shapes to validate actual runtime input dimensions.",
        )

    precision = str(result.get("precision", "")).lower()
    if precision in {"int8", "fp16"} and not _has_accuracy_value(result):
        add_anomaly(
            "accuracy_missing_warning",
            "medium",
            "Quantized precision result is missing accuracy or task metric validation.",
            {"precision": result.get("precision")},
            "missing_accuracy_validation",
            (
                "Add accuracy or task metric validation before accepting quantized "
                "inference results."
            ),
        )

    run_config = result.get("run_config")
    if not isinstance(run_config, dict) or not run_config:
        add_anomaly(
            "missing_run_config",
            "medium",
            "run_config is missing from the structured result.",
            {"run_config": run_config},
            "missing_run_configuration",
            "Record warmup/runs/batch/shape configuration for reproducible validation.",
        )

    system = result.get("system")
    if not isinstance(system, dict) or not system:
        add_anomaly(
            "missing_system_metadata",
            "low",
            "system metadata is missing from the structured result.",
            {"system": system},
            "missing_environment_metadata",
            (
                "Record system metadata such as OS, architecture, device, or "
                "accelerator information."
            ),
        )

    status = _status_from_anomalies(anomalies)
    return {
        "mode": "structured_result_reasoning",
        "status": status,
        "anomalies": anomalies,
        "explanations": explanations,
        "suspected_causes": suspected_causes,
        "confidence": _confidence_for_status(status),
        "recommendations": recommendations,
    }


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data.get(key)
    return None


def _latency_improved(compare_result: dict[str, Any]) -> bool:
    if compare_result.get("overall_judgement") == "improvement":
        return True
    if compare_result.get("mean_judgement") == "improvement":
        return True

    for key in ("latency_delta_pct", "mean_delta_pct"):
        value = compare_result.get(key)
        if isinstance(value, (int, float)) and value < 0:
            return True
    return False


def _accuracy_dropped(compare_result: dict[str, Any]) -> bool:
    accuracy_delta = compare_result.get("accuracy_delta")
    if isinstance(accuracy_delta, (int, float)) and accuracy_delta < 0:
        return True

    base_accuracy = compare_result.get("base_accuracy")
    new_accuracy = _first_present(compare_result, "new_accuracy", "candidate_accuracy")
    if isinstance(base_accuracy, (int, float)) and isinstance(new_accuracy, (int, float)):
        return new_accuracy < base_accuracy
    return False


def _is_cross_precision(compare_result: dict[str, Any]) -> bool:
    if compare_result.get("comparison_mode") == "cross_precision":
        return True

    precision_pair = compare_result.get("precision_pair")
    if precision_pair is None:
        return False
    precision_text = str(precision_pair).lower()
    return "int8" in precision_text or "fp16" in precision_text


def _large_latency_delta(compare_result: dict[str, Any]) -> bool:
    for key in ("latency_delta_pct", "mean_delta_pct"):
        value = compare_result.get(key)
        if isinstance(value, (int, float)) and abs(value) >= 30:
            return True
    return False


def _has_insufficient_precision_speedup(compare_result: dict[str, Any]) -> bool:
    latency_delta_pct = compare_result.get("latency_delta_pct")
    if not isinstance(latency_delta_pct, (int, float)) or isinstance(
        latency_delta_pct, bool
    ):
        return False
    if not _is_cross_precision(compare_result):
        return False
    if _candidate_precision(compare_result) not in {"fp16", "int8"}:
        return False
    return latency_delta_pct > -10.0


def _candidate_precision(compare_result: dict[str, Any]) -> str | None:
    for parent_key in ("candidate", "new"):
        value = compare_result.get(parent_key)
        if isinstance(value, dict):
            precision = value.get("precision")
            if precision is not None:
                return str(precision).lower()

    precision_pair = compare_result.get("precision_pair")
    if precision_pair is None:
        return None

    precision_text = str(precision_pair).lower()
    if "_vs_" in precision_text:
        candidate_precision = precision_text.rsplit("_vs_", 1)[1]
        if candidate_precision in {"fp16", "int8"}:
            return candidate_precision
    if precision_text in {"fp32_vs_fp16", "fp32_vs_int8"}:
        return precision_text.rsplit("_", 1)[1]
    return None


def _latency_evidence(compare_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall_judgement": compare_result.get("overall_judgement"),
        "mean_judgement": compare_result.get("mean_judgement"),
        "latency_delta_pct": compare_result.get("latency_delta_pct"),
        "mean_delta_pct": compare_result.get("mean_delta_pct"),
    }


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


def _as_list(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [value]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_accuracy_value(result: dict[str, Any]) -> bool:
    if "accuracy" in result and result.get("accuracy") is not None:
        return True

    metrics = result.get("metrics")
    if isinstance(metrics, dict) and metrics.get("accuracy") is not None:
        return True

    extra = result.get("extra")
    return isinstance(extra, dict) and extra.get("accuracy") is not None
