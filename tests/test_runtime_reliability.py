import json
import subprocess
import sys
from pathlib import Path

from inferedge_aiguard.runtime_reliability import (
    analyze_edgeenv_regression_report,
    analyze_orchestration_summary,
    analyze_remote_dispatch_result,
    analyze_runtime_result,
    compute_edgeenv_regression_metrics,
    compute_remote_dispatch_metrics,
    compute_runtime_reliability_metrics,
    compute_runtime_operation_metrics,
)
from inferedge_aiguard.schema import validate_diagnosis_report


ROOT = Path(__file__).resolve().parents[1]
EDGEENV_REGRESSION_FIXTURES = ROOT / "tests" / "fixtures" / "edgeenv_regression"
RUNTIME_INTELLIGENCE_EXAMPLES = ROOT / "examples" / "runtime_intelligence"


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


def operation_telemetry_summary() -> dict:
    summary = multi_workload_sustained_summary()
    summary["worker_health_snapshot"] = {
        "schema_version": "inferedge-orchestrator-worker-health-v1",
        "health_state_counts": {"healthy": 1, "degraded": 2},
        "degraded_workers": ["vision_agent", "voice_command_agent"],
        "constrained_workers": [],
        "workers": {
            "safety_monitor_agent": {
                "agent_id": "safety_monitor_agent",
                "agent_type": "safety",
                "health_state": "healthy",
                "health_reasons": ["healthy_without_runtime_risk"],
                "primary_health_reason": "healthy_without_runtime_risk",
                "operation_risk_summary": "healthy_without_runtime_risk",
                "drop_rate": 0.0,
                "deadline_miss_rate": 0.0,
                "fallback_rate": 0.0,
                "queue_pressure_ratio": 0.25,
                "runtime_loop": "safety_monitor_loop",
                "ingress_profile": "periodic_monitor",
                "device_local_validation": True,
                "producer_stage": "device_local_starter",
                "producer_sources": ["resource_snapshot_fixture"],
                "producer_event_count": 3,
            },
            "vision_agent": {
                "agent_id": "vision_agent",
                "agent_type": "vision",
                "health_state": "degraded",
                "health_reasons": [
                    "fallback_policy_used",
                    "frames_dropped",
                    "queue_reached_capacity",
                ],
                "primary_health_reason": "fallback_policy_used",
                "operation_risk_summary": "latency_or_fallback_risk",
                "drop_rate": 0.25,
                "deadline_miss_rate": 0.10,
                "fallback_rate": 0.25,
                "queue_pressure_ratio": 1.0,
                "runtime_loop": "yolo_detection_loop",
                "ingress_profile": "frame_queue",
                "device_local_validation": True,
                "producer_stage": "device_local_starter",
                "producer_sources": ["image_file"],
                "producer_event_count": 8,
            },
            "voice_command_agent": {
                "agent_id": "voice_command_agent",
                "agent_type": "voice",
                "health_state": "degraded",
                "health_reasons": [
                    "fallback_policy_used",
                    "frames_dropped",
                    "queue_reached_capacity",
                ],
                "primary_health_reason": "fallback_policy_used",
                "operation_risk_summary": "drop_or_queue_pressure_risk",
                "drop_rate": 0.75,
                "deadline_miss_rate": 0.0,
                "fallback_rate": 0.75,
                "queue_pressure_ratio": 1.0,
                "runtime_loop": "whisper_command_burst",
                "ingress_profile": "fastapi_concurrent_request",
                "device_local_validation": True,
                "producer_stage": "device_local_starter",
                "producer_sources": ["fastapi_request_fixture"],
                "producer_event_count": 2,
            },
        },
    }
    summary["queue_state_summary"] = {
        "schema_version": "inferedge-orchestrator-queue-state-v1",
        "sample_count": 2,
        "overload_backlog_threshold": 3,
        "max_total_queue_depth": 11,
        "average_total_queue_depth": 7.5,
        "final_queue_depth": {
            "vision_agent": 4,
            "voice_command_agent": 2,
            "safety_monitor_agent": 0,
        },
        "max_queue_depth_by_task": {
            "vision_agent": 8,
            "voice_command_agent": 3,
            "safety_monitor_agent": 1,
        },
        "max_pressure_task": "vision_agent",
        "queue_pressure_state": "overloaded",
        "queue_pressure_reason": (
            "max_total_queue_depth_exceeded_overload_threshold"
        ),
        "device_local_task_count": 3,
        "device_local_tasks": [
            "safety_monitor_agent",
            "vision_agent",
            "voice_command_agent",
        ],
        "device_local_producer_sources": [
            "resource_snapshot_fixture",
            "image_file",
            "fastapi_request_fixture",
        ],
        "producer_sources_by_task": {
            "safety_monitor_agent": ["resource_snapshot_fixture"],
            "vision_agent": ["image_file"],
            "voice_command_agent": ["fastapi_request_fixture"],
        },
    }
    summary["runtime_event_summary"] = {
        "schema_version": "inferedge-orchestrator-runtime-event-summary-v1",
        "event_count": 9,
        "event_type_counts": {
            "queue_snapshot": 2,
            "schedule": 2,
            "execution": 2,
            "drop": 2,
            "policy_decision": 1,
        },
        "reason_counts": {
            "priority_deadline": 2,
            "completed_within_latency_budget": 1,
            "scheduler_delay_observed": 1,
            "load_shedding_backlog_threshold_exceeded": 2,
            "queue_backlog_threshold_exceeded": 1,
        },
        "policy_decision_reason_counts": {
            "queue_backlog_threshold_exceeded": 1
        },
        "drop_reason_counts": {
            "load_shedding_backlog_threshold_exceeded": 2
        },
        "queue_pressure_reason_counts": {
            "queue_backlog_threshold_exceeded": 1,
            "queue_pressure_elevated": 2,
        },
        "fallback_decision_count": 2,
        "deadline_missed_count": 1,
        "scheduler_delay_event_count": 2,
        "producer_sources": [
            "resource_snapshot_fixture",
            "image_file",
            "fastapi_request_fixture",
        ],
        "producer_event_count": 13,
        "device_local_event_count": 9,
        "latest_event_index": 8,
        "latest_event_type": "execution",
    }
    summary["runtime_event_timeline"] = [
        {
            "event_index": 0,
            "event_type": "execution",
            "agent_id": "vision_agent",
            "scheduler_delay_cycles": 2,
            "queue_wait_ms": 10.0,
            "reason": "scheduler_delay_observed",
        },
        {
            "event_index": 1,
            "event_type": "execution",
            "agent_id": "voice_command_agent",
            "scheduler_delay_cycles": 1,
            "queue_wait_ms": 5.0,
            "reason": "scheduler_delay_observed",
        },
    ]
    return summary


def edgeenv_regression_report() -> dict:
    return {
        "baseline_run_id": "edgeenv-smoke-baseline",
        "candidate_run_id": "edgeenv-smoke-candidate",
        "comparable": True,
        "mode": "same-condition",
        "regression_detected": True,
        "regression_type": "mixed",
        "severity": "high",
        "recommendation": "review_required",
        "evidence": {
            "mean_delta_pct": 18.0,
            "p95_delta_pct": 10.0,
            "p99_delta_pct": 32.0,
            "fps_delta_pct": -22.0,
            "memory_peak_delta_pct": 40.0,
            "triggered_thresholds": [
                {
                    "name": "p99_latency_high",
                    "metric": "latency_p99_ms",
                    "observed": 32.0,
                    "threshold": 25.0,
                    "severity": "high",
                    "type": "latency",
                }
            ],
        },
        "runtime_telemetry_context": {
            "role": "supplemental_runtime_telemetry_context",
            "source": "result_artifacts+runtime_telemetry_history",
            "baseline": {
                "run_id": "edgeenv-smoke-baseline",
                "result_telemetry_present": True,
                "history_entry_present": True,
                "execution_sequence_id": 1,
                "telemetry_source": "synthetic_local_fixture",
            },
            "candidate": {
                "run_id": "edgeenv-smoke-candidate",
                "result_telemetry_present": True,
                "history_entry_present": True,
                "execution_sequence_id": 2,
                "telemetry_source": "synthetic_local_fixture",
            },
            "history": {
                "schema_version": "edgeenv.runtime-telemetry-history.v1",
                "summary": {
                    "registered_runs": 2,
                    "telemetry_runs": 2,
                    "missing_telemetry_runs": 0,
                },
            },
            "evidence_gaps": [],
        },
    }


def edgeenv_regression_report_with_candidate_telemetry_gap() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["candidate"]["result_telemetry_present"] = False
    context["candidate"]["history_entry_present"] = False
    context["candidate"]["history_missing_recorded"] = True
    context["candidate"]["history_missing_reason"] = "runtime_telemetry_missing"
    context["history"]["summary"]["registered_runs"] = 3
    context["history"]["summary"]["telemetry_runs"] = 2
    context["history"]["summary"]["missing_telemetry_runs"] = 1
    context["evidence_gaps"] = [
        {
            "run_id": "edgeenv-smoke-candidate",
            "reason": "runtime_telemetry_missing_in_result",
        },
        {
            "run_id": "edgeenv-smoke-candidate",
            "reason": "runtime_telemetry_missing",
        },
    ]
    return report


def edgeenv_regression_report_with_sequence_inversion() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["baseline"]["execution_sequence_id"] = 5
    context["baseline"]["history_execution_sequence_id"] = 5
    context["candidate"]["execution_sequence_id"] = 2
    context["candidate"]["history_execution_sequence_id"] = 2
    return report


def edgeenv_regression_report_with_runtime_telemetry_signals() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["baseline"].update(
        {
            "gpu_temperature": 55.0,
            "cpu_temperature": 50.0,
            "queue_depth": 1,
            "throttling_detected": False,
        }
    )
    context["candidate"].update(
        {
            "gpu_temperature": 76.2,
            "cpu_temperature": 68.0,
            "queue_depth": 6,
            "throttling_detected": True,
        }
    )
    return report


def edgeenv_regression_report_with_runtime_telemetry_coverage_gap() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["baseline"]["telemetry_coverage"] = {
        "schema_version": "inferedge-runtime-telemetry-coverage-v1",
        "expected_fields": ["gpu_temperature", "queue_depth", "telemetry_timestamp"],
        "observed_fields": ["gpu_temperature", "queue_depth", "telemetry_timestamp"],
        "missing_fields": [],
        "expected_field_count": 3,
        "observed_field_count": 3,
        "missing_field_count": 0,
        "coverage_ratio": 1.0,
        "comparability_owner": "edgeenv",
        "missing_telemetry_is_failure": False,
    }
    context["candidate"]["telemetry_coverage"] = {
        "schema_version": "inferedge-runtime-telemetry-coverage-v1",
        "expected_fields": ["gpu_temperature", "queue_depth", "telemetry_timestamp"],
        "observed_fields": ["gpu_temperature", "telemetry_timestamp"],
        "missing_fields": ["queue_depth"],
        "expected_field_count": 3,
        "observed_field_count": 2,
        "missing_field_count": 1,
        "coverage_ratio": 0.666667,
        "comparability_owner": "edgeenv",
        "missing_telemetry_is_failure": False,
    }
    context["history"]["telemetry_coverage"] = _edgeenv_history_coverage_summary()
    return report


def edgeenv_regression_report_with_history_telemetry_coverage_gap() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["history"]["telemetry_coverage"] = _edgeenv_history_coverage_summary()
    return report


def edgeenv_regression_report_with_runtime_telemetry_history_seed() -> dict:
    report = edgeenv_regression_report_with_history_telemetry_coverage_gap()
    context = report["runtime_telemetry_context"]
    context["history"]["summary"]["history_seed_runs"] = 2
    context["history"]["runs"] = [
        {
            "run_id": "edgeenv-smoke-baseline",
            "runtime_telemetry_history_seed": _runtime_history_seed(
                "edgeenv-smoke-baseline",
                sequence_id=1,
            ),
        },
        {
            "run_id": "edgeenv-smoke-candidate",
            "runtime_telemetry_history_seed": _runtime_history_seed(
                "edgeenv-smoke-candidate",
                sequence_id=2,
            ),
        },
    ]
    return report


def _runtime_history_seed(run_id: str, *, sequence_id: int) -> dict:
    return {
        "schema_version": "inferedge-runtime-telemetry-history-seed-v1",
        "evidence_role": "runtime_telemetry_history_seed",
        "registry_owner": "edgeenv",
        "decision_owner": "lab",
        "source_result_schema_version": "inferedge-runtime-result-v1",
        "source_telemetry_schema_version": "inferedge-runtime-telemetry-v1",
        "replay_scope": "single_result_to_history",
        "replay_ready": True,
        "production_monitoring": False,
        "missing_telemetry_is_failure": False,
        "source_result": {
            "run_id": run_id,
            "compare_key": "yolov8n__b1__h640w640__fp32",
            "backend_key": "onnxruntime__cpu",
            "engine_backend": "onnxruntime",
            "device": "cpu",
            "precision": "fp32",
            "power_mode": "unknown",
        },
        "points": [
            {
                "execution_sequence_id": sequence_id,
                "telemetry_timestamp": f"2026-05-22T00:00:0{sequence_id}Z",
                "mean_ms": 100.0 + sequence_id,
                "p99_ms": 130.0 + sequence_id,
                "timeout_observed": False,
            }
        ],
    }


def _edgeenv_history_coverage_summary() -> dict:
    return {
        "runs_with_coverage": 2,
        "runs_without_coverage": 0,
        "expected_fields": [
            "gpu_temperature",
            "queue_depth",
            "telemetry_timestamp",
        ],
        "observed_fields": [
            "gpu_temperature",
            "queue_depth",
            "telemetry_timestamp",
        ],
        "missing_fields": ["queue_depth"],
        "coverage_ratio_min": 0.666667,
        "coverage_ratio_max": 1.0,
        "missing_telemetry_is_failure_values": [False],
        "any_missing_telemetry_is_failure": False,
        "missing_field_run_count": 1,
        "missing_field_runs": [
            {
                "run_id": "edgeenv-smoke-candidate",
                "missing_fields": ["queue_depth"],
                "missing_field_count": 1,
                "missing_telemetry_is_failure": False,
            }
        ],
        "run_summaries": [
            {
                "run_id": "edgeenv-smoke-baseline",
                "coverage_present": True,
                "expected_fields": [
                    "gpu_temperature",
                    "queue_depth",
                    "telemetry_timestamp",
                ],
                "observed_fields": [
                    "gpu_temperature",
                    "queue_depth",
                    "telemetry_timestamp",
                ],
                "missing_fields": [],
                "expected_field_count": 3,
                "observed_field_count": 3,
                "missing_field_count": 0,
                "coverage_ratio": 1.0,
                "missing_telemetry_is_failure": False,
            },
            {
                "run_id": "edgeenv-smoke-candidate",
                "coverage_present": True,
                "expected_fields": [
                    "gpu_temperature",
                    "queue_depth",
                    "telemetry_timestamp",
                ],
                "observed_fields": [
                    "gpu_temperature",
                    "telemetry_timestamp",
                ],
                "missing_fields": ["queue_depth"],
                "expected_field_count": 3,
                "observed_field_count": 2,
                "missing_field_count": 1,
                "coverage_ratio": 0.666667,
                "missing_telemetry_is_failure": False,
            },
        ],
    }


def edgeenv_regression_report_with_orchestrator_feed_context() -> dict:
    report = edgeenv_regression_report()
    report["regression_detected"] = False
    report["evidence"] = {}
    context = report["runtime_telemetry_context"]
    context["history"]["summary"]["orchestrator_feed_runs"] = 1
    context["candidate"]["orchestrator_context_present"] = True
    context["candidate"]["orchestrator_available_sections"] = [
        "available_sections",
        "operation",
        "queue_depth",
        "resource",
        "run_id",
    ]
    context["candidate"]["orchestrator_operation_context"] = {
        "schema_version": "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1",
        "role": "orchestrator_operation_context_for_edgeenv",
        "source_repository": "InferEdgeOrchestrator",
        "artifact_role": "orchestrator-supplemental-operation-context",
        "producer_contract": (
            "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
        ),
        "source": "orchestration_summary",
        "run_id": "edgeenv-smoke-candidate",
        "not_a_regression_judgement": True,
        "not_a_comparability_gate": True,
        "decision_owner": "lab",
        "regression_owner": "edgeenv",
        "candidate_context": {
            "run_id": "edgeenv-smoke-candidate",
            "telemetry_source": "inferedge_orchestrator_operation_summary",
            "available_sections": ["operation", "resource"],
            "queue_depth": 7,
            "operation": {
                "queue_depth": 7,
                "deadline_missed_count": 2,
                "fallback_count": 1,
            },
            "resource": {
                "source": "tegrastats_timeline",
                "resource_evidence_available": True,
                "gpu_temperature": 78.5,
                "ram_used_mb": 2048.0,
                "throttling_detected": True,
            },
            "producer": {
                "operation_context_role": "supplemental",
                "producer_sources": [
                    "device_local_cli_override",
                    "orchestration_summary",
                ],
                "device_local_producer_sources": ["device_local_cli_override"],
                "producer_sources_by_task": {
                    "vision_agent": ["device_local_cli_override"],
                },
                "producer_stage_by_task": {
                    "vision_agent": "device_local_starter",
                },
                "producer_event_count": 4,
                "device_local_event_count": 2,
                "device_local_task_count": 1,
            },
        },
        "edgeenv_mapping_hint": {
            "copy_candidate_context_to": "runtime_telemetry_context.candidate",
            "operation_context_role": "supplemental",
            "coverage_summary_owner": "edgeenv",
            "coverage_summary_path": (
                "runtime_telemetry_context.history.telemetry_coverage"
            ),
            "candidate_context_required_fields": [
                "run_id",
                "telemetry_source",
                "operation",
                "resource",
            ],
            "aiguard_evidence_candidates": [
                "runtime_queue_overload",
                "runtime_thermal_instability",
            ],
        },
    }
    return report


def edgeenv_regression_report_with_missing_telemetry_orchestrator_context() -> dict:
    report = edgeenv_regression_report_with_candidate_telemetry_gap()
    context = report["runtime_telemetry_context"]
    orchestrator_report = edgeenv_regression_report_with_orchestrator_feed_context()
    orchestrator_context = orchestrator_report["runtime_telemetry_context"][
        "candidate"
    ]["orchestrator_operation_context"]
    context["history"]["summary"]["orchestrator_feed_runs"] = 1
    context["history"]["missing_telemetry"] = [
        {
            "run_id": "edgeenv-smoke-candidate",
            "reason": "runtime_telemetry_missing",
            "missing_telemetry_is_failure": False,
            "orchestrator_context_present": True,
            "orchestrator_operation_context": orchestrator_context,
        }
    ]
    return report


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
            "retryable": True,
            "retry_hint": "check_backend_availability",
        },
        "runtime_operation_summary": {
            "schema_version": "inferedge-runtime-operation-summary-v1",
            "observation_scope": "single_runtime_result",
            "decision_owner": "lab",
            "scheduler_owner": "orchestrator",
            "production_cancellation": False,
            "health_status": "degraded",
            "health_reason": "backend_unavailable_or_not_enabled",
            "error_category": "runtime_execution_skipped",
            "retryable": True,
            "recommended_action": "check_backend_availability",
            "risk_labels": [
                "runtime_execution_skipped",
                "backend_unavailable",
            ],
            "evidence_gaps": [
                "timeout_policy_not_configured",
                "thermal_memory_evidence_missing",
            ],
            "timeout_observed": False,
            "latency_budget_exceeded": True,
            "deadline_missed": True,
            "thermal_memory_evidence_available": False,
        },
        "runtime_events": [
            {
                "schema_version": "inferedge-runtime-event-v1",
                "event_index": 0,
                "event_type": "runtime_health_snapshot",
                "latency_budget_ms": 50.0,
                "latency_budget_exceeded": True,
                "deadline_missed": True,
                "retryable": True,
                "retry_hint": "check_backend_availability",
                "tegrastats_sample_count": 0,
            },
            {
                "schema_version": "inferedge-runtime-event-v1",
                "event_index": 1,
                "type": "runtime_operation_summary_recorded",
                "status": "degraded",
                "health_reason": "backend_unavailable_or_not_enabled",
                "recommended_action": "check_backend_availability",
                "risk_labels": [
                    "runtime_execution_skipped",
                    "backend_unavailable",
                ],
                "evidence_gaps": [
                    "timeout_policy_not_configured",
                    "thermal_memory_evidence_missing",
                ],
            }
        ],
    }


def remote_dispatch_success_result() -> dict:
    return {
        "schema_version": "inferedge-remote-dispatch-result-v1",
        "dispatch_status": "accepted",
        "selected_worker_id": "jetson-nano-01",
        "decision_reason": "selected online worker matching backend/device requirements",
        "remote_execution": {
            "mode": "file_contract_starter",
            "production_remote_execution": False,
            "execution_requested": True,
        },
        "remote_execution_plan": {
            "schema_version": "inferedge-remote-execution-plan-v1",
            "mode": "starter_execute",
            "network_execution_performed": True,
            "transport": "http",
            "endpoint_type": "http_request",
            "selected_worker_id": "jetson-nano-01",
            "task_id": "remote_task_001",
            "agent_id": "vision_agent",
        },
        "remote_execution_result": {
            "schema_version": "inferedge-remote-execution-result-v1",
            "execution_requested": True,
            "execution_performed": True,
            "production_remote_execution": False,
            "status": "succeeded",
            "transport": "http",
            "selected_worker_id": "jetson-nano-01",
            "task_id": "remote_task_001",
            "agent_id": "vision_agent",
            "http_status": 200,
            "response_json": {"status": "ok"},
        },
        "retry_fallback_plan": {
            "schema_version": "inferedge-remote-retry-fallback-plan-v1",
            "fallback_worker_ids": ["jetson-fallback"],
            "fallback_execution_performed": False,
            "last_execution_status": "succeeded",
        },
        "runtime_events": [
            {"event": "remote_dispatch_selected"},
            {"event": "remote_execution_completed", "status": "succeeded"},
        ],
    }


def remote_dispatch_failure_result() -> dict:
    result = remote_dispatch_success_result()
    result["remote_execution_plan"]["network_execution_performed"] = False
    result["remote_execution_result"] = {
        "schema_version": "inferedge-remote-execution-result-v1",
        "execution_requested": True,
        "execution_performed": True,
        "production_remote_execution": False,
        "status": "failed",
        "transport": "http",
        "selected_worker_id": "jetson-nano-01",
        "task_id": "remote_task_001",
        "agent_id": "vision_agent",
        "error_category": "connection_error",
        "error_message": "connection refused",
    }
    result["retry_fallback_plan"]["last_execution_status"] = "failed"
    result["runtime_events"][-1] = {
        "event": "remote_execution_failed",
        "status": "failed",
        "error_category": "connection_error",
    }
    return result


def remote_dispatch_fallback_recovered_result() -> dict:
    result = remote_dispatch_failure_result()
    result["retry_fallback_plan"].update(
        {
            "fallback_execution_performed": True,
            "fallback_attempted_worker_ids": ["jetson-fallback"],
            "fallback_final_status": "succeeded",
            "last_execution_status": "succeeded",
        }
    )
    result["fallback_execution_result"] = {
        "schema_version": "inferedge-remote-fallback-execution-v1",
        "fallback_requested": True,
        "fallback_reason": "connection_error",
        "primary_worker_id": "jetson-nano-01",
        "attempted_worker_ids": ["jetson-fallback"],
        "final_status": "succeeded",
        "attempts": [
            {
                "schema_version": "inferedge-remote-execution-result-v1",
                "execution_requested": True,
                "execution_performed": True,
                "production_remote_execution": False,
                "status": "succeeded",
                "transport": "http",
                "selected_worker_id": "jetson-fallback",
                "task_id": "remote_task_001",
                "agent_id": "vision_agent",
                "http_status": 200,
                "fallback_attempt": 1,
                "fallback_for_worker_id": "jetson-nano-01",
                "response_json": {"status": "ok"},
            }
        ],
        "production_remote_execution": False,
    }
    result["runtime_events"].append(
        {
            "event": "remote_fallback_execution_completed",
            "status": "succeeded",
            "selected_worker_id": "jetson-fallback",
        }
    )
    return result


def remote_dispatch_plan_only_result() -> dict:
    result = remote_dispatch_success_result()
    result["remote_execution"]["execution_requested"] = False
    result["remote_execution_plan"]["mode"] = "plan_only"
    result["remote_execution_plan"]["network_execution_performed"] = False
    result["remote_execution_result"] = {
        "schema_version": "inferedge-remote-execution-result-v1",
        "execution_requested": False,
        "execution_performed": False,
        "production_remote_execution": False,
        "status": "skipped",
        "transport": "file_contract",
        "selected_worker_id": "jetson-nano-01",
        "task_id": "remote_task_001",
        "agent_id": "vision_agent",
        "error_category": "execution_not_requested",
    }
    result["retry_fallback_plan"]["last_execution_status"] = "skipped"
    result["runtime_events"] = [{"event": "remote_dispatch_selected"}]
    return result


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
    assert metrics["runtime_error_retryable"] is True
    assert metrics["retry_hint"] == "check_backend_availability"
    assert metrics["thermal_memory_evidence_available"] is False
    assert metrics["runtime_event_count"] == 2
    assert metrics["runtime_operation_summary_schema"] == (
        "inferedge-runtime-operation-summary-v1"
    )
    assert metrics["runtime_operation_health_reason"] == (
        "backend_unavailable_or_not_enabled"
    )
    assert metrics["runtime_operation_recommended_action"] == (
        "check_backend_availability"
    )
    assert metrics["runtime_operation_risk_labels"] == [
        "runtime_execution_skipped",
        "backend_unavailable",
    ]
    assert metrics["runtime_operation_evidence_gaps"] == [
        "timeout_policy_not_configured",
        "thermal_memory_evidence_missing",
    ]
    assert metrics["runtime_operation_decision_owner"] == "lab"
    assert metrics["runtime_operation_scheduler_owner"] == "orchestrator"


def test_compute_remote_dispatch_metrics_from_execution_result():
    metrics = compute_remote_dispatch_metrics(remote_dispatch_failure_result())

    assert metrics["schema_version"] == "inferedge-remote-dispatch-result-v1"
    assert metrics["dispatch_status"] == "accepted"
    assert metrics["selected_worker_id"] == "jetson-nano-01"
    assert metrics["execution_requested"] is True
    assert metrics["execution_performed"] is True
    assert metrics["execution_failed"] is True
    assert metrics["transport"] == "http"
    assert metrics["error_category"] == "connection_error"
    assert metrics["runtime_event_count"] == 2


def test_compute_remote_dispatch_metrics_from_fallback_recovery():
    metrics = compute_remote_dispatch_metrics(remote_dispatch_fallback_recovered_result())

    assert metrics["execution_failed"] is True
    assert metrics["fallback_execution_performed"] is True
    assert metrics["fallback_attempted_worker_ids"] == ["jetson-fallback"]
    assert metrics["fallback_attempt_count"] == 1
    assert metrics["fallback_final_status"] == "succeeded"
    assert metrics["fallback_recovered"] is True
    assert metrics["fallback_failed"] is False
    assert metrics["fallback_primary_worker_id"] == "jetson-nano-01"
    assert metrics["fallback_reason"] == "connection_error"
    assert metrics["runtime_event_count"] == 3


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


def test_operation_telemetry_summary_preserves_phase2_metrics():
    metrics = compute_runtime_reliability_metrics(operation_telemetry_summary())

    assert metrics["policy_decision_reason_counts"] == {
        "queue_backlog_threshold_exceeded": 1
    }
    assert metrics["drop_reason_counts"] == {
        "load_shedding_backlog_threshold_exceeded": 2
    }
    assert metrics["runtime_event_reason_counts"]["scheduler_delay_observed"] == 1
    assert metrics["queue_pressure_reason_counts"] == {
        "queue_backlog_threshold_exceeded": 1,
        "queue_pressure_elevated": 2,
    }
    assert metrics["scheduler_delay_event_count"] == 2
    assert metrics["fallback_decision_count"] == 2
    assert metrics["runtime_event_count"] == 9
    assert metrics["latest_runtime_event_type"] == "execution"
    assert metrics["queue_pressure_state"] == "overloaded"
    assert metrics["queue_pressure_reason"] == (
        "max_total_queue_depth_exceeded_overload_threshold"
    )
    assert metrics["max_pressure_task"] == "vision_agent"
    assert metrics["device_local_task_count"] == 3
    assert metrics["device_local_event_count"] == 9
    assert metrics["producer_event_count"] == 13
    assert metrics["runtime_event_producer_sources"] == [
        "resource_snapshot_fixture",
        "image_file",
        "fastapi_request_fixture",
    ]
    assert metrics["device_local_producer_sources"] == [
        "resource_snapshot_fixture",
        "image_file",
        "fastapi_request_fixture",
    ]
    assert metrics["producer_sources_by_task"]["vision_agent"] == ["image_file"]
    assert metrics["worker_health"]["degraded_worker_count"] == 2
    assert metrics["worker_health"]["health_reason_counts"] == {
        "healthy_without_runtime_risk": 1,
        "fallback_policy_used": 2,
        "frames_dropped": 2,
        "queue_reached_capacity": 2,
    }
    assert metrics["worker_health"]["primary_health_reason_counts"] == {
        "healthy_without_runtime_risk": 1,
        "fallback_policy_used": 2,
    }
    assert metrics["worker_health"]["operation_risk_summary_counts"] == {
        "healthy_without_runtime_risk": 1,
        "latency_or_fallback_risk": 1,
        "drop_or_queue_pressure_risk": 1,
    }
    assert metrics["worker_health"]["device_local_worker_count"] == 3
    assert metrics["worker_health"]["producer_sources"] == [
        "resource_snapshot_fixture",
        "image_file",
        "fastapi_request_fixture",
    ]


def test_compute_edgeenv_regression_metrics_preserves_telemetry_context():
    metrics = compute_edgeenv_regression_metrics(edgeenv_regression_report())

    assert metrics["comparable"] is True
    assert metrics["mode"] == "same-condition"
    assert metrics["regression_detected"] is True
    assert metrics["p99_delta_pct"] == 32.0
    assert metrics["fps_delta_pct"] == -22.0
    assert metrics["memory_peak_delta_pct"] == 40.0
    assert metrics["runtime_telemetry_context_present"] is True
    assert metrics["candidate_telemetry_present"] is True
    assert metrics["candidate_history_entry_present"] is True
    assert metrics["history_missing_telemetry_runs"] == 0.0
    assert metrics["baseline_execution_sequence_id"] == 1.0
    assert metrics["candidate_execution_sequence_id"] == 2.0
    assert metrics["execution_sequence_order_valid"] is True
    assert metrics["evidence_gap_count"] == 0.0


def test_compute_edgeenv_regression_metrics_extracts_runtime_telemetry_signals():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_runtime_telemetry_signals()
    )

    assert metrics["baseline_max_temperature_c"] == 55.0
    assert metrics["candidate_max_temperature_c"] == 76.2
    assert metrics["baseline_throttling_detected"] is False
    assert metrics["candidate_throttling_detected"] is True
    assert metrics["baseline_queue_depth"] == 1.0
    assert metrics["candidate_queue_depth"] == 6.0


def test_compute_edgeenv_regression_metrics_extracts_telemetry_coverage_metadata():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_runtime_telemetry_coverage_gap()
    )

    assert metrics["baseline_telemetry_coverage_ratio"] == 1.0
    assert metrics["candidate_telemetry_coverage_ratio"] == 0.666667
    assert metrics["baseline_telemetry_coverage_missing_fields"] == []
    assert metrics["candidate_telemetry_coverage_missing_fields"] == ["queue_depth"]
    assert metrics["telemetry_coverage_missing_field_count"] == 1.0
    assert metrics["telemetry_coverage_source"] == "history_telemetry_coverage"
    assert metrics["history_telemetry_coverage_missing_field_run_count"] == 1.0
    assert metrics["history_telemetry_coverage_missing_field_runs"] == [
        {
            "run_id": "edgeenv-smoke-candidate",
            "missing_fields": ["queue_depth"],
            "missing_field_count": 1,
            "missing_telemetry_is_failure": False,
        }
    ]
    assert metrics["history_telemetry_coverage_run_summaries_present"] is True
    assert metrics["baseline_missing_telemetry_is_failure"] is False
    assert metrics["candidate_missing_telemetry_is_failure"] is False
    assert metrics["evidence_gap_count"] == 1.0


def test_compute_edgeenv_regression_metrics_prefers_history_coverage_summary():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_history_telemetry_coverage_gap()
    )

    assert metrics["baseline_telemetry_coverage_ratio"] == 1.0
    assert metrics["candidate_telemetry_coverage_ratio"] == 0.666667
    assert metrics["baseline_telemetry_coverage_missing_fields"] == []
    assert metrics["candidate_telemetry_coverage_missing_fields"] == ["queue_depth"]
    assert metrics["telemetry_coverage_source"] == "history_telemetry_coverage"
    assert metrics["telemetry_coverage_missing_field_count"] == 1.0
    assert metrics["evidence_gap_count"] == 1.0


def test_compute_edgeenv_regression_metrics_preserves_runtime_history_seed():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_runtime_telemetry_history_seed()
    )

    assert metrics["history_telemetry_seed_runs"] == 2.0
    assert metrics["baseline_runtime_telemetry_history_seed_schema_version"] == (
        "inferedge-runtime-telemetry-history-seed-v1"
    )
    assert metrics["candidate_runtime_telemetry_history_seed_schema_version"] == (
        "inferedge-runtime-telemetry-history-seed-v1"
    )
    assert metrics["candidate_runtime_telemetry_history_seed_registry_owner"] == (
        "edgeenv"
    )
    assert metrics["candidate_runtime_telemetry_history_seed_decision_owner"] == "lab"
    assert (
        metrics["candidate_runtime_telemetry_history_seed_production_monitoring"]
        is False
    )
    assert (
        metrics[
            "candidate_runtime_telemetry_history_seed_missing_telemetry_is_failure"
        ]
        is False
    )
    assert metrics["candidate_runtime_telemetry_history_seed_point_count"] == 1.0


def test_compute_edgeenv_regression_metrics_extracts_orchestrator_feed_context():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_orchestrator_feed_context()
    )

    assert metrics["history_orchestrator_feed_runs"] == 1.0
    assert metrics["candidate_orchestrator_context_present"] is True
    assert metrics["orchestrator_candidate_context_telemetry_source"] == (
        "inferedge_orchestrator_operation_summary"
    )
    assert metrics["orchestrator_source_repository"] == "InferEdgeOrchestrator"
    assert (
        metrics["orchestrator_artifact_role"]
        == "orchestrator-supplemental-operation-context"
    )
    assert metrics["orchestrator_producer_contract"] == (
        "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    )
    assert metrics["orchestrator_mapping_hint_coverage_summary_owner"] == "edgeenv"
    assert metrics["orchestrator_mapping_hint_coverage_summary_path"] == (
        "runtime_telemetry_context.history.telemetry_coverage"
    )
    assert metrics["orchestrator_mapping_hint_operation_context_role"] == "supplemental"
    assert set(metrics["orchestrator_mapping_hint_candidate_context_required_fields"]) >= {
        "run_id",
        "telemetry_source",
        "operation",
        "resource",
    }
    assert set(metrics["orchestrator_mapping_hint_aiguard_evidence_candidates"]) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }
    assert metrics["orchestrator_candidate_context_producer"][
        "operation_context_role"
    ] == "supplemental"
    assert metrics["orchestrator_candidate_producer_sources"] == [
        "device_local_cli_override",
        "orchestration_summary",
    ]
    assert metrics["orchestrator_candidate_device_local_producer_sources"] == [
        "device_local_cli_override"
    ]
    assert metrics["orchestrator_candidate_producer_sources_by_task"] == {
        "vision_agent": ["device_local_cli_override"]
    }
    assert metrics["orchestrator_candidate_producer_stage_by_task"] == {
        "vision_agent": "device_local_starter"
    }
    assert metrics["orchestrator_candidate_producer_event_count"] == 4.0
    assert metrics["orchestrator_candidate_device_local_event_count"] == 2.0
    assert metrics["orchestrator_candidate_device_local_task_count"] == 1.0
    assert metrics["orchestrator_candidate_operation_context_role"] == "supplemental"
    assert metrics["candidate_max_temperature_c"] == 78.5
    assert metrics["candidate_throttling_detected"] is True
    assert metrics["candidate_queue_depth"] == 7.0


def test_compute_edgeenv_regression_metrics_preserves_missing_orchestrator_context():
    metrics = compute_edgeenv_regression_metrics(
        edgeenv_regression_report_with_missing_telemetry_orchestrator_context()
    )

    assert metrics["history_missing_telemetry_runs"] == 1.0
    assert metrics["history_orchestrator_feed_runs"] == 1.0
    assert metrics["candidate_orchestrator_context_present"] is False
    assert metrics["history_missing_orchestrator_context_count"] == 1.0
    assert metrics["history_missing_orchestrator_context_run_ids"] == [
        "edgeenv-smoke-candidate"
    ]
    assert metrics["history_missing_orchestrator_source_repository"] == (
        "InferEdgeOrchestrator"
    )
    assert metrics["history_missing_orchestrator_artifact_role"] == (
        "orchestrator-supplemental-operation-context"
    )
    assert metrics["history_missing_orchestrator_producer_contract"] == (
        "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    )
    assert metrics[
        "history_missing_orchestrator_candidate_context_telemetry_source"
    ] == "inferedge_orchestrator_operation_summary"
    assert metrics["history_missing_orchestrator_candidate_context_producer"][
        "operation_context_role"
    ] == "supplemental"
    assert metrics[
        "history_missing_orchestrator_candidate_producer_sources"
    ] == [
        "device_local_cli_override",
        "orchestration_summary",
    ]
    assert metrics[
        "history_missing_orchestrator_candidate_device_local_producer_sources"
    ] == ["device_local_cli_override"]
    assert metrics[
        "history_missing_orchestrator_candidate_producer_sources_by_task"
    ] == {"vision_agent": ["device_local_cli_override"]}
    assert metrics[
        "history_missing_orchestrator_candidate_producer_stage_by_task"
    ] == {"vision_agent": "device_local_starter"}
    assert metrics[
        "history_missing_orchestrator_candidate_producer_event_count"
    ] == 4.0
    assert metrics[
        "history_missing_orchestrator_candidate_device_local_event_count"
    ] == 2.0
    assert metrics[
        "history_missing_orchestrator_candidate_device_local_task_count"
    ] == 1.0
    assert (
        metrics["history_missing_orchestrator_candidate_operation_context_role"]
        == "supplemental"
    )
    assert metrics["history_missing_orchestrator_edgeenv_mapping_hint"][
        "coverage_summary_owner"
    ] == "edgeenv"
    assert set(
        metrics[
            "history_missing_orchestrator_mapping_hint_aiguard_evidence_candidates"
        ]
    ) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }


def test_analyze_edgeenv_regression_report_returns_runtime_anomaly_evidence():
    report = analyze_edgeenv_regression_report(edgeenv_regression_report())

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "blocked"
    assert report["severity"] == "high"
    assert report["source"]["edgeenv_runtime_regression_report"] is True
    assert report["source"]["edgeenv_mode"] == "same-condition"
    assert report["primary_reason"] == (
        "EdgeEnv same-condition runtime regression evidence requires "
        "deterministic AIGuard review."
    )
    evidence_types = {item["type"] for item in report["evidence"]}
    assert evidence_types == {
        "runtime_latency_regression",
        "runtime_throughput_regression",
        "runtime_memory_regression",
        "runtime_telemetry_context_coverage",
    }
    latency_evidence = next(
        item for item in report["evidence"] if item["type"] == "runtime_latency_regression"
    )
    assert latency_evidence["metric_name"] == "p99_delta_pct"
    assert latency_evidence["observed_value"] == 32.0
    assert latency_evidence["threshold"] == 25.0
    assert "tail_latency_spike" in latency_evidence["suspected_causes"]

    telemetry_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_telemetry_context_coverage"
    )
    assert telemetry_evidence["status"] == "passed"
    assert telemetry_evidence["observed_value"] == 0.0
    assert report["candidate_summary"]["edgeenv_regression"]["candidate_run_id"] == (
        "edgeenv-smoke-candidate"
    )


def test_analyze_edgeenv_regression_report_warns_on_runtime_telemetry_signals():
    report = analyze_edgeenv_regression_report(
        edgeenv_regression_report_with_runtime_telemetry_signals()
    )

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "suspicious"
    assert report["severity"] == "medium"
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "runtime_thermal_instability" in evidence_types
    assert "runtime_queue_overload" in evidence_types
    thermal_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_thermal_instability"
    )
    assert thermal_evidence["status"] == "warning"
    assert thermal_evidence["metric_name"] == "candidate_max_temperature_c"
    assert thermal_evidence["observed_value"] == 76.2
    assert "thermal_throttling" in thermal_evidence["suspected_causes"]
    queue_evidence = next(
        item for item in report["evidence"] if item["type"] == "runtime_queue_overload"
    )
    assert queue_evidence["status"] == "warning"
    assert queue_evidence["observed_value"] == 6.0
    assert "queue_overload" in queue_evidence["suspected_causes"]
    assert report["candidate_summary"]["edgeenv_regression"][
        "candidate_throttling_detected"
    ] is True


def test_analyze_edgeenv_regression_report_warns_on_telemetry_coverage_metadata_gap():
    report = analyze_edgeenv_regression_report(
        edgeenv_regression_report_with_runtime_telemetry_coverage_gap()
    )

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "suspicious"
    assert report["severity"] == "medium"
    evidence = report["evidence"][0]
    assert evidence["type"] == "runtime_telemetry_context_coverage"
    assert evidence["status"] == "warning"
    assert evidence["observed_value"] == 1.0
    assert "runtime_telemetry_field_gap" in evidence["suspected_causes"]
    assert "runtime_telemetry_gap" in evidence["suspected_causes"]
    metrics = evidence["raw_context"]["edgeenv_regression"]
    assert metrics["candidate_telemetry_coverage_missing_fields"] == ["queue_depth"]
    assert metrics["telemetry_coverage_source"] == "history_telemetry_coverage"
    assert metrics["history_telemetry_coverage_missing_field_runs"] == [
        {
            "run_id": "edgeenv-smoke-candidate",
            "missing_fields": ["queue_depth"],
            "missing_field_count": 1,
            "missing_telemetry_is_failure": False,
        }
    ]
    assert metrics["candidate_missing_telemetry_is_failure"] is False
    assert "Inspect telemetry coverage missing fields" in evidence["recommendation"]


def test_analyze_edgeenv_regression_report_preserves_history_seed_raw_context():
    report = analyze_edgeenv_regression_report(
        edgeenv_regression_report_with_runtime_telemetry_history_seed()
    )

    validate_diagnosis_report(report)
    evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_telemetry_context_coverage"
    )
    metrics = evidence["raw_context"]["edgeenv_regression"]
    assert metrics["history_telemetry_seed_runs"] == 2.0
    assert metrics["candidate_runtime_telemetry_history_seed_schema_version"] == (
        "inferedge-runtime-telemetry-history-seed-v1"
    )
    assert metrics["candidate_runtime_telemetry_history_seed_registry_owner"] == (
        "edgeenv"
    )
    assert metrics["candidate_runtime_telemetry_history_seed_decision_owner"] == "lab"
    assert (
        metrics["candidate_runtime_telemetry_history_seed_production_monitoring"]
        is False
    )
    assert (
        metrics[
            "candidate_runtime_telemetry_history_seed_missing_telemetry_is_failure"
        ]
        is False
    )


def test_analyze_edgeenv_regression_report_warns_on_orchestrator_feed_context():
    report = analyze_edgeenv_regression_report(
        edgeenv_regression_report_with_orchestrator_feed_context()
    )

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "suspicious"
    assert report["severity"] == "medium"
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "edgeenv_orchestrator_producer_lineage" in evidence_types
    assert "runtime_thermal_instability" in evidence_types
    assert "runtime_queue_overload" in evidence_types
    queue_evidence = next(
        item for item in report["evidence"] if item["type"] == "runtime_queue_overload"
    )
    assert queue_evidence["observed_value"] == 7.0
    assert "queue_overload" in queue_evidence["suspected_causes"]
    assert report["candidate_summary"]["edgeenv_regression"][
        "candidate_orchestrator_context_present"
    ] is True
    assert report["candidate_summary"]["edgeenv_regression"][
        "orchestrator_mapping_hint_coverage_summary_owner"
    ] == "edgeenv"
    assert report["candidate_summary"]["edgeenv_regression"][
        "orchestrator_mapping_hint_operation_context_role"
    ] == "supplemental"
    assert set(
        report["candidate_summary"]["edgeenv_regression"][
            "orchestrator_mapping_hint_aiguard_evidence_candidates"
        ]
    ) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }
    queue_context = queue_evidence["raw_context"]["edgeenv_regression"]
    assert queue_context["orchestrator_source_repository"] == "InferEdgeOrchestrator"
    assert (
        queue_context["orchestrator_artifact_role"]
        == "orchestrator-supplemental-operation-context"
    )
    assert queue_context["orchestrator_producer_contract"] == (
        "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    )
    assert queue_context["orchestrator_candidate_context_producer"][
        "operation_context_role"
    ] == "supplemental"
    assert queue_context["orchestrator_candidate_device_local_producer_sources"] == [
        "device_local_cli_override"
    ]
    assert queue_context["orchestrator_candidate_producer_stage_by_task"] == {
        "vision_agent": "device_local_starter"
    }
    producer_lineage = next(
        item
        for item in report["evidence"]
        if item["type"] == "edgeenv_orchestrator_producer_lineage"
    )
    assert producer_lineage["status"] == "passed"
    assert producer_lineage["observed_value"] == 1
    assert producer_lineage["baseline_value"] == 1
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_device_local_sources"
    ] == ["device_local_cli_override"]
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_producer_sources"
    ] == ["device_local_cli_override", "orchestration_summary"]
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_sources_by_task"
    ] == {"vision_agent": ["device_local_cli_override"]}
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_stage_by_task"
    ] == {"vision_agent": "device_local_starter"}
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_producer_event_count"
    ] == 4.0
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_device_local_event_count"
    ] == 2.0
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_device_local_task_count"
    ] == 1.0
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_lineage_shape_valid"
    ] is True


def test_analyze_edgeenv_regression_report_warns_on_missing_producer_lineage():
    regression_report = edgeenv_regression_report_with_orchestrator_feed_context()
    regression_report["runtime_telemetry_context"]["candidate"][
        "orchestrator_operation_context"
    ]["candidate_context"].pop("producer")

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    producer_lineage = next(
        item
        for item in report["evidence"]
        if item["type"] == "edgeenv_orchestrator_producer_lineage"
    )
    assert producer_lineage["status"] == "warning"
    assert producer_lineage["observed_value"] == 0
    assert producer_lineage["baseline_value"] == 1
    assert "device_local_producer_lineage_gap" in producer_lineage[
        "suspected_causes"
    ]


def test_analyze_edgeenv_regression_report_warns_on_bad_producer_shape():
    regression_report = edgeenv_regression_report_with_orchestrator_feed_context()
    producer = regression_report["runtime_telemetry_context"]["candidate"][
        "orchestrator_operation_context"
    ]["candidate_context"]["producer"]
    producer["producer_sources_by_task"] = {"vision_agent": ["orchestration_summary"]}

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    producer_lineage = next(
        item
        for item in report["evidence"]
        if item["type"] == "edgeenv_orchestrator_producer_lineage"
    )
    assert producer_lineage["status"] == "warning"
    assert producer_lineage["observed_value"] == 0
    assert producer_lineage["baseline_value"] == 1
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_device_local_sources"
    ] == ["device_local_cli_override"]
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_sources_by_task"
    ] == {"vision_agent": ["orchestration_summary"]}
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_lineage_shape_valid"
    ] is False


def test_analyze_edgeenv_regression_report_warns_on_telemetry_gap():
    regression_report = edgeenv_regression_report()
    regression_report["regression_detected"] = False
    regression_report["evidence"] = {}
    regression_report["runtime_telemetry_context"]["candidate"][
        "result_telemetry_present"
    ] = False
    regression_report["runtime_telemetry_context"]["candidate"][
        "history_entry_present"
    ] = False
    regression_report["runtime_telemetry_context"]["evidence_gaps"] = [
        {
            "run_id": "edgeenv-smoke-candidate",
            "reason": "runtime_telemetry_missing_in_result",
        }
    ]

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "suspicious"
    assert report["severity"] == "medium"
    evidence = report["evidence"][0]
    assert evidence["type"] == "runtime_telemetry_context_coverage"
    assert evidence["status"] == "warning"
    assert evidence["observed_value"] == 3.0
    assert "runtime_telemetry_gap" in evidence["suspected_causes"]


def test_analyze_edgeenv_regression_report_warns_on_replay_history_gap():
    regression_report = edgeenv_regression_report()
    regression_report["regression_detected"] = False
    regression_report["evidence"] = {}
    regression_report["runtime_telemetry_context"]["history"]["summary"][
        "registered_runs"
    ] = 3
    regression_report["runtime_telemetry_context"]["history"]["summary"][
        "missing_telemetry_runs"
    ] = 1

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "suspicious"
    assert report["severity"] == "medium"
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "runtime_telemetry_context_coverage" in evidence_types
    replay_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_telemetry_replay_context"
    )
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 1.0
    assert "telemetry_history_replay_gap" in replay_evidence["suspected_causes"]
    assert "EdgeEnv telemetry history is the replay artifact" in replay_evidence[
        "why_it_matters"
    ]


def test_analyze_edgeenv_regression_report_preserves_missing_orchestrator_raw_context():
    regression_report = (
        edgeenv_regression_report_with_missing_telemetry_orchestrator_context()
    )

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    replay_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_telemetry_replay_context"
    )
    replay_context = replay_evidence["raw_context"]["edgeenv_regression"]
    assert replay_context["history_missing_orchestrator_context_run_ids"] == [
        "edgeenv-smoke-candidate"
    ]
    assert replay_context["history_missing_orchestrator_source_repository"] == (
        "InferEdgeOrchestrator"
    )
    assert replay_context["history_missing_orchestrator_artifact_role"] == (
        "orchestrator-supplemental-operation-context"
    )
    assert replay_context["history_missing_orchestrator_producer_contract"] == (
        "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    )
    assert replay_context["history_missing_orchestrator_edgeenv_mapping_hint"][
        "operation_context_role"
    ] == "supplemental"
    assert set(
        replay_context[
            "history_missing_orchestrator_mapping_hint_aiguard_evidence_candidates"
        ]
    ) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }
    assert report["candidate_summary"]["edgeenv_regression"][
        "history_missing_orchestrator_context_count"
    ] == 1.0
    producer_lineage = next(
        item
        for item in report["evidence"]
        if item["type"] == "edgeenv_orchestrator_producer_lineage"
    )
    assert producer_lineage["status"] == "passed"
    assert producer_lineage["observed_value"] == 1
    assert producer_lineage["baseline_value"] == 1
    assert producer_lineage["raw_context"]["producer_lineage"][
        "missing_device_local_sources"
    ] == ["device_local_cli_override"]
    assert producer_lineage["raw_context"]["producer_lineage"][
        "missing_sources_by_task"
    ] == {"vision_agent": ["device_local_cli_override"]}
    assert producer_lineage["raw_context"]["producer_lineage"][
        "missing_stage_by_task"
    ] == {"vision_agent": "device_local_starter"}
    assert producer_lineage["raw_context"]["producer_lineage"][
        "missing_lineage_shape_valid"
    ] is True
    assert producer_lineage["raw_context"]["producer_lineage"][
        "missing_context_run_ids"
    ] == ["edgeenv-smoke-candidate"]


def test_analyze_edgeenv_regression_report_warns_on_replay_sequence_order():
    regression_report = edgeenv_regression_report()
    regression_report["regression_detected"] = False
    regression_report["evidence"] = {}
    regression_report["runtime_telemetry_context"]["baseline"][
        "execution_sequence_id"
    ] = 5
    regression_report["runtime_telemetry_context"]["candidate"][
        "execution_sequence_id"
    ] = 2

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    replay_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_telemetry_replay_context"
    )
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 0.0
    assert "telemetry_sequence_order_mismatch" in replay_evidence[
        "suspected_causes"
    ]


def test_analyze_edgeenv_regression_report_skips_non_comparable_regression():
    regression_report = edgeenv_regression_report()
    regression_report["comparable"] = False
    regression_report["mode"] = "protocol_mismatch"

    report = analyze_edgeenv_regression_report(regression_report)

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "pass"
    evidence = report["evidence"][0]
    assert evidence["type"] == "edgeenv_comparability_guardrail"
    assert evidence["status"] == "skipped"
    assert "does not reinterpret non-comparable" in evidence["why_it_matters"]


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


def test_analyze_operation_telemetry_adds_worker_and_scheduler_warnings():
    report = analyze_orchestration_summary(operation_telemetry_summary())

    validate_diagnosis_report(report)
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "worker_health_degradation" in evidence_types
    assert "scheduler_delay_pattern" in evidence_types
    assert "queue_pressure_context" in evidence_types
    assert "worker_operation_risk_summary" in evidence_types
    assert "device_local_operation_context" in evidence_types

    worker_evidence = next(
        item for item in report["evidence"] if item["type"] == "worker_health_degradation"
    )
    assert worker_evidence["status"] == "warning"
    assert worker_evidence["raw_context"]["worker_health"]["degraded_workers"] == [
        "vision_agent",
        "voice_command_agent",
    ]
    assert "fallback_policy_used" in worker_evidence["suspected_causes"]

    scheduler_evidence = next(
        item for item in report["evidence"] if item["type"] == "scheduler_delay_pattern"
    )
    assert scheduler_evidence["observed_value"] == 2
    assert scheduler_evidence["status"] == "failed"
    assert scheduler_evidence["raw_context"]["drop_reason_counts"] == {
        "load_shedding_backlog_threshold_exceeded": 2
    }
    assert (
        report["candidate_summary"]["runtime_reliability"][
            "policy_decision_reason_counts"
        ]
        == {"queue_backlog_threshold_exceeded": 1}
    )
    queue_pressure = next(
        item for item in report["evidence"] if item["type"] == "queue_pressure_context"
    )
    assert queue_pressure["status"] == "warning"
    assert queue_pressure["raw_context"]["queue_pressure_reason"] == (
        "max_total_queue_depth_exceeded_overload_threshold"
    )
    assert queue_pressure["raw_context"]["max_pressure_task"] == "vision_agent"
    assert "queue_backlog" in queue_pressure["suspected_causes"]

    worker_risk = next(
        item
        for item in report["evidence"]
        if item["type"] == "worker_operation_risk_summary"
    )
    assert worker_risk["status"] == "warning"
    assert worker_risk["observed_value"] == 2
    assert worker_risk["raw_context"]["operation_risk_summary_counts"] == {
        "latency_or_fallback_risk": 1,
        "drop_or_queue_pressure_risk": 1,
    }

    device_local = next(
        item
        for item in report["evidence"]
        if item["type"] == "device_local_operation_context"
    )
    assert device_local["status"] == "passed"
    assert device_local["observed_value"] == 9
    assert device_local["raw_context"]["device_local_producer_sources"] == [
        "resource_snapshot_fixture",
        "image_file",
        "fastapi_request_fixture",
    ]


def test_device_local_operation_context_warns_when_event_coverage_is_missing():
    summary = operation_telemetry_summary()
    summary["runtime_event_summary"]["device_local_event_count"] = 0
    summary["runtime_event_summary"]["producer_event_count"] = 0
    summary["runtime_event_summary"]["producer_sources"] = []
    summary["queue_state_summary"]["device_local_producer_sources"] = []

    report = analyze_orchestration_summary(summary)

    validate_diagnosis_report(report)
    evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "device_local_operation_context"
    )
    assert evidence["status"] == "warning"
    assert evidence["severity"] == "medium"
    assert "device_local_evidence_gap" in evidence["suspected_causes"]
    assert "local input overrides" in evidence["recommendation"]


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
        "runtime_operation_health",
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
    error_evidence = next(
        item
        for item in report["evidence"]
        if item["type"] == "runtime_error_classification"
    )
    runtime_operation = error_evidence["raw_context"]["runtime_operation"]
    assert runtime_operation["runtime_error_retryable"] is True
    assert runtime_operation["retry_hint"] == "check_backend_availability"
    assert runtime_operation["runtime_operation_summary_schema"] == (
        "inferedge-runtime-operation-summary-v1"
    )
    assert runtime_operation["runtime_operation_health_reason"] == (
        "backend_unavailable_or_not_enabled"
    )
    assert runtime_operation["runtime_operation_recommended_action"] == (
        "check_backend_availability"
    )
    assert runtime_operation["runtime_operation_risk_labels"] == [
        "runtime_execution_skipped",
        "backend_unavailable",
    ]
    assert "runtime_retryable_error" in error_evidence["suspected_causes"]
    assert "retryable Runtime-side failure evidence" in error_evidence["recommendation"]
    operation_evidence = next(
        item for item in report["evidence"] if item["type"] == "runtime_operation_health"
    )
    assert operation_evidence["metric_name"] == "runtime_operation_summary_risk_count"
    assert operation_evidence["observed_value"] == 2
    assert operation_evidence["status"] == "warning"
    assert operation_evidence["recommendation"] == "check_backend_availability"
    assert "backend_unavailable" in operation_evidence["suspected_causes"]
    assert operation_evidence["raw_context"]["decision_owner"] == "lab"
    assert operation_evidence["raw_context"]["scheduler_owner"] == "orchestrator"
    assert (
        report["candidate_summary"]["runtime_operation"]["runtime_event_count"]
        == 2
    )


def test_analyze_remote_dispatch_result_warns_on_plan_only():
    report = analyze_remote_dispatch_result(remote_dispatch_plan_only_result())

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "pass"
    assert report["severity"] == "low"
    assert report["source"]["remote_dispatch_schema_version"] == (
        "inferedge-remote-dispatch-result-v1"
    )
    evidence = report["evidence"][0]
    assert evidence["type"] == "remote_execution_plan_only"
    assert evidence["status"] == "skipped"
    assert (
        report["candidate_summary"]["remote_dispatch"]["execution_requested"]
        is False
    )


def test_analyze_remote_dispatch_result_passes_on_success():
    report = analyze_remote_dispatch_result(remote_dispatch_success_result())

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "pass"
    evidence = report["evidence"][0]
    assert evidence["type"] == "remote_execution_starter_success"
    assert evidence["status"] == "passed"
    assert report["candidate_summary"]["remote_dispatch"]["http_status"] == 200


def test_analyze_remote_dispatch_result_blocks_on_connection_failure():
    report = analyze_remote_dispatch_result(remote_dispatch_failure_result())

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "blocked"
    assert report["severity"] == "high"
    evidence = report["evidence"][0]
    assert evidence["type"] == "remote_execution_failed"
    assert evidence["status"] == "failed"
    assert "connection_error" in evidence["suspected_causes"]


def test_analyze_remote_dispatch_result_warns_when_fallback_recovers_primary_failure():
    report = analyze_remote_dispatch_result(remote_dispatch_fallback_recovered_result())

    validate_diagnosis_report(report)
    assert report["guard_verdict"] == "review_required"
    assert report["severity"] == "medium"
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "remote_execution_failed" in evidence_types
    assert "remote_execution_recovered_by_fallback" in evidence_types
    primary_failure = next(
        item for item in report["evidence"] if item["type"] == "remote_execution_failed"
    )
    recovery = next(
        item
        for item in report["evidence"]
        if item["type"] == "remote_execution_recovered_by_fallback"
    )
    assert primary_failure["status"] == "failed"
    assert recovery["status"] == "warning"
    assert "primary_worker_unstable" in recovery["suspected_causes"]
    assert (
        report["candidate_summary"]["remote_dispatch"]["fallback_recovered"]
        is True
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


def test_orchestration_summary_can_include_remote_dispatch_evidence():
    summary = orchestration_summary()
    summary["remote_dispatch_results"] = [remote_dispatch_failure_result()]

    report = analyze_orchestration_summary(summary)

    validate_diagnosis_report(report)
    evidence_types = {item["type"] for item in report["evidence"]}
    assert "remote_execution_failed" in evidence_types
    assert (
        report["candidate_summary"]["remote_dispatch_results"][0]["error_category"]
        == "connection_error"
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


def test_cli_reason_remote_dispatch_and_unified_route(tmp_path):
    input_path = tmp_path / "remote_dispatch_result.json"
    input_path.write_text(
        json.dumps(remote_dispatch_failure_result()),
        encoding="utf-8",
    )

    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-remote-dispatch",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "remote_execution_failed" in explicit.stdout
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
    assert "connection_error" in unified.stdout


def test_cli_reason_edgeenv_regression_and_unified_route(tmp_path):
    input_path = tmp_path / "edgeenv_regression.json"
    input_path.write_text(
        json.dumps(edgeenv_regression_report()),
        encoding="utf-8",
    )

    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "runtime_latency_regression" in explicit.stdout
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
    assert "runtime_telemetry_context_coverage" in unified.stdout


def test_cli_reason_edgeenv_regression_saves_replay_context_evidence(tmp_path):
    regression_report = edgeenv_regression_report()
    regression_report["regression_detected"] = False
    regression_report["evidence"] = {}
    regression_report["runtime_telemetry_context"]["history"]["summary"][
        "registered_runs"
    ] = 3
    regression_report["runtime_telemetry_context"]["history"]["summary"][
        "missing_telemetry_runs"
    ] = 1
    input_path = tmp_path / "edgeenv_regression_history_gap.json"
    output_path = tmp_path / "reports" / "edgeenv_guard_analysis.json"
    input_path.write_text(json.dumps(regression_report), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    replay_evidence = next(
        item
        for item in saved["evidence"]
        if item["type"] == "runtime_telemetry_replay_context"
    )
    assert "runtime_telemetry_replay_context" in result.stdout
    assert "- saved_json:" in result.stdout
    assert saved["guard_verdict"] == "suspicious"
    assert replay_evidence["metric_name"] == (
        "runtime_telemetry_history_missing_run_count"
    )
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 1.0
    assert "telemetry_history_replay_gap" in replay_evidence["suspected_causes"]


def test_cli_reason_edgeenv_regression_saves_candidate_gap_replay_warning(tmp_path):
    input_path = tmp_path / "edgeenv_regression_candidate_gap.json"
    output_path = tmp_path / "reports" / "edgeenv_guard_analysis.json"
    input_path.write_text(
        json.dumps(edgeenv_regression_report_with_candidate_telemetry_gap()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    evidence_by_type = {item["type"]: item for item in saved["evidence"]}
    coverage_evidence = evidence_by_type["runtime_telemetry_context_coverage"]
    replay_evidence = evidence_by_type["runtime_telemetry_replay_context"]
    assert "runtime_telemetry_replay_context" in result.stdout
    assert "- saved_json:" in result.stdout
    assert saved["guard_verdict"] == "suspicious"
    assert coverage_evidence["status"] == "warning"
    assert "runtime_telemetry_gap" in coverage_evidence["suspected_causes"]
    assert replay_evidence["metric_name"] == (
        "runtime_telemetry_history_missing_run_count"
    )
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 1.0
    assert "telemetry_history_replay_gap" in replay_evidence["suspected_causes"]


def test_cli_reason_edgeenv_regression_saves_sequence_order_warning(tmp_path):
    input_path = tmp_path / "edgeenv_regression_sequence_inversion.json"
    output_path = tmp_path / "reports" / "edgeenv_guard_analysis.json"
    input_path.write_text(
        json.dumps(edgeenv_regression_report_with_sequence_inversion()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    replay_evidence = next(
        item
        for item in saved["evidence"]
        if item["type"] == "runtime_telemetry_replay_context"
    )
    assert "runtime_telemetry_replay_context" in result.stdout
    assert "- saved_json:" in result.stdout
    assert saved["guard_verdict"] == "suspicious"
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 0.0
    assert "telemetry_sequence_order_mismatch" in replay_evidence[
        "suspected_causes"
    ]


def test_cli_reason_edgeenv_regression_consumes_edgeenv_candidate_gap_fixture(tmp_path):
    input_path = EDGEENV_REGRESSION_FIXTURES / "edgeenv_candidate_telemetry_gap.json"
    output_path = tmp_path / "reports" / "edgeenv_guard_analysis.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    evidence_by_type = {item["type"]: item for item in saved["evidence"]}
    coverage_evidence = evidence_by_type["runtime_telemetry_context_coverage"]
    replay_evidence = evidence_by_type["runtime_telemetry_replay_context"]
    assert "runtime_telemetry_replay_context" in result.stdout
    assert saved["guard_verdict"] == "suspicious"
    assert saved["source"]["edgeenv_runtime_regression_report"] is True
    assert saved["source"]["edgeenv_mode"] == "same-condition"
    assert coverage_evidence["status"] == "warning"
    assert coverage_evidence["observed_value"] == 4.0
    assert "runtime_telemetry_gap" in coverage_evidence["suspected_causes"]
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 1.0
    assert "telemetry_history_replay_gap" in replay_evidence["suspected_causes"]
    assert "guard_analysis" not in json.loads(input_path.read_text(encoding="utf-8"))


def test_cli_reason_edgeenv_regression_consumes_edgeenv_sequence_fixture(tmp_path):
    input_path = EDGEENV_REGRESSION_FIXTURES / "edgeenv_sequence_inversion.json"
    output_path = tmp_path / "reports" / "edgeenv_guard_analysis.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    evidence_by_type = {item["type"]: item for item in saved["evidence"]}
    coverage_evidence = evidence_by_type["runtime_telemetry_context_coverage"]
    replay_evidence = evidence_by_type["runtime_telemetry_replay_context"]
    assert "runtime_telemetry_replay_context" in result.stdout
    assert saved["guard_verdict"] == "suspicious"
    assert coverage_evidence["status"] == "passed"
    assert coverage_evidence["observed_value"] == 0.0
    assert replay_evidence["status"] == "warning"
    assert replay_evidence["observed_value"] == 0.0
    assert "telemetry_sequence_order_mismatch" in replay_evidence[
        "suspected_causes"
    ]
    assert "guard_analysis" not in json.loads(input_path.read_text(encoding="utf-8"))


def test_runtime_intelligence_example_exports_lab_ready_guard_analysis(tmp_path):
    input_path = (
        RUNTIME_INTELLIGENCE_EXAMPLES
        / "edgeenv_runtime_regression_with_orchestrator_feed.json"
    )
    expected_path = (
        RUNTIME_INTELLIGENCE_EXAMPLES
        / "aiguard_runtime_operation_guard_analysis.json"
    )
    output_path = tmp_path / "aiguard_runtime_operation_guard_analysis.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    validate_diagnosis_report(expected)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inferedge_aiguard.cli",
            "reason-edgeenv-regression",
            "--input",
            str(input_path),
            "--save-json",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    validate_diagnosis_report(saved)
    saved_evidence_types = {item["type"] for item in saved["evidence"]}
    expected_evidence_types = {item["type"] for item in expected["evidence"]}
    forbidden_decision_keys = {
        "deployment_decision",
        "final_decision",
        "decision_owner",
    }

    assert output_path.name == expected_path.name
    assert "- saved_json:" in result.stdout
    assert saved["source"] == expected["source"]
    assert saved["guard_verdict"] == expected["guard_verdict"] == "suspicious"
    assert saved["severity"] == expected["severity"] == "medium"
    assert expected_evidence_types == {
        "runtime_telemetry_context_coverage",
        "edgeenv_orchestrator_producer_lineage",
        "runtime_thermal_instability",
        "runtime_queue_overload",
    }
    assert expected_evidence_types <= saved_evidence_types
    assert saved["candidate_summary"]["edgeenv_regression"][
        "history_orchestrator_feed_runs"
    ] == 1.0
    assert saved["candidate_summary"]["edgeenv_regression"][
        "candidate_orchestrator_context_present"
    ] is True
    assert saved["candidate_summary"]["edgeenv_regression"][
        "candidate_queue_depth"
    ] == 7.0
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_mapping_hint_coverage_summary_owner"
    ] == "edgeenv"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_mapping_hint_coverage_summary_path"
    ] == "runtime_telemetry_context.history.telemetry_coverage"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_mapping_hint_operation_context_role"
    ] == "supplemental"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_candidate_context_telemetry_source"
    ] == "inferedge_orchestrator_operation_summary"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_source_repository"
    ] == "InferEdgeOrchestrator"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_artifact_role"
    ] == "orchestrator-supplemental-operation-context"
    assert saved["candidate_summary"]["edgeenv_regression"][
        "orchestrator_producer_contract"
    ] == "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    assert set(
        saved["candidate_summary"]["edgeenv_regression"][
            "orchestrator_mapping_hint_aiguard_evidence_candidates"
        ]
    ) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }
    coverage_evidence = next(
        item
        for item in saved["evidence"]
        if item["type"] == "runtime_telemetry_context_coverage"
    )
    coverage_context = coverage_evidence["raw_context"]["edgeenv_regression"]
    assert coverage_context["orchestrator_edgeenv_mapping_hint"][
        "coverage_summary_owner"
    ] == "edgeenv"
    assert coverage_context["orchestrator_edgeenv_mapping_hint"][
        "coverage_summary_path"
    ] == "runtime_telemetry_context.history.telemetry_coverage"
    assert set(
        coverage_context["orchestrator_mapping_hint_aiguard_evidence_candidates"]
    ) == {
        "runtime_queue_overload",
        "runtime_thermal_instability",
    }
    assert coverage_context["orchestrator_source_repository"] == "InferEdgeOrchestrator"
    assert (
        coverage_context["orchestrator_artifact_role"]
        == "orchestrator-supplemental-operation-context"
    )
    assert coverage_context["orchestrator_producer_contract"] == (
        "inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1"
    )
    producer_lineage = next(
        item
        for item in saved["evidence"]
        if item["type"] == "edgeenv_orchestrator_producer_lineage"
    )
    assert producer_lineage["status"] == "passed"
    assert producer_lineage["observed_value"] == 1
    assert producer_lineage["baseline_value"] == 1
    assert producer_lineage["raw_context"]["producer_lineage"][
        "candidate_device_local_sources"
    ] == ["device_local_cli_override"]
    assert forbidden_decision_keys.isdisjoint(saved)
    assert forbidden_decision_keys.isdisjoint(expected)
