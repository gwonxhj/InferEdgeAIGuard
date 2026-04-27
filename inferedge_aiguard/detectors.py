"""Failure detectors for a single inference output."""

from __future__ import annotations

from typing import Any

from .schema import validate_output


Failure = dict[str, Any]
Summary = dict[str, Any]


def detect_bbox_collapse(output: dict[str, Any], threshold: float = 1e-6) -> Failure | None:
    """Detect boxes whose width or height has collapsed near zero."""

    validate_output(output)
    affected_count = 0

    for detection in output["detections"]:
        _, _, width, height = detection["bbox"]
        if abs(float(width)) <= threshold or abs(float(height)) <= threshold:
            affected_count += 1

    if affected_count == 0:
        return None

    return {
        "failure_type": "bbox_collapse",
        "severity": "high",
        "message": (
            f"{affected_count} detection(s) have bbox width/height at or below "
            f"collapse threshold {threshold}."
        ),
        "affected_count": affected_count,
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
    if not detections:
        return None

    saturated_count = sum(
        1
        for detection in detections
        if float(detection["confidence"]) <= low_threshold
        or float(detection["confidence"]) >= high_threshold
    )
    ratio = saturated_count / len(detections)

    if ratio < ratio_threshold:
        return None

    return {
        "failure_type": "confidence_saturation",
        "severity": "medium",
        "message": (
            f"{saturated_count}/{len(detections)} detection confidence values are "
            f"near {low_threshold} or {high_threshold}."
        ),
        "affected_count": saturated_count,
        "saturation_ratio": ratio,
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
