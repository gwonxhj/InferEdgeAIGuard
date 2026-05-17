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
    "max_total_queue_depth_review": 3,
    "max_total_queue_depth_blocked": 8,
    "profiled_workload_risk_count_review": 1,
    "profiled_workload_risk_count_blocked": 3,
    "thermal_pressure_temperature_c_review": 70.0,
    "thermal_pressure_temperature_c_blocked": 85.0,
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
        _sustained_overload_evidence(metrics, totals, policy),
    ]
    workload_evidence = _profiled_workload_evidence(metrics, totals, policy)
    if workload_evidence is not None:
        evidence.append(workload_evidence)
    thermal_evidence = _thermal_pressure_evidence(metrics, totals, policy)
    if thermal_evidence is not None:
        evidence.append(thermal_evidence)

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
    sustained_summary = _sustained_summary(summary)
    multi_workload_summary = _multi_workload_summary(summary)
    observed_signals = _observed_runtime_signals(multi_workload_summary)
    tegrastats_timeline = _tegrastats_timeline(summary)
    tegrastats_summary = _mapping(tegrastats_timeline.get("summary"))
    totals = _totals(runtime_summary)
    latency_timeline = _list(summary.get("latency_timeline"))
    queue_depth_timeline = _list(summary.get("queue_depth_timeline"))

    executed_count = max(
        _non_negative_number(totals.get("executed_count")),
        _non_negative_number(observed_signals.get("executed_count")),
    )
    dropped_count = max(
        _non_negative_number(totals.get("dropped_count")),
        _non_negative_number(observed_signals.get("dropped_count")),
    )
    timeline_deadline_missed_count = sum(
        1 for item in latency_timeline if bool(item.get("deadline_missed"))
    )
    deadline_missed_count = max(
        _non_negative_number(totals.get("deadline_missed_count")),
        _non_negative_number(observed_signals.get("deadline_missed_count")),
        float(timeline_deadline_missed_count),
    )
    fallback_count = max(
        _non_negative_number(totals.get("fallback_count")),
        _non_negative_number(observed_signals.get("fallback_count")),
    )
    policy_decision_count = max(
        _non_negative_number(totals.get("policy_decision_count")),
        _non_negative_number(observed_signals.get("policy_decision_count")),
    )
    overload_event_count = _non_negative_number(totals.get("overload_event_count"))
    if executed_count <= 0 and latency_timeline:
        executed_count = float(len(latency_timeline))

    policy_decision_log = _list(summary.get("policy_decision_log"))
    if not policy_decision_log:
        policy_decision_log = _list(summary.get("policy_decisions"))
    policy_decision_reasons = _policy_decision_reasons(policy_decision_log)
    if not policy_decision_reasons:
        policy_decision_reasons = _policy_decision_reasons_from_values(
            observed_signals.get("policy_decision_reasons")
        )
    queue_backlog_decisions = [
        item
        for item in policy_decision_log
        if "backlog" in str(item.get("reason", "")).lower()
        or "backlog" in str(item.get("decision_reason", "")).lower()
        or "backlog" in str(item.get("decision", "")).lower()
    ]
    max_total_queue_depth = max(
        _non_negative_number(sustained_summary.get("max_total_queue_depth")),
        _non_negative_number(observed_signals.get("max_total_queue_depth")),
        _max_total_queue_depth(queue_depth_timeline),
    )
    workload_profiles = _workload_profiles(multi_workload_summary)
    affected_workload_profiles = _affected_workload_profiles(workload_profiles)
    if affected_workload_profiles:
        overload_event_count = max(overload_event_count, float(len(affected_workload_profiles)))

    total_task_events = executed_count + dropped_count
    return {
        "scenario_mode": _scenario_mode(summary),
        "evidence_scope": multi_workload_summary.get("evidence_scope"),
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
        "policy_decision_reasons": policy_decision_reasons,
        "top_policy_decision_reason": _top_reason(policy_decision_reasons),
        "queue_backlog_policy_decision_count": len(queue_backlog_decisions),
        "queue_depth_sample_count": len(queue_depth_timeline),
        "latency_sample_count": len(latency_timeline),
        "max_total_queue_depth": max_total_queue_depth,
        "affected_agents": sorted(_affected_agents(summary)),
        "workload_profile_count": len(workload_profiles),
        "profiled_workload_risk_count": len(affected_workload_profiles),
        "workload_profiles": workload_profiles,
        "affected_workload_profiles": affected_workload_profiles,
        "tegrastats_sample_count": _non_negative_number(
            tegrastats_timeline.get("sample_count")
        ),
        "max_temperature_c": _optional_non_negative_number(
            tegrastats_summary.get("max_temperature_c")
        ),
        "max_gpu_percent": _optional_non_negative_number(
            tegrastats_summary.get("max_gpu_percent")
        ),
        "max_ram_used_mb": _optional_non_negative_number(
            tegrastats_summary.get("max_ram_used_mb")
        ),
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
    top_reason = metrics.get("top_policy_decision_reason") or "none"
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
            "Inspect policy_decision_log decision_reason values and verify that "
            "protected agents match the intended priority model."
            if status != "passed"
            else "No backlog-triggered policy decisions were observed."
        ),
        raw_context={
            "totals": totals,
            "metrics": metrics,
            "top_policy_decision_reason": top_reason,
            "policy_decision_reasons": metrics.get("policy_decision_reasons", {}),
        },
    )


def _sustained_overload_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    max_depth = metrics["max_total_queue_depth"]
    severity = _rate_severity(
        value=max_depth,
        review=thresholds["max_total_queue_depth_review"],
        blocked=thresholds["max_total_queue_depth_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="sustained_overload_risk",
        metric_name="max_total_queue_depth",
        observed_value=max_depth,
        baseline_value=None,
        threshold=thresholds["max_total_queue_depth_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Sustained queue depth growth shows that incoming workload pressure "
            "can exceed edge-device execution capacity even when individual tasks "
            "still complete."
        ),
        suspected_causes=[
            "sustained_multi_agent_overload",
            "producer_rate_exceeds_scheduler_capacity",
            "resource_degradation_or_contention",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Lower producer rate, tighten stale-frame drop policy, or move lower "
            "priority work behind a fallback path before deployment."
            if status != "passed"
            else "Queue depth stayed within the configured sustained-load threshold."
        ),
        raw_context={
            "totals": totals,
            "scenario_mode": metrics.get("scenario_mode"),
            "queue_depth_sample_count": metrics.get("queue_depth_sample_count"),
            "latency_sample_count": metrics.get("latency_sample_count"),
            "metrics": metrics,
        },
    )


def _profiled_workload_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    if metrics.get("workload_profile_count", 0) <= 0:
        return None
    risk_count = metrics["profiled_workload_risk_count"]
    severity = _rate_severity(
        value=risk_count,
        review=thresholds["profiled_workload_risk_count_review"],
        blocked=thresholds["profiled_workload_risk_count_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="profiled_workload_pressure",
        metric_name="profiled_workload_risk_count",
        observed_value=risk_count,
        baseline_value=None,
        threshold=thresholds["profiled_workload_risk_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Per-workload pressure shows which sustained demo profiles are "
            "missing deadlines, dropping work, using fallback, or building queue "
            "backlog under the same edge-device scenario."
        ),
        suspected_causes=[
            "workload_contention",
            "producer_rate_exceeds_profile_budget",
            "runtime_loop_capacity_shortfall",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Inspect affected_workload_profiles and tune frame rate, burst "
            "frequency, scheduling profile, or fallback policy before deployment."
            if status != "passed"
            else "No per-workload pressure signals were observed."
        ),
        raw_context={
            "totals": totals,
            "evidence_scope": metrics.get("evidence_scope"),
            "workload_profiles": metrics.get("workload_profiles", []),
            "affected_workload_profiles": metrics.get("affected_workload_profiles", []),
        },
    )


def _thermal_pressure_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    max_temperature = metrics.get("max_temperature_c")
    if max_temperature is None:
        return None
    severity = _rate_severity(
        value=max_temperature,
        review=thresholds["thermal_pressure_temperature_c_review"],
        blocked=thresholds["thermal_pressure_temperature_c_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="thermal_resource_pressure",
        metric_name="max_temperature_c",
        observed_value=max_temperature,
        baseline_value=None,
        threshold=thresholds["thermal_pressure_temperature_c_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "High tegrastats temperature or resource pressure can cause sustained "
            "latency degradation on Jetson-class edge devices."
        ),
        suspected_causes=[
            "thermal_pressure",
            "gpu_or_cpu_resource_contention",
            "sustained_high_load_runtime_degradation",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review power mode, cooling, frame rate, and workload placement before "
            "treating the sustained run as deployment-ready."
            if status != "passed"
            else "Tegrastats temperature stayed within the configured threshold."
        ),
        raw_context={
            "totals": totals,
            "tegrastats_sample_count": metrics.get("tegrastats_sample_count"),
            "max_gpu_percent": metrics.get("max_gpu_percent"),
            "max_ram_used_mb": metrics.get("max_ram_used_mb"),
        },
    )


def _runtime_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("agent_runtime_summary")
    return value if isinstance(value, dict) else {}


def _sustained_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("sustained_runtime_summary")
    return value if isinstance(value, dict) else {}


def _multi_workload_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("multi_workload_sustained_summary")
    return value if isinstance(value, dict) else {}


def _observed_runtime_signals(multi_workload_summary: dict[str, Any]) -> dict[str, Any]:
    value = multi_workload_summary.get("observed_runtime_signals")
    return value if isinstance(value, dict) else {}


def _tegrastats_timeline(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("tegrastats_timeline")
    return value if isinstance(value, dict) else {}


def _totals(runtime_summary: dict[str, Any]) -> dict[str, Any]:
    value = runtime_summary.get("totals")
    return value if isinstance(value, dict) else {}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _non_negative_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return 0.0


def _optional_non_negative_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return None


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


def _scenario_mode(summary: dict[str, Any]) -> str:
    run = summary.get("run")
    if isinstance(run, dict) and isinstance(run.get("scenario_mode"), str):
        return run["scenario_mode"]
    multi_workload_summary = _multi_workload_summary(summary)
    if isinstance(multi_workload_summary.get("scenario_mode"), str):
        return multi_workload_summary["scenario_mode"]
    sustained_summary = _sustained_summary(summary)
    if isinstance(sustained_summary.get("scenario_mode"), str):
        return sustained_summary["scenario_mode"]
    return "unknown"


def _policy_decision_reasons(policy_decision_log: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in policy_decision_log:
        reason = item.get("decision_reason") or item.get("reason") or item.get("decision")
        if not isinstance(reason, str) or not reason:
            reason = "unknown"
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def _policy_decision_reasons_from_values(value: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if isinstance(value, dict):
        for reason, count in value.items():
            if not isinstance(reason, str) or not reason:
                reason = "unknown"
            counts[reason] = counts.get(reason, 0) + int(_non_negative_number(count))
    elif isinstance(value, list):
        for item in value:
            reason = item if isinstance(item, str) and item else "unknown"
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def _top_reason(reasons: dict[str, int]) -> str | None:
    if not reasons:
        return None
    return max(reasons.items(), key=lambda item: (item[1], item[0]))[0]


def _max_total_queue_depth(queue_depth_timeline: list[dict[str, Any]]) -> float:
    max_depth = 0.0
    for item in queue_depth_timeline:
        max_depth = max(max_depth, _non_negative_number(item.get("total_queue_depth")))
        queue_depth = item.get("queue_depth")
        if isinstance(queue_depth, dict):
            max_depth = max(
                max_depth,
                sum(_non_negative_number(value) for value in queue_depth.values()),
            )
    return max_depth


def _workload_profiles(multi_workload_summary: dict[str, Any]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for item in _list(multi_workload_summary.get("workload_profiles")):
        profiles.append(
            {
                "agent_id": item.get("agent_id"),
                "agent_type": item.get("agent_type"),
                "workload_type": item.get("workload_type"),
                "runtime_loop": item.get("runtime_loop"),
                "ingress_profile": item.get("ingress_profile"),
                "expected_runtime_mode": item.get("expected_runtime_mode"),
                "preferred_device": item.get("preferred_device"),
                "executed": _non_negative_number(item.get("executed")),
                "dropped": _non_negative_number(item.get("dropped")),
                "deadline_missed": _non_negative_number(item.get("deadline_missed")),
                "fallback_used": _non_negative_number(item.get("fallback_used")),
                "mean_latency_ms": _optional_non_negative_number(
                    item.get("mean_latency_ms")
                ),
                "p95_latency_ms": _optional_non_negative_number(item.get("p95_latency_ms")),
                "max_queue_backlog": _non_negative_number(item.get("max_queue_backlog")),
            }
        )
    return profiles


def _affected_workload_profiles(
    workload_profiles: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    affected: list[dict[str, Any]] = []
    for profile in workload_profiles:
        reasons: list[str] = []
        if profile["dropped"] > 0:
            reasons.append("dropped_work")
        if profile["deadline_missed"] > 0:
            reasons.append("deadline_missed")
        if profile["fallback_used"] > 0:
            reasons.append("fallback_used")
        if profile["max_queue_backlog"] > 0:
            reasons.append("queue_backlog")
        if not reasons:
            continue
        affected.append({**profile, "risk_reasons": reasons})
    return affected


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _severity_rank(value: Any) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(str(value), 0)
