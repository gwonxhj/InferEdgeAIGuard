import json
import subprocess
import sys
from pathlib import Path
from shutil import copyfile

from inferedge_aiguard.batch import analyze_directory, compare_directories
from inferedge_aiguard.compare import compare_outputs
from inferedge_aiguard.detectors import get_detector_config, summarize_failures
from inferedge_aiguard.schema import load_output_json


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SINGLE_EXAMPLES = EXAMPLES / "single"
FP32_EXAMPLES = EXAMPLES / "fp32"
INT8_EXAMPLES = EXAMPLES / "int8"


def load_example(name: str) -> dict:
    return load_output_json(SINGLE_EXAMPLES / name)


def copy_example(name: str, destination: Path) -> None:
    copyfile(SINGLE_EXAMPLES / name, destination)


def assert_summary_metadata(summary: dict) -> None:
    assert summary["guard_version"] == "0.1.0"
    assert isinstance(summary["created_at"], str)
    assert summary["created_at"].endswith("Z")
    assert "detector_config" in summary
    assert_detector_config(summary["detector_config"])


def assert_detector_config(config: dict) -> None:
    assert "bbox_collapse" in config
    assert "confidence_saturation" in config
    assert "detection_count_mismatch" in config


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


def test_detector_config_contains_all_failure_definitions():
    config = get_detector_config()

    assert_detector_config(config)
    assert config["bbox_collapse"]["threshold"] == 1e-6
    assert config["confidence_saturation"]["ratio_threshold"] == 0.8
    assert config["detection_count_mismatch"]["threshold"] == 0.5


def test_summarize_failures_includes_metadata():
    summary = summarize_failures(load_example("fp32_normal.json"))

    assert_summary_metadata(summary)


def test_compare_outputs_includes_metadata():
    summary = compare_outputs(
        load_example("fp32_normal.json"),
        load_example("int8_count_mismatch.json"),
    )

    assert_summary_metadata(summary)


def test_cli_analyze_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(SINGLE_EXAMPLES / "fp32_normal.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "No failure detected" in result.stdout
    assert "guard_version" in result.stdout or "created_at" in result.stdout


def test_cli_analyze_bbox_collapse_shows_numeric_context():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(SINGLE_EXAMPLES / "int8_bbox_collapse.json"),
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
            str(SINGLE_EXAMPLES / "fp32_normal.json"),
            "--candidate",
            str(SINGLE_EXAMPLES / "int8_count_mismatch.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "detection_count_mismatch" in result.stdout
    assert "mismatch_ratio" in result.stdout


def test_analyze_directory_summarizes_examples():
    summary = analyze_directory(SINGLE_EXAMPLES)
    json_count = len(list(SINGLE_EXAMPLES.glob("*.json")))

    assert summary["mode"] == "batch_analyze"
    assert summary["sample_count"] == json_count
    assert summary["failure_rate"] > 0
    assert (
        "bbox_collapse" in summary["failure_type_counts"]
        or "confidence_saturation" in summary["failure_type_counts"]
    )
    assert all(
        {"path", "image_id", "precision", "has_failure", "failure_types"} <= sample.keys()
        for sample in summary["samples"]
    )


def test_analyze_directory_includes_metadata():
    summary = analyze_directory(SINGLE_EXAMPLES)

    assert_summary_metadata(summary)


def test_cli_batch_analyze_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-analyze",
            "--input-dir",
            str(SINGLE_EXAMPLES),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "InferEdgeAIGuard batch analyze summary" in result.stdout
    assert "sample_count" in result.stdout
    assert "failure_rate" in result.stdout


def test_analyze_directory_empty_dir(tmp_path):
    summary = analyze_directory(tmp_path)

    assert summary["sample_count"] == 0
    assert summary["failure_sample_count"] == 0
    assert summary["failure_rate"] == 0.0
    assert summary["failure_type_counts"] == {}
    assert summary["samples"] == []


def test_compare_directories_matches_common_filenames(tmp_path):
    base_dir = tmp_path / "base"
    candidate_dir = tmp_path / "candidate"
    base_dir.mkdir()
    candidate_dir.mkdir()
    copy_example("fp32_normal.json", base_dir / "sample_001.json")
    copy_example("int8_count_mismatch.json", candidate_dir / "sample_001.json")
    copy_example("fp32_normal.json", base_dir / "base_only.json")
    copy_example("int8_count_mismatch.json", candidate_dir / "candidate_only.json")

    summary = compare_directories(base_dir, candidate_dir)

    assert summary["mode"] == "batch_compare"
    assert summary["pair_count"] == 1
    assert summary["failure_rate"] > 0
    assert "detection_count_mismatch" in summary["failure_type_counts"]
    assert summary["unmatched_base_files"] == ["base_only.json"]
    assert summary["unmatched_candidate_files"] == ["candidate_only.json"]
    assert summary["pairs"][0]["filename"] == "sample_001.json"
    assert summary["pairs"][0]["base_precision"] == "fp32"
    assert summary["pairs"][0]["candidate_precision"] == "int8"
    assert summary["pairs"][0]["failure_types"] == ["detection_count_mismatch"]


def test_cli_batch_compare_runs(tmp_path):
    base_dir = tmp_path / "base"
    candidate_dir = tmp_path / "candidate"
    base_dir.mkdir()
    candidate_dir.mkdir()
    copy_example("fp32_normal.json", base_dir / "sample_001.json")
    copy_example("int8_count_mismatch.json", candidate_dir / "sample_001.json")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-compare",
            "--base-dir",
            str(base_dir),
            "--candidate-dir",
            str(candidate_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "InferEdgeAIGuard batch compare summary" in result.stdout
    assert "pair_count" in result.stdout
    assert "failure_rate" in result.stdout
    assert "detection_count_mismatch" in result.stdout


def test_compare_directories_zero_pairs(tmp_path):
    base_dir = tmp_path / "base"
    candidate_dir = tmp_path / "candidate"
    base_dir.mkdir()
    candidate_dir.mkdir()
    copy_example("fp32_normal.json", base_dir / "base_only.json")
    copy_example("int8_count_mismatch.json", candidate_dir / "candidate_only.json")

    summary = compare_directories(base_dir, candidate_dir)

    assert summary["pair_count"] == 0
    assert summary["failure_pair_count"] == 0
    assert summary["failure_rate"] == 0.0
    assert summary["failure_type_counts"] == {}
    assert summary["unmatched_base_files"] == ["base_only.json"]
    assert summary["unmatched_candidate_files"] == ["candidate_only.json"]


def test_compare_directories_examples_pair_fixtures():
    summary = compare_directories(FP32_EXAMPLES, INT8_EXAMPLES)

    assert summary["pair_count"] == 3
    assert summary["failure_rate"] > 0
    assert (
        "detection_count_mismatch" in summary["failure_type_counts"]
        or "bbox_collapse" in summary["failure_type_counts"]
        or "confidence_saturation" in summary["failure_type_counts"]
    )


def test_compare_directories_includes_metadata():
    summary = compare_directories(FP32_EXAMPLES, INT8_EXAMPLES)

    assert_summary_metadata(summary)


def test_cli_batch_compare_examples_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-compare",
            "--base-dir",
            str(FP32_EXAMPLES),
            "--candidate-dir",
            str(INT8_EXAMPLES),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "pair_count" in result.stdout
    assert "failure_rate" in result.stdout


def test_cli_analyze_save_json(tmp_path):
    output_path = tmp_path / "reports" / "analyze_normal.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(SINGLE_EXAMPLES / "fp32_normal.json"),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.exists()
    assert "has_failure" in saved
    assert "failures" in saved
    assert "detector_config" in saved


def test_cli_analyze_save_markdown(tmp_path):
    output_path = tmp_path / "reports" / "analyze_normal.md"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "analyze",
            "--input",
            str(SINGLE_EXAMPLES / "fp32_normal.json"),
            "--save-md",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert output_path.exists()
    assert (
        "InferEdgeAIGuard Analyze Report" in content
        or "No failure detected" in content
    )


def test_cli_batch_analyze_save_json(tmp_path):
    output_path = tmp_path / "reports" / "batch_analyze.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-analyze",
            "--input-dir",
            str(SINGLE_EXAMPLES),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.exists()
    assert saved["mode"] == "batch_analyze"


def test_cli_batch_compare_save_markdown(tmp_path):
    base_dir = tmp_path / "base"
    candidate_dir = tmp_path / "candidate"
    output_path = tmp_path / "reports" / "batch_compare.md"
    base_dir.mkdir()
    candidate_dir.mkdir()
    copy_example("fp32_normal.json", base_dir / "sample_001.json")
    copy_example("int8_count_mismatch.json", candidate_dir / "sample_001.json")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-compare",
            "--base-dir",
            str(base_dir),
            "--candidate-dir",
            str(candidate_dir),
            "--save-md",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert output_path.exists()
    assert "Batch Compare Report" in content or "pair_count" in content
