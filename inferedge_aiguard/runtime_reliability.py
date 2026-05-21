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
RUNTIME_RESULT_SCHEMA_VERSION = "inferedge-runtime-result-v1"
REMOTE_DISPATCH_SCHEMA_VERSION = "inferedge-remote-dispatch-result-v1"

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
    "runtime_latency_budget_overrun_review": 1,
    "runtime_deadline_missed_review": 1,
    "runtime_backend_unavailable_review": 1,
    "runtime_error_severity_review": 1,
    "remote_dispatch_failure_review": 1,
    "remote_execution_failure_review": 1,
    "worker_degraded_count_review": 1,
    "worker_degraded_count_blocked": 3,
    "worker_constrained_count_review": 1,
    "scheduler_delay_event_count_review": 1,
    "scheduler_delay_event_count_blocked": 3,
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
    runtime_operation_metrics = [
        compute_runtime_operation_metrics(runtime_result)
        for runtime_result in _runtime_results(summary)
    ]
    remote_dispatch_metrics = [
        compute_remote_dispatch_metrics(remote_dispatch_result)
        for remote_dispatch_result in _remote_dispatch_results(summary)
    ]

    evidence = [
        _deadline_miss_evidence(metrics, totals, policy),
        _drop_rate_evidence(metrics, totals, policy),
        _fallback_rate_evidence(metrics, totals, policy),
        _queue_backlog_evidence(metrics, totals, policy),
        _sustained_overload_evidence(metrics, totals, policy),
    ]
    worker_health_evidence = _worker_health_degradation_evidence(
        metrics, totals, policy
    )
    if worker_health_evidence is not None:
        evidence.append(worker_health_evidence)
    scheduler_delay_evidence = _scheduler_delay_pattern_evidence(
        metrics, totals, policy
    )
    if scheduler_delay_evidence is not None:
        evidence.append(scheduler_delay_evidence)
    for runtime_metrics in runtime_operation_metrics:
        evidence.extend(_runtime_operation_evidence(runtime_metrics, policy))
    for remote_metrics in remote_dispatch_metrics:
        evidence.extend(_remote_dispatch_evidence(remote_metrics, policy))
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
            "runtime_operation_results": runtime_operation_metrics,
            "remote_dispatch_results": remote_dispatch_metrics,
        },
    )


def analyze_runtime_result(
    runtime_result: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build guard_analysis from a Runtime result JSON object.

    This consumes additive Runtime health/error/event fields. It is intentionally
    separate from Lab's final deployment decision and only produces deterministic
    runtime operation warning evidence.
    """

    policy = {**DEFAULT_RUNTIME_RELIABILITY_THRESHOLDS, **(thresholds or {})}
    metrics = compute_runtime_operation_metrics(runtime_result)
    evidence = _runtime_operation_evidence(metrics, policy)

    return build_diagnosis_report(
        evidence=evidence,
        source={
            "runtime_result_schema_version": runtime_result.get("schema_version"),
            "runtime_operation_evidence": True,
            **(source or {}),
        },
        confidence=_confidence_from_evidence(evidence),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "schema_version": runtime_result.get("schema_version"),
            "model": runtime_result.get("model"),
            "engine": runtime_result.get("engine"),
            "device": runtime_result.get("device"),
            "runtime_operation": metrics,
        },
    )


def analyze_remote_dispatch_result(
    remote_dispatch_result: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build guard_analysis from an Orchestrator remote dispatch result.

    This consumes the additive ``inferedge-remote-dispatch-result-v1`` contract.
    AIGuard does not execute remote tasks; it only turns selected/rejected worker
    and explicit starter execution evidence into deterministic warnings.
    """

    policy = {**DEFAULT_RUNTIME_RELIABILITY_THRESHOLDS, **(thresholds or {})}
    metrics = compute_remote_dispatch_metrics(remote_dispatch_result)
    evidence = _remote_dispatch_evidence(metrics, policy)

    return build_diagnosis_report(
        evidence=evidence,
        source={
            "remote_dispatch_schema_version": remote_dispatch_result.get(
                "schema_version"
            ),
            "remote_operation_evidence": True,
            **(source or {}),
        },
        confidence=_confidence_from_evidence(evidence),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "schema_version": remote_dispatch_result.get("schema_version"),
            "remote_dispatch": metrics,
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
    worker_health_snapshot = _worker_health_snapshot(summary)
    runtime_event_summary = _runtime_event_summary(summary)
    runtime_event_timeline = _runtime_event_timeline(summary)
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
    policy_decision_reason_counts = _count_mapping(
        runtime_event_summary.get("policy_decision_reason_counts")
    )
    if policy_decision_reason_counts:
        policy_decision_reasons = policy_decision_reason_counts
    drop_reason_counts = _count_mapping(runtime_event_summary.get("drop_reason_counts"))
    runtime_event_reason_counts = _count_mapping(
        runtime_event_summary.get("reason_counts")
    )
    runtime_event_type_counts = _count_mapping(
        runtime_event_summary.get("event_type_counts")
    )
    queue_backlog_decisions = [
        item
        for item in policy_decision_log
        if "backlog" in str(item.get("reason", "")).lower()
        or "backlog" in str(item.get("decision_reason", "")).lower()
        or "backlog" in str(item.get("decision", "")).lower()
    ]
    queue_backlog_decision_count = len(queue_backlog_decisions)
    if queue_backlog_decision_count <= 0 and policy_decision_reasons:
        queue_backlog_decision_count = sum(
            count
            for reason, count in policy_decision_reasons.items()
            if "backlog" in reason.lower()
        )
    max_total_queue_depth = max(
        _non_negative_number(sustained_summary.get("max_total_queue_depth")),
        _non_negative_number(observed_signals.get("max_total_queue_depth")),
        _max_total_queue_depth(queue_depth_timeline),
    )
    workload_profiles = _workload_profiles(multi_workload_summary)
    affected_workload_profiles = _affected_workload_profiles(workload_profiles)
    if affected_workload_profiles:
        overload_event_count = max(overload_event_count, float(len(affected_workload_profiles)))
    worker_health_metrics = _worker_health_metrics(worker_health_snapshot)
    scheduler_delay_event_count = max(
        _non_negative_number(runtime_event_summary.get("scheduler_delay_event_count")),
        float(_scheduler_delay_event_count(runtime_event_timeline)),
    )

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
        "policy_decision_reason_counts": policy_decision_reason_counts,
        "drop_reason_counts": drop_reason_counts,
        "runtime_event_reason_counts": runtime_event_reason_counts,
        "runtime_event_type_counts": runtime_event_type_counts,
        "top_policy_decision_reason": _top_reason(policy_decision_reasons),
        "queue_backlog_policy_decision_count": queue_backlog_decision_count,
        "queue_depth_sample_count": len(queue_depth_timeline),
        "latency_sample_count": len(latency_timeline),
        "runtime_event_count": _non_negative_number(
            runtime_event_summary.get("event_count")
        )
        or float(len(runtime_event_timeline)),
        "fallback_decision_count": _non_negative_number(
            runtime_event_summary.get("fallback_decision_count")
        ),
        "scheduler_delay_event_count": scheduler_delay_event_count,
        "latest_runtime_event_index": _optional_non_negative_number(
            runtime_event_summary.get("latest_event_index")
        ),
        "max_total_queue_depth": max_total_queue_depth,
        "affected_agents": sorted(_affected_agents(summary)),
        "worker_health": worker_health_metrics,
        "workload_profile_count": len(workload_profiles),
        "profiled_workload_risk_count": len(affected_workload_profiles),
        "local_profile_adapter_count": _non_negative_number(
            observed_signals.get("local_profile_adapter_count")
        ),
        "local_profile_elapsed_ms": _non_negative_number(
            observed_signals.get("local_profile_elapsed_ms")
        ),
        "local_profile_kinds": _string_list(
            observed_signals.get("local_profile_kinds")
        ),
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


def compute_remote_dispatch_metrics(remote_dispatch_result: dict[str, Any]) -> dict[str, Any]:
    """Compute deterministic reliability metrics from a remote dispatch result."""

    remote_execution = _mapping(remote_dispatch_result.get("remote_execution"))
    remote_plan = _mapping(remote_dispatch_result.get("remote_execution_plan"))
    remote_result = _mapping(remote_dispatch_result.get("remote_execution_result"))
    retry_plan = _mapping(remote_dispatch_result.get("retry_fallback_plan"))
    fallback_result = _mapping(remote_dispatch_result.get("fallback_execution_result"))
    fallback_attempts = _list(fallback_result.get("attempts"))
    runtime_events = _list(remote_dispatch_result.get("runtime_events"))
    dispatch_status = _first_string(remote_dispatch_result.get("dispatch_status")) or "unknown"
    execution_status = _first_string(remote_result.get("status")) or "unknown"
    execution_requested = _bool_value(remote_execution.get("execution_requested")) or _bool_value(
        remote_result.get("execution_requested")
    )
    execution_performed = _bool_value(remote_result.get("execution_performed"))
    error_category = _first_string(remote_result.get("error_category"))
    selected_worker_id = _first_string(remote_dispatch_result.get("selected_worker_id"))
    transport = _first_string(remote_result.get("transport"), remote_plan.get("transport"))
    http_status = _optional_non_negative_number(remote_result.get("http_status"))
    exit_code = _optional_non_negative_number(remote_result.get("exit_code"))
    fallback_final_status = _first_string(
        fallback_result.get("final_status"),
        retry_plan.get("fallback_final_status"),
    )
    fallback_execution_performed = _bool_value(
        retry_plan.get("fallback_execution_performed")
    ) or any(_bool_value(attempt.get("execution_performed")) for attempt in fallback_attempts)
    fallback_attempted_worker_ids = _string_list(
        fallback_result.get("attempted_worker_ids")
    ) or _string_list(retry_plan.get("fallback_attempted_worker_ids"))
    return {
        "schema_version": remote_dispatch_result.get("schema_version"),
        "dispatch_status": dispatch_status,
        "dispatch_failed": dispatch_status != "accepted",
        "selected_worker_id": selected_worker_id,
        "decision_reason": remote_dispatch_result.get("decision_reason"),
        "transport": transport,
        "execution_requested": execution_requested,
        "execution_performed": execution_performed,
        "execution_status": execution_status,
        "execution_failed": execution_requested and execution_status == "failed",
        "execution_skipped": execution_status == "skipped",
        "network_execution_performed": _bool_value(
            remote_plan.get("network_execution_performed")
        ),
        "error_category": error_category,
        "error_message": remote_result.get("error_message"),
        "http_status": http_status,
        "exit_code": exit_code,
        "fallback_worker_ids": retry_plan.get("fallback_worker_ids", []),
        "fallback_execution_performed": fallback_execution_performed,
        "fallback_attempted_worker_ids": fallback_attempted_worker_ids,
        "fallback_attempt_count": len(fallback_attempts),
        "fallback_final_status": fallback_final_status,
        "fallback_primary_worker_id": _first_string(
            fallback_result.get("primary_worker_id")
        ),
        "fallback_reason": _first_string(fallback_result.get("fallback_reason")),
        "fallback_recovered": (
            fallback_execution_performed and fallback_final_status == "succeeded"
        ),
        "fallback_failed": (
            fallback_execution_performed and fallback_final_status == "failed"
        ),
        "runtime_event_count": len(runtime_events),
        "runtime_events": runtime_events,
        "production_remote_execution": _bool_value(
            remote_execution.get("production_remote_execution")
        )
        or _bool_value(remote_result.get("production_remote_execution")),
    }


def compute_runtime_operation_metrics(runtime_result: dict[str, Any]) -> dict[str, Any]:
    """Compute deterministic operation metrics from a Runtime result JSON object."""

    health = _runtime_health_snapshot(runtime_result)
    error = _runtime_error_classification(runtime_result)
    events = _runtime_events(runtime_result)
    latency_budget_ms = _first_number(
        health.get("latency_budget_ms"),
        runtime_result.get("latency_budget_ms"),
        *[event.get("latency_budget_ms") for event in events],
    )
    observed_mean_ms = _first_number(
        error.get("observed_mean_ms"),
        runtime_result.get("mean_ms"),
        health.get("observed_mean_ms"),
    )
    latency_budget_exceeded = (
        _bool_value(health.get("latency_budget_exceeded"))
        or any(_bool_value(event.get("latency_budget_exceeded")) for event in events)
    )
    deadline_missed = (
        _bool_value(health.get("deadline_missed"))
        or any(_bool_value(event.get("deadline_missed")) for event in events)
    )
    retry_hint = _first_string(
        error.get("retry_hint"),
        *[event.get("retry_hint") for event in events],
    )
    error_severity = _first_string(
        error.get("severity"),
        error.get("runtime_error_severity"),
        *[event.get("severity") for event in events],
    )
    engine_available = _optional_bool(health.get("engine_available"))
    thermal_memory_evidence_available = _optional_bool(
        health.get("thermal_memory_evidence_available")
    )
    tegrastats_sample_count = max(
        _non_negative_number(health.get("tegrastats_sample_count")),
        *[
            _non_negative_number(event.get("tegrastats_sample_count"))
            for event in events
        ],
        0.0,
    )
    return {
        "schema_version": runtime_result.get("schema_version"),
        "model": runtime_result.get("model"),
        "engine": runtime_result.get("engine"),
        "device": runtime_result.get("device"),
        "execution_status": _first_string(
            runtime_result.get("execution_status"),
            health.get("execution_status"),
            error.get("execution_status"),
        ),
        "engine_available": engine_available,
        "engine_status_message": health.get("engine_status_message"),
        "latency_budget_ms": latency_budget_ms,
        "observed_mean_ms": observed_mean_ms,
        "latency_budget_exceeded": latency_budget_exceeded,
        "deadline_missed": deadline_missed,
        "runtime_error_category": _first_string(
            error.get("category"),
            error.get("error_category"),
            error.get("classification"),
        ),
        "runtime_error_severity": error_severity,
        "retry_hint": retry_hint,
        "timeout_budget_ms": _first_number(
            error.get("timeout_budget_ms"),
            error.get("latency_budget_ms"),
            latency_budget_ms,
        ),
        "tegrastats_status": health.get("tegrastats_status"),
        "tegrastats_sample_count": tegrastats_sample_count,
        "thermal_memory_evidence_available": thermal_memory_evidence_available,
        "runtime_event_count": len(events),
        "runtime_events": events,
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


def _worker_health_degradation_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    worker_health = _mapping(metrics.get("worker_health"))
    if not worker_health.get("worker_count"):
        return None
    degraded_count = worker_health.get("degraded_worker_count", 0.0)
    constrained_count = worker_health.get("constrained_worker_count", 0.0)
    observed = degraded_count + constrained_count
    if observed < thresholds["worker_degraded_count_review"]:
        return None
    severity = _rate_severity(
        value=observed,
        review=thresholds["worker_degraded_count_review"],
        blocked=thresholds["worker_degraded_count_blocked"],
    )
    if constrained_count >= thresholds["worker_constrained_count_review"]:
        severity = "high"
    status = "failed" if severity == "high" else "warning"
    return build_evidence_item(
        evidence_type="worker_health_degradation",
        metric_name="degraded_or_constrained_worker_count",
        observed_value=observed,
        baseline_value=0,
        threshold=thresholds["worker_degraded_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Worker health degradation explains which runtime loops were marked "
            "degraded or constrained and preserves the scheduler-observed reasons "
            "without making AIGuard the deployment decision owner."
        ),
        suspected_causes=[
            reason
            for reason in worker_health.get("health_reason_counts", {})
            if reason != "healthy_without_runtime_risk"
        ],
        recommendation=(
            "Inspect worker_health_snapshot health_reasons, per-worker drop and "
            "fallback rates, and queue pressure before treating the operation path "
            "as stable."
        ),
        raw_context={
            "totals": totals,
            "worker_health": worker_health,
        },
    )


def _scheduler_delay_pattern_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    count = metrics.get("scheduler_delay_event_count", 0.0)
    if count < thresholds["scheduler_delay_event_count_review"]:
        return None
    severity = _rate_severity(
        value=count,
        review=thresholds["scheduler_delay_event_count_review"],
        blocked=thresholds["scheduler_delay_event_count_blocked"],
    )
    status = _status_for_runtime_metric(severity)
    return build_evidence_item(
        evidence_type="scheduler_delay_pattern",
        metric_name="scheduler_delay_event_count",
        observed_value=count,
        baseline_value=0,
        threshold=thresholds["scheduler_delay_event_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Scheduler delay events show that tasks waited across scheduling "
            "cycles before execution, which can make edge workloads stale even "
            "when final execution latency stays inside budget."
        ),
        suspected_causes=[
            "scheduler_queue_wait",
            "priority_contention",
            "producer_rate_exceeds_scheduler_capacity",
        ],
        recommendation=(
            "Inspect runtime_event_timeline scheduler_delay_cycles, queue_wait_ms, "
            "and policy decision reasons before relying on this scheduling profile."
        ),
        raw_context={
            "totals": totals,
            "scheduler_delay_event_count": count,
            "policy_decision_reason_counts": metrics.get(
                "policy_decision_reason_counts", {}
            ),
            "drop_reason_counts": metrics.get("drop_reason_counts", {}),
            "runtime_event_reason_counts": metrics.get(
                "runtime_event_reason_counts", {}
            ),
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
            "local_profile_adapter_count": metrics.get("local_profile_adapter_count"),
            "local_profile_elapsed_ms": metrics.get("local_profile_elapsed_ms"),
            "local_profile_kinds": metrics.get("local_profile_kinds", []),
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


def _runtime_operation_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []

    if metrics.get("engine_available") is False:
        evidence.append(_runtime_backend_unavailable_evidence(metrics, thresholds))

    if metrics.get("latency_budget_exceeded") or metrics.get("deadline_missed"):
        evidence.append(_runtime_latency_budget_evidence(metrics, thresholds))

    if metrics.get("runtime_error_category") or metrics.get("retry_hint"):
        evidence.append(_runtime_error_classification_evidence(metrics, thresholds))

    if (
        metrics.get("device") == "jetson"
        and metrics.get("thermal_memory_evidence_available") is False
    ):
        evidence.append(_runtime_thermal_evidence_gap(metrics))

    if not evidence:
        evidence.append(_runtime_operation_pass_evidence(metrics))
    return evidence


def _remote_dispatch_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if metrics.get("dispatch_failed"):
        evidence.append(_remote_dispatch_failure_evidence(metrics, thresholds))

    if metrics.get("execution_requested") and metrics.get("execution_failed"):
        evidence.append(_remote_execution_failure_evidence(metrics, thresholds))
        if metrics.get("fallback_recovered"):
            evidence.append(_remote_execution_recovered_evidence(metrics))
        elif metrics.get("fallback_failed"):
            evidence.append(_remote_fallback_execution_failed_evidence(metrics, thresholds))
    elif metrics.get("execution_requested") and metrics.get("execution_status") == "succeeded":
        evidence.append(_remote_execution_success_evidence(metrics))
    elif not metrics.get("execution_requested"):
        evidence.append(_remote_execution_plan_only_evidence(metrics))
    elif metrics.get("execution_skipped"):
        evidence.append(_remote_execution_skipped_evidence(metrics))

    if not evidence:
        evidence.append(_remote_dispatch_pass_evidence(metrics))
    return evidence


def _remote_dispatch_failure_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_worker_selection_failed",
        metric_name="dispatch_status",
        observed_value=metrics.get("dispatch_status"),
        baseline_value="accepted",
        threshold=thresholds["remote_dispatch_failure_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="high",
        status="failed",
        why_it_matters=(
            "Remote edge operation cannot proceed if no compatible healthy worker "
            "is selected for the requested backend/device contract."
        ),
        suspected_causes=[
            "worker_offline",
            "worker_health_unavailable",
            "backend_device_capability_mismatch",
        ],
        recommendation=(
            "Check worker registry status, health state, backend/device capability, "
            "and request contract before retrying remote execution."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_execution_failure_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    error_category = metrics.get("error_category") or "remote_execution_failed"
    fallback_recovered = bool(metrics.get("fallback_recovered"))
    severity = (
        "medium"
        if fallback_recovered or str(error_category).startswith("missing_")
        else "high"
    )
    return build_evidence_item(
        evidence_type="remote_execution_failed",
        metric_name="remote_execution_status",
        observed_value=metrics.get("execution_status"),
        baseline_value="succeeded",
        threshold=thresholds["remote_execution_failure_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status="failed",
        why_it_matters=(
            "A selected remote worker that fails explicit starter execution is an "
            "operation reliability risk. If fallback recovered the task, this still "
            "indicates primary worker instability rather than a clean pass."
        ),
        suspected_causes=[
            cause
            for cause in [
                error_category,
                "remote_worker_endpoint_unreachable"
                if error_category in {"connection_error", "timeout"}
                else None,
                "remote_command_or_http_contract_error"
                if error_category in {"http_error", "remote_command_failed"}
                else None,
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            "Inspect remote_execution_result, endpoint metadata, timeout budget, "
            "worker logs, and fallback usage before treating this path as "
            "deployment-ready."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_execution_recovered_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_execution_recovered_by_fallback",
        metric_name="fallback_final_status",
        observed_value=metrics.get("fallback_final_status"),
        baseline_value="primary_execution_succeeded_without_fallback",
        threshold="succeeded",
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium",
        status="warning",
        why_it_matters=(
            "Fallback recovered explicit starter execution after the primary remote "
            "worker failed. This shows resilience evidence, but also means the "
            "primary worker path is not stable enough to treat as clean operation."
        ),
        suspected_causes=[
            cause
            for cause in [
                "primary_worker_unstable",
                metrics.get("fallback_reason"),
                metrics.get("error_category"),
                "remote_worker_endpoint_unreachable"
                if metrics.get("error_category") in {"connection_error", "timeout"}
                else None,
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            "Keep fallback enabled, inspect the primary worker, and validate this "
            "path with real device telemetry before relying on it for deployment."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_fallback_execution_failed_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_fallback_execution_failed",
        metric_name="fallback_final_status",
        observed_value=metrics.get("fallback_final_status"),
        baseline_value="succeeded",
        threshold=thresholds["remote_execution_failure_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="high",
        status="failed",
        why_it_matters=(
            "Fallback execution was attempted but did not recover the remote task. "
            "This means both the selected primary path and resilience path require "
            "review before remote edge operation is trusted."
        ),
        suspected_causes=[
            cause
            for cause in [
                "fallback_worker_unavailable",
                metrics.get("fallback_reason"),
                metrics.get("error_category"),
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            "Inspect fallback worker health, endpoint contracts, timeout budget, "
            "and retry policy before running remote dispatch in a reliability demo."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_execution_success_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_execution_starter_success",
        metric_name="remote_execution_status",
        observed_value=metrics.get("execution_status"),
        baseline_value="succeeded",
        threshold="succeeded",
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="passed",
        why_it_matters=(
            "Explicit remote execution starter succeeded and produced structured "
            "operation evidence for Lab to preserve."
        ),
        suspected_causes=[],
        recommendation=(
            "Use this as starter evidence only; auth, heartbeat, retries, and "
            "production worker lifecycle still require hardening."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_execution_plan_only_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_execution_plan_only",
        metric_name="execution_requested",
        observed_value=0,
        baseline_value=None,
        threshold=0,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="skipped",
        why_it_matters=(
            "Remote dispatch selected a worker, but explicit remote starter "
            "execution was not requested. This is valid plan-only evidence, not "
            "proof of live remote execution."
        ),
        suspected_causes=[],
        recommendation=(
            "Run Orchestrator remote-dispatch with --execute-plan when HTTP/SSH "
            "starter execution evidence is required."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_execution_skipped_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_execution_skipped",
        metric_name="remote_execution_status",
        observed_value=metrics.get("execution_status"),
        baseline_value="succeeded",
        threshold="succeeded",
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium",
        status="warning",
        why_it_matters=(
            "Explicit remote execution was requested but the selected transport did "
            "not perform starter execution."
        ),
        suspected_causes=[metrics.get("error_category") or "unsupported_transport"],
        recommendation=(
            "Use an http_request or ssh_command worker endpoint with required "
            "metadata, or keep this as selection-only evidence."
        ),
        raw_context={"remote_dispatch": metrics},
    )


def _remote_dispatch_pass_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="remote_dispatch_health",
        metric_name="remote_dispatch_signal_count",
        observed_value=0,
        baseline_value=None,
        threshold=0,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="passed",
        why_it_matters=(
            "Remote dispatch evidence was present without worker selection or "
            "starter execution risk signals."
        ),
        suspected_causes=[],
        recommendation="Remote dispatch evidence is within configured thresholds.",
        raw_context={"remote_dispatch": metrics},
    )


def _runtime_backend_unavailable_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="runtime_backend_unavailable",
        metric_name="engine_available",
        observed_value=0,
        baseline_value=None,
        threshold=thresholds["runtime_backend_unavailable_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="high",
        status="failed",
        why_it_matters=(
            "A Runtime result that cannot confirm backend availability cannot be "
            "treated as reliable device execution evidence."
        ),
        suspected_causes=[
            "backend_runtime_unavailable",
            "runtime_artifact_or_engine_load_failure",
            "device_environment_mismatch",
        ],
        recommendation=(
            "Check backend installation, runtime artifact path, engine load logs, "
            "and device target before using this result as deployment evidence."
        ),
        raw_context={"runtime_operation": metrics},
    )


def _runtime_latency_budget_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    deadline_missed = bool(metrics.get("deadline_missed"))
    latency_budget_exceeded = bool(metrics.get("latency_budget_exceeded"))
    severity = "medium"
    if deadline_missed and latency_budget_exceeded:
        severity = "high"
    observed = metrics.get("observed_mean_ms")
    threshold = metrics.get("latency_budget_ms")
    return build_evidence_item(
        evidence_type="runtime_latency_budget_overrun",
        metric_name="latency_budget_exceeded",
        observed_value=1 if latency_budget_exceeded else 0,
        baseline_value=None,
        threshold=threshold
        if threshold is not None
        else thresholds["runtime_latency_budget_overrun_review"],
        delta=(observed - threshold)
        if isinstance(observed, (int, float)) and isinstance(threshold, (int, float))
        else None,
        delta_pct=_ratio(observed - threshold, threshold)
        if isinstance(observed, (int, float))
        and isinstance(threshold, (int, float))
        and threshold > 0
        else None,
        increase_factor=None,
        severity=severity,
        status="failed",
        why_it_matters=(
            "Latency budget overrun or deadline miss means the runtime evidence "
            "does not satisfy the timing contract expected by the edge workload."
        ),
        suspected_causes=[
            "runtime_latency_spike",
            "insufficient_latency_budget",
            "device_resource_contention",
        ],
        recommendation=(
            "Review latency_budget_ms, deadline_missed runtime events, worker load, "
            "and fallback policy before deployment."
        ),
        raw_context={"runtime_operation": metrics},
    )


def _runtime_error_classification_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    raw_severity = str(metrics.get("runtime_error_severity") or "").lower()
    severity = "high" if raw_severity in {"high", "critical"} else "medium"
    return build_evidence_item(
        evidence_type="runtime_error_classification",
        metric_name="runtime_error_severity",
        observed_value=metrics.get("runtime_error_severity") or "unknown",
        baseline_value=None,
        threshold=thresholds["runtime_error_severity_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status="failed",
        why_it_matters=(
            "Runtime classified the execution path as needing operator attention. "
            "AIGuard preserves this deterministic warning instead of guessing a "
            "root cause."
        ),
        suspected_causes=[
            cause
            for cause in [
                metrics.get("runtime_error_category"),
                metrics.get("retry_hint"),
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            f"Follow Runtime retry hint: {metrics.get('retry_hint')}."
            if metrics.get("retry_hint")
            else "Inspect Runtime error classification and event log before deployment."
        ),
        raw_context={"runtime_operation": metrics},
    )


def _runtime_thermal_evidence_gap(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="runtime_thermal_memory_evidence_missing",
        metric_name="thermal_memory_evidence_available",
        observed_value=0,
        baseline_value=None,
        threshold=1,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium",
        status="warning",
        why_it_matters=(
            "Jetson runtime evidence without thermal or memory context is weaker "
            "for sustained deployment review."
        ),
        suspected_causes=["tegrastats_not_collected", "runtime_telemetry_gap"],
        recommendation=(
            "Collect tegrastats or runtime health telemetry for sustained Jetson "
            "validation when possible."
        ),
        raw_context={"runtime_operation": metrics},
    )


def _runtime_operation_pass_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="runtime_operation_health",
        metric_name="runtime_operation_signal_count",
        observed_value=0,
        baseline_value=None,
        threshold=0,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="passed",
        why_it_matters=(
            "Runtime operation health fields were present without latency, "
            "deadline, backend, or classified error risk signals."
        ),
        suspected_causes=[],
        recommendation="Runtime operation evidence is within configured thresholds.",
        raw_context={"runtime_operation": metrics},
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _tegrastats_timeline(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("tegrastats_timeline")
    return value if isinstance(value, dict) else {}


def _worker_health_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("worker_health_snapshot")
    return value if isinstance(value, dict) else {}


def _runtime_event_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("runtime_event_summary")
    return value if isinstance(value, dict) else {}


def _runtime_event_timeline(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return _list(summary.get("runtime_event_timeline"))


def _runtime_health_snapshot(runtime_result: dict[str, Any]) -> dict[str, Any]:
    value = runtime_result.get("runtime_health_snapshot")
    return value if isinstance(value, dict) else {}


def _runtime_error_classification(runtime_result: dict[str, Any]) -> dict[str, Any]:
    value = runtime_result.get("runtime_error_classification")
    return value if isinstance(value, dict) else {}


def _runtime_events(runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
    return _list(runtime_result.get("runtime_events"))


def _runtime_results(summary: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key in ("runtime_result", "runtime_result_context"):
        value = summary.get(key)
        if isinstance(value, dict):
            results.append(value)
    for key in ("runtime_results", "runtime_result_contexts"):
        value = summary.get(key)
        if isinstance(value, list):
            results.extend(item for item in value if isinstance(item, dict))
    return results


def _remote_dispatch_results(summary: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key in ("remote_dispatch_result", "remote_execution_result_context"):
        value = summary.get(key)
        if isinstance(value, dict):
            results.append(value)
    for key in ("remote_dispatch_results", "remote_execution_result_contexts"):
        value = summary.get(key)
        if isinstance(value, list):
            results.extend(item for item in value if isinstance(item, dict))
    return [
        item
        for item in results
        if item.get("schema_version") == REMOTE_DISPATCH_SCHEMA_VERSION
    ]


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


def _first_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _bool_value(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


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


def _count_mapping(value: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(value, dict):
        return counts
    for name, count in value.items():
        key = name if isinstance(name, str) and name else "unknown"
        counts[key] = counts.get(key, 0) + int(_non_negative_number(count))
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
                "implementation": item.get("implementation"),
                "profile_work_units": item.get("profile_work_units"),
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


def _worker_health_metrics(snapshot: dict[str, Any]) -> dict[str, Any]:
    workers_raw = snapshot.get("workers")
    workers = workers_raw if isinstance(workers_raw, dict) else {}
    worker_metrics: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    for worker_id, worker in workers.items():
        if not isinstance(worker, dict):
            continue
        health_reasons = _string_list(worker.get("health_reasons"))
        for reason in health_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        worker_metrics.append(
            {
                "worker_id": worker_id,
                "agent_id": worker.get("agent_id") or worker_id,
                "agent_type": worker.get("agent_type"),
                "health_state": worker.get("health_state"),
                "health_reasons": health_reasons,
                "drop_rate": _non_negative_number(worker.get("drop_rate")),
                "deadline_miss_rate": _non_negative_number(
                    worker.get("deadline_miss_rate")
                ),
                "fallback_rate": _non_negative_number(worker.get("fallback_rate")),
                "queue_pressure_ratio": _non_negative_number(
                    worker.get("queue_pressure_ratio")
                ),
                "runtime_loop": worker.get("runtime_loop"),
                "ingress_profile": worker.get("ingress_profile"),
            }
        )
    health_state_counts = _count_mapping(snapshot.get("health_state_counts"))
    degraded_workers = _string_list(snapshot.get("degraded_workers"))
    constrained_workers = _string_list(snapshot.get("constrained_workers"))
    return {
        "schema_version": snapshot.get("schema_version"),
        "worker_count": len(worker_metrics),
        "health_state_counts": health_state_counts,
        "degraded_workers": degraded_workers,
        "constrained_workers": constrained_workers,
        "degraded_worker_count": max(
            _non_negative_number(health_state_counts.get("degraded")),
            float(len(degraded_workers)),
        ),
        "constrained_worker_count": max(
            _non_negative_number(health_state_counts.get("constrained")),
            float(len(constrained_workers)),
        ),
        "health_reason_counts": reason_counts,
        "workers": worker_metrics,
    }


def _scheduler_delay_event_count(timeline: list[dict[str, Any]]) -> int:
    count = 0
    for event in timeline:
        delay = event.get("scheduler_delay_cycles")
        if isinstance(delay, int) and not isinstance(delay, bool) and delay > 0:
            count += 1
    return count


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _severity_rank(value: Any) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(str(value), 0)
