import json
from pathlib import Path

from inferedge_aiguard.provenance import analyze_forge_runtime_provenance
from inferedge_aiguard.provenance import analyze_worker_provenance
from inferedge_aiguard.schema import validate_guard_analysis


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_matching_forge_runtime_provenance_is_ok():
    summary = analyze_forge_runtime_provenance(
        _runtime_result(),
        forge_metadata=_forge_metadata(),
        forge_manifest=_forge_manifest(),
    )

    assert summary["mode"] == "forge_runtime_provenance_reasoning"
    assert summary["status"] == "ok"
    assert summary["anomalies"] == []
    validate_guard_analysis(summary)


def test_matching_worker_provenance_is_ok():
    summary = analyze_worker_provenance(
        load_fixture("forge_worker_runtime_summary.json"),
        load_fixture("runtime_worker_completed_response.json"),
    )

    assert summary["status"] == "ok"
    assert summary["anomalies"] == []
    validate_guard_analysis(summary)


def test_worker_artifact_hash_mismatch_is_error_with_worker_sources():
    summary = analyze_worker_provenance(
        load_fixture("forge_worker_runtime_summary.json"),
        load_fixture("runtime_worker_completed_response_artifact_mismatch.json"),
    )

    anomaly = _first_anomaly(summary, "artifact_sha256_mismatch")
    assert summary["status"] == "error"
    assert anomaly["severity"] == "high"
    assert anomaly["evidence"] == {
        "field": "artifact_sha256",
        "expected": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "observed": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        "expected_source": "forge_worker_runtime_summary",
        "observed_source": "runtime_worker_response",
    }
    validate_guard_analysis(summary)


def test_worker_source_model_hash_mismatch_is_error():
    summary = analyze_worker_provenance(
        load_fixture("forge_worker_runtime_summary.json"),
        load_fixture("runtime_worker_completed_response_source_mismatch.json"),
    )

    anomaly = _first_anomaly(summary, "source_model_sha256_mismatch")
    assert summary["status"] == "error"
    assert anomaly["severity"] == "high"
    assert anomaly["evidence"]["expected_source"] == "forge_worker_runtime_summary"
    assert anomaly["evidence"]["observed_source"] == "runtime_worker_response"


def test_worker_precision_shape_and_artifact_type_mismatch_are_warning_anomalies():
    runtime_response = load_fixture("runtime_worker_completed_response.json")
    runtime_response["runtime_result"]["precision"] = "fp32"
    runtime_response["runtime_result"]["run_config"]["height"] = 320
    runtime_response["runtime_result"]["extra"]["artifact_type"] = "onnx"

    summary = analyze_worker_provenance(
        load_fixture("forge_worker_runtime_summary.json"),
        runtime_response,
    )

    anomaly_types = {anomaly["type"] for anomaly in summary["anomalies"]}
    assert summary["status"] == "warning"
    assert "runtime_config_mismatch" in anomaly_types
    assert "shape_mismatch" in anomaly_types
    assert "artifact_type_mismatch" in anomaly_types


def test_worker_missing_provenance_warns_without_crashing():
    runtime_response = load_fixture("runtime_worker_completed_response.json")
    runtime_response["runtime_result"].pop("extra")

    summary = analyze_worker_provenance(
        load_fixture("forge_worker_runtime_summary.json"),
        runtime_response,
    )

    anomaly = _first_anomaly(summary, "insufficient_provenance")
    missing_fields = anomaly["evidence"]["missing_fields"]
    missing_names = {field["field"] for field in missing_fields}

    assert summary["status"] == "warning"
    assert "artifact_sha256" in missing_names
    assert "source_model_sha256" in missing_names
    assert all(
        field["expected_source"] == "forge_worker_runtime_summary"
        for field in missing_fields
    )
    assert all(
        field["observed_source"] == "runtime_worker_response"
        for field in missing_fields
    )
    validate_guard_analysis(summary)


def test_artifact_sha256_mismatch_is_error_with_evidence():
    runtime_result = _runtime_result()
    runtime_result["extra"]["runtime_artifact_sha256"] = "different-artifact"

    summary = analyze_forge_runtime_provenance(
        runtime_result,
        forge_metadata=_forge_metadata(),
        forge_manifest=_forge_manifest(),
    )

    anomaly = _first_anomaly(summary, "artifact_sha256_mismatch")
    assert summary["status"] == "error"
    assert anomaly["severity"] == "high"
    assert anomaly["evidence"] == {
        "field": "artifact_sha256",
        "expected": "artifact-sha",
        "observed": "different-artifact",
        "expected_source": "forge_manifest",
        "observed_source": "runtime_result.extra",
    }
    validate_guard_analysis(summary)


def test_source_model_sha256_mismatch_is_error():
    runtime_result = _runtime_result()
    runtime_result["extra"]["source_model_sha256"] = "different-source"

    summary = analyze_forge_runtime_provenance(
        runtime_result,
        forge_metadata=_forge_metadata(),
        forge_manifest=_forge_manifest(),
    )

    anomaly = _first_anomaly(summary, "source_model_sha256_mismatch")
    assert summary["status"] == "error"
    assert anomaly["severity"] == "high"
    assert anomaly["evidence"]["field"] == "source_model_sha256"
    assert anomaly["evidence"]["expected"] == "source-sha"
    assert anomaly["evidence"]["observed"] == "different-source"


def test_precision_and_shape_mismatch_are_warning_anomalies():
    runtime_result = _runtime_result()
    runtime_result["precision"] = "fp32"
    runtime_result["run_config"]["height"] = 320

    summary = analyze_forge_runtime_provenance(
        runtime_result,
        forge_metadata=_forge_metadata(),
        forge_manifest=_forge_manifest(),
    )

    anomaly_types = {anomaly["type"] for anomaly in summary["anomalies"]}
    assert summary["status"] == "warning"
    assert "runtime_config_mismatch" in anomaly_types
    assert "shape_mismatch" in anomaly_types
    assert all(anomaly["severity"] == "medium" for anomaly in summary["anomalies"])


def test_missing_provenance_warns_without_crashing():
    runtime_result = _runtime_result()
    runtime_result["extra"].pop("runtime_artifact_sha256")

    summary = analyze_forge_runtime_provenance(runtime_result, forge_metadata={})

    anomaly = _first_anomaly(summary, "insufficient_provenance")
    missing_fields = anomaly["evidence"]["missing_fields"]
    missing_names = {field["field"] for field in missing_fields}

    assert summary["status"] == "warning"
    assert anomaly["severity"] == "medium"
    assert "artifact_sha256" in missing_names
    assert "source_model_sha256" in missing_names
    validate_guard_analysis(summary)


def _first_anomaly(summary: dict, anomaly_type: str) -> dict:
    return next(
        anomaly for anomaly in summary["anomalies"] if anomaly["type"] == anomaly_type
    )


def _runtime_result() -> dict:
    return {
        "model": "yolov8n",
        "engine": "onnxruntime",
        "device": "jetson-orin",
        "precision": "fp16",
        "mean_ms": 4.8,
        "p50_ms": 4.7,
        "p95_ms": 5.2,
        "p99_ms": 5.8,
        "run_config": {
            "batch": 1,
            "height": 640,
            "width": 640,
        },
        "extra": {
            "runtime_artifact_path": "artifacts/yolov8n_fp16.engine",
            "runtime_artifact_sha256": "artifact-sha",
            "source_model_sha256": "source-sha",
        },
    }


def _forge_manifest() -> dict:
    return {
        "build_id": "build-001",
        "source_model": {
            "path": "models/yolov8n.onnx",
            "sha256": "source-sha",
        },
        "artifact": {
            "path": "artifacts/yolov8n_fp16.engine",
            "sha256": "artifact-sha",
        },
        "build": {
            "backend": "onnxruntime",
            "target": "jetson-orin",
        },
        "runtime_compat": {
            "precision": "fp16",
            "batch": 1,
            "height": 640,
            "width": 640,
        },
    }


def _forge_metadata() -> dict:
    return {
        "preset_name": "jetson-fp16",
        "artifacts": [
            {
                "path": "artifacts/yolov8n_fp16.engine",
                "sha256": "artifact-sha",
                "type": "engine",
            }
        ],
        "source_model_sha256": "source-sha",
        "backend": "onnxruntime",
        "target": "jetson-orin",
        "precision": "fp16",
        "requested_shape": {
            "batch": 1,
            "height": 640,
            "width": 640,
        },
    }
