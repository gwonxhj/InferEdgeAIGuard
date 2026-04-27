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
