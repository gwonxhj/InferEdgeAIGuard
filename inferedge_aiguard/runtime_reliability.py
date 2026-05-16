"""Runtime reliability evidence for Orchestrator summaries.

This module consumes InferEdgeOrchestrator's additive
``inferedge-orchestration-summary-v1`` contract and converts scheduling
telemetry into the existing AIGuard diagnosis report contract. It does not make
the final deployment decision; Lab remains the decision owner.
"""

from __future__ import annotations

from typing import Any

from .diagnosis import build_diagnosis_report, build_evidence_item


ORCHESTRATION_SCHEMA_VERSION = "inferedge-orchestration-summary-v1"

DEFAULT_RUNTIME_RELIABILITY_THRESHOLDS = {
    "deadline_miss_rate_review": 0.05,
    "deadline_miss_rate_blocked": 0.20,
    "drop_rate_review": 0.20,
    "drop_rate_blocked": 0.50,
    "fallback_rate_review": 0.20,
    "fallback_rate_blocked": 0.50,
    "queue_backlog_policy_decision_count_review": 1,
}


def analyze_orchestration_summary(
    summary: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build guard_analysis from an Orchestrator summary JSON object."""

    policy = {**DEFAULT_RUNTIME_RELIABILITY_THRESHOLDS, **(thresholds or {})}
    runtime_summary = _runtime_summary(summary)
    totals = _totals(runtime_summary)
    metrics = compute_runtime_reliability_metrics(summary)

    evidence = [
        _deadline_miss_evidence(metrics, totals, policy),
        _drop_rate_evidence(metrics, totals, policy),
        _fallback_rate_evidence(metrics, totals, policy),
        _queue_backlog_evidence(metrics, totals, policy),
    ]

    return build_diagnosis_report(
        evidence=evidence,
        source={
            "orchestration_summary_schema_version": summary.get("schema_version")
            or runtime_summary.get("schema_version"),
            "source_contracts": runtime_summary.get("source_contracts", {}),
            **(source or {}),
        },
        confidence=_confidence_from_evidence(evidence),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "schema_version": summary.get("schema_version")
            or runtime_summary.get("schema_version"),
            "agents": runtime_summary.get("agents", {}),
            "totals": totals,
            "runtime_reliability": metrics,
        },
    )


def compute_runtime_reliability_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    """Compute deterministic runtime reliability metrics from Orchestrator output."""

    runtime_summary = _runtime_summary(summary)
    totals = _totals(runtime_summary)
    executed_count = _non_negative_number(totals.get("executed_count"))
    dropped_count = _non_negative_number(totals.get("dropped_count"))
    deadline_missed_count = _non_negative_number(totals.get("deadline_missed_count"))
    fallback_count = _non_negative_number(totals.get("fallback_count"))
    policy_decision_count = _non_negative_number(totals.get("policy_decision_count"))
    overload_event_count = _non_negative_number(totals.get("overload_event_count"))

    policy_decision_log = _list(summary.get("policy_decision_log"))
    if not policy_decision_log:
        policy_decision_log = _list(summary.get("policy_decisions"))
    queue_backlog_decisions = [
        item
        for item in policy_decision_log
        if "backlog" in str(item.get("reason", "")).lower()
        or "backlog" in str(item.get("decision", "")).lower()
    ]

    total_task_events = executed_count + dropped_count
    return {
        "executed_count": executed_count,
        "dropped_count": dropped_count,
        "deadline_missed_count": deadline_missed_count,
        "fallback_count": fallback_count,
        "policy_decision_count": policy_decision_count,
        "overload_event_count": overload_event_count,
        "total_task_events": total_task_events,
        "deadline_miss_rate": _ratio(deadline_missed_count, executed_count),
        "drop_rate": _ratio(dropped_count, total_task_events),
        "fallback_rate": _ratio(fallback_count, total_task_events),
        "policy_decision_log_count": len(policy_decision_log),
        "queue_backlog_policy_decision_count": len(queue_backlog_decisions),
        "affected_agents": sorted(_affected_agents(summary)),
    }


def _deadline_miss_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    rate = metrics["deadline_miss_rate"]
    severity = _rate_severity(
        value=rate,
        review=thresholds["deadline_miss_rate_review"],
        blocked=thresholds["deadline_miss_rate_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="repeated_deadline_miss",
        metric_name="deadline_miss_rate",
        observed_value=rate,
        baseline_value=None,
        threshold=thresholds["deadline_miss_rate_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Repeated deadline misses indicate that an agent workload may not "
            "meet its latency budget under constrained edge-device conditions."
        ),
        suspected_causes=[
            "runtime_latency_spike",
            "insufficient_scheduling_budget",
            "device_resource_contention",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review agent latency budgets, scheduling priority, and worker runtime "
            "latency before deployment."
            if status != "passed"
            else "Deadline miss rate is within the configured threshold."
        ),
        raw_context={"totals": totals, "metrics": metrics},
    )


def _drop_rate_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    rate = metrics["drop_rate"]
    severity = _rate_severity(
        value=rate,
        review=thresholds["drop_rate_review"],
        blocked=thresholds["drop_rate_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="excessive_drop_rate",
        metric_name="drop_rate",
        observed_value=rate,
        baseline_value=None,
        threshold=thresholds["drop_rate_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "High drop rate can make camera or command workloads stale even if "
            "selected high-priority tasks are protected."
        ),
        suspected_causes=[
            "queue_backlog",
            "overload_load_shedding",
            "producer_rate_exceeds_runtime_capacity",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Tune target FPS, queue size, drop policy, or fallback policy for the "
            "affected agents."
            if status != "passed"
            else "Drop rate is within the configured threshold."
        ),
        raw_context={"totals": totals, "metrics": metrics},
    )


def _fallback_rate_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    rate = metrics["fallback_rate"]
    severity = _rate_severity(
        value=rate,
        review=thresholds["fallback_rate_review"],
        blocked=thresholds["fallback_rate_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="fallback_overuse",
        metric_name="fallback_rate",
        observed_value=rate,
        baseline_value=None,
        threshold=thresholds["fallback_rate_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Fallback is useful as a safety mechanism, but frequent fallback means "
            "the nominal runtime path may not be stable enough for deployment."
        ),
        suspected_causes=[
            "resource_degradation",
            "overload_policy_triggered",
            "runtime_capacity_shortfall",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Investigate why fallback is repeatedly used and verify that user-facing "
            "behavior remains acceptable."
            if status != "passed"
            else "Fallback usage is within the configured threshold."
        ),
        raw_context={"totals": totals, "metrics": metrics},
    )


def _queue_backlog_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    count = metrics["queue_backlog_policy_decision_count"]
    threshold = thresholds["queue_backlog_policy_decision_count_review"]
    severity = "medium" if count >= threshold else "low"
    status = "warning" if severity == "medium" else "passed"
    return build_evidence_item(
        evidence_type="queue_backlog_risk",
        metric_name="queue_backlog_policy_decision_count",
        observed_value=count,
        baseline_value=None,
        threshold=threshold,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Backlog-triggered policy decisions show that Orchestrator had to "
            "intervene to protect higher-priority work."
        ),
        suspected_causes=["queue_backlog", "multi_agent_resource_contention"]
        if status != "passed"
        else [],
        recommendation=(
            "Inspect policy_decision_log and verify that protected agents match the "
            "intended priority model."
            if status != "passed"
            else "No backlog-triggered policy decisions were observed."
        ),
        raw_context={"totals": totals, "metrics": metrics},
    )


def _runtime_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("agent_runtime_summary")
    return value if isinstance(value, dict) else {}


def _totals(runtime_summary: dict[str, Any]) -> dict[str, Any]:
    value = runtime_summary.get("totals")
    return value if isinstance(value, dict) else {}


def _non_negative_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return 0.0


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _rate_severity(*, value: float, review: float, blocked: float) -> str:
    if value >= blocked:
        return "high"
    if value >= review:
        return "medium"
    return "low"


def _status_for_runtime_metric(severity: str) -> str:
    if severity in {"high", "critical", "medium"}:
        return "failed"
    return "passed"


def _confidence_from_evidence(evidence: list[dict[str, Any]]) -> float:
    failed_count = sum(1 for item in evidence if item.get("status") == "failed")
    warning_count = sum(1 for item in evidence if item.get("status") == "warning")
    if failed_count:
        return 0.88
    if warning_count:
        return 0.74
    return 0.93


def _primary_reason(evidence: list[dict[str, Any]]) -> str:
    failed = [item for item in evidence if item.get("status") == "failed"]
    if not failed:
        warnings = [item for item in evidence if item.get("status") == "warning"]
        if warnings:
            return "Runtime scheduling evidence requires review."
        return "Runtime scheduling evidence is within configured thresholds."
    first = max(failed, key=lambda item: _severity_rank(item.get("severity")))
    return (
        f"{first.get('metric_name', 'runtime_reliability_metric')} indicates "
        "runtime reliability risk under orchestrated multi-agent load."
    )


def _affected_agents(summary: dict[str, Any]) -> set[str]:
    agents: set[str] = set()
    for field in ("drop_events", "overload_events", "policy_decision_log", "policy_decisions"):
        for item in _list(summary.get(field)):
            for key in ("agent_id", "protected_agent_id"):
                agent_id = item.get(key)
                if isinstance(agent_id, str) and agent_id:
                    agents.add(agent_id)
    return agents


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _severity_rank(value: Any) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(str(value), 0)
