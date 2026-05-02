"""BBox and score evidence detectors for diagnosis reports.

These helpers are intentionally tolerant of malformed detection output. The
older single-output schema validator is still useful for strict CLI paths, but
diagnosis needs to explain broken output instead of failing before evidence can
be generated.
"""

from __future__ import annotations

import math
from typing import Any

from .diagnosis import build_diagnosis_report, build_evidence_item, map_severity


DEFAULT_EVIDENCE_THRESHOLDS = {
    "invalid_bbox_rate_review": 0.05,
    "invalid_bbox_rate_blocked": 0.20,
    "bbox_collapse_ratio_review": 0.05,
    "bbox_collapse_ratio_high": 0.10,
    "score_saturation_low_threshold": 0.01,
    "score_saturation_high_threshold": 0.99,
    "saturation_ratio_review": 0.70,
    "saturation_ratio_high": 0.85,
}


def analyze_detection_quality(
    output: dict[str, Any],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnosis report from one detection output JSON-like object."""

    policy = {**DEFAULT_EVIDENCE_THRESHOLDS, **(thresholds or {})}
    bbox_metrics = compute_bbox_validity_metrics(
        output,
        image_width=image_width,
        image_height=image_height,
        collapse_threshold=1e-6,
    )
    score_metrics = compute_score_distribution_metrics(output, thresholds=policy)

    evidence = [
        _bbox_validity_evidence(bbox_metrics, policy),
        _bbox_collapse_evidence(bbox_metrics, policy),
        _score_range_evidence(score_metrics),
        _score_distribution_evidence(score_metrics, policy),
    ]

    return build_diagnosis_report(
        evidence=evidence,
        source=source or {},
        confidence=_confidence_from_metrics(bbox_metrics, score_metrics),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "model": output.get("model"),
            "precision": output.get("precision"),
            "image_id": output.get("image_id"),
            "bbox": bbox_metrics,
            "score": score_metrics,
        },
    )


def analyze_guard_analysis(
    output: dict[str, Any],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Phase 1 bbox/score guard_analysis from one detection output.

    This is a public naming alias for the evidence-based Obsidian contract.
    ``analyze_detection_quality`` remains available for callers that prefer the
    implementation-oriented name.
    """

    return analyze_detection_quality(
        output,
        image_width=image_width,
        image_height=image_height,
        thresholds=thresholds,
        source=source,
    )


def compute_bbox_validity_metrics(
    output: dict[str, Any],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    collapse_threshold: float = 1e-6,
) -> dict[str, Any]:
    """Compute bbox validity metrics without requiring a fully valid schema."""

    detections = _detections(output)
    total = len(detections)
    invalid_count = 0
    zero_area_count = 0
    out_of_bounds_count = 0
    nan_or_inf_count = 0
    collapse_count = 0

    for detection in detections:
        bbox = detection.get("bbox") if isinstance(detection, dict) else None
        values = _bbox_values(bbox)
        if values is None:
            invalid_count += 1
            continue

        x, y, width, height = values
        if any(not math.isfinite(value) for value in values):
            nan_or_inf_count += 1
            invalid_count += 1
            continue

        if width <= 0 or height <= 0:
            invalid_count += 1
            if width == 0 or height == 0:
                zero_area_count += 1

        if abs(width) <= collapse_threshold or abs(height) <= collapse_threshold:
            collapse_count += 1

        if image_width is not None and image_height is not None:
            if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
                out_of_bounds_count += 1

    return {
        "total_predictions": total,
        "invalid_bbox_count": invalid_count,
        "invalid_bbox_rate": _ratio(invalid_count, total),
        "zero_area_count": zero_area_count,
        "out_of_bounds_count": out_of_bounds_count,
        "nan_or_inf_count": nan_or_inf_count,
        "bbox_collapse_count": collapse_count,
        "bbox_collapse_ratio": _ratio(collapse_count, total),
        "boundary_check_enabled": image_width is not None and image_height is not None,
    }


def compute_score_distribution_metrics(
    output: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute score distribution metrics without requiring valid score ranges."""

    policy = {**DEFAULT_EVIDENCE_THRESHOLDS, **(thresholds or {})}
    low_threshold = policy["score_saturation_low_threshold"]
    high_threshold = policy["score_saturation_high_threshold"]
    detections = _detections(output)
    scores: list[float] = []
    score_range_violation_count = 0
    nan_or_inf_count = 0

    for detection in detections:
        value = detection.get("confidence") if isinstance(detection, dict) else None
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            score_range_violation_count += 1
            continue
        score = float(value)
        if not math.isfinite(score):
            nan_or_inf_count += 1
            score_range_violation_count += 1
            continue
        scores.append(score)
        if score < 0.0 or score > 1.0:
            score_range_violation_count += 1

    total = len(detections)
    low_count = sum(1 for score in scores if score <= low_threshold)
    high_count = sum(1 for score in scores if score >= high_threshold)
    saturation_count = low_count + high_count
    mean_score = sum(scores) / len(scores) if scores else None
    std_score = _std(scores, mean_score) if mean_score is not None else None

    return {
        "total_predictions": total,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "mean_score": mean_score,
        "std_score": std_score,
        "low_confidence_ratio": _ratio(low_count, total),
        "high_confidence_ratio": _ratio(high_count, total),
        "saturation_ratio": _ratio(saturation_count, total),
        "score_range_violation_count": score_range_violation_count,
        "score_nan_or_inf_count": nan_or_inf_count,
        "low_threshold": low_threshold,
        "high_threshold": high_threshold,
    }


def _bbox_validity_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    invalid_rate = metrics["invalid_bbox_rate"]
    severity = map_severity(
        metric_name="invalid_bbox_rate",
        observed_value=invalid_rate,
        thresholds=thresholds,
    )
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="bbox_validity",
        metric_name="invalid_bbox_rate",
        observed_value=invalid_rate,
        threshold=thresholds["invalid_bbox_rate_review"],
        severity=severity,
        status=status,
        why_it_matters=(
            "Invalid boxes indicate that detection geometry may be unusable even "
            "when latency looks acceptable."
        ),
        suspected_causes=[
            "Incorrect bbox decoder",
            "Preprocessing/postprocess mismatch",
            "Output tensor layout mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review bbox decoder, output layout, and preprocessing/postprocess settings."
            if status != "passed"
            else "BBox validity is within the configured threshold."
        ),
        raw_context=metrics,
    )


def _bbox_collapse_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    collapse_ratio = metrics["bbox_collapse_ratio"]
    severity = map_severity(
        metric_name="bbox_collapse_ratio",
        observed_value=collapse_ratio,
        thresholds=thresholds,
    )
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="bbox_collapse",
        metric_name="bbox_collapse_ratio",
        observed_value=collapse_ratio,
        threshold=thresholds["bbox_collapse_ratio_review"],
        severity=severity,
        status=status,
        why_it_matters=(
            "Near-zero area boxes can indicate decoder mismatch or quantization "
            "artifacts that make detections unusable."
        ),
        suspected_causes=[
            "Incorrect bbox decoder",
            "INT8 quantization artifact",
            "Preprocessing/postprocess mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Do not deploy until bbox collapse is reviewed."
            if status != "passed"
            else "BBox collapse ratio is within the configured threshold."
        ),
        raw_context=metrics,
    )


def _score_range_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    violation_count = metrics["score_range_violation_count"]
    severity = map_severity(
        metric_name="score_range_violation_count",
        observed_value=float(violation_count),
    )
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="score_range_violation",
        metric_name="score_range_violation_count",
        observed_value=violation_count,
        threshold=0,
        severity=severity,
        status=status,
        why_it_matters=(
            "Scores outside 0..1 or non-finite scores make ranking and thresholding "
            "unreliable."
        ),
        suspected_causes=[
            "Incorrect score decoder",
            "Missing sigmoid or duplicated postprocess",
            "Output tensor layout mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Block deployment until score decoding and score range are fixed."
            if status != "passed"
            else "Score range is valid."
        ),
        raw_context=metrics,
    )


def _score_distribution_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    saturation_ratio = metrics["saturation_ratio"]
    severity = map_severity(
        metric_name="saturation_ratio",
        observed_value=saturation_ratio,
        thresholds=thresholds,
    )
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="confidence_saturation",
        metric_name="saturation_ratio",
        observed_value=saturation_ratio,
        threshold=thresholds["saturation_ratio_review"],
        severity=severity,
        status=status,
        why_it_matters=(
            "Confidence saturation can hide ranking quality problems and may indicate "
            "quantization or postprocess mistakes."
        ),
        suspected_causes=[
            "Quantization artifact",
            "Duplicated sigmoid/postprocess",
            "Incorrect score decoder",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review score decoder, sigmoid application, and quantization calibration."
            if status != "passed"
            else "Confidence distribution is within the configured threshold."
        ),
        raw_context=metrics,
    )


def _primary_reason(evidence: list[dict[str, Any]]) -> str:
    failed = [item for item in evidence if item["status"] == "failed"]
    if failed:
        return f"{failed[0]['metric_name']} exceeded the configured diagnosis threshold."
    warnings = [item for item in evidence if item["status"] == "warning"]
    if warnings:
        return f"{warnings[0]['metric_name']} should be reviewed before deployment."
    return "BBox and score structural evidence is within configured thresholds."


def _confidence_from_metrics(
    bbox_metrics: dict[str, Any],
    score_metrics: dict[str, Any],
) -> float:
    total = max(bbox_metrics["total_predictions"], score_metrics["total_predictions"])
    if total == 0:
        return 0.5
    return 0.9


def _detections(output: dict[str, Any]) -> list[Any]:
    detections = output.get("detections", [])
    return detections if isinstance(detections, list) else []


def _bbox_values(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    if any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in value):
        return None
    return tuple(float(item) for item in value)  # type: ignore[return-value]


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return count / total


def _std(values: list[float], mean: float) -> float:
    if not values:
        return 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _status_from_severity(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "failed"
    if severity == "medium":
        return "warning"
    return "passed"
