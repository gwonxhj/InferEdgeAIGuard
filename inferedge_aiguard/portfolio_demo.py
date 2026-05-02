"""Portfolio demo case bundle for evidence-based AIGuard diagnosis.

Phase 6 packages existing detectors into small, reproducible demo cases. The
bundle is intentionally static and local-first: it does not add a service,
database, queue, or Lab ownership change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline import compare_detection_quality
from .evidence_detectors import analyze_guard_analysis
from .schema import validate_diagnosis_report
from .temporal import analyze_temporal_consistency


PORTFOLIO_DEMO_SCHEMA_VERSION = "inferedge-aiguard-portfolio-demo-v1"
ROOT = Path(__file__).resolve().parents[1]
SINGLE_EXAMPLES = ROOT / "examples" / "single"


def build_portfolio_demo_bundle() -> dict[str, Any]:
    """Build the Phase 6 portfolio demo bundle.

    Cases:
    - normal output quality evidence
    - latency improvement with bbox collapse
    - confidence score saturation
    - temporal instability without tracking dependencies
    """

    normal = _load_single("fp32_normal.json")
    bbox_collapse = _load_single("int8_bbox_collapse.json")
    score_saturation = _load_single("int8_conf_saturation.json")

    normal_report = analyze_guard_analysis(
        normal,
        source={"runtime_result_path": "examples/single/fp32_normal.json"},
    )
    bbox_report = compare_detection_quality(
        normal,
        bbox_collapse,
        baseline_label="fp32_baseline",
        candidate_label="int8_bbox_collapse",
        baseline_latency_ms=45.43,
        candidate_latency_ms=12.0,
        source={
            "baseline_result_path": "examples/single/fp32_normal.json",
            "candidate_result_path": "examples/single/int8_bbox_collapse.json",
        },
    )
    score_report = compare_detection_quality(
        normal,
        score_saturation,
        baseline_label="fp32_baseline",
        candidate_label="int8_score_saturation",
        baseline_latency_ms=45.43,
        candidate_latency_ms=14.5,
        source={
            "baseline_result_path": "examples/single/fp32_normal.json",
            "candidate_result_path": "examples/single/int8_conf_saturation.json",
        },
    )
    temporal_report = analyze_temporal_consistency(
        _temporal_instability_sequence(),
        thresholds={"zero_detection_frame_ratio_blocked": 1.0},
        source={"sequence_path": "examples/portfolio_demo/temporal_instability"},
    )

    cases = [
        _case(
            case_id="normal_pass",
            title="Normal output quality",
            category="normal",
            summary="BBox and score evidence stay within configured thresholds.",
            report=normal_report,
        ),
        _case(
            case_id="bbox_collapse_blocked",
            title="Latency improvement with bbox collapse",
            category="bbox_quality",
            summary=(
                "Candidate latency improves, but bbox collapse increases enough "
                "to block deployment review."
            ),
            report=bbox_report,
        ),
        _case(
            case_id="score_saturation_blocked",
            title="Confidence score saturation",
            category="confidence_distribution",
            summary=(
                "Candidate scores concentrate near 0 or 1, indicating possible "
                "quantization or postprocess risk."
            ),
            report=score_report,
        ),
        _case(
            case_id="temporal_instability_review",
            title="Temporal instability",
            category="temporal_consistency",
            summary=(
                "Frame-level detection count variance is high enough to require "
                "review before deployment."
            ),
            report=temporal_report,
        ),
    ]
    for case in cases:
        validate_diagnosis_report(case["guard_analysis"])

    return {
        "schema_version": PORTFOLIO_DEMO_SCHEMA_VERSION,
        "source": "InferEdgeAIGuard Phase 6 portfolio demo cases",
        "scope": "local-first evidence replay",
        "case_count": len(cases),
        "cases": cases,
    }


def portfolio_demo_bundle_to_markdown(bundle: dict[str, Any]) -> str:
    """Render the demo bundle as a compact Markdown report."""

    lines = [
        "# InferEdgeAIGuard Portfolio Demo Cases",
        "",
        f"- schema_version: {bundle.get('schema_version')}",
        f"- scope: {bundle.get('scope')}",
        f"- case_count: {bundle.get('case_count')}",
        "",
        "| Case | Category | Guard verdict | Severity | Summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in bundle.get("cases", []):
        report = case.get("guard_analysis", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape(case.get("title", "")),
                    _escape(case.get("category", "")),
                    _escape(report.get("guard_verdict", "")),
                    _escape(report.get("severity", "")),
                    _escape(case.get("summary", "")),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Review Notes"])
    for case in bundle.get("cases", []):
        report = case.get("guard_analysis", {})
        lines.extend(
            [
                "",
                f"### {case.get('title')}",
                f"- guard_verdict: {report.get('guard_verdict')}",
                f"- primary_reason: {report.get('primary_reason')}",
                f"- recommendation: {_first_recommendation(report)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _case(
    *,
    case_id: str,
    title: str,
    category: str,
    summary: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "title": title,
        "category": category,
        "summary": summary,
        "guard_analysis": report,
    }


def _load_single(file_name: str) -> dict[str, Any]:
    with (SINGLE_EXAMPLES / file_name).open("r", encoding="utf-8") as file:
        return json.load(file)


def _temporal_instability_sequence() -> dict[str, Any]:
    return {
        "sequence_id": "temporal_instability_demo",
        "frames": [
            {"frame_id": "0", "timestamp_ms": 0, "detections": []},
            {
                "frame_id": "1",
                "timestamp_ms": 33,
                "detections": [
                    {"class_id": 0, "confidence": 0.71, "bbox": [10, 20, 30, 40]}
                    for _ in range(10)
                ],
            },
            {"frame_id": "2", "timestamp_ms": 66, "detections": []},
            {
                "frame_id": "3",
                "timestamp_ms": 99,
                "detections": [
                    {"class_id": 0, "confidence": 0.69, "bbox": [12, 22, 30, 40]}
                    for _ in range(10)
                ],
            },
            {"frame_id": "4", "timestamp_ms": 132, "detections": []},
        ],
    }


def _first_recommendation(report: dict[str, Any]) -> str:
    recommendations = report.get("recommendations") or []
    return str(recommendations[0]) if recommendations else ""


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
