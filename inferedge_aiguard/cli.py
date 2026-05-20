"""Command-line interface for InferEdgeAIGuard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import normalize_lab_compare_result
from .batch import analyze_directory, compare_directories
from .compare import compare_outputs
from .detectors import summarize_failures
from .history import analyze_run_history
from .portfolio_demo import build_portfolio_demo_bundle
from .reasoning import analyze_compare_result, analyze_structured_result
from .report import format_summary, save_summary_json, save_summary_markdown
from .runtime_reliability import analyze_orchestration_summary, analyze_runtime_result
from .schema import load_output_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inferedge-aiguard",
        description="Detect likely Edge AI inference output failures.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one output JSON")
    analyze_parser.add_argument("--input", required=True, help="Path to output JSON")
    _add_save_options(analyze_parser)

    compare_parser = subparsers.add_parser(
        "compare", help="Compare FP32 baseline and candidate output JSON"
    )
    compare_parser.add_argument("--base", required=True, help="Path to FP32 output JSON")
    compare_parser.add_argument(
        "--candidate", required=True, help="Path to candidate output JSON"
    )
    _add_save_options(compare_parser)

    batch_parser = subparsers.add_parser(
        "batch-analyze", help="Analyze all output JSON files in a directory"
    )
    batch_parser.add_argument(
        "--input-dir", required=True, help="Directory containing output JSON files"
    )
    _add_save_options(batch_parser)

    batch_compare_parser = subparsers.add_parser(
        "batch-compare",
        help="Compare matching baseline and candidate output JSON files by filename",
    )
    batch_compare_parser.add_argument(
        "--base-dir", required=True, help="Directory containing FP32 output JSON files"
    )
    batch_compare_parser.add_argument(
        "--candidate-dir",
        required=True,
        help="Directory containing candidate output JSON files",
    )
    _add_save_options(batch_compare_parser)

    reason_parser = subparsers.add_parser(
        "reason",
        help="Auto-route an InferEdgeLab JSON file to the appropriate reasoning path",
    )
    reason_parser.add_argument(
        "--input", required=True, help="Path to InferEdgeLab reasoning input JSON"
    )
    _add_save_options(reason_parser)

    reason_compare_parser = subparsers.add_parser(
        "reason-compare",
        help="Reason over an InferEdgeLab compare result JSON file",
    )
    reason_compare_parser.add_argument(
        "--input", required=True, help="Path to InferEdgeLab compare result JSON"
    )
    _add_save_options(reason_compare_parser)

    reason_result_parser = subparsers.add_parser(
        "reason-result",
        help="Reason over an InferEdgeLab structured result JSON file",
    )
    reason_result_parser.add_argument(
        "--input", required=True, help="Path to InferEdgeLab structured result JSON"
    )
    _add_save_options(reason_result_parser)

    reason_history_parser = subparsers.add_parser(
        "reason-history",
        help="Reason over an InferEdgeLab structured result history JSON file",
    )
    reason_history_parser.add_argument(
        "--input",
        required=True,
        help="Path to InferEdgeLab structured result history JSON list",
    )
    _add_save_options(reason_history_parser)

    reason_orchestration_parser = subparsers.add_parser(
        "reason-orchestration",
        help="Reason over an InferEdgeOrchestrator orchestration summary JSON file",
    )
    reason_orchestration_parser.add_argument(
        "--input",
        required=True,
        help="Path to InferEdgeOrchestrator orchestration summary JSON",
    )
    _add_save_options(reason_orchestration_parser)

    reason_runtime_parser = subparsers.add_parser(
        "reason-runtime",
        help="Reason over an InferEdge Runtime result JSON with operation evidence",
    )
    reason_runtime_parser.add_argument(
        "--input",
        required=True,
        help="Path to InferEdge Runtime result JSON",
    )
    _add_save_options(reason_runtime_parser)

    portfolio_demo_parser = subparsers.add_parser(
        "portfolio-demo",
        help="Replay bundled AIGuard portfolio demo cases",
    )
    _add_save_options(portfolio_demo_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        output = load_output_json(args.input)
        _emit_summary(
            summarize_failures(output),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "compare":
        base = load_output_json(args.base)
        candidate = load_output_json(args.candidate)
        _emit_summary(
            compare_outputs(base, candidate),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "batch-analyze":
        _emit_summary(
            analyze_directory(args.input_dir),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "batch-compare":
        _emit_summary(
            compare_directories(args.base_dir, args.candidate_dir),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason":
        raw = _load_json(args.input)
        _emit_summary(
            _infer_reasoning_summary(raw),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason-compare":
        raw = _load_json_dict(args.input)
        compare_result = normalize_lab_compare_result(raw)
        _emit_summary(
            analyze_compare_result(compare_result),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason-result":
        raw = _load_json_dict(args.input)
        _emit_summary(
            analyze_structured_result(raw),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason-history":
        raw = _load_json_list(args.input)
        _emit_summary(
            analyze_run_history(raw),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason-orchestration":
        raw = _load_json_dict(args.input)
        _emit_summary(
            analyze_orchestration_summary(raw),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "reason-runtime":
        raw = _load_json_dict(args.input)
        _emit_summary(
            analyze_runtime_result(raw),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    if args.command == "portfolio-demo":
        _emit_summary(
            build_portfolio_demo_bundle(),
            save_json=args.save_json,
            save_md=args.save_md,
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _add_save_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--save-json", help="Path to save the raw summary JSON")
    parser.add_argument("--save-md", help="Path to save the formatted Markdown report")


def _emit_summary(
    summary: dict,
    save_json: str | None = None,
    save_md: str | None = None,
) -> None:
    print(format_summary(summary))
    if save_json:
        save_summary_json(summary, save_json)
        print(f"- saved_json: {save_json}")
    if save_md:
        save_summary_markdown(summary, save_md)
        print(f"- saved_md: {save_md}")


def _infer_reasoning_summary(data: object) -> dict:
    if isinstance(data, list):
        return analyze_run_history(data)

    if not isinstance(data, dict):
        raise ValueError("Unable to infer reasoning input type: expected JSON object or list")

    if _looks_like_compare_result(data):
        return analyze_compare_result(normalize_lab_compare_result(data))

    if _looks_like_runtime_operation_result(data):
        return analyze_runtime_result(data)

    if _looks_like_structured_result(data):
        return analyze_structured_result(data)

    if _looks_like_orchestration_summary(data):
        return analyze_orchestration_summary(data)

    raise ValueError("Unable to infer reasoning input type from JSON object")


def _looks_like_compare_result(data: dict) -> bool:
    compare_keys = {
        "comparison_mode",
        "precision_pair",
        "overall_judgement",
        "overall_judgment",
        "mean_judgement",
        "mean_judgment",
        "latency_delta_pct",
        "mean_delta_pct",
        "shape_match",
        "shape_matched",
        "run_config_match",
        "run_config_matched",
        "compare_result",
        "comparison",
    }
    return any(key in data for key in compare_keys)


def _looks_like_structured_result(data: dict) -> bool:
    structured_keys = {
        "model",
        "engine",
        "device",
        "precision",
        "mean_ms",
        "p99_ms",
        "run_config",
        "system",
        "extra",
    }
    return any(key in data for key in structured_keys)


def _looks_like_runtime_operation_result(data: dict) -> bool:
    if data.get("schema_version") == "inferedge-runtime-result-v1":
        return True
    return any(
        key in data
        for key in {
            "runtime_health_snapshot",
            "runtime_error_classification",
            "runtime_events",
        }
    )


def _looks_like_orchestration_summary(data: dict) -> bool:
    if data.get("schema_version") == "inferedge-orchestration-summary-v1":
        return True
    agent_runtime_summary = data.get("agent_runtime_summary")
    if isinstance(agent_runtime_summary, dict):
        if agent_runtime_summary.get("schema_version") == "inferedge-orchestration-summary-v1":
            return True
        if "policy_decision_log" in data or "policy_decisions" in data:
            return True
    return False


def _load_json(path: str) -> object:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_json_dict(path: str) -> dict:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _load_json_list(path: str) -> list:
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
