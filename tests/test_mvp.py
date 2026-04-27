import json
import subprocess
import sys
from pathlib import Path
from shutil import copyfile

from inferedge_aiguard.adapters import normalize_lab_compare_result
from inferedge_aiguard.batch import analyze_directory, compare_directories
from inferedge_aiguard.compare import compare_outputs
from inferedge_aiguard.detectors import get_detector_config, summarize_failures
from inferedge_aiguard.history import analyze_run_history
from inferedge_aiguard.reasoning import analyze_compare_result, analyze_structured_result
from inferedge_aiguard.report import format_summary, save_summary_json, save_summary_markdown
from inferedge_aiguard.schema import load_output_json


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SINGLE_EXAMPLES = EXAMPLES / "single"
FP32_EXAMPLES = EXAMPLES / "fp32"
INT8_EXAMPLES = EXAMPLES / "int8"
LAB_COMPARE_EXAMPLES = EXAMPLES / "lab_compare"
LAB_RESULT_EXAMPLES = EXAMPLES / "lab_result"
LAB_HISTORY_EXAMPLES = EXAMPLES / "lab_history"


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


def test_cli_batch_analyze_save_markdown_tables(tmp_path):
    output_path = tmp_path / "reports" / "batch_analyze.md"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "batch-analyze",
            "--input-dir",
            str(SINGLE_EXAMPLES),
            "--save-md",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Metadata" in content
    assert "## Aggregate Summary" in content
    assert "## Failure Type Counts" in content
    assert "## Samples" in content
    assert "| Metric | Value |" in content
    assert "failure_rate" in content


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
    assert "## Metadata" in content
    assert "## Aggregate Summary" in content
    assert "## Failure Type Counts" in content
    assert "## Unmatched Files" in content
    assert "## Pairs" in content
    assert "| Filename | Base Image ID | Candidate Image ID" in content
    assert "pair_count" in content


def test_reasoning_shape_mismatch_is_error():
    summary = analyze_compare_result({"shape_match": False})

    assert summary["status"] == "error"
    assert summary["anomalies"][0]["type"] == "unreliable_comparison"
    assert "input_shape_mismatch" in summary["suspected_causes"]


def test_reasoning_run_config_mismatch_is_error():
    summary = analyze_compare_result({"run_config_match": False})

    assert summary["status"] == "error"
    assert any(
        anomaly["type"] == "unreliable_comparison"
        for anomaly in summary["anomalies"]
    )
    assert "run_config_mismatch" in summary["suspected_causes"]


def test_reasoning_latency_improvement_without_accuracy_warns():
    summary = analyze_compare_result({"overall_judgement": "improvement"})

    assert summary["status"] == "warning"
    assert any(
        anomaly["type"] == "accuracy_missing_warning"
        for anomaly in summary["anomalies"]
    )
    assert "missing_accuracy_validation" in summary["suspected_causes"]


def test_reasoning_latency_improvement_with_accuracy_drop_warns():
    summary = analyze_compare_result(
        {
            "overall_judgement": "improvement",
            "accuracy_delta": -0.03,
        }
    )

    assert summary["status"] == "warning"
    assert any(anomaly["type"] == "risky_tradeoff" for anomaly in summary["anomalies"])
    assert "possible_quantization_accuracy_loss" in summary["suspected_causes"]


def test_reasoning_cross_precision_large_latency_delta_warns():
    summary = analyze_compare_result(
        {
            "comparison_mode": "cross_precision",
            "latency_delta_pct": -45.0,
            "accuracy": 0.9,
        }
    )

    assert summary["status"] == "warning"
    assert any(
        anomaly["type"] == "likely_quantization_effect"
        for anomaly in summary["anomalies"]
    )
    assert "precision_or_runtime_change" in summary["suspected_causes"]


def test_reasoning_ok_result_has_no_anomalies():
    summary = analyze_compare_result(
        {
            "shape_match": True,
            "run_config_match": True,
            "overall_judgement": "same",
            "accuracy": 0.9,
            "latency_delta_pct": 2.0,
        }
    )

    assert summary["status"] == "ok"
    assert summary["anomalies"] == []
    assert summary["confidence"] == 0.5


def test_reasoning_format_summary_includes_status_and_recommendations():
    summary = analyze_compare_result({"shape_matched": False})
    formatted = format_summary(summary)

    assert "InferEdgeAIGuard compare reasoning summary" in formatted
    assert "status" in formatted
    assert "recommendations" in formatted


def test_reasoning_save_json_preserves_mode(tmp_path):
    output_path = tmp_path / "reasoning.json"
    summary = analyze_compare_result({"mean_judgement": "improvement"})

    save_summary_json(summary, output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved["mode"] == "compare_reasoning"


def test_cli_reason_compare_runs_cross_precision_example():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-compare",
            "--input",
            str(LAB_COMPARE_EXAMPLES / "cross_precision_latency_only.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "InferEdgeAIGuard compare reasoning summary" in result.stdout
    assert "status" in result.stdout
    assert (
        "accuracy_missing_warning" in result.stdout
        or "likely_quantization_effect" in result.stdout
    )


def test_cli_reason_compare_save_json(tmp_path):
    output_path = tmp_path / "reports" / "reasoning.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-compare",
            "--input",
            str(LAB_COMPARE_EXAMPLES / "cross_precision_latency_only.json"),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["mode"] == "compare_reasoning"
    assert "status" in saved
    assert "anomalies" in saved
    assert "recommendations" in saved


def test_cli_reason_compare_save_markdown(tmp_path):
    output_path = tmp_path / "reports" / "reasoning.md"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-compare",
            "--input",
            str(LAB_COMPARE_EXAMPLES / "cross_precision_latency_only.json"),
            "--save-md",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "Compare Reasoning Report" in content
    assert "Aggregate Summary" in content
    assert "Anomalies" in content
    assert "Recommendations" in content


def test_cli_reason_compare_shape_mismatch_example():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-compare",
            "--input",
            str(LAB_COMPARE_EXAMPLES / "invalid_shape_mismatch.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "unreliable_comparison" in result.stdout


def test_adapter_normalizes_shape_alias():
    normalized = normalize_lab_compare_result({"shape_matched": True})

    assert normalized["shape_match"] is True


def test_adapter_normalizes_run_config_alias():
    normalized = normalize_lab_compare_result({"run_config_matched": False})

    assert normalized["run_config_match"] is False


def test_adapter_normalizes_latency_delta_alias():
    normalized = normalize_lab_compare_result({"mean_delta_pct": -42.0})

    assert normalized["latency_delta_pct"] == -42.0


def test_adapter_normalizes_judgement_alias():
    normalized = normalize_lab_compare_result({"overall_judgment": "improvement"})

    assert normalized["overall_judgement"] == "improvement"


def test_adapter_extracts_nested_accuracy_and_delta():
    normalized = normalize_lab_compare_result(
        {
            "base": {"accuracy": 0.76},
            "candidate": {"accuracy": 0.72},
        }
    )

    assert normalized["base_accuracy"] == 0.76
    assert normalized["candidate_accuracy"] == 0.72
    assert normalized["accuracy_delta"] == 0.72 - 0.76


def test_adapter_normalizes_metrics_accuracy_delta():
    normalized = normalize_lab_compare_result({"metrics": {"accuracy_delta": -0.04}})

    assert normalized["accuracy_delta"] == -0.04


def test_adapter_normalizes_nested_compare_result():
    normalized = normalize_lab_compare_result(
        {
            "compare_result": {
                "overall_judgment": "improvement",
                "shape_matched": True,
                "run_config_matched": True,
                "mean_delta_pct": -42.0,
                "precision_comparison": "fp32_vs_int8",
            }
        }
    )

    assert normalized["overall_judgement"] == "improvement"
    assert normalized["shape_match"] is True
    assert normalized["run_config_match"] is True
    assert normalized["latency_delta_pct"] == -42.0
    assert normalized["precision_pair"] == "fp32_vs_int8"


def test_cli_reason_compare_alias_schema_example():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-compare",
            "--input",
            str(LAB_COMPARE_EXAMPLES / "alias_schema_example.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (
        "accuracy_missing_warning" in result.stdout
        or "unreliable_comparison" in result.stdout
    )
    assert "likely_quantization_effect" in result.stdout


def load_lab_result(name: str) -> dict:
    return json.loads((LAB_RESULT_EXAMPLES / name).read_text(encoding="utf-8"))


def anomaly_types(summary: dict) -> list[str]:
    return [anomaly.get("type") for anomaly in summary.get("anomalies", [])]


def test_structured_result_valid_fp32_is_ok():
    summary = analyze_structured_result(load_lab_result("valid_fp32_result.json"))

    assert summary["status"] == "ok"
    assert summary["anomalies"] == []


def test_structured_result_suspicious_int8_has_accuracy_warning():
    summary = analyze_structured_result(
        load_lab_result("suspicious_int8_missing_accuracy.json")
    )

    assert summary["status"] in {"warning", "error"}
    assert "accuracy_missing_warning" in anomaly_types(summary)


def test_structured_result_missing_runtime_artifact_detected():
    summary = analyze_structured_result(
        load_lab_result("suspicious_int8_missing_accuracy.json")
    )

    assert "missing_runtime_artifact" in anomaly_types(summary)


def test_structured_result_missing_resolved_input_shapes_detected():
    summary = analyze_structured_result(
        load_lab_result("suspicious_int8_missing_accuracy.json")
    )

    assert "missing_resolved_input_shapes" in anomaly_types(summary)


def test_structured_result_latency_instability_detected():
    summary = analyze_structured_result(
        load_lab_result("suspicious_int8_missing_accuracy.json")
    )

    assert "latency_instability" in anomaly_types(summary)


def test_structured_result_missing_identity_field_is_error():
    summary = analyze_structured_result(
        {
            "engine": "onnxruntime",
            "device": "cpu",
            "precision": "fp32",
            "mean_ms": 1.0,
            "p99_ms": 1.2,
            "run_config": {"runs": 3},
            "system": {"os": "linux"},
            "extra": {
                "runtime_artifact_path": "model.onnx",
                "resolved_input_shapes": {"input": [1, 3, 224, 224]},
            },
        }
    )

    assert summary["status"] == "error"
    assert "missing_identity_field" in anomaly_types(summary)


def test_structured_result_missing_latency_metric_is_error():
    result = load_lab_result("valid_fp32_result.json")
    result.pop("p99_ms")
    summary = analyze_structured_result(result)

    assert summary["status"] == "error"
    assert "missing_latency_metric" in anomaly_types(summary)


def test_structured_result_invalid_latency_value_is_error():
    result = load_lab_result("valid_fp32_result.json")
    result["mean_ms"] = 0
    summary = analyze_structured_result(result)

    assert summary["status"] == "error"
    assert "invalid_latency_value" in anomaly_types(summary)


def test_structured_result_missing_run_config_detected():
    result = load_lab_result("valid_fp32_result.json")
    result.pop("run_config")
    summary = analyze_structured_result(result)

    assert "missing_run_config" in anomaly_types(summary)


def test_structured_result_missing_system_metadata_detected():
    result = load_lab_result("valid_fp32_result.json")
    result.pop("system")
    summary = analyze_structured_result(result)

    assert "missing_system_metadata" in anomaly_types(summary)


def test_structured_result_format_summary():
    summary = analyze_structured_result(load_lab_result("suspicious_int8_missing_accuracy.json"))
    formatted = format_summary(summary)

    assert "InferEdgeAIGuard structured result reasoning summary" in formatted
    assert "status" in formatted
    assert "recommendations" in formatted


def test_structured_result_save_json_preserves_mode(tmp_path):
    output_path = tmp_path / "structured.json"
    summary = analyze_structured_result(load_lab_result("valid_fp32_result.json"))

    save_summary_json(summary, output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved["mode"] == "structured_result_reasoning"


def test_structured_result_save_markdown_report(tmp_path):
    output_path = tmp_path / "structured.md"
    summary = analyze_structured_result(
        load_lab_result("suspicious_int8_missing_accuracy.json")
    )

    save_summary_markdown(summary, output_path)
    content = output_path.read_text(encoding="utf-8")

    assert "Structured Result Reasoning Report" in content
    assert "Aggregate Summary" in content
    assert "Anomalies" in content
    assert "Recommendations" in content


def test_cli_reason_result_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-result",
            "--input",
            str(LAB_RESULT_EXAMPLES / "suspicious_int8_missing_accuracy.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "InferEdgeAIGuard structured result reasoning summary" in result.stdout
    assert "accuracy_missing_warning" in result.stdout


def test_cli_reason_result_save_json(tmp_path):
    output_path = tmp_path / "reports" / "result_reasoning.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-result",
            "--input",
            str(LAB_RESULT_EXAMPLES / "suspicious_int8_missing_accuracy.json"),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["mode"] == "structured_result_reasoning"
    assert "status" in saved
    assert "anomalies" in saved
    assert "recommendations" in saved


def test_cli_reason_result_save_markdown(tmp_path):
    output_path = tmp_path / "reports" / "result_reasoning.md"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-result",
            "--input",
            str(LAB_RESULT_EXAMPLES / "suspicious_int8_missing_accuracy.json"),
            "--save-md",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "Structured Result Reasoning Report" in content
    assert "Aggregate Summary" in content
    assert "Anomalies" in content
    assert "Recommendations" in content


def test_cli_reason_result_valid_fp32_is_ok():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-result",
            "--input",
            str(LAB_RESULT_EXAMPLES / "valid_fp32_result.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "- status: ok" in result.stdout
    assert "No anomaly detected" in result.stdout


def load_lab_history(name: str) -> list[dict]:
    return json.loads((LAB_HISTORY_EXAMPLES / name).read_text(encoding="utf-8"))


def test_run_history_stable_fp32_is_ok():
    summary = analyze_run_history(load_lab_history("stable_fp32_history.json"))

    assert summary["status"] == "ok"
    assert summary["anomalies"] == []
    assert summary["history_metrics"]["run_count"] == 3


def test_run_history_unstable_int8_has_mean_latency_instability():
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))

    assert summary["status"] == "warning"
    assert "mean_latency_instability" in anomaly_types(summary)


def test_run_history_unstable_int8_has_p99_latency_instability():
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))

    assert "p99_latency_instability" in anomaly_types(summary)


def test_run_history_unstable_int8_has_latency_outlier_run():
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))

    assert "latency_outlier_run" in anomaly_types(summary)


def test_run_history_unstable_int8_has_quantized_accuracy_missing():
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))

    assert "quantized_history_accuracy_missing" in anomaly_types(summary)


def test_run_history_single_run_is_insufficient():
    history = load_lab_history("stable_fp32_history.json")[:1]
    summary = analyze_run_history(history)

    assert "insufficient_history" in anomaly_types(summary)


def test_run_history_mixed_identity_is_error():
    history = load_lab_history("stable_fp32_history.json")
    history[1]["precision"] = "int8"
    summary = analyze_run_history(history)

    assert summary["status"] == "error"
    assert "mixed_run_identity" in anomaly_types(summary)


def test_run_history_mixed_shape_config_is_error():
    history = load_lab_history("stable_fp32_history.json")
    history[1]["height"] = 256
    summary = analyze_run_history(history)

    assert summary["status"] == "error"
    assert "mixed_shape_config" in anomaly_types(summary)


def test_run_history_partial_accuracy_missing_detected():
    history = load_lab_history("stable_fp32_history.json")
    history[1].pop("accuracy")
    summary = analyze_run_history(history)

    assert "partial_accuracy_missing" in anomaly_types(summary)


def test_run_history_format_summary():
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))
    formatted = format_summary(summary)

    assert "InferEdgeAIGuard run history reasoning summary" in formatted
    assert "status" in formatted
    assert "recommendations" in formatted


def test_run_history_save_json_preserves_mode(tmp_path):
    output_path = tmp_path / "history.json"
    summary = analyze_run_history(load_lab_history("stable_fp32_history.json"))

    save_summary_json(summary, output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved["mode"] == "run_history_reasoning"


def test_run_history_save_markdown_report(tmp_path):
    output_path = tmp_path / "history.md"
    summary = analyze_run_history(load_lab_history("unstable_int8_history.json"))

    save_summary_markdown(summary, output_path)
    content = output_path.read_text(encoding="utf-8")

    assert "Run History Reasoning Report" in content
    assert "Aggregate Summary" in content
    assert "History Metrics" in content
    assert "Anomalies" in content
    assert "Recommendations" in content
