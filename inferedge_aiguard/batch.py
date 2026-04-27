"""Batch evaluation utilities for inference output JSON files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .detectors import summarize_failures
from .schema import load_output_json


def analyze_directory(input_dir: str | Path) -> dict[str, Any]:
    """Analyze all JSON outputs in a directory and aggregate failure signals."""

    directory = Path(input_dir)
    if not directory.exists():
        raise FileNotFoundError(f"input_dir does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"input_dir must be a directory: {directory}")

    json_paths = sorted(directory.glob("*.json"), key=lambda path: path.name)
    samples: list[dict[str, Any]] = []
    failure_type_counts: dict[str, int] = {}
    failure_sample_count = 0

    for path in json_paths:
        output = load_output_json(path)
        summary = summarize_failures(output)
        failures = summary["failures"]
        failure_types = [failure["failure_type"] for failure in failures]

        if summary["has_failure"]:
            failure_sample_count += 1

        for failure_type in failure_types:
            failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1

        samples.append(
            {
                "path": str(path),
                "image_id": summary["image_id"],
                "precision": summary["precision"],
                "has_failure": summary["has_failure"],
                "failure_types": failure_types,
            }
        )

    sample_count = len(samples)
    failure_rate = failure_sample_count / sample_count if sample_count else 0.0

    return {
        "mode": "batch_analyze",
        "input_dir": str(directory),
        "sample_count": sample_count,
        "failure_sample_count": failure_sample_count,
        "failure_rate": failure_rate,
        "failure_type_counts": failure_type_counts,
        "samples": samples,
    }
