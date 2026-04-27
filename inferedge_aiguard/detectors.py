"""Failure detectors for a single inference output."""

from __future__ import annotations

from typing import Any

from .schema import validate_output


Failure = dict[str, Any]
Summary = dict[str, Any]


def detect_bbox_collapse(output: dict[str, Any], threshold: float = 1e-6) -> Failure | None:
    """Detect boxes whose width or height has collapsed near zero."""

    validate_output(output)
    total_count = len(output["detections"])
    if total_count == 0:
        return None

    affected_count = 0

    for detection in output["detections"]:
        _, _, width, height = detection["bbox"]
        if abs(float(width)) <= threshold or abs(float(height)) <= threshold:
            affected_count += 1

    if affected_count == 0:
        return None

    collapse_ratio = affected_count / total_count
    if collapse_ratio >= 0.5:
        severity = "high"
    elif collapse_ratio >= 0.1:
        severity = "medium"
    else:
        severity = "low"

    return {
        "failure_type": "bbox_collapse",
        "severity": severity,
        "message": (
            f"{affected_count}/{total_count} detection bbox width/height values are "
            f"at or below collapse threshold {threshold}."
        ),
        "affected_count": affected_count,
        "total_count": total_count,
        "collapse_ratio": collapse_ratio,
        "threshold": threshold,
    }


def detect_confidence_saturation(
    output: dict[str, Any],
    low_threshold: float = 0.01,
    high_threshold: float = 0.99,
    ratio_threshold: float = 0.8,
) -> Failure | None:
    """Detect excessive confidence mass near 0.0 or 1.0."""

    validate_output(output)
    detections = output["detections"]
    total_count = len(detections)
    if total_count == 0:
        return None

    saturated_count = sum(
        1
        for detection in detections
        if float(detection["confidence"]) <= low_threshold
        or float(detection["confidence"]) >= high_threshold
    )
    saturation_ratio = saturated_count / total_count

    if saturation_ratio < ratio_threshold:
        return None

    severity = "high" if saturation_ratio >= 0.95 else "medium"

    return {
        "failure_type": "confidence_saturation",
        "severity": severity,
        "message": (
            f"{saturated_count}/{total_count} detection confidence values are "
            f"near {low_threshold} or {high_threshold}."
        ),
        "affected_count": saturated_count,
        "total_count": total_count,
        "saturation_ratio": saturation_ratio,
        "low_threshold": low_threshold,
        "high_threshold": high_threshold,
        "ratio_threshold": ratio_threshold,
    }


def summarize_failures(output: dict[str, Any]) -> Summary:
    """Run all single-output detectors and return a compact summary."""

    validate_output(output)
    failures = [
        failure
        for failure in (
            detect_bbox_collapse(output),
            detect_confidence_saturation(output),
        )
        if failure is not None
    ]

    return {
        "has_failure": bool(failures),
        "failures": failures,
        "detection_count": len(output["detections"]),
        "model": output["model"],
        "precision": output["precision"],
        "image_id": output["image_id"],
    }
