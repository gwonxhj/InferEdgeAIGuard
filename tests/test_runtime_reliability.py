import json
import subprocess
import sys
from pathlib import Path

from inferedge_aiguard.runtime_reliability import (
    analyze_orchestration_summary,
    analyze_runtime_result,
    compute_runtime_reliability_metrics,
    compute_runtime_operation_metrics,
)
from inferedge_aiguard.schema import validate_diagnosis_report


ROOT = Path(__file__).resolve().parents[1]


def orchestration_summary() -> dict:
    return {
        "schema_version": "inferedge-orchestration-summary-v1",
        "run": {
            "name": "agent_3_workload_sustained_high_load",
            "scenario_mode": "sustained_high_load",
            "frame_interval_ms": 5.0,
        },
        "agent_runtime_summary": {
            "schema_version": "inferedge-orchestration-summary-v1",
            "source_contracts": {
                "forge_agent_manifest": "inferedge-agent-manifest-v1",
                "runtime_agent_result": "inferedge-runtime-agent-task-v1",
            },
            "agents": {
                "safety_monitor_agent": {
                    "agent_id": "safety_monitor_agent",
                    "agent_type": "safety",
                    "priority": 100,
                    "latency_budget_ms": 20.0,
                    "fallback_policy": "protect",
                },
                "vision_agent": {
                    "agent_id": "vision_agent",
                    "agent_type": "vision",
                    "priority": 90,
                    "latency_budget_ms": 33.0,
                    "fallback_policy": "drop_stale",
                },
            },
            "totals": {
                "executed_count": 10,
                "dropped_count": 14,
                "deadline_missed_count": 1,
                "fallback_count": 14,
                "policy_decision_count": 14,
                "overload_event_count": 14,
            },
        },
        "sustained_runtime_summary": {
            "schema_version": "inferedge-orchestrator-sustained-summary-v1",
            "scenario_mode": "sustained_high_load",
            "queue_depth_sample_count": 3,
            "latency_sample_count": 2,
            "max_total_queue_depth": 6,
        },
        "queue_depth_timeline": [
            {
                "cycle": 1,
                "stage": "before_policy",
                "queue_depth": {
                    "vision_agent": 4,
                    "voice_command_agent": 2,
                    "safety_monitor_agent": 0,
                },
                "total_queue_depth": 6,
            }
        ],
        "latency_timeline": [
            {
                "agent_id": "vision_agent",
                "task_id": "task_vision_agent",
                "latency_ms": 41.0,
                "latency_budget_ms": 33.0,
                "deadline_missed": True,
            }
        ],
        "policy_decision_log": [
            {
                "agent_id": "vision_agent",
                "task_id": "task_vision_agent",
                "decision": "load_shedding",
                "reason": "queue_backlog_threshold_exceeded",
                "decision_reason": "queue_backlog_threshold_exceeded",
                "total_backlog_before": 6,
                "backlog_threshold": 3,
                "queue_depth_snapshot": {
                    "vision_agent": 4,
                    "voice_command_agent": 2,
                    "safety_monitor_agent": 0,
                },
                "fallback_used": True,
                "protected_agent_id": "safety_monitor_agent",
            }
        ],
        "drop_events": [
            {
                "agent_id": "vision_agent",
                "reason": "load_shedding_backlog_threshold_exceeded",
            }
        ],
        "overload_events": [
            {
                "agent_id": "vision_agent",
                "fallback_used": True,
                "reason": "queue_backlog_threshold_exceeded",
            }
        ],
    }


def multi_workload_sustained_summary() -> dict:
    summary = orchestration_summary()
    summary["multi_workload_sustained_summary"] = {
        "schema_version": "inferedge-orchestrator-multi-workload-sustained-v1",
        "scenario_mode": "sustained_high_load",
        "evidence_scope": (
            "local sustained workload profiles with lightweight CPU profile "
            "adapters; external YOLO/Whisper/FastAPI integrations remain optional"
        ),
        "workload_profiles": [
            {
                "agent_id": "vision_agent",
                "agent_type": "vision",
                "workload_type": "realtime_vision",
                "runtime_loop": "yolo_detection_loop",
                "implementation": "local_profile_adapter",
                "profile_work_units": 24000,
                "ingress_profile": "frame_queue",
                "expected_runtime_mode": "sustained",
                "preferred_device": "gpu",
                "executed": 18,
                "dropped": 6,
                "deadline_missed": 4,
                "fallback_used": 2,
                "mean_latency_ms": 41.5,
                "p95_latency_ms": 74.0,
                "max_queue_backlog": 8,
            },
            {
                "agent_id": "voice_command_agent",
                "agent_type": "voice",
                "workload_type": "voice_command",
                "runtime_loop": "whisper_command_burst",
                "implementation": "local_profile_adapter",
                "profile_work_units": 16000,
                "ingress_profile": "fastapi_concurrent_request",
                "expected_runtime_mode": "burst",
                "preferred_device": "cpu",
                "executed": 4,
                "dropped": 1,
                "deadline_missed": 1,
                "fallback_used": 1,
                "mean_latency_ms": 122.0,
                "p95_latency_ms": 180.0,
                "max_queue_backlog": 3,
            },
            {
                "agent_id": "safety_monitor_agent",
                "agent_type": "safety",
                "workload_type": "telemetry_monitor",
                "runtime_loop": "safety_monitor_loop",
                "implementation": "local_profile_adapter",
                "profile_work_units": 6000,
                "ingress_profile": "periodic_monitor",
                "expected_runtime_mode": "periodic",
                "preferred_device": "cpu",
                "executed": 8,
                "dropped": 0,
                "deadline_missed": 0,
                "fallback_used": 0,
                "mean_latency_ms": 8.0,
                "p95_latency_ms": 11.0,
                "max_queue_backlog": 0,
            },
        ],
        "observed_runtime_signals": {
            "max_total_queue_depth": 11,
            "executed_count": 30,
            "dropped_count": 7,
            "deadline_missed_count": 5,
            "fallback_count": 3,
            "policy_decision_count": 5,
            "policy_decision_reasons": [
                "stale_frame_drop_due_to_queue_latency",
                "fallback_activated_due_to_overload_risk",
            ],
            "tegrastats_sample_count": 2,
            "local_profile_adapter_count": 30,
            "local_profile_elapsed_ms": 124.5,
            "local_profile_kinds": [
                "safety_monitor_loop",
                "vision_frame_loop",
                "voice_command_burst",
            ],
        },
    }
    summary["tegrastats_timeline"] = {
        "source": "sample",
        "sample_count": 2,
        "samples": [
            {
                "sample_index": 0,
                "ram_used_mb": 2048,
                "gpu_percent": 42,
                "temperatures_c": {"cpu": 66.5, "gpu": 68.1},
            },
            {
                "sample_index": 1,
                "ram_used_mb": 2304,
                "gpu_percent": 91,
                "temperatures_c": {"cpu": 76.2, "gpu": 74.0},
            },
        ],
        "summary": {
            "max_gpu_percent": 91,
            "max_ram_used_mb": 2304,
            "max_temperature_c": 76.2,
        },
    }
    return summary


def runtime_result_with_operation_signals() -> dict:
    return {
        "schema_version": "inferedge-runtime-result-v1",
        "model": "models/yolov8n.onnx",
        "engine": "tensorrt",
        "device": "jetson",
        "mean_ms": 72.5,
        "runtime_health_snapshot": {
            "engine_available": False,
            "engine_status_message": "TensorRT engine load failed",
            "latency_budget_ms": 50.0,
            "latency_budget_exceeded": True,
            "deadline_missed": True,
            "tegrastats_status": "not_collected",
            "tegrastats_sample_count": 0,
            "thermal_memory_evidence_available": False,
        },
        "runtime_error_classification": {
            "category": "runtime_execution_skipped",
            "severity": "high",
            "observed_mean_ms": 72.5,
            "timeout_budget_ms": 50.0,
            "retry_hint": "check_backend_availability",
        },
        "runtime_events": [
            {
                "schema_version": "inferedge-runtime-event-v1",
                "event_index": 0,
                "event_type": "runtime_health_snapshot",
                "latency_budget_ms": 50.0,
                "latency_budget_exceeded": True,
                "deadline_missed": True,
                "retry_hint": "check_backend_availability",
                "tegrastats_sample_count": 0,
            }
        ],
    }


def test_compute_runtime_reliability_metrics_from_orchestration_summary():
    metrics = compute_runtime_reliability_metrics(orchestration_summary())

    assert metrics["deadline_miss_rate"] == 0.1
    assert metrics["drop_rate"] == 14 / 24
    assert metrics["fallback_rate"] == 14 / 24
    assert metrics["queue_backlog_policy_decision_count"] == 1
    assert metrics["scenario_mode"] == "sustained_high_load"
    assert metrics["max_total_queue_depth"] == 6
    assert metrics["queue_depth_sample_count"] == 1
    assert metrics["latency_sample_count"] == 1
    assert metrics["top_policy_decision_reason"] == "queue_backlog_threshold_exceeded"
    assert metrics["policy_decision_reasons"] == {
        "queue_backlog_threshold_exceeded": 1
    }
    assert metrics["affected_agents"] == ["safety_monitor_agent", "vision_agent"]


def test_compute_runtime_operation_metrics_from_runtime_result():
    metrics = compute_runtime_operation_metrics(runtime_result_with_operation_signals())

    assert metrics["schema_version"] == "inferedge-runtime-result-v1"
    assert metrics["engine_available"] is False
    assert metrics["latency_budget_exceeded"] is True
    assert metrics["deadline_missed"] is True
    assert metrics["latency_budget_ms"] == 50.0
    assert metrics["observed_mean_ms"] == 72.5
    assert metrics["runtime_error_category"] == "runtime_execution_skipped"
    assert metrics["runtime_error_severity"] == "high"
    assert metrics["retry_hint"] == "check_backend_availability"
    assert metrics["thermal_memory_evidence_available"] is False
    assert metrics["runtime_event_count"] == 1


def test_multi_workload_sustained_summary_adds_profile_and_thermal_metrics():
    metrics = compute_runtime_reliability_metrics(multi_workload_sustained_summary())

    assert metrics["scenario_mode"] == "sustained_high_load"
    assert metrics["executed_count"] == 30
    assert metrics["dropped_count"] == 14
    assert metrics["deadline_missed_count"] == 5
    assert metrics["fallback_count"] == 14
    assert metrics["max_total_queue_depth"] == 11
    assert metrics["workload_profile_count"] == 3
    assert metrics["profiled_workload_risk_count"] == 2
    assert metrics["local_profile_adapter_count"] == 30
    assert metrics["local_profile_elapsed_ms"] == 124.5
    assert metrics["local_profile_kinds"] == [
        "safety_monitor_loop",
        "vision_frame_loop",
        "voice_command_burst",
    ]
    assert metrics["tegrastats_sample_count"] == 2
    assert metrics["max_temperature_c"] == 76.2
    assert metrics["max_gpu_percent"] == 91
    assert {
        item["runtime_loop"] for item in metrics["affected_workload_profiles"]
    } == {"yolo_detection_loop", "whisper_command_burst"}
    assert {
        item["implementation"] for item in metrics["affected_workload_profiles"]
    } == {"local_profile_adapter"}


def test_analyze_orchestration_summary_returns_diagnosis_report():
    report = analyze_orchestration_summary(orchestration_summary())

    validate_diagnosis_report(report)
    assert report["schema_version"] == "inferedge-aiguard-diagnosis-v1"
    assert report["guard_verdict"] == "blocked"
    assert report["severity"] == "high"
    assert report["source"]["orchestration_summary_schema_version"] == (
        "inferedge-orchestration-summary-v1"
    )
    assert {
        item["type"] for item in report["evidence"]
    } == {
        "repeated_deadline_miss",
        "excessive_drop_rate",
        "fallback_overuse",
        "queue_backlog_risk",
        "sustained_overload_risk",
    }
    assert report["candidate_summary"]["runtime_reliability"]["drop_rate"] == 14 / 24
    assert (
        report["candidate_summary"]["runtime_reliability"]["max_total_queue_depth"]
        == 6
    )
    queue_evidence = next(
        item for item in report["evidence"] if item["type"] == "queue_backlog_risk"
    )
    assert queue_evidence["raw_context"]["top_policy_decision_reason"] == (
        "queue_backlog_threshold_exceeded"
    )


def test_analyze_multi_workload_sustained_summary_adds_runtime_evidence():
    report = analyze_orchestration_summary(multi_workload_sustained_summary())

    validate_diagnosis_report(report)
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "profiled_workload_pressure" in evidence_types
    assert "thermal_resource_pressure" in evidence_types
    profile_evidence = next(
        item for item in report["evidence"] if item["type"] == "profiled_workload_pressure"
    )
    assert profile_evidence["observed_value"] == 2
    assert profile_evidence["status"] == "failed"
    assert {
        item["agent_id"]
        for item in profile_evidence["raw_context"]["affected_workload_profiles"]
    } == {"vision_agent", "voice_command_agent"}
    assert profile_evidence["raw_context"]["local_profile_adapter_count"] == 30
    assert profile_evidence["raw_context"]["local_profile_elapsed_ms"] == 124.5
    assert profile_evidence["raw_context"]["local_profile_kinds"] == [
        "safety_monitor_loop",
        "vision_frame_loop",
        "voice_command_burst",
    ]

    thermal_evidence = next(
        item for item in report["evidence"] if item["type"] == "thermal_resource_pressure"
    )
    assert thermal_evidence["observed_value"] == 76.2
    assert thermal_evidence["status"] == "failed"
    assert (
        report["candidate_summary"]["runtime_reliability"]["max_temperature_c"]
        == 76.2
    )


def test_analyze_runtime_result_returns_operation_evidence():
    report = analyze_runtime_result(runtime_result_with_operation_signals())

    validate_diagnosis_report(report)
    assert report["schema_version"] == "inferedge-aiguard-diagnosis-v1"
    assert report["guard_verdict"] == "blocked"
    assert report["severity"] == "high"
    assert report["source"]["runtime_result_schema_version"] == (
        "inferedge-runtime-result-v1"
    )
    evidence_types = {item["type"] for item in report["evidence"]}
    assert evidence_types == {
        "runtime_backend_unavailable",
        "runtime_latency_budget_overrun",
        "runtime_error_classification",
        "runtime_thermal_memory_evidence_missing",
    }
    latency_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_latency_budget_overrun"
    )
    assert latency_evidence["observed_value"] == 1
    assert latency_evidence["threshold"] == 50.0
    assert latency_evidence["delta"] == 22.5
    assert (
        report["candidate_summary"]["runtime_operation"]["runtime_event_count"]
        == 1
    )


def test_orchestration_summary_can_include_runtime_result_operation_evidence():
    summary = orchestration_summary()
    summary["runtime_results"] = [runtime_result_with_operation_signals()]

    report = analyze_orchestration_summary(summary)

    validate_diagnosis_report(report)
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "runtime_backend_unavailable" in evidence_types
    assert "runtime_latency_budget_overrun" in evidence_types
    assert (
        report["candidate_summary"]["runtime_operation_results"][0][
            "runtime_error_category"
        ]
        == "runtime_execution_skipped"
    )


def test_cli_reason_orchestration_and_unified_reason_route(tmp_path):
    input_path = tmp_path / "orchestration_summary.json"
    input_path.write_text(json.dumps(orchestration_summary()), encoding="utf-8")

    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-orchestration",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "guard_verdict: blocked" in explicit.stdout
    assert "excessive_drop_rate" in explicit.stdout

    unified = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "fallback_overuse" in unified.stdout


def test_cli_reason_runtime_and_unified_runtime_route(tmp_path):
    input_path = tmp_path / "runtime_result.json"
    input_path.write_text(
        json.dumps(runtime_result_with_operation_signals()),
        encoding="utf-8",
    )

    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-runtime",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "runtime_backend_unavailable" in explicit.stdout
    assert "guard_verdict: blocked" in explicit.stdout

    unified = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "runtime_latency_budget_overrun" in unified.stdout
