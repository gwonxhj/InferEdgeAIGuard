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
}


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
    score_metrics = compute_score_distribution_metrics(
        baseline_output,
        thresholds=policy,
    )
    return {
        "schema_version": BASELINE_PROFILE_SCHEMA_VERSION,
        "label": label,
        "source": dict(source or {}),
        "model": baseline_output.get("model"),
        "precision": baseline_output.get("precision"),
        "image_id": baseline_output.get("image_id"),
        "bbox": bbox_metrics,
        "score": score_metrics,
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
        "latency_ms": baseline_latency_ms,
        "accuracy": baseline_accuracy,
    }
    candidate_summary = {
        "label": candidate_label,
        "model": candidate_output.get("model"),
        "precision": candidate_output.get("precision"),
        "bbox": metrics["candidate"]["bbox"],
        "score": metrics["candidate"]["score"],
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
    baseline_score = compute_score_distribution_metrics(
        baseline_output,
        thresholds=policy,
    )
    candidate_score = compute_score_distribution_metrics(
        candidate_output,
        thresholds=policy,
    )

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
    }

    return {
        "baseline": {
            "bbox": baseline_bbox,
            "score": baseline_score,
            "latency_ms": baseline_latency_ms,
            "accuracy": baseline_accuracy,
        },
        "candidate": {
            "bbox": candidate_bbox,
            "score": candidate_score,
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
    candidate_bbox = compute_bbox_validity_metrics(
        candidate_output,
        image_width=image_width,
        image_height=image_height,
    )
    candidate_score = compute_score_distribution_metrics(
        candidate_output,
        thresholds=policy,
    )
    comparison = _comparison_metrics(
        baseline_bbox=baseline_bbox,
        candidate_bbox=candidate_bbox,
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_latency_ms=baseline_profile.get("latency_ms"),
        candidate_latency_ms=candidate_latency_ms,
        baseline_accuracy=baseline_profile.get("accuracy"),
        candidate_accuracy=candidate_accuracy,
    )
    return {
        "baseline": {
            "bbox": baseline_bbox,
            "score": baseline_score,
            "latency_ms": baseline_profile.get("latency_ms"),
            "accuracy": baseline_profile.get("accuracy"),
        },
        "candidate": {
            "bbox": candidate_bbox,
            "score": candidate_score,
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
