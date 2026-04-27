import subprocess
import sys
from pathlib import Path

from inferedge_aiguard.compare import compare_outputs
from inferedge_aiguard.detectors import summarize_failures
from inferedge_aiguard.schema import load_output_json


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    return load_output_json(ROOT / "examples" / name)


def test_normal_case_has_no_false_positive():
    summary = summarize_failures(load_example("fp32_normal.json"))

    assert summary["has_failure"] is False
    assert summary["failures"] == []


def test_bbox_collapse_detected():
    summary = summarize_failures(load_example("int8_bbox_collapse.json"))
    failure = summary["failures"][0]

    assert summary["has_failure"] is True
    assert failure["failure_type"] == "bbox_collapse"
    assert failure["affected_count"] == 1
    assert failure["total_count"] == 2
    assert failure["collapse_ratio"] == 0.5
    assert failure["threshold"] == 1e-6


def test_confidence_saturation_detected():
    summary = summarize_failures(load_example("int8_conf_saturation.json"))
    failure = summary["failures"][0]

    assert summary["has_failure"] is True
    assert failure["failure_type"] == "confidence_saturation"
    assert failure["total_count"] == 5
    assert failure["saturation_ratio"] == 1.0
    assert failure["ratio_threshold"] == 0.8


def test_detection_count_mismatch_detected():
    summary = compare_outputs(
        load_example("fp32_normal.json"),
        load_example("int8_count_mismatch.json"),
    )
    failure = summary["failures"][0]

    assert summary["has_failure"] is True
    assert summary["base_count"] == 3
    assert summary["candidate_count"] == 1
    assert failure["failure_type"] == "detection_count_mismatch"
    assert failure["base_count"] == 3
    assert failure["candidate_count"] == 1
    assert failure["mismatch_ratio"] == 2 / 3
    assert failure["threshold"] == 0.5


def test_cli_analyze_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(ROOT / "examples" / "fp32_normal.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "No failure detected" in result.stdout


def test_cli_analyze_bbox_collapse_shows_numeric_context():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(ROOT / "examples" / "int8_bbox_collapse.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "affected_count" in result.stdout or "collapse_ratio" in result.stdout


def test_cli_compare_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "compare",
            "--base",
            str(ROOT / "examples" / "fp32_normal.json"),
            "--candidate",
            str(ROOT / "examples" / "int8_count_mismatch.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "detection_count_mismatch" in result.stdout
    assert "mismatch_ratio" in result.stdout
