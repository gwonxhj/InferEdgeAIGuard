"""Comparison utilities for FP32 baseline and candidate inference outputs."""

from __future__ import annotations

from typing import Any

from .detectors import (
    detect_bbox_collapse,
    detect_confidence_saturation,
    summary_metadata,
)
from .schema import validate_output


def compare_outputs(
    base: dict[str, Any],
    candidate: dict[str, Any],
    count_mismatch_ratio_threshold: float = 0.5,
) -> dict[str, Any]:
    """Compare a baseline output with a candidate output and summarize failures."""

    validate_output(base)
    validate_output(candidate)

    base_count = len(base["detections"])
    candidate_count = len(candidate["detections"])
    failures: list[dict[str, Any]] = []

    count_failure = _detect_count_mismatch(
        base_count, candidate_count, count_mismatch_ratio_threshold
    )
    if count_failure is not None:
        failures.append(count_failure)

    for failure in (
        detect_bbox_collapse(candidate),
        detect_confidence_saturation(candidate),
    ):
        if failure is not None:
            failures.append(failure)

    return {
        **summary_metadata(),
        "has_failure": bool(failures),
        "failures": failures,
        "base_count": base_count,
        "candidate_count": candidate_count,
    }


def _detect_count_mismatch(
    base_count: int,
    candidate_count: int,
    threshold: float,
) -> dict[str, Any] | None:
    if base_count == 0:
        if candidate_count == 0:
            return None
        mismatch_ratio = 1.0
    else:
        mismatch_ratio = abs(base_count - candidate_count) / base_count

    if mismatch_ratio < threshold:
        return None

    severity = "high" if mismatch_ratio >= 0.8 else "medium"

    return {
        "failure_type": "detection_count_mismatch",
        "severity": severity,
        "message": (
            f"Detection count changed from {base_count} to {candidate_count} "
            f"(mismatch ratio {mismatch_ratio:.2f}, threshold {threshold:.2f})."
        ),
        "affected_count": abs(base_count - candidate_count),
        "base_count": base_count,
        "candidate_count": candidate_count,
        "mismatch_ratio": mismatch_ratio,
        "threshold": threshold,
    }
