"""Evidence-based diagnosis report helpers.

This module implements the first contract layer for AIGuard diagnosis reports.
It does not run detectors by itself; detector outputs can be normalized into the
schema here so Lab and Markdown reports receive consistent evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DIAGNOSIS_SCHEMA_VERSION = "inferedge-aiguard-diagnosis-v1"

GUARD_VERDICTS = {"pass", "suspicious", "review_required", "blocked"}
SEVERITIES = {"low", "medium", "high", "critical"}
EVIDENCE_STATUSES = {"passed", "warning", "failed", "skipped"}

_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def build_evidence_item(
    *,
    evidence_type: str,
    metric_name: str,
    observed_value: Any,
    baseline_value: Any = None,
    threshold: Any = None,
    delta: Any = None,
    delta_pct: Any = None,
    increase_factor: Any = None,
    severity: str = "low",
    status: str = "warning",
    explanation: str | None = None,
    why_it_matters: str = "",
    suspected_causes: list[str] | None = None,
    recommendation: str = "",
    raw_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one diagnosis evidence item using the v1 contract."""

    _require_non_empty_string("evidence_type", evidence_type)
    _require_non_empty_string("metric_name", metric_name)
    _validate_severity(severity)
    _validate_status(status)

    causes = list(suspected_causes or [])
    return {
        "type": evidence_type,
        "metric_name": metric_name,
        "observed_value": observed_value,
        "baseline_value": baseline_value,
        "threshold": threshold,
        "delta": delta,
        "delta_pct": delta_pct,
        "increase_factor": increase_factor,
        "severity": severity,
        "status": status,
        "explanation": explanation
        or build_explanation(
            evidence_type=evidence_type,
            metric_name=metric_name,
            observed_value=observed_value,
            baseline_value=baseline_value,
            threshold=threshold,
            increase_factor=increase_factor,
        ),
        "why_it_matters": why_it_matters,
        "suspected_causes": causes,
        "recommendation": recommendation,
        "raw_context": dict(raw_context or {}),
    }


def build_explanation(
    *,
    evidence_type: str,
    metric_name: str,
    observed_value: Any,
    baseline_value: Any = None,
    threshold: Any = None,
    increase_factor: Any = None,
) -> str:
    """Build a compact deterministic explanation for one metric."""

    parts = [
        f"{metric_name} observed value is {_format_metric_value(observed_value)}."
    ]
    if baseline_value is not None:
        parts.append(f"Baseline value is {_format_metric_value(baseline_value)}.")
    if threshold is not None:
        parts.append(f"Threshold is {_format_metric_value(threshold)}.")
    if increase_factor is not None:
        parts.append(f"Increase factor is {_format_metric_value(increase_factor)}x.")
    parts.append(
        f"This {evidence_type} evidence should be reviewed before deployment."
    )
    return " ".join(parts)


def map_severity(
    *,
    metric_name: str,
    observed_value: float,
    thresholds: dict[str, float] | None = None,
) -> str:
    """Map common diagnosis metrics to severity.

    Thresholds may override defaults by metric-specific names, but the default
    policy follows the Obsidian diagnosis design.
    """

    policy = thresholds or {}
    if metric_name == "score_range_violation_count":
        return "critical" if observed_value > 0 else "low"
    if metric_name == "invalid_bbox_rate":
        blocked = policy.get("invalid_bbox_rate_blocked", 0.20)
        review = policy.get("invalid_bbox_rate_review", 0.05)
        if observed_value > blocked:
            return "high"
        if observed_value > review:
            return "medium"
        return "low"
    if metric_name == "bbox_collapse_ratio":
        high = policy.get("bbox_collapse_ratio_high", 0.10)
        review = policy.get("bbox_collapse_ratio_review", 0.05)
        if observed_value > high:
            return "high"
        if observed_value > review:
            return "medium"
        return "low"
    if metric_name == "saturation_ratio":
        high = policy.get("saturation_ratio_high", 0.85)
        review = policy.get("saturation_ratio_review", 0.70)
        if observed_value > high:
            return "high"
        if observed_value > review:
            return "medium"
        return "low"
    if metric_name == "detection_count_drop_pct":
        blocked = policy.get("detection_count_drop_pct_blocked", 0.80)
        review = policy.get("detection_count_drop_pct_review", 0.50)
        magnitude = abs(observed_value)
        if magnitude > blocked:
            return "high"
        if magnitude > review:
            return "medium"
        return "low"
    return "low"


def map_guard_verdict(evidence: list[dict[str, Any]]) -> str:
    """Map evidence items into an AIGuard guard_verdict."""

    failed_items = [item for item in evidence if item.get("status") == "failed"]
    if not failed_items:
        warning_items = [item for item in evidence if item.get("status") == "warning"]
        return "suspicious" if warning_items else "pass"

    max_severity = combine_severity(failed_items)
    if max_severity in {"critical", "high"}:
        return "blocked"
    if max_severity == "medium":
        return "review_required"
    return "suspicious"


def combine_severity(evidence: list[dict[str, Any]]) -> str:
    """Return the highest severity found in evidence items."""

    if not evidence:
        return "low"
    severities = [
        item.get("severity", "low")
        for item in evidence
        if item.get("severity", "low") in SEVERITIES
    ]
    if not severities:
        return "low"
    return max(severities, key=lambda value: _SEVERITY_RANK[value])


def build_diagnosis_report(
    *,
    evidence: list[dict[str, Any]],
    source: dict[str, Any] | None = None,
    guard_verdict: str | None = None,
    severity: str | None = None,
    confidence: float = 0.0,
    primary_reason: str | None = None,
    suspected_causes: list[str] | None = None,
    recommendations: list[str] | None = None,
    thresholds: dict[str, Any] | None = None,
    baseline_summary: dict[str, Any] | None = None,
    candidate_summary: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a complete v1 diagnosis report."""

    verdict = guard_verdict or map_guard_verdict(evidence)
    _validate_verdict(verdict)
    combined_severity = severity or combine_severity(evidence)
    _validate_severity(combined_severity)

    report_causes = _merge_unique(
        list(suspected_causes or []),
        *[item.get("suspected_causes", []) for item in evidence],
    )
    report_recommendations = _merge_unique(
        list(recommendations or []),
        *[
            [item["recommendation"]]
            for item in evidence
            if isinstance(item.get("recommendation"), str)
            and item.get("recommendation")
        ],
    )

    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "source": dict(source or {}),
        "guard_verdict": verdict,
        "severity": combined_severity,
        "confidence": float(confidence),
        "primary_reason": primary_reason or _primary_reason_from_evidence(evidence),
        "evidence": evidence,
        "suspected_causes": report_causes,
        "recommendations": report_recommendations,
        "thresholds": dict(thresholds or {}),
        "baseline_summary": dict(baseline_summary or {}),
        "candidate_summary": dict(candidate_summary or {}),
        "created_at": created_at or _utc_now(),
    }


def diagnosis_report_to_markdown(report: dict[str, Any]) -> str:
    """Render a diagnosis report as a small Markdown report skeleton."""

    evidence_rows = []
    for item in report.get("evidence", []):
        evidence_rows.append(
            "| "
            + " | ".join(
                _escape_markdown_cell(value)
                for value in [
                    item.get("type", ""),
                    item.get("metric_name", ""),
                    item.get("observed_value", ""),
                    item.get("baseline_value", ""),
                    item.get("threshold", ""),
                    item.get("severity", ""),
                    item.get("status", ""),
                ]
            )
            + " |"
        )

    evidence_table = "\n".join(
        [
            "| Type | Metric | Observed | Baseline | Threshold | Severity | Status |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *evidence_rows,
        ]
    )
    if not evidence_rows:
        evidence_table = "No diagnosis evidence recorded."

    explanation_lines = [
        f"- {item.get('explanation')}"
        for item in report.get("evidence", [])
        if item.get("explanation")
    ]
    explanations = "\n".join(explanation_lines) if explanation_lines else "[]"

    return "\n\n".join(
        [
            "# InferEdgeAIGuard Evidence Diagnosis Report",
            "## Summary",
            "\n".join(
                [
                    f"- schema_version: {report.get('schema_version', '')}",
                    f"- guard_verdict: {report.get('guard_verdict', '')}",
                    f"- severity: {report.get('severity', '')}",
                    f"- confidence: {_format_metric_value(report.get('confidence', 0.0))}",
                    f"- primary_reason: {report.get('primary_reason', '')}",
                    f"- created_at: {report.get('created_at', '')}",
                ]
            ),
            "## Evidence",
            evidence_table,
            "## Explanations",
            explanations,
            "## Suspected Causes",
            _bullet_list(report.get("suspected_causes", [])),
            "## Recommendations",
            _bullet_list(report.get("recommendations", [])),
        ]
    ) + "\n"


def _primary_reason_from_evidence(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "No diagnosis evidence indicates deployment risk."
    failed = [item for item in evidence if item.get("status") == "failed"]
    items = failed or evidence
    first = items[0]
    metric = first.get("metric_name", "diagnosis_metric")
    return f"{metric} indicates possible deployment risk."


def _merge_unique(base: list[str], *groups: list[str]) -> list[str]:
    merged: list[str] = []
    for value in base:
        _append_unique(merged, value)
    for group in groups:
        for value in group:
            _append_unique(merged, value)
    return merged


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _validate_verdict(value: str) -> None:
    if value not in GUARD_VERDICTS:
        raise ValueError(f"guard_verdict must be one of: {', '.join(sorted(GUARD_VERDICTS))}")


def _validate_severity(value: str) -> None:
    if value not in SEVERITIES:
        raise ValueError(f"severity must be one of: {', '.join(sorted(SEVERITIES))}")


def _validate_status(value: str) -> None:
    if value not in EVIDENCE_STATUSES:
        raise ValueError(
            f"evidence status must be one of: {', '.join(sorted(EVIDENCE_STATUSES))}"
        )


def _require_non_empty_string(field: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_metric_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _bullet_list(values: list[Any]) -> str:
    if not values:
        return "[]"
    return "\n".join(f"- {value}" for value in values)


def _escape_markdown_cell(value: Any) -> str:
    return _format_metric_value(value).replace("|", "\\|").replace("\n", " ")
