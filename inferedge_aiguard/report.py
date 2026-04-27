"""Human-readable report formatting."""

from __future__ import annotations

from typing import Any


def format_summary(summary: dict[str, Any]) -> str:
    """Format an analyze or compare summary for CLI output."""

    lines: list[str] = []

    if "base_count" in summary:
        lines.append("InferEdgeAIGuard compare summary")
        lines.append(f"- base_count: {summary['base_count']}")
        lines.append(f"- candidate_count: {summary['candidate_count']}")
    else:
        lines.append("InferEdgeAIGuard analyze summary")
        lines.append(f"- model: {summary.get('model', 'unknown')}")
        lines.append(f"- precision: {summary.get('precision', 'unknown')}")
        lines.append(f"- image_id: {summary.get('image_id', 'unknown')}")
        lines.append(f"- detection_count: {summary.get('detection_count', 'unknown')}")

    if not summary.get("has_failure", False):
        lines.append("- result: No failure detected")
        return "\n".join(lines)

    lines.append("- result: Failure detected")
    for failure in summary.get("failures", []):
        parts = [
            f"failure_type={failure['failure_type']}",
            f"severity={failure['severity']}",
            f"message={failure['message']}",
        ]
        for field in (
            "affected_count",
            "total_count",
            "collapse_ratio",
            "saturation_ratio",
            "mismatch_ratio",
            "threshold",
            "ratio_threshold",
        ):
            if field in failure:
                parts.append(f"{field}={_format_value(failure[field])}")
        lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
