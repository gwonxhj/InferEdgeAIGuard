"""Command-line interface for InferEdgeAIGuard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch import analyze_directory, compare_directories
from .compare import compare_outputs
from .detectors import summarize_failures
from .reasoning import analyze_compare_result
from .report import format_summary, save_summary_json, save_summary_markdown
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

    reason_compare_parser = subparsers.add_parser(
        "reason-compare",
        help="Reason over an InferEdgeLab compare result JSON file",
    )
    reason_compare_parser.add_argument(
        "--input", required=True, help="Path to InferEdgeLab compare result JSON"
    )
    _add_save_options(reason_compare_parser)

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

    if args.command == "reason-compare":
        compare_result = _load_json_dict(args.input)
        _emit_summary(
            analyze_compare_result(compare_result),
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


def _load_json_dict(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
