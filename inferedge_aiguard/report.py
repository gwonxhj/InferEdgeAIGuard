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
    if summary.get("mode") == "compare_reasoning":
        return _format_compare_reasoning_summary(summary)

    lines: list[str] = []

    if "base_count" in summary:
        lines.append("InferEdgeAIGuard compare summary")
        lines.extend(_metadata_lines(summary))
        lines.append(f"- base_count: {summary['base_count']}")
        lines.append(f"- candidate_count: {summary['candidate_count']}")
    else:
        lines.append("InferEdgeAIGuard analyze summary")
        lines.extend(_metadata_lines(summary))
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
        *_metadata_lines(summary),
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
        *_metadata_lines(summary),
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


def _format_compare_reasoning_summary(summary: dict[str, Any]) -> str:
    lines = [
        "InferEdgeAIGuard compare reasoning summary",
        f"- status: {summary.get('status', 'unknown')}",
        f"- confidence: {_format_value(summary.get('confidence', 0.0))}",
        "- anomalies:",
    ]

    anomalies = summary.get("anomalies", [])
    if not anomalies:
        lines.append("  No anomaly detected")
    else:
        for anomaly in anomalies:
            lines.append(
                "  - "
                f"type={anomaly.get('type')} | "
                f"severity={anomaly.get('severity')} | "
                f"message={anomaly.get('message')}"
            )

    lines.append(f"- suspected_causes: {_format_list(summary.get('suspected_causes', []))}")
    lines.append(f"- recommendations: {_format_list(summary.get('recommendations', []))}")
    return "\n".join(lines)


def _format_list(values: list[Any]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(str(value) for value in values) + "]"


def _metadata_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if "guard_version" in summary:
        lines.append(f"- guard_version: {summary['guard_version']}")
    if "created_at" in summary:
        lines.append(f"- created_at: {summary['created_at']}")
    return lines


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
    if summary.get("mode") == "batch_analyze":
        content = _markdown_batch_analyze_report(summary)
    elif summary.get("mode") == "batch_compare":
        content = _markdown_batch_compare_report(summary)
    elif summary.get("mode") == "compare_reasoning":
        content = _markdown_compare_reasoning_report(summary)
    else:
        content = _markdown_basic_report(summary)
    path.write_text(content, encoding="utf-8")


def _markdown_title(summary: dict[str, Any]) -> str:
    if summary.get("mode") == "batch_analyze":
        return "# InferEdgeAIGuard Batch Analyze Report"
    if summary.get("mode") == "batch_compare":
        return "# InferEdgeAIGuard Batch Compare Report"
    if summary.get("mode") == "compare_reasoning":
        return "# InferEdgeAIGuard Compare Reasoning Report"
    if "base_count" in summary:
        return "# InferEdgeAIGuard Compare Report"
    return "# InferEdgeAIGuard Analyze Report"


def _markdown_basic_report(summary: dict[str, Any]) -> str:
    return f"{_markdown_title(summary)}\n\n```text\n{format_summary(summary)}\n```\n"


def _markdown_batch_analyze_report(summary: dict[str, Any]) -> str:
    sections = [
        _markdown_title(summary),
        _markdown_metadata_table(summary),
        "## Aggregate Summary",
        _markdown_table(
            ["Metric", "Value"],
            [
                ["input_dir", summary.get("input_dir", "")],
                ["sample_count", summary.get("sample_count", 0)],
                ["failure_sample_count", summary.get("failure_sample_count", 0)],
                ["failure_rate", _format_value(summary.get("failure_rate", 0.0))],
            ],
        ),
        _markdown_failure_type_counts(summary),
        "## Samples",
        _markdown_table(
            ["Path", "Image ID", "Precision", "Has Failure", "Failure Types"],
            [
                [
                    sample.get("path", ""),
                    sample.get("image_id", ""),
                    sample.get("precision", ""),
                    sample.get("has_failure", False),
                    _format_markdown_list(sample.get("failure_types", [])),
                ]
                for sample in summary.get("samples", [])
            ],
        ),
        _markdown_raw_cli_summary(summary),
    ]
    return "\n\n".join(sections) + "\n"


def _markdown_batch_compare_report(summary: dict[str, Any]) -> str:
    sections = [
        _markdown_title(summary),
        _markdown_metadata_table(summary),
        "## Aggregate Summary",
        _markdown_table(
            ["Metric", "Value"],
            [
                ["base_dir", summary.get("base_dir", "")],
                ["candidate_dir", summary.get("candidate_dir", "")],
                ["pair_count", summary.get("pair_count", 0)],
                ["failure_pair_count", summary.get("failure_pair_count", 0)],
                ["failure_rate", _format_value(summary.get("failure_rate", 0.0))],
            ],
        ),
        _markdown_failure_type_counts(summary),
        "## Unmatched Files",
        _markdown_table(
            ["Side", "Files"],
            [
                ["base", _format_markdown_list(summary.get("unmatched_base_files", []))],
                [
                    "candidate",
                    _format_markdown_list(summary.get("unmatched_candidate_files", [])),
                ],
            ],
        ),
        "## Pairs",
        _markdown_table(
            [
                "Filename",
                "Base Image ID",
                "Candidate Image ID",
                "Base Precision",
                "Candidate Precision",
                "Has Failure",
                "Failure Types",
            ],
            [
                [
                    pair.get("filename", ""),
                    pair.get("base_image_id", ""),
                    pair.get("candidate_image_id", ""),
                    pair.get("base_precision", ""),
                    pair.get("candidate_precision", ""),
                    pair.get("has_failure", False),
                    _format_markdown_list(pair.get("failure_types", [])),
                ]
                for pair in summary.get("pairs", [])
            ],
        ),
        _markdown_raw_cli_summary(summary),
    ]
    return "\n\n".join(sections) + "\n"


def _markdown_compare_reasoning_report(summary: dict[str, Any]) -> str:
    anomalies = summary.get("anomalies", [])
    anomaly_section = "No anomaly detected"
    if anomalies:
        anomaly_section = _markdown_table(
            ["Type", "Severity", "Message"],
            [
                [
                    anomaly.get("type", ""),
                    anomaly.get("severity", ""),
                    anomaly.get("message", ""),
                ]
                for anomaly in anomalies
            ],
        )

    sections = [
        _markdown_title(summary),
        "## Aggregate Summary",
        _markdown_table(
            ["Metric", "Value"],
            [
                ["status", summary.get("status", "unknown")],
                ["confidence", _format_value(summary.get("confidence", 0.0))],
            ],
        ),
        "## Anomalies",
        anomaly_section,
        "## Suspected Causes",
        _format_markdown_list(summary.get("suspected_causes", [])),
        "## Recommendations",
        _format_markdown_list(summary.get("recommendations", [])),
        _markdown_raw_cli_summary(summary),
    ]
    return "\n\n".join(sections) + "\n"


def _markdown_metadata_table(summary: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "## Metadata",
            _markdown_table(
                ["Field", "Value"],
                [
                    ["guard_version", summary.get("guard_version", "")],
                    ["created_at", summary.get("created_at", "")],
                ],
            ),
        ]
    )


def _markdown_failure_type_counts(summary: dict[str, Any]) -> str:
    failure_type_counts = summary.get("failure_type_counts", {})
    if not failure_type_counts:
        return "## Failure Type Counts\n\nNo failure detected"

    return "\n\n".join(
        [
            "## Failure Type Counts",
            _markdown_table(
                ["Failure Type", "Count"],
                [
                    [failure_type, count]
                    for failure_type, count in sorted(failure_type_counts.items())
                ],
            ),
        ]
    )


def _markdown_raw_cli_summary(summary: dict[str, Any]) -> str:
    return f"## Raw CLI Summary\n\n```text\n{format_summary(summary)}\n```"


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_markdown_cell(value) for value in row) + " |")
    return "\n".join(lines)


def _format_markdown_list(values: list[Any]) -> str:
    if not values:
        return "[]"
    return ", ".join(str(value) for value in values)


def _escape_markdown_cell(value: Any) -> str:
    text = _format_value(value)
    return text.replace("|", "\\|").replace("\n", " ")
