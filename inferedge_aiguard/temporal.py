"""Temporal consistency evidence for frame sequence diagnosis.

Phase 3 intentionally avoids a tracking dependency. It computes aggregate
frame-to-frame signals from a small frame sequence contract and turns them into
diagnosis evidence that Lab can consume as optional guard_analysis.
"""

from __future__ import annotations

import math
from typing import Any

from .diagnosis import build_diagnosis_report, build_evidence_item


DEFAULT_TEMPORAL_THRESHOLDS = {
    "detection_count_cv_review": 1.0,
    "zero_detection_frame_ratio_blocked": 0.30,
    "zero_detection_streak_review": 2,
    "zero_detection_streak_blocked": 3,
    "bbox_center_jump_p95_review": 0.50,
    "class_flip_rate_review": 0.30,
}


def analyze_temporal_consistency(
    sequence: dict[str, Any],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build guard_analysis for tracking-less temporal consistency evidence.

    Expected minimal input:

    ``{"frames": [{"frame_id": "0", "timestamp_ms": 0, "detections": [...]}]}``
    """

    policy = {**DEFAULT_TEMPORAL_THRESHOLDS, **(thresholds or {})}
    metrics = compute_temporal_consistency_metrics(
        sequence,
        image_width=image_width,
        image_height=image_height,
    )
    evidence = [
        _detection_count_cv_evidence(metrics, policy),
        _zero_detection_frame_evidence(metrics, policy),
        _sequence_disappearance_evidence(metrics, policy),
        _bbox_center_jump_evidence(metrics, policy),
        _class_flip_evidence(metrics, policy),
    ]
    return build_diagnosis_report(
        evidence=evidence,
        source=source or {},
        guard_verdict=_temporal_verdict(evidence),
        confidence=_confidence_from_metrics(metrics),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "sequence_id": sequence.get("sequence_id"),
            "frame_count": metrics["frame_count"],
            "temporal": metrics,
        },
    )


def compute_temporal_consistency_metrics(
    sequence: dict[str, Any],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
) -> dict[str, Any]:
    """Compute tracking-less temporal metrics from a frame sequence."""

    frames = _frames(sequence)
    counts = [len(_detections(frame)) for frame in frames]
    frame_count = len(frames)
    zero_count = sum(1 for count in counts if count == 0)
    disappearance = _zero_detection_streak_metrics(frames, counts)
    mean_count = _mean(counts)
    std_count = _std(counts, mean_count)
    count_cv = std_count / mean_count if mean_count > 0 else 0.0

    centers = [_frame_center(_detections(frame)) for frame in frames]
    jumps = _center_jumps(centers, image_width=image_width, image_height=image_height)
    dominant_classes = [_dominant_class(_detections(frame)) for frame in frames]
    class_flip_rate = _class_flip_rate(dominant_classes)

    return {
        "frame_count": frame_count,
        "detection_counts": counts,
        "mean_detection_count": mean_count,
        "std_detection_count": std_count,
        "frame_to_frame_detection_count_cv": count_cv,
        "zero_detection_frame_count": zero_count,
        "zero_detection_frame_ratio": _ratio(zero_count, frame_count),
        "zero_detection_streak_count": disappearance["streak_count"],
        "max_zero_detection_streak": disappearance["max_streak"],
        "first_zero_detection_frame_id": disappearance["first_frame_id"],
        "first_zero_detection_frame_index": disappearance["first_frame_index"],
        "zero_detection_streaks": disappearance["streaks"],
        "bbox_center_jump_mean": _mean(jumps),
        "bbox_center_jump_p95": _percentile(jumps, 0.95),
        "bbox_center_jump_unit": (
            "image_diagonal_ratio"
            if image_width is not None and image_height is not None
            else "pixels"
        ),
        "class_flip_rate": class_flip_rate,
        "dominant_classes": dominant_classes,
    }


def _detection_count_cv_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    observed = metrics["frame_to_frame_detection_count_cv"]
    threshold = thresholds["detection_count_cv_review"]
    severity = "medium" if observed > threshold else "low"
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="temporal_consistency",
        metric_name="frame_to_frame_detection_count_cv",
        observed_value=observed,
        threshold=threshold,
        severity=severity,
        status=status,
        explanation=(
            f"Frame-to-frame detection count CV is {_fmt(observed)}. "
            f"Review threshold is {_fmt(threshold)}."
        ),
        why_it_matters=(
            "Large detection count variance can indicate unstable output across "
            "adjacent frames in the same scene."
        ),
        suspected_causes=[
            "Temporal instability",
            "Preprocessing/postprocess mismatch",
            "Confidence threshold instability",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review frame sequence output before deployment."
            if status != "passed"
            else "Detection count variance is within threshold."
        ),
        raw_context=metrics,
    )


def _zero_detection_frame_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    observed = metrics["zero_detection_frame_ratio"]
    threshold = thresholds["zero_detection_frame_ratio_blocked"]
    severity = "high" if observed > threshold else "low"
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="temporal_consistency",
        metric_name="zero_detection_frame_ratio",
        observed_value=observed,
        threshold=threshold,
        severity=severity,
        status=status,
        explanation=(
            f"Zero-detection frame ratio is {_fmt(observed)}. "
            f"Blocked threshold is {_fmt(threshold)}."
        ),
        why_it_matters=(
            "Frequent zero-detection frames can mean objects disappear across a "
            "sequence even when individual frames appear valid."
        ),
        suspected_causes=[
            "Detection disappearance",
            "Confidence threshold mismatch",
            "Quantization artifact",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Block or review deployment until zero-detection frames are explained."
            if status != "passed"
            else "Zero-detection frame ratio is within threshold."
        ),
        raw_context=metrics,
    )


def _sequence_disappearance_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    observed = metrics["max_zero_detection_streak"]
    review_threshold = thresholds["zero_detection_streak_review"]
    blocked_threshold = thresholds["zero_detection_streak_blocked"]
    if observed >= blocked_threshold:
        severity = "high"
        threshold = blocked_threshold
    elif observed >= review_threshold:
        severity = "medium"
        threshold = review_threshold
    else:
        severity = "low"
        threshold = review_threshold
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="sequence_disappearance",
        metric_name="max_zero_detection_streak",
        observed_value=observed,
        threshold=threshold,
        severity=severity,
        status=status,
        explanation=(
            f"Max zero-detection frame streak is {_fmt(observed)}. "
            f"Review threshold is {_fmt(review_threshold)} and blocked "
            f"threshold is {_fmt(blocked_threshold)}."
        ),
        why_it_matters=(
            "A repeated zero-detection streak is stronger disappearance evidence "
            "than an isolated empty frame because it shows objects vanished across "
            "adjacent frames."
        ),
        suspected_causes=[
            "Sequence-level detection disappearance",
            "Confidence threshold instability",
            "Temporal preprocessing mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Inspect first_zero_detection_frame_id, zero_detection_streaks, and "
            "input sequence continuity before deployment."
            if status != "passed"
            else "No repeated zero-detection streak exceeded review thresholds."
        ),
        raw_context=metrics,
    )


def _bbox_center_jump_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    observed = metrics["bbox_center_jump_p95"]
    threshold = thresholds["bbox_center_jump_p95_review"]
    severity = "medium" if observed > threshold else "low"
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="temporal_consistency",
        metric_name="bbox_center_jump_p95",
        observed_value=observed,
        threshold=threshold,
        severity=severity,
        status=status,
        explanation=(
            f"BBox center jump p95 is {_fmt(observed)} "
            f"({metrics['bbox_center_jump_unit']}). Review threshold is "
            f"{_fmt(threshold)}."
        ),
        why_it_matters=(
            "Large bbox center jumps across adjacent frames can indicate unstable "
            "geometry without requiring a full tracker."
        ),
        suspected_causes=[
            "Temporal instability",
            "BBox decoder instability",
            "Preprocessing mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Inspect adjacent-frame bbox geometry before deployment."
            if status != "passed"
            else "BBox center jumps are within threshold."
        ),
        raw_context=metrics,
    )


def _class_flip_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    observed = metrics["class_flip_rate"]
    threshold = thresholds["class_flip_rate_review"]
    severity = "medium" if observed > threshold else "low"
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="temporal_consistency",
        metric_name="class_flip_rate",
        observed_value=observed,
        threshold=threshold,
        severity=severity,
        status=status,
        explanation=(
            f"Dominant class flip rate is {_fmt(observed)}. "
            f"Review threshold is {_fmt(threshold)}."
        ),
        why_it_matters=(
            "Frequent dominant class changes in adjacent non-empty frames can "
            "indicate unstable classification in a detection sequence."
        ),
        suspected_causes=[
            "Class prediction instability",
            "Postprocess mismatch",
            "Low confidence margin",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review class stability on the frame sequence."
            if status != "passed"
            else "Dominant class stability is within threshold."
        ),
        raw_context=metrics,
    )


def _frames(sequence: dict[str, Any]) -> list[dict[str, Any]]:
    frames = sequence.get("frames", [])
    if not isinstance(frames, list):
        return []
    return [frame for frame in frames if isinstance(frame, dict)]


def _detections(frame: dict[str, Any]) -> list[dict[str, Any]]:
    detections = frame.get("detections", [])
    return (
        [detection for detection in detections if isinstance(detection, dict)]
        if isinstance(detections, list)
        else []
    )


def _zero_detection_streak_metrics(
    frames: list[dict[str, Any]],
    counts: list[int],
) -> dict[str, Any]:
    streaks: list[dict[str, Any]] = []
    current_start: int | None = None
    current_length = 0

    for index, count in enumerate(counts):
        if count == 0:
            if current_start is None:
                current_start = index
            current_length += 1
            continue
        if current_start is not None:
            streaks.append(
                _zero_detection_streak(
                    frames,
                    start_index=current_start,
                    length=current_length,
                )
            )
            current_start = None
            current_length = 0

    if current_start is not None:
        streaks.append(
            _zero_detection_streak(
                frames,
                start_index=current_start,
                length=current_length,
            )
        )

    max_streak = max((streak["length"] for streak in streaks), default=0)
    first = streaks[0] if streaks else {}
    return {
        "streak_count": len(streaks),
        "max_streak": max_streak,
        "first_frame_id": first.get("start_frame_id"),
        "first_frame_index": first.get("start_index"),
        "streaks": streaks,
    }


def _zero_detection_streak(
    frames: list[dict[str, Any]],
    *,
    start_index: int,
    length: int,
) -> dict[str, Any]:
    end_index = start_index + length - 1
    return {
        "start_index": start_index,
        "end_index": end_index,
        "length": length,
        "start_frame_id": frames[start_index].get("frame_id"),
        "end_frame_id": frames[end_index].get("frame_id"),
    }


def _frame_center(detections: list[dict[str, Any]]) -> tuple[float, float] | None:
    centers: list[tuple[float, float]] = []
    for detection in detections:
        bbox = detection.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        invalid_bbox_value = any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            for value in bbox
        )
        if invalid_bbox_value:
            continue
        x, y, width, height = [float(value) for value in bbox]
        if not all(math.isfinite(value) for value in (x, y, width, height)):
            continue
        centers.append((x + width / 2.0, y + height / 2.0))
    if not centers:
        return None
    return (
        sum(center[0] for center in centers) / len(centers),
        sum(center[1] for center in centers) / len(centers),
    )


def _center_jumps(
    centers: list[tuple[float, float] | None],
    *,
    image_width: float | None,
    image_height: float | None,
) -> list[float]:
    jumps: list[float] = []
    diagonal = None
    if image_width is not None and image_height is not None:
        diagonal = math.hypot(image_width, image_height)
    previous: tuple[float, float] | None = None
    for center in centers:
        if center is None:
            previous = None
            continue
        if previous is not None:
            distance = math.hypot(center[0] - previous[0], center[1] - previous[1])
            jumps.append(distance / diagonal if diagonal else distance)
        previous = center
    return jumps


def _dominant_class(detections: list[dict[str, Any]]) -> int | None:
    counts: dict[int, int] = {}
    for detection in detections:
        class_id = detection.get("class_id")
        if isinstance(class_id, int) and not isinstance(class_id, bool):
            counts[class_id] = counts.get(class_id, 0) + 1
    if not counts:
        return None
    return max(sorted(counts), key=lambda class_id: counts[class_id])


def _class_flip_rate(classes: list[int | None]) -> float:
    pairs = 0
    flips = 0
    previous: int | None = None
    for class_id in classes:
        if class_id is None:
            previous = None
            continue
        if previous is not None:
            pairs += 1
            if class_id != previous:
                flips += 1
        previous = class_id
    return _ratio(flips, pairs)


def _primary_reason(evidence: list[dict[str, Any]]) -> str:
    failed = [item for item in evidence if item["status"] == "failed"]
    if failed:
        return "Temporal consistency evidence indicates deployment risk."
    warnings = [item for item in evidence if item["status"] == "warning"]
    if warnings:
        return "Temporal consistency should be reviewed before deployment."
    return "Temporal consistency evidence is within configured thresholds."


def _temporal_verdict(evidence: list[dict[str, Any]]) -> str:
    failed = [item for item in evidence if item["status"] == "failed"]
    if failed:
        return "blocked"
    warnings = [item for item in evidence if item["status"] == "warning"]
    if warnings:
        return "review_required"
    return "pass"


def _confidence_from_metrics(metrics: dict[str, Any]) -> float:
    return 0.5 if metrics["frame_count"] < 2 else 0.88


def _status_from_severity(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "failed"
    if severity == "medium":
        return "warning"
    return "passed"


def _mean(values: list[float] | list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[int], mean: float) -> float:
    if not values:
        return 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, math.ceil(percentile * len(sorted_values)) - 1)
    return sorted_values[index]


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return count / total


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)
