import json
import subprocess
import sys
from pathlib import Path

from inferedge_aiguard.runtime_reliability import (
    analyze_orchestration_summary,
    compute_runtime_reliability_metrics,
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
