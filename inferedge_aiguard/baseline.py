"""Baseline comparison evidence for AIGuard diagnosis reports.

Phase 2 compares a known-good baseline output with a candidate output and
explains measurable drift. It intentionally reuses the single-output bbox/score
detectors so the report remains compatible with the v1 diagnosis contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .diagnosis import build_diagnosis_report, build_evidence_item, combine_severity
from .evidence_detectors import (
    DEFAULT_EVIDENCE_THRESHOLDS,
    compute_bbox_validity_metrics,
    compute_score_distribution_metrics,
)


BASELINE_PROFILE_SCHEMA_VERSION = "inferedge-aiguard-baseline-profile-v1"

DEFAULT_BASELINE_THRESHOLDS = {
    **DEFAULT_EVIDENCE_THRESHOLDS,
    "invalid_bbox_rate_factor_review": 5.0,
    "invalid_bbox_rate_factor_blocked": 10.0,
    "bbox_collapse_ratio_factor_review": 5.0,
    "bbox_collapse_ratio_factor_blocked": 10.0,
    "score_saturation_factor_review": 5.0,
    "score_saturation_factor_blocked": 10.0,
    "detection_count_drop_pct_review": 0.50,
    "detection_count_drop_pct_blocked": 0.80,
    "detection_disappearance_blocked": 1.0,
    "per_class_detection_drop_pct_review": 0.50,
    "per_class_detection_drop_pct_blocked": 1.0,
    "per_class_drift_min_baseline_count": 1.0,
    "calibration_histogram_distance_review": 0.30,
    "calibration_mean_score_delta_review": 0.20,
    "calibration_std_score_delta_review": 0.20,
    "calibration_std_score_floor_review": 0.05,
    "calibration_saturation_delta_review": 0.30,
}

SCORE_HISTOGRAM_BINS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def build_baseline_profile(
    baseline_output: dict[str, Any],
    *,
    label: str = "baseline",
    latency_ms: float | None = None,
    accuracy: float | None = None,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable known-good baseline profile.

    The profile is the explicit Phase 2 handoff artifact: it captures bbox and
    score quality metrics once, then candidate outputs can be compared against
    it without re-running the baseline detector path.
    """

    policy = {**DEFAULT_BASELINE_THRESHOLDS, **(thresholds or {})}
    bbox_metrics = compute_bbox_validity_metrics(
        baseline_output,
        image_width=image_width,
        image_height=image_height,
    )
    score_metrics = _score_metrics_with_histogram(baseline_output, policy)
    class_distribution = compute_class_distribution_metrics(baseline_output)
    return {
        "schema_version": BASELINE_PROFILE_SCHEMA_VERSION,
        "label": label,
        "source": dict(source or {}),
        "model": baseline_output.get("model"),
        "precision": baseline_output.get("precision"),
        "image_id": baseline_output.get("image_id"),
        "bbox": bbox_metrics,
        "score": score_metrics,
        "class_distribution": class_distribution,
        "latency_ms": latency_ms,
        "accuracy": accuracy,
        "thresholds": policy,
        "created_at": created_at or _utc_now(),
    }


def compare_detection_quality(
    baseline_output: dict[str, Any],
    candidate_output: dict[str, Any],
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
    baseline_latency_ms: float | None = None,
    candidate_latency_ms: float | None = None,
    baseline_accuracy: float | None = None,
    candidate_accuracy: float | None = None,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnosis report comparing baseline and candidate output quality."""

    policy = {**DEFAULT_BASELINE_THRESHOLDS, **(thresholds or {})}
    metrics = compute_baseline_comparison_metrics(
        baseline_output,
        candidate_output,
        baseline_latency_ms=baseline_latency_ms,
        candidate_latency_ms=candidate_latency_ms,
        baseline_accuracy=baseline_accuracy,
        candidate_accuracy=candidate_accuracy,
        image_width=image_width,
        image_height=image_height,
        thresholds=policy,
    )
    baseline_summary = {
        "label": baseline_label,
        "model": baseline_output.get("model"),
        "precision": baseline_output.get("precision"),
        "bbox": metrics["baseline"]["bbox"],
        "score": metrics["baseline"]["score"],
        "class_distribution": metrics["baseline"]["class_distribution"],
        "latency_ms": baseline_latency_ms,
        "accuracy": baseline_accuracy,
    }
    candidate_summary = {
        "label": candidate_label,
        "model": candidate_output.get("model"),
        "precision": candidate_output.get("precision"),
        "bbox": metrics["candidate"]["bbox"],
        "score": metrics["candidate"]["score"],
        "class_distribution": metrics["candidate"]["class_distribution"],
        "latency_ms": candidate_latency_ms,
        "accuracy": candidate_accuracy,
        "comparison": metrics["comparison"],
    }
    return _build_comparison_report(
        metrics=metrics,
        policy=policy,
        source=source,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )


def compare_guard_analysis(
    baseline_profile: dict[str, Any],
    candidate_output: dict[str, Any],
    *,
    candidate_label: str = "candidate",
    candidate_latency_ms: float | None = None,
    candidate_accuracy: float | None = None,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare a candidate output against a saved Phase 2 baseline profile."""

    _validate_baseline_profile_shape(baseline_profile)
    policy = {
        **DEFAULT_BASELINE_THRESHOLDS,
        **baseline_profile.get("thresholds", {}),
        **(thresholds or {}),
    }
    metrics = compute_candidate_against_baseline_profile(
        baseline_profile,
        candidate_output,
        candidate_latency_ms=candidate_latency_ms,
        candidate_accuracy=candidate_accuracy,
        image_width=image_width,
        image_height=image_height,
        thresholds=policy,
    )
    merged_source = {
        **dict(baseline_profile.get("source", {})),
        **dict(source or {}),
    }
    baseline_summary = {
        "label": baseline_profile.get("label", "baseline"),
        "model": baseline_profile.get("model"),
        "precision": baseline_profile.get("precision"),
        "bbox": metrics["baseline"]["bbox"],
        "score": metrics["baseline"]["score"],
        "class_distribution": metrics["baseline"].get("class_distribution", {}),
        "latency_ms": metrics["baseline"].get("latency_ms"),
        "accuracy": metrics["baseline"].get("accuracy"),
        "profile_schema_version": baseline_profile.get("schema_version"),
    }
    candidate_summary = {
        "label": candidate_label,
        "model": candidate_output.get("model"),
        "precision": candidate_output.get("precision"),
        "bbox": metrics["candidate"]["bbox"],
        "score": metrics["candidate"]["score"],
        "class_distribution": metrics["candidate"]["class_distribution"],
        "latency_ms": candidate_latency_ms,
        "accuracy": candidate_accuracy,
        "comparison": metrics["comparison"],
    }
    return _build_comparison_report(
        metrics=metrics,
        policy=policy,
        source=merged_source,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )


def compute_class_distribution_metrics(output: dict[str, Any]) -> dict[str, Any]:
    """Compute per-class detection counts using JSON-stable class IDs."""

    class_counts: dict[str, int] = {}
    for detection in output.get("detections", []):
        if not isinstance(detection, dict):
            continue
        class_id = detection.get("class_id")
        if not isinstance(class_id, int) or isinstance(class_id, bool):
            continue
        key = str(class_id)
        class_counts[key] = class_counts.get(key, 0) + 1

    return {
        "class_counts": dict(sorted(class_counts.items(), key=_class_count_sort_key)),
        "class_count": len(class_counts),
        "total_predictions": sum(class_counts.values()),
    }


def compute_score_histogram_metrics(
    output: dict[str, Any],
    *,
    bins: list[float] | None = None,
) -> dict[str, Any]:
    """Compute a fixed-bin score histogram for calibration drift evidence."""

    histogram_bins = list(bins or SCORE_HISTOGRAM_BINS)
    if len(histogram_bins) < 2:
        raise ValueError("score histogram bins must contain at least two edges")
    if histogram_bins != sorted(histogram_bins):
        raise ValueError("score histogram bins must be sorted")

    counts = [0 for _ in range(len(histogram_bins) - 1)]
    for detection in _detections(output):
        value = detection.get("confidence") if isinstance(detection, dict) else None
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        score = float(value)
        if score < histogram_bins[0] or score > histogram_bins[-1]:
            continue
        for index in range(len(histogram_bins) - 1):
            lower = histogram_bins[index]
            upper = histogram_bins[index + 1]
            is_last = index == len(histogram_bins) - 2
            if lower <= score < upper or (is_last and score == upper):
                counts[index] += 1
                break

    total = sum(counts)
    return {
        "bins": histogram_bins,
        "counts": counts,
        "ratios": [_ratio_float(count, total) for count in counts],
        "total_scores": total,
    }


def _build_comparison_report(
    *,
    metrics: dict[str, Any],
    policy: dict[str, float],
    source: dict[str, Any] | None,
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    evidence = [
        _factor_evidence(
            evidence_type="baseline_deviation",
            metric_name="invalid_bbox_rate_factor",
            candidate_metric_name="invalid_bbox_rate",
            baseline_value=metrics["baseline"]["bbox"]["invalid_bbox_rate"],
            candidate_value=metrics["candidate"]["bbox"]["invalid_bbox_rate"],
            factor=metrics["comparison"]["invalid_bbox_rate_factor"],
            review_threshold=policy["invalid_bbox_rate_factor_review"],
            blocked_threshold=policy["invalid_bbox_rate_factor_blocked"],
            candidate_floor=policy["invalid_bbox_rate_review"],
            why_it_matters=(
                "A candidate with a much higher invalid bbox rate than the baseline "
                "may have unusable detection geometry even if it runs faster."
            ),
            suspected_causes=[
                "Incorrect bbox decoder",
                "Output tensor layout mismatch",
                "Preprocessing/postprocess mismatch",
            ],
            recommendation="Review decoder, output layout, and postprocess settings.",
            raw_context=metrics["comparison"],
        ),
        _factor_evidence(
            evidence_type="baseline_deviation",
            metric_name="bbox_collapse_ratio_factor",
            candidate_metric_name="bbox_collapse_ratio",
            baseline_value=metrics["baseline"]["bbox"]["bbox_collapse_ratio"],
            candidate_value=metrics["candidate"]["bbox"]["bbox_collapse_ratio"],
            factor=metrics["comparison"]["bbox_collapse_ratio_factor"],
            review_threshold=policy["bbox_collapse_ratio_factor_review"],
            blocked_threshold=policy["bbox_collapse_ratio_factor_blocked"],
            candidate_floor=policy["bbox_collapse_ratio_review"],
            why_it_matters=(
                "Near-zero boxes increasing over baseline can indicate decoder or "
                "quantization problems that make detections unreliable."
            ),
            suspected_causes=[
                "INT8 quantization artifact",
                "Incorrect bbox decoder",
                "Preprocessing/postprocess mismatch",
            ],
            recommendation="Do not deploy until bbox collapse drift is reviewed.",
            raw_context=metrics["comparison"],
        ),
        _factor_evidence(
            evidence_type="baseline_deviation",
            metric_name="score_saturation_factor",
            candidate_metric_name="saturation_ratio",
            baseline_value=metrics["baseline"]["score"]["saturation_ratio"],
            candidate_value=metrics["candidate"]["score"]["saturation_ratio"],
            factor=metrics["comparison"]["score_saturation_factor"],
            review_threshold=policy["score_saturation_factor_review"],
            blocked_threshold=policy["score_saturation_factor_blocked"],
            candidate_floor=policy["saturation_ratio_review"],
            why_it_matters=(
                "Score saturation drift can hide ranking failures and may indicate "
                "quantization or score decoder mistakes."
            ),
            suspected_causes=[
                "Quantization artifact",
                "Duplicated sigmoid/postprocess",
                "Incorrect score decoder",
            ],
            recommendation="Review score decoder and quantization calibration.",
            raw_context=metrics["comparison"],
        ),
        _detection_count_drift_evidence(metrics, policy),
        _detection_disappearance_evidence(metrics, policy),
        _per_class_detection_drift_evidence(metrics, policy),
        _calibration_drift_evidence(metrics, policy),
    ]

    latency_item = _latency_quality_tradeoff_evidence(metrics, evidence)
    if latency_item is not None:
        evidence.append(latency_item)

    return build_diagnosis_report(
        evidence=evidence,
        source=source or {},
        confidence=_comparison_confidence(metrics),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )


def compute_baseline_comparison_metrics(
    baseline_output: dict[str, Any],
    candidate_output: dict[str, Any],
    *,
    baseline_latency_ms: float | None = None,
    candidate_latency_ms: float | None = None,
    baseline_accuracy: float | None = None,
    candidate_accuracy: float | None = None,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute baseline/candidate drift metrics without assigning a verdict."""

    policy = {**DEFAULT_BASELINE_THRESHOLDS, **(thresholds or {})}
    baseline_bbox = compute_bbox_validity_metrics(
        baseline_output,
        image_width=image_width,
        image_height=image_height,
    )
    candidate_bbox = compute_bbox_validity_metrics(
        candidate_output,
        image_width=image_width,
        image_height=image_height,
    )
    baseline_score = _score_metrics_with_histogram(baseline_output, policy)
    candidate_score = _score_metrics_with_histogram(candidate_output, policy)
    baseline_class_distribution = compute_class_distribution_metrics(baseline_output)
    candidate_class_distribution = compute_class_distribution_metrics(candidate_output)

    baseline_count = baseline_bbox["total_predictions"]
    candidate_count = candidate_bbox["total_predictions"]
    detection_delta = candidate_count - baseline_count
    signed_delta_pct = _ratio_float(detection_delta, baseline_count)
    detection_drop_pct = _ratio_float(baseline_count - candidate_count, baseline_count)

    comparison = {
        "baseline_detection_count": baseline_count,
        "candidate_detection_count": candidate_count,
        "detection_count_delta": detection_delta,
        "detection_count_delta_pct": signed_delta_pct,
        "detection_count_drop_pct": max(0.0, detection_drop_pct),
        "detection_disappeared": _detection_disappeared(
            baseline_count=baseline_count,
            candidate_count=candidate_count,
        ),
        "invalid_bbox_rate_factor": _factor(
            candidate_bbox["invalid_bbox_rate"],
            baseline_bbox["invalid_bbox_rate"],
        ),
        "bbox_collapse_ratio_factor": _factor(
            candidate_bbox["bbox_collapse_ratio"],
            baseline_bbox["bbox_collapse_ratio"],
        ),
        "score_saturation_factor": _factor(
            candidate_score["saturation_ratio"],
            baseline_score["saturation_ratio"],
        ),
        "latency_delta_pct": _optional_delta_pct(
            candidate_latency_ms,
            baseline_latency_ms,
        ),
        "accuracy_delta_pp": _optional_delta(candidate_accuracy, baseline_accuracy),
        "per_class_detection_drift": _per_class_detection_drift_metrics(
            baseline_class_distribution=baseline_class_distribution,
            candidate_class_distribution=candidate_class_distribution,
            thresholds=policy,
        ),
        "calibration_drift": _calibration_drift_metrics(
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            thresholds=policy,
        ),
    }

    return {
        "baseline": {
            "bbox": baseline_bbox,
            "score": baseline_score,
            "class_distribution": baseline_class_distribution,
            "latency_ms": baseline_latency_ms,
            "accuracy": baseline_accuracy,
        },
        "candidate": {
            "bbox": candidate_bbox,
            "score": candidate_score,
            "class_distribution": candidate_class_distribution,
            "latency_ms": candidate_latency_ms,
            "accuracy": candidate_accuracy,
        },
        "comparison": comparison,
    }


def compute_candidate_against_baseline_profile(
    baseline_profile: dict[str, Any],
    candidate_output: dict[str, Any],
    *,
    candidate_latency_ms: float | None = None,
    candidate_accuracy: float | None = None,
    image_width: float | None = None,
    image_height: float | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute drift metrics using a saved baseline profile."""

    _validate_baseline_profile_shape(baseline_profile)
    policy = {
        **DEFAULT_BASELINE_THRESHOLDS,
        **baseline_profile.get("thresholds", {}),
        **(thresholds or {}),
    }
    baseline_bbox = dict(baseline_profile["bbox"])
    baseline_score = dict(baseline_profile["score"])
    baseline_class_distribution = _class_distribution_from_profile(baseline_profile)
    candidate_bbox = compute_bbox_validity_metrics(
        candidate_output,
        image_width=image_width,
        image_height=image_height,
    )
    baseline_score = _ensure_score_histogram(baseline_score)
    candidate_score = _score_metrics_with_histogram(candidate_output, policy)
    candidate_class_distribution = compute_class_distribution_metrics(candidate_output)
    comparison = _comparison_metrics(
        baseline_bbox=baseline_bbox,
        candidate_bbox=candidate_bbox,
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_class_distribution=baseline_class_distribution,
        candidate_class_distribution=candidate_class_distribution,
        thresholds=policy,
        baseline_latency_ms=baseline_profile.get("latency_ms"),
        candidate_latency_ms=candidate_latency_ms,
        baseline_accuracy=baseline_profile.get("accuracy"),
        candidate_accuracy=candidate_accuracy,
    )
    return {
        "baseline": {
            "bbox": baseline_bbox,
            "score": baseline_score,
            "class_distribution": baseline_class_distribution,
            "latency_ms": baseline_profile.get("latency_ms"),
            "accuracy": baseline_profile.get("accuracy"),
        },
        "candidate": {
            "bbox": candidate_bbox,
            "score": candidate_score,
            "class_distribution": candidate_class_distribution,
            "latency_ms": candidate_latency_ms,
            "accuracy": candidate_accuracy,
        },
        "comparison": comparison,
    }


def _comparison_metrics(
    *,
    baseline_bbox: dict[str, Any],
    candidate_bbox: dict[str, Any],
    baseline_score: dict[str, Any],
    candidate_score: dict[str, Any],
    baseline_class_distribution: dict[str, Any],
    candidate_class_distribution: dict[str, Any],
    thresholds: dict[str, float],
    baseline_latency_ms: float | None,
    candidate_latency_ms: float | None,
    baseline_accuracy: float | None,
    candidate_accuracy: float | None,
) -> dict[str, Any]:
    baseline_count = baseline_bbox["total_predictions"]
    candidate_count = candidate_bbox["total_predictions"]
    detection_delta = candidate_count - baseline_count
    signed_delta_pct = _ratio_float(detection_delta, baseline_count)
    detection_drop_pct = _ratio_float(baseline_count - candidate_count, baseline_count)
    return {
        "baseline_detection_count": baseline_count,
        "candidate_detection_count": candidate_count,
        "detection_count_delta": detection_delta,
        "detection_count_delta_pct": signed_delta_pct,
        "detection_count_drop_pct": max(0.0, detection_drop_pct),
        "detection_disappeared": _detection_disappeared(
            baseline_count=baseline_count,
            candidate_count=candidate_count,
        ),
        "invalid_bbox_rate_factor": _factor(
            candidate_bbox["invalid_bbox_rate"],
            baseline_bbox["invalid_bbox_rate"],
        ),
        "bbox_collapse_ratio_factor": _factor(
            candidate_bbox["bbox_collapse_ratio"],
            baseline_bbox["bbox_collapse_ratio"],
        ),
        "score_saturation_factor": _factor(
            candidate_score["saturation_ratio"],
            baseline_score["saturation_ratio"],
        ),
        "latency_delta_pct": _optional_delta_pct(
            candidate_latency_ms,
            baseline_latency_ms,
        ),
        "accuracy_delta_pp": _optional_delta(candidate_accuracy, baseline_accuracy),
        "per_class_detection_drift": _per_class_detection_drift_metrics(
            baseline_class_distribution=baseline_class_distribution,
            candidate_class_distribution=candidate_class_distribution,
            thresholds=thresholds,
        ),
        "calibration_drift": _calibration_drift_metrics(
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            thresholds=thresholds,
        ),
    }


def _factor_evidence(
    *,
    evidence_type: str,
    metric_name: str,
    candidate_metric_name: str,
    baseline_value: float,
    candidate_value: float,
    factor: float,
    review_threshold: float,
    blocked_threshold: float,
    candidate_floor: float,
    why_it_matters: str,
    suspected_causes: list[str],
    recommendation: str,
    raw_context: dict[str, Any],
) -> dict[str, Any]:
    severity = _factor_severity(
        factor=factor,
        candidate_value=candidate_value,
        review_threshold=review_threshold,
        blocked_threshold=blocked_threshold,
        candidate_floor=candidate_floor,
    )
    status = _status_from_severity(severity)
    causes = suspected_causes if status != "passed" else []
    return build_evidence_item(
        evidence_type=evidence_type,
        metric_name=metric_name,
        observed_value=factor,
        baseline_value=baseline_value,
        threshold=review_threshold,
        delta=candidate_value - baseline_value,
        delta_pct=_optional_delta_pct(candidate_value, baseline_value),
        increase_factor=factor,
        severity=severity,
        status=status,
        explanation=(
            f"{candidate_metric_name} changed from {_fmt(baseline_value)} in the "
            f"baseline to {_fmt(candidate_value)} in the candidate "
            f"({_fmt(factor)}x). Review threshold is {_fmt(review_threshold)}x."
        ),
        why_it_matters=why_it_matters,
        suspected_causes=causes,
        recommendation=(
            recommendation if status != "passed" else "Baseline deviation is within threshold."
        ),
        raw_context=raw_context,
    )


def _detection_count_drift_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    comparison = metrics["comparison"]
    drop_pct = comparison["detection_count_drop_pct"]
    severity = _drop_severity(drop_pct, thresholds)
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="detection_count_drift",
        metric_name="detection_count_drop_pct",
        observed_value=drop_pct,
        baseline_value=comparison["baseline_detection_count"],
        threshold=thresholds["detection_count_drop_pct_review"],
        delta=comparison["detection_count_delta"],
        delta_pct=comparison["detection_count_delta_pct"],
        severity=severity,
        status=status,
        explanation=(
            f"Candidate detection count changed from "
            f"{comparison['baseline_detection_count']} to "
            f"{comparison['candidate_detection_count']} "
            f"({ _fmt(comparison['detection_count_delta_pct']) } signed delta)."
        ),
        why_it_matters=(
            "A large detection count drop can mean the candidate became faster by "
            "missing objects rather than by improving execution efficiency."
        ),
        suspected_causes=[
            "Preprocessing/postprocess mismatch",
            "Quantization artifact",
            "Confidence threshold mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Compare candidate detections against the baseline before deployment."
            if status != "passed"
            else "Detection count drift is within threshold."
        ),
        raw_context=comparison,
    )


def _detection_disappearance_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    comparison = metrics["comparison"]
    observed = 1.0 if comparison["detection_disappeared"] else 0.0
    threshold = thresholds["detection_disappearance_blocked"]
    severity = "high" if observed >= threshold else "low"
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="detection_disappearance",
        metric_name="detection_disappearance_flag",
        observed_value=observed,
        baseline_value=comparison["baseline_detection_count"],
        threshold=threshold,
        delta=comparison["detection_count_delta"],
        delta_pct=comparison["detection_count_delta_pct"],
        severity=severity,
        status=status,
        explanation=(
            "Candidate produced zero detections while the baseline had "
            f"{comparison['baseline_detection_count']} detections."
            if status != "passed"
            else "Candidate did not fully disappear relative to the baseline."
        ),
        why_it_matters=(
            "A complete detection disappearance can make a faster candidate look "
            "deployable even though it stopped detecting objects."
        ),
        suspected_causes=[
            "Confidence threshold mismatch",
            "Quantization artifact",
            "Postprocess class/filter mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Block deployment until candidate disappearance is explained."
            if status != "passed"
            else "Detection disappearance is not present for this comparison."
        ),
        raw_context=comparison,
    )


def _per_class_detection_drift_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    comparison = metrics["comparison"]["per_class_detection_drift"]
    drop_pct = comparison["max_drop_pct"]
    severity = _per_class_drop_severity(drop_pct, thresholds)
    status = _status_from_severity(severity)
    max_drop_class_id = comparison.get("max_drop_class_id")
    return build_evidence_item(
        evidence_type="per_class_detection_drift",
        metric_name="per_class_detection_drop_pct",
        observed_value=drop_pct,
        baseline_value=comparison.get("max_drop_baseline_count"),
        threshold=thresholds["per_class_detection_drop_pct_review"],
        delta=comparison.get("max_drop_delta"),
        delta_pct=-drop_pct if drop_pct else 0.0,
        severity=severity,
        status=status,
        explanation=(
            f"Class {max_drop_class_id} detection count dropped by "
            f"{_fmt(drop_pct)} relative to baseline."
            if status != "passed"
            else "Per-class detection counts are within threshold."
        ),
        why_it_matters=(
            "Total detection count can remain stable while a safety- or "
            "accuracy-relevant class disappears."
        ),
        suspected_causes=[
            "Class mapping mismatch",
            "Class-specific confidence threshold mismatch",
            "Quantization artifact affecting one class",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review per-class outputs against the baseline before deployment."
            if status != "passed"
            else "Per-class detection drift is within threshold."
        ),
        raw_context=comparison,
    )


def _calibration_drift_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    comparison = metrics["comparison"]["calibration_drift"]
    trigger_count = len(comparison["triggered_policy_items"])
    status = "failed" if trigger_count else "passed"
    severity = "medium" if trigger_count else "low"
    return build_evidence_item(
        evidence_type="calibration_drift",
        metric_name="calibration_drift_trigger_count",
        observed_value=trigger_count,
        baseline_value=None,
        threshold=1,
        delta=None,
        delta_pct=None,
        severity=severity,
        status=status,
        explanation=(
            "Candidate score distribution drift triggered calibration review "
            f"items: {', '.join(comparison['triggered_policy_items'])}."
            if status != "passed"
            else "Calibration drift metrics are within threshold."
        ),
        why_it_matters=(
            "Score distribution shifts can change threshold behavior even when "
            "bbox geometry and detection count remain stable."
        ),
        suspected_causes=[
            "Quantization calibration shift",
            "Score decoder or sigmoid mismatch",
            "Confidence threshold mismatch",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review score histogram, mean/std score deltas, and saturation delta "
            "against the known-good baseline before deployment."
            if status != "passed"
            else "Calibration drift is within the bounded policy thresholds."
        ),
        raw_context=comparison,
    )


def _latency_quality_tradeoff_evidence(
    metrics: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any] | None:
    latency_delta_pct = metrics["comparison"].get("latency_delta_pct")
    if latency_delta_pct is None or latency_delta_pct >= 0:
        return None

    risky_items = [
        item for item in evidence if item.get("status") in {"warning", "failed"}
    ]
    if not risky_items:
        return None

    severity = combine_severity(risky_items)
    status = _status_from_severity(severity)
    return build_evidence_item(
        evidence_type="latency_quality_tradeoff",
        metric_name="latency_delta_pct",
        observed_value=latency_delta_pct,
        baseline_value=metrics["baseline"].get("latency_ms"),
        threshold=0,
        delta=(
            metrics["candidate"].get("latency_ms") - metrics["baseline"].get("latency_ms")
            if metrics["candidate"].get("latency_ms") is not None
            and metrics["baseline"].get("latency_ms") is not None
            else None
        ),
        delta_pct=latency_delta_pct,
        severity=severity,
        status=status,
        explanation=(
            f"Candidate latency improved by {_fmt(abs(latency_delta_pct))}, but "
            "baseline comparison evidence indicates output quality risk."
        ),
        why_it_matters=(
            "Latency improvement alone is not deployment-ready evidence when bbox, "
            "score, or detection count quality regresses."
        ),
        suspected_causes=[
            "Quantization artifact",
            "Decoder mismatch",
            "Run configuration mismatch",
        ],
        recommendation=(
            "Treat speedup as review evidence until output quality drift is resolved."
        ),
        raw_context=metrics["comparison"],
    )


def _primary_reason(evidence: list[dict[str, Any]]) -> str:
    failed = [item for item in evidence if item["status"] == "failed"]
    if failed:
        return (
            "Candidate output quality deviates from the baseline diagnosis profile."
        )
    warnings = [item for item in evidence if item["status"] == "warning"]
    if warnings:
        return "Candidate baseline deviation should be reviewed before deployment."
    return "Candidate output quality is consistent with the baseline diagnosis profile."


def _comparison_confidence(metrics: dict[str, Any]) -> float:
    baseline_count = metrics["comparison"]["baseline_detection_count"]
    candidate_count = metrics["comparison"]["candidate_detection_count"]
    if baseline_count == 0 and candidate_count == 0:
        return 0.5
    return 0.92


def _factor(
    candidate_value: float,
    baseline_value: float,
    *,
    epsilon: float = 1e-9,
) -> float:
    if candidate_value == 0 and baseline_value == 0:
        return 1.0
    return round(candidate_value / max(baseline_value, epsilon), 6)


def _factor_severity(
    *,
    factor: float,
    candidate_value: float,
    review_threshold: float,
    blocked_threshold: float,
    candidate_floor: float,
) -> str:
    if factor > blocked_threshold and candidate_value > candidate_floor:
        return "high"
    if factor > review_threshold and candidate_value > candidate_floor:
        return "medium"
    return "low"


def _drop_severity(drop_pct: float, thresholds: dict[str, float]) -> str:
    if drop_pct > thresholds["detection_count_drop_pct_blocked"]:
        return "high"
    if drop_pct > thresholds["detection_count_drop_pct_review"]:
        return "medium"
    return "low"


def _per_class_drop_severity(
    drop_pct: float,
    thresholds: dict[str, float],
) -> str:
    if drop_pct >= thresholds["per_class_detection_drop_pct_blocked"]:
        return "high"
    if drop_pct >= thresholds["per_class_detection_drop_pct_review"]:
        return "medium"
    return "low"


def _detection_disappeared(*, baseline_count: int, candidate_count: int) -> bool:
    return baseline_count > 0 and candidate_count == 0


def _per_class_detection_drift_metrics(
    *,
    baseline_class_distribution: dict[str, Any],
    candidate_class_distribution: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    baseline_counts = _normalized_class_counts(baseline_class_distribution)
    candidate_counts = _normalized_class_counts(candidate_class_distribution)
    min_baseline_count = int(thresholds["per_class_drift_min_baseline_count"])
    class_ids = sorted(set(baseline_counts) | set(candidate_counts), key=_class_sort_key)
    classes = []
    dropped_class_ids = []
    max_drop_pct = 0.0
    max_drop_class_id: str | None = None
    max_drop_delta = 0
    max_drop_baseline_count = 0

    for class_id in class_ids:
        baseline_count = baseline_counts.get(class_id, 0)
        candidate_count = candidate_counts.get(class_id, 0)
        delta = candidate_count - baseline_count
        drop_count = max(0, baseline_count - candidate_count)
        eligible = baseline_count >= min_baseline_count
        drop_pct = _ratio_float(drop_count, baseline_count) if eligible else 0.0
        if eligible and drop_pct > max_drop_pct:
            max_drop_pct = drop_pct
            max_drop_class_id = class_id
            max_drop_delta = delta
            max_drop_baseline_count = baseline_count
        if eligible and baseline_count > 0 and candidate_count == 0:
            dropped_class_ids.append(class_id)
        classes.append(
            {
                "class_id": class_id,
                "baseline_count": baseline_count,
                "candidate_count": candidate_count,
                "delta": delta,
                "drop_pct": drop_pct,
            }
        )

    return {
        "max_drop_class_id": max_drop_class_id,
        "max_drop_pct": max_drop_pct,
        "max_drop_delta": max_drop_delta,
        "max_drop_baseline_count": max_drop_baseline_count,
        "dropped_class_ids": dropped_class_ids,
        "min_baseline_count": min_baseline_count,
        "classes": classes,
    }


def _calibration_drift_metrics(
    *,
    baseline_score: dict[str, Any],
    candidate_score: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    histogram_distance = _score_histogram_distance(
        baseline_score.get("score_histogram"),
        candidate_score.get("score_histogram"),
    )
    mean_delta = _optional_delta(
        candidate_score.get("mean_score"),
        baseline_score.get("mean_score"),
    )
    std_delta = _optional_delta(
        candidate_score.get("std_score"),
        baseline_score.get("std_score"),
    )
    saturation_delta = _optional_delta(
        candidate_score.get("saturation_ratio"),
        baseline_score.get("saturation_ratio"),
    )
    triggered = []
    if histogram_distance >= thresholds["calibration_histogram_distance_review"]:
        triggered.append("histogram_shift")
    if mean_delta is not None and abs(mean_delta) >= thresholds["calibration_mean_score_delta_review"]:
        triggered.append("mean_score_shift")
    candidate_std = candidate_score.get("std_score")
    baseline_std = baseline_score.get("std_score")
    if (
        isinstance(candidate_std, (int, float))
        and isinstance(baseline_std, (int, float))
        and baseline_std >= thresholds["calibration_std_score_floor_review"]
        and candidate_std < thresholds["calibration_std_score_floor_review"]
    ) or (
        std_delta is not None
        and abs(std_delta) >= thresholds["calibration_std_score_delta_review"]
    ):
        triggered.append("spread_collapse_or_expansion")
    if (
        saturation_delta is not None
        and saturation_delta >= thresholds["calibration_saturation_delta_review"]
    ) or candidate_score.get("saturation_ratio", 0.0) >= thresholds["saturation_ratio_review"]:
        triggered.append("saturation_drift")

    return {
        "histogram_distance": histogram_distance,
        "mean_score_delta": mean_delta,
        "std_score_delta": std_delta,
        "saturation_delta": saturation_delta,
        "triggered_policy_items": triggered,
        "thresholds": {
            "histogram_distance_review": thresholds["calibration_histogram_distance_review"],
            "mean_score_delta_review": thresholds["calibration_mean_score_delta_review"],
            "std_score_delta_review": thresholds["calibration_std_score_delta_review"],
            "std_score_floor_review": thresholds["calibration_std_score_floor_review"],
            "saturation_delta_review": thresholds["calibration_saturation_delta_review"],
        },
        "baseline_score_histogram": baseline_score.get("score_histogram", {}),
        "candidate_score_histogram": candidate_score.get("score_histogram", {}),
    }


def _score_histogram_distance(
    baseline_histogram: Any,
    candidate_histogram: Any,
) -> float:
    if not isinstance(baseline_histogram, dict) or not isinstance(candidate_histogram, dict):
        return 0.0
    baseline_ratios = baseline_histogram.get("ratios", [])
    candidate_ratios = candidate_histogram.get("ratios", [])
    if not isinstance(baseline_ratios, list) or not isinstance(candidate_ratios, list):
        return 0.0
    if len(baseline_ratios) != len(candidate_ratios):
        return 0.0
    distance = sum(
        abs(float(candidate) - float(baseline))
        for baseline, candidate in zip(baseline_ratios, candidate_ratios)
        if isinstance(baseline, (int, float)) and isinstance(candidate, (int, float))
    )
    return round(distance / 2.0, 6)


def _score_metrics_with_histogram(
    output: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    metrics = compute_score_distribution_metrics(output, thresholds=thresholds)
    metrics["score_histogram"] = compute_score_histogram_metrics(output)
    return metrics


def _ensure_score_histogram(score_metrics: dict[str, Any]) -> dict[str, Any]:
    metrics = dict(score_metrics)
    if not isinstance(metrics.get("score_histogram"), dict):
        metrics["score_histogram"] = {}
    return metrics


def _class_distribution_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    distribution = profile.get("class_distribution")
    if isinstance(distribution, dict):
        class_counts = _normalized_class_counts(distribution)
        return {
            "class_counts": class_counts,
            "class_count": len(class_counts),
            "total_predictions": sum(class_counts.values()),
        }
    return {
        "class_counts": {},
        "class_count": 0,
        "total_predictions": profile["bbox"]["total_predictions"],
    }


def _normalized_class_counts(distribution: dict[str, Any]) -> dict[str, int]:
    raw_counts = distribution.get("class_counts", {})
    if not isinstance(raw_counts, dict):
        return {}
    counts: dict[str, int] = {}
    for class_id, count in raw_counts.items():
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            counts[str(class_id)] = count
    return dict(sorted(counts.items(), key=_class_count_sort_key))


def _class_count_sort_key(item: tuple[str, int]) -> tuple[int, Any]:
    return _class_sort_key(item[0])


def _class_sort_key(class_id: Any) -> tuple[int, Any]:
    try:
        return (0, int(class_id))
    except (TypeError, ValueError):
        return (1, str(class_id))


def _detections(output: dict[str, Any]) -> list[Any]:
    detections = output.get("detections", [])
    return detections if isinstance(detections, list) else []


def _status_from_severity(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "failed"
    if severity == "medium":
        return "warning"
    return "passed"


def _optional_delta(candidate_value: float | None, baseline_value: float | None) -> float | None:
    if candidate_value is None or baseline_value is None:
        return None
    return candidate_value - baseline_value


def _optional_delta_pct(
    candidate_value: float | None,
    baseline_value: float | None,
) -> float | None:
    if candidate_value is None or baseline_value in {None, 0}:
        return None
    return _ratio_float(candidate_value - baseline_value, baseline_value)


def _ratio_float(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _validate_baseline_profile_shape(profile: dict[str, Any]) -> None:
    if profile.get("schema_version") != BASELINE_PROFILE_SCHEMA_VERSION:
        raise ValueError(
            "baseline_profile.schema_version must be "
            f"{BASELINE_PROFILE_SCHEMA_VERSION}"
        )
    for field in ("bbox", "score"):
        if not isinstance(profile.get(field), dict):
            raise ValueError(f"baseline_profile.{field} must be an object")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
