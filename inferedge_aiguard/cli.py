"""Command-line interface for InferEdgeAIGuard."""

from __future__ import annotations

import argparse

from .batch import analyze_directory, compare_directories
from .compare import compare_outputs
from .detectors import summarize_failures
from .report import format_summary
from .schema import load_output_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inferedge-aiguard",
        description="Detect likely Edge AI inference output failures.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one output JSON")
    analyze_parser.add_argument("--input", required=True, help="Path to output JSON")

    compare_parser = subparsers.add_parser(
        "compare", help="Compare FP32 baseline and candidate output JSON"
    )
    compare_parser.add_argument("--base", required=True, help="Path to FP32 output JSON")
    compare_parser.add_argument(
        "--candidate", required=True, help="Path to candidate output JSON"
    )

    batch_parser = subparsers.add_parser(
        "batch-analyze", help="Analyze all output JSON files in a directory"
    )
    batch_parser.add_argument(
        "--input-dir", required=True, help="Directory containing output JSON files"
    )

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        output = load_output_json(args.input)
        print(format_summary(summarize_failures(output)))
        return 0

    if args.command == "compare":
        base = load_output_json(args.base)
        candidate = load_output_json(args.candidate)
        print(format_summary(compare_outputs(base, candidate)))
        return 0

    if args.command == "batch-analyze":
        print(format_summary(analyze_directory(args.input_dir)))
        return 0

    if args.command == "batch-compare":
        print(format_summary(compare_directories(args.base_dir, args.candidate_dir)))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
