"""Batch evaluation utilities for inference output JSON files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .compare import compare_outputs
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


def compare_directories(base_dir: str | Path, candidate_dir: str | Path) -> dict[str, Any]:
    """Compare matching JSON outputs in two directories and aggregate failures."""

    base_directory = _validate_directory(base_dir, "base_dir")
    candidate_directory = _validate_directory(candidate_dir, "candidate_dir")

    base_paths = {path.name: path for path in base_directory.glob("*.json")}
    candidate_paths = {path.name: path for path in candidate_directory.glob("*.json")}
    base_filenames = set(base_paths)
    candidate_filenames = set(candidate_paths)
    matched_filenames = sorted(base_filenames & candidate_filenames)

    pairs: list[dict[str, Any]] = []
    failure_type_counts: dict[str, int] = {}
    failure_pair_count = 0

    for filename in matched_filenames:
        base_output = load_output_json(base_paths[filename])
        candidate_output = load_output_json(candidate_paths[filename])
        summary = compare_outputs(base_output, candidate_output)
        failures = summary["failures"]
        failure_types = [failure["failure_type"] for failure in failures]

        if summary["has_failure"]:
            failure_pair_count += 1

        for failure_type in failure_types:
            failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1

        pairs.append(
            {
                "filename": filename,
                "base_image_id": base_output["image_id"],
                "candidate_image_id": candidate_output["image_id"],
                "base_precision": base_output["precision"],
                "candidate_precision": candidate_output["precision"],
                "has_failure": summary["has_failure"],
                "failure_types": failure_types,
            }
        )

    pair_count = len(pairs)
    failure_rate = failure_pair_count / pair_count if pair_count else 0.0

    return {
        "mode": "batch_compare",
        "base_dir": str(base_directory),
        "candidate_dir": str(candidate_directory),
        "pair_count": pair_count,
        "failure_pair_count": failure_pair_count,
        "failure_rate": failure_rate,
        "failure_type_counts": failure_type_counts,
        "unmatched_base_files": sorted(base_filenames - candidate_filenames),
        "unmatched_candidate_files": sorted(candidate_filenames - base_filenames),
        "pairs": pairs,
    }


def _validate_directory(path: str | Path, label: str) -> Path:
    directory = Path(path)
    if not directory.exists():
        raise FileNotFoundError(f"{label} does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"{label} must be a directory: {directory}")
    return directory
