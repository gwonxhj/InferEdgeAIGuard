"""Human-readable report formatting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def format_summary(summary: dict[str, Any]) -> str:
    """Format an analyze or compare summary for CLI output."""

    if summary.get("mode") == "batch_analyze":
        return _format_batch_summary(summary)
    if summary.get("mode") == "batch_compare":
        return _format_batch_compare_summary(summary)

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


def _format_batch_summary(summary: dict[str, Any]) -> str:
    lines = [
        "InferEdgeAIGuard batch analyze summary",
        f"- input_dir: {summary['input_dir']}",
        f"- sample_count: {summary['sample_count']}",
        f"- failure_sample_count: {summary['failure_sample_count']}",
        f"- failure_rate: {_format_value(summary['failure_rate'])}",
        "- failure_type_counts:",
    ]

    failure_type_counts = summary.get("failure_type_counts", {})
    if not failure_type_counts:
        lines.append("  No failure detected")
        return "\n".join(lines)

    for failure_type, count in sorted(failure_type_counts.items()):
        lines.append(f"  - {failure_type}: {count}")

    return "\n".join(lines)


def _format_batch_compare_summary(summary: dict[str, Any]) -> str:
    lines = [
        "InferEdgeAIGuard batch compare summary",
        f"- base_dir: {summary['base_dir']}",
        f"- candidate_dir: {summary['candidate_dir']}",
        f"- pair_count: {summary['pair_count']}",
        f"- failure_pair_count: {summary['failure_pair_count']}",
        f"- failure_rate: {_format_value(summary['failure_rate'])}",
        "- failure_type_counts:",
    ]

    failure_type_counts = summary.get("failure_type_counts", {})
    if not failure_type_counts:
        lines.append("  No failure detected")
    else:
        for failure_type, count in sorted(failure_type_counts.items()):
            lines.append(f"  - {failure_type}: {count}")

    lines.append(
        f"- unmatched_base_files: {_format_list(summary.get('unmatched_base_files', []))}"
    )
    lines.append(
        "- unmatched_candidate_files: "
        f"{_format_list(summary.get('unmatched_candidate_files', []))}"
    )
    return "\n".join(lines)


def _format_list(values: list[Any]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(str(value) for value in values) + "]"


def save_summary_json(summary: dict[str, Any], output_path: str | Path) -> None:
    """Save a summary dict as a JSON report."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")


def save_summary_markdown(summary: dict[str, Any], output_path: str | Path) -> None:
    """Save a formatted summary as a Markdown report."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"{_markdown_title(summary)}\n\n```text\n{format_summary(summary)}\n```\n"
    path.write_text(content, encoding="utf-8")


def _markdown_title(summary: dict[str, Any]) -> str:
    if summary.get("mode") == "batch_analyze":
        return "# InferEdgeAIGuard Batch Analyze Report"
    if summary.get("mode") == "batch_compare":
        return "# InferEdgeAIGuard Batch Compare Report"
    if "base_count" in summary:
        return "# InferEdgeAIGuard Compare Report"
    return "# InferEdgeAIGuard Analyze Report"
