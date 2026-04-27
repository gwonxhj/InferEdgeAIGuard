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

    assert summary["has_failure"] is True
    assert summary["failures"][0]["failure_type"] == "bbox_collapse"
    assert summary["failures"][0]["affected_count"] == 1


def test_confidence_saturation_detected():
    summary = summarize_failures(load_example("int8_conf_saturation.json"))

    assert summary["has_failure"] is True
    assert summary["failures"][0]["failure_type"] == "confidence_saturation"


def test_detection_count_mismatch_detected():
    summary = compare_outputs(
        load_example("fp32_normal.json"),
        load_example("int8_count_mismatch.json"),
    )

    assert summary["has_failure"] is True
    assert summary["base_count"] == 3
    assert summary["candidate_count"] == 1
    assert summary["failures"][0]["failure_type"] == "detection_count_mismatch"


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
