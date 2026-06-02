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
REMOTE_RUNTIME_EVENT_SUMMARY_SCHEMA_VERSION = (
    "inferedge-remote-runtime-event-summary-v1"
)
REMOTE_DISPATCH_STARTER_OPERATION_BOUNDARY = "remote dispatch starter evidence only"
REMOTE_RUNTIME_EVENT_SUMMARY_EVIDENCE_ROLE = (
    "remote_dispatch_runtime_event_compact_summary"
)
EDGEENV_HANDOFF_GUARD_ALIGNMENT_SCHEMA_VERSION = (
    "inferedge-aiguard-edgeenv-handoff-alignment-v1"
)
EDGEENV_ORCHESTRATOR_PRODUCER_LINEAGE_EVIDENCE_TYPE = (
    "edgeenv_orchestrator_producer_lineage"
)
EDGEENV_ORCHESTRATOR_TASK_EVENT_ROLLUP_EVIDENCE_TYPE = (
    "edgeenv_orchestrator_task_event_rollup"
)
EDGEENV_ORCHESTRATOR_LATENCY_BUDGET_PROTECTION_EVIDENCE_TYPE = (
    "edgeenv_orchestrator_latency_budget_protection"
)
EDGEENV_ORCHESTRATOR_LATENCY_BUDGET_PROTECTION_SCHEMA_VERSION = (
    "inferedge-orchestrator-latency-budget-protection-v1"
)
EDGEENV_ORCHESTRATOR_OPERATION_EVIDENCE_CANDIDATES = (
    "runtime_queue_overload",
    "runtime_thermal_instability",
    EDGEENV_ORCHESTRATOR_LATENCY_BUDGET_PROTECTION_EVIDENCE_TYPE,
)
RUN_CONFIG_MARKER_FIELDS = (
    "input_mode",
    "input_preprocess",
    "power_mode",
    "jetson_clocks",
    "warmup",
    "runs",
)

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
    "queue_pressure_reason_count_review": 1,
    "worker_operation_risk_count_review": 1,
    "worker_operation_risk_count_blocked": 3,
    "device_local_event_count_review": 1,
    "edgeenv_mean_delta_pct_review": 15.0,
    "edgeenv_p99_delta_pct_review": 25.0,
    "edgeenv_fps_drop_pct_review": -20.0,
    "edgeenv_memory_peak_delta_pct_warning": 30.0,
    "edgeenv_telemetry_gap_review": 1.0,
    "edgeenv_telemetry_queue_depth_review": 3.0,
    "edgeenv_telemetry_queue_depth_blocked": 8.0,
    "edgeenv_telemetry_temperature_c_review": 70.0,
    "edgeenv_telemetry_temperature_c_blocked": 85.0,
}


def validate_edgeenv_handoff_guard_evidence_alignment(
    edgeenv_handoff: dict[str, Any],
    guard_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Validate EdgeEnv handoff required evidence against AIGuard output.

    This is a cross-repo smoke helper. EdgeEnv declares the external AIGuard
    evidence types Lab should expect; AIGuard verifies its guard_analysis
    satisfies that minimum without taking over Lab's deployment decision.
    """

    lab_bundle_alignment = _mapping(edgeenv_handoff.get("lab_bundle_alignment"))
    raw_required_evidence_types = lab_bundle_alignment.get(
        "external_aiguard_required_evidence_types"
    )
    required_evidence_types = _unique_string_values(raw_required_evidence_types)
    invalid_required_evidence_types = _invalid_string_values(
        raw_required_evidence_types
    )
    raw_expected_report_markers = lab_bundle_alignment.get("expected_report_markers")
    expected_report_markers = _unique_string_values(raw_expected_report_markers)

    raw_evidence = guard_analysis.get("evidence")
    evidence_items = _list(raw_evidence)
    guard_evidence_types = _unique_string_values(
        [item.get("type") for item in evidence_items]
    )
    invalid_guard_evidence_items = [
        {
            "index": index,
            "reason": "missing_or_invalid_type",
        }
        for index, item in enumerate(raw_evidence if isinstance(raw_evidence, list) else [])
        if not isinstance(item, dict) or not _non_empty_string(item.get("type"))
    ]
    if raw_evidence is not None and not isinstance(raw_evidence, list):
        invalid_guard_evidence_items.append(
            {
                "index": None,
                "reason": "evidence_not_list",
            }
        )

    required_set = set(required_evidence_types)
    guard_set = set(guard_evidence_types)
    missing_required_evidence_types = sorted(required_set - guard_set)
    supplemental_guard_evidence_types = sorted(guard_set - required_set)

    boundary_flags = _mapping(lab_bundle_alignment.get("boundary_flags"))
    expected_boundary_flags = {
        "aiguard_guard_analysis_is_external": True,
        "edgeenv_does_not_generate_guard_analysis": True,
        "aiguard_is_final_decision_owner": False,
        "lab_is_final_decision_owner": True,
        "production_observability_platform": False,
    }
    boundary_errors = [
        {
            "field": field,
            "expected": expected,
            "observed": boundary_flags.get(field),
        }
        for field, expected in expected_boundary_flags.items()
        if boundary_flags.get(field) is not expected
    ]
    handoff_summary = _mapping(edgeenv_handoff.get("edgeenv_report_summary"))
    handoff_duration_traceability_run_ids = _unique_string_values(
        handoff_summary.get("duration_traceability_run_ids")
    )
    handoff_duration_sources = _unique_string_values(
        handoff_summary.get("duration_sources")
    )
    handoff_duration_scope_labels = _unique_string_values(
        handoff_summary.get("duration_scope_labels")
    )
    producer_lineage_evidence = _first_evidence_item(
        evidence_items,
        EDGEENV_ORCHESTRATOR_PRODUCER_LINEAGE_EVIDENCE_TYPE,
    )
    handoff_guard_alignment_run_ids = _unique_string_values(
        handoff_summary.get("producer_lineage_guard_alignment_run_ids")
    )
    guard_analysis_guard_alignment_run_ids = (
        _guard_analysis_producer_lineage_guard_alignment_run_ids(
            producer_lineage_evidence
        )
    )
    guard_alignment_summary_errors = _guard_alignment_summary_errors(
        handoff_summary,
        handoff_guard_alignment_run_ids=handoff_guard_alignment_run_ids,
        guard_analysis_guard_alignment_run_ids=guard_analysis_guard_alignment_run_ids,
        producer_lineage_evidence=producer_lineage_evidence,
    )

    errors = []
    if not isinstance(raw_required_evidence_types, list):
        errors.append("missing_external_aiguard_required_evidence_types")
    if invalid_required_evidence_types:
        errors.append("invalid_required_evidence_type")
    if not isinstance(raw_evidence, list):
        errors.append("guard_analysis_evidence_not_list")
    if invalid_guard_evidence_items:
        errors.append("invalid_guard_evidence_item_type")
    if missing_required_evidence_types:
        errors.append("missing_required_guard_evidence")
    if boundary_errors:
        errors.append("boundary_flag_mismatch")
    if guard_alignment_summary_errors:
        errors.append("producer_lineage_guard_alignment_summary_mismatch")

    status = "failed" if errors else "passed"
    recommendation = (
        "alignment_satisfied"
        if status == "passed"
        else "regenerate_guard_analysis_or_update_handoff_contract"
    )

    return {
        "schema_version": EDGEENV_HANDOFF_GUARD_ALIGNMENT_SCHEMA_VERSION,
        "status": status,
        "recommendation": recommendation,
        "decision_owner": "lab",
        "diagnosis_owner": "aiguard",
        "handoff_schema_version": edgeenv_handoff.get("schema_version"),
        "guard_analysis_schema_version": guard_analysis.get("schema_version"),
        "required_evidence_type_count": len(required_evidence_types),
        "guard_evidence_type_count": len(guard_evidence_types),
        "lab_expected_report_marker_count": len(expected_report_markers),
        "lab_expected_report_markers": expected_report_markers,
        "lab_report_marker_owner": "lab",
        "report_marker_context_role": "lab_report_contract_context",
        "aiguard_validates_expected_report_markers": False,
        "handoff_duration_traceability_present": bool(
            handoff_duration_traceability_run_ids
        ),
        "handoff_duration_traceability_run_ids": (
            handoff_duration_traceability_run_ids
        ),
        "handoff_duration_sources": handoff_duration_sources,
        "handoff_duration_scope_labels": handoff_duration_scope_labels,
        "required_evidence_types": required_evidence_types,
        "guard_analysis_evidence_types": guard_evidence_types,
        "missing_required_evidence_types": missing_required_evidence_types,
        "supplemental_guard_evidence_types": supplemental_guard_evidence_types,
        "invalid_required_evidence_types": invalid_required_evidence_types,
        "invalid_guard_evidence_items": invalid_guard_evidence_items,
        "boundary_flags": {
            field: boundary_flags.get(field)
            for field in expected_boundary_flags
        },
        "boundary_errors": boundary_errors,
        "handoff_producer_lineage_guard_alignment_run_ids": (
            handoff_guard_alignment_run_ids
        ),
        "guard_analysis_producer_lineage_guard_alignment_run_ids": (
            guard_analysis_guard_alignment_run_ids
        ),
        "guard_alignment_summary_errors": guard_alignment_summary_errors,
        "errors": errors,
    }


def _first_evidence_item(
    evidence_items: list[dict[str, Any]],
    evidence_type: str,
) -> dict[str, Any] | None:
    for item in evidence_items:
        if item.get("type") == evidence_type:
            return item
    return None


def _guard_analysis_producer_lineage_guard_alignment_run_ids(
    producer_lineage_evidence: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(producer_lineage_evidence, dict):
        return []
    raw_context = _mapping(producer_lineage_evidence.get("raw_context"))
    edgeenv_context = _mapping(raw_context.get("edgeenv_regression"))
    producer_lineage = _mapping(raw_context.get("producer_lineage"))
    run_ids: list[str] = []

    if (
        producer_lineage.get("candidate_expected") is True
        and producer_lineage.get("candidate_guard_alignment_valid") is True
    ):
        candidate_run_id = edgeenv_context.get("candidate_run_id")
        if _non_empty_string(candidate_run_id):
            run_ids.append(candidate_run_id)

    if (
        producer_lineage.get("missing_expected") is True
        and producer_lineage.get("missing_guard_alignment_valid") is True
    ):
        for run_id in _string_list(producer_lineage.get("missing_context_run_ids")):
            if run_id not in run_ids:
                run_ids.append(run_id)

    return run_ids


def _guard_alignment_summary_errors(
    handoff_summary: dict[str, Any],
    *,
    handoff_guard_alignment_run_ids: list[str],
    guard_analysis_guard_alignment_run_ids: list[str],
    producer_lineage_evidence: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not handoff_summary:
        return []

    errors: list[dict[str, Any]] = []
    observed_present = handoff_summary.get("producer_lineage_guard_alignment_present")
    expected_present = bool(guard_analysis_guard_alignment_run_ids)
    if observed_present is not expected_present:
        errors.append(
            {
                "field": "producer_lineage_guard_alignment_present",
                "expected": expected_present,
                "observed": observed_present,
            }
        )

    if handoff_guard_alignment_run_ids != guard_analysis_guard_alignment_run_ids:
        errors.append(
            {
                "field": "producer_lineage_guard_alignment_run_ids",
                "expected": guard_analysis_guard_alignment_run_ids,
                "observed": handoff_guard_alignment_run_ids,
            }
        )

    producer_lineage_status = (
        producer_lineage_evidence.get("status")
        if isinstance(producer_lineage_evidence, dict)
        else None
    )
    if expected_present and producer_lineage_status != "passed":
        errors.append(
            {
                "field": "edgeenv_orchestrator_producer_lineage.status",
                "expected": "passed",
                "observed": producer_lineage_status,
            }
        )

    return errors


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
    queue_pressure_evidence = _queue_pressure_context_evidence(
        metrics, totals, policy
    )
    if queue_pressure_evidence is not None:
        evidence.append(queue_pressure_evidence)
    worker_operation_evidence = _worker_operation_risk_summary_evidence(
        metrics, totals, policy
    )
    if worker_operation_evidence is not None:
        evidence.append(worker_operation_evidence)
    device_local_evidence = _device_local_operation_context_evidence(
        metrics, totals, policy
    )
    if device_local_evidence is not None:
        evidence.append(device_local_evidence)
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


def analyze_edgeenv_regression_report(
    regression_report: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build guard_analysis from an EdgeEnv runtime regression report.

    EdgeEnv owns comparability and regression calculation. AIGuard only turns
    already reported same-condition regression and telemetry coverage signals
    into deterministic diagnosis evidence for Lab to consume.
    """

    policy = {**DEFAULT_RUNTIME_RELIABILITY_THRESHOLDS, **(thresholds or {})}
    metrics = compute_edgeenv_regression_metrics(regression_report)
    evidence = _edgeenv_regression_evidence(metrics, policy)

    return build_diagnosis_report(
        evidence=evidence,
        source={
            "edgeenv_runtime_regression_report": True,
            "edgeenv_mode": metrics.get("mode"),
            "edgeenv_comparable": metrics.get("comparable"),
            **(source or {}),
        },
        confidence=_confidence_from_evidence(evidence),
        primary_reason=_primary_reason(evidence),
        thresholds=policy,
        candidate_summary={
            "edgeenv_regression": metrics,
            "runtime_telemetry_context": regression_report.get(
                "runtime_telemetry_context", {}
            ),
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
    queue_state_summary = _queue_state_summary(summary)
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
    queue_pressure_reason_counts = _count_mapping(
        runtime_event_summary.get("queue_pressure_reason_counts")
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
        "queue_pressure_reason_counts": queue_pressure_reason_counts,
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
        "latest_runtime_event_type": _first_string(
            runtime_event_summary.get("latest_event_type")
        ),
        "runtime_event_producer_sources": _string_list(
            runtime_event_summary.get("producer_sources")
        ),
        "producer_event_count": _non_negative_number(
            runtime_event_summary.get("producer_event_count")
        ),
        "device_local_event_count": _non_negative_number(
            runtime_event_summary.get("device_local_event_count")
        ),
        "queue_pressure_state": queue_state_summary.get("queue_pressure_state"),
        "queue_pressure_reason": queue_state_summary.get("queue_pressure_reason"),
        "max_pressure_task": queue_state_summary.get("max_pressure_task"),
        "device_local_task_count": _non_negative_number(
            queue_state_summary.get("device_local_task_count")
        ),
        "device_local_producer_sources": _string_list(
            queue_state_summary.get("device_local_producer_sources")
        ),
        "producer_sources_by_task": _producer_sources_by_task(queue_state_summary),
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


def compute_edgeenv_regression_metrics(regression_report: dict[str, Any]) -> dict[str, Any]:
    """Extract deterministic runtime regression metrics from EdgeEnv output."""

    evidence = _mapping(regression_report.get("evidence"))
    context = _mapping(regression_report.get("runtime_telemetry_context"))
    baseline_context = _mapping(context.get("baseline"))
    candidate_context = _mapping(context.get("candidate"))
    history = _mapping(context.get("history"))
    history_summary = _mapping(history.get("summary"))
    history_coverage = _mapping(history.get("telemetry_coverage"))
    history_seed_by_role = _history_telemetry_seed_by_role(context, history)
    history_coverage_by_role = _history_telemetry_coverage_by_role(
        context,
        history_coverage,
    )
    gaps = [
        item
        for item in _list(context.get("evidence_gaps"))
        if isinstance(item, dict)
    ]
    missing_coverage_count = 0.0
    for run_context in (baseline_context, candidate_context):
        if run_context and run_context.get("result_telemetry_present") is False:
            missing_coverage_count += 1.0
        if run_context and run_context.get("history_entry_present") is False:
            missing_coverage_count += 1.0
    baseline_coverage = history_coverage_by_role.get(
        "baseline",
        _telemetry_coverage_payload(baseline_context),
    )
    candidate_coverage = history_coverage_by_role.get(
        "candidate",
        _telemetry_coverage_payload(candidate_context),
    )
    baseline_history_seed = history_seed_by_role.get("baseline", {})
    candidate_history_seed = history_seed_by_role.get("candidate", {})
    baseline_history_seed_run_config = _mapping(
        baseline_history_seed.get("run_config")
    )
    candidate_history_seed_run_config = _mapping(
        candidate_history_seed.get("run_config")
    )
    seed_run_config_marker_labels = _history_seed_run_config_marker_labels(
        baseline_history_seed_run_config=baseline_history_seed_run_config,
        candidate_history_seed_run_config=candidate_history_seed_run_config,
    )
    baseline_coverage_missing_fields = _coverage_missing_fields(baseline_coverage)
    candidate_coverage_missing_fields = _coverage_missing_fields(candidate_coverage)
    history_missing_field_count = _optional_number(
        history_coverage.get("missing_field_run_count")
    )
    coverage_missing_field_count = (
        history_missing_field_count
        if history_missing_field_count is not None
        else float(
            len(baseline_coverage_missing_fields)
            + len(candidate_coverage_missing_fields)
        )
    )
    missing_coverage_count += coverage_missing_field_count
    baseline_sequence_id = _optional_number(
        baseline_context.get("execution_sequence_id")
    )
    candidate_sequence_id = _optional_number(
        candidate_context.get("execution_sequence_id")
    )
    baseline_orchestrator_context_present = isinstance(
        baseline_context.get("orchestrator_operation_context"),
        dict,
    )
    candidate_orchestrator_context = _mapping(
        candidate_context.get("orchestrator_operation_context")
    )
    candidate_orchestrator_candidate_context = _mapping(
        candidate_orchestrator_context.get("candidate_context")
    )
    candidate_orchestrator_operation = _mapping(
        candidate_orchestrator_candidate_context.get("operation")
    )
    candidate_orchestrator_producer = _mapping(
        candidate_orchestrator_candidate_context.get("producer")
    )
    candidate_edgeenv_mapping_hint = _mapping(
        candidate_orchestrator_context.get("edgeenv_mapping_hint")
    )
    candidate_downstream_guard_alignment = _mapping(
        candidate_orchestrator_context.get("downstream_guard_alignment")
    )
    candidate_remote_runtime_event_summary = _mapping(
        candidate_orchestrator_context.get("remote_runtime_event_summary")
    )
    candidate_operation_risk_summary = _mapping(
        candidate_orchestrator_context.get("operation_risk_summary")
    )
    candidate_latency_budget_protection = _mapping(
        candidate_orchestrator_operation.get("latency_budget_protection")
        or candidate_orchestrator_context.get("latency_budget_protection")
    )
    candidate_runtime_task_event_summary = _mapping(
        candidate_orchestrator_operation.get("runtime_task_event_summary")
        or candidate_orchestrator_context.get("runtime_task_event_summary")
    )
    candidate_orchestrator_context_present = isinstance(
        candidate_context.get("orchestrator_operation_context"),
        dict,
    )
    missing_orchestrator_contexts = _history_missing_orchestrator_contexts(history)
    first_missing_orchestrator_context = (
        missing_orchestrator_contexts[0] if missing_orchestrator_contexts else {}
    )
    first_missing_orchestrator_candidate_context = _mapping(
        first_missing_orchestrator_context.get("candidate_context")
    )
    first_missing_orchestrator_producer = _mapping(
        first_missing_orchestrator_candidate_context.get("producer")
    )
    first_missing_edgeenv_mapping_hint = _mapping(
        first_missing_orchestrator_context.get("edgeenv_mapping_hint")
    )
    first_missing_downstream_guard_alignment = _mapping(
        first_missing_orchestrator_context.get("downstream_guard_alignment")
    )
    first_missing_remote_runtime_event_summary = _mapping(
        first_missing_orchestrator_context.get("remote_runtime_event_summary")
    )
    first_missing_operation_risk_summary = _mapping(
        first_missing_orchestrator_context.get("operation_risk_summary")
    )
    baseline_max_temperature_c = _max_optional_number(
        _telemetry_number(
            baseline_context,
            "gpu_temperature",
            "resource.gpu_temperature",
            "orchestrator_operation_context.candidate_context.gpu_temperature",
            "orchestrator_operation_context.candidate_context.resource.gpu_temperature",
        ),
        _telemetry_number(
            baseline_context,
            "cpu_temperature",
            "resource.cpu_temperature",
            "orchestrator_operation_context.candidate_context.cpu_temperature",
            "orchestrator_operation_context.candidate_context.resource.cpu_temperature",
        ),
        _telemetry_number(
            baseline_context,
            "gpu_temperature_c",
            "resource.gpu_temperature_c",
            "orchestrator_operation_context.candidate_context.gpu_temperature_c",
            "orchestrator_operation_context.candidate_context.resource.gpu_temperature_c",
        ),
        _telemetry_number(
            baseline_context,
            "cpu_temperature_c",
            "resource.cpu_temperature_c",
            "orchestrator_operation_context.candidate_context.cpu_temperature_c",
            "orchestrator_operation_context.candidate_context.resource.cpu_temperature_c",
        ),
    )
    candidate_max_temperature_c = _max_optional_number(
        _telemetry_number(
            candidate_context,
            "gpu_temperature",
            "resource.gpu_temperature",
            "orchestrator_operation_context.candidate_context.gpu_temperature",
            "orchestrator_operation_context.candidate_context.resource.gpu_temperature",
        ),
        _telemetry_number(
            candidate_context,
            "cpu_temperature",
            "resource.cpu_temperature",
            "orchestrator_operation_context.candidate_context.cpu_temperature",
            "orchestrator_operation_context.candidate_context.resource.cpu_temperature",
        ),
        _telemetry_number(
            candidate_context,
            "gpu_temperature_c",
            "resource.gpu_temperature_c",
            "orchestrator_operation_context.candidate_context.gpu_temperature_c",
            "orchestrator_operation_context.candidate_context.resource.gpu_temperature_c",
        ),
        _telemetry_number(
            candidate_context,
            "cpu_temperature_c",
            "resource.cpu_temperature_c",
            "orchestrator_operation_context.candidate_context.cpu_temperature_c",
            "orchestrator_operation_context.candidate_context.resource.cpu_temperature_c",
        ),
    )
    return {
        "baseline_run_id": regression_report.get("baseline_run_id"),
        "candidate_run_id": regression_report.get("candidate_run_id"),
        "comparable": bool(regression_report.get("comparable")),
        "mode": regression_report.get("mode"),
        "regression_detected": bool(regression_report.get("regression_detected")),
        "regression_type": regression_report.get("regression_type"),
        "severity": regression_report.get("severity"),
        "recommendation": regression_report.get("recommendation"),
        "mean_delta_pct": _optional_number(evidence.get("mean_delta_pct")),
        "p95_delta_pct": _optional_number(evidence.get("p95_delta_pct")),
        "p99_delta_pct": _optional_number(evidence.get("p99_delta_pct")),
        "fps_delta_pct": _optional_number(evidence.get("fps_delta_pct")),
        "memory_peak_delta_pct": _optional_number(
            evidence.get("memory_peak_delta_pct")
        ),
        "triggered_thresholds": _list(evidence.get("triggered_thresholds")),
        "runtime_telemetry_context_present": bool(context),
        "runtime_telemetry_source": context.get("source"),
        "runtime_telemetry_history_schema_version": history.get("schema_version"),
        "history_orchestrator_feed_runs": _optional_number(
            history_summary.get("orchestrator_feed_runs")
        ),
        "history_registered_runs": _optional_number(
            history_summary.get("registered_runs")
        ),
        "history_telemetry_runs": _optional_number(
            history_summary.get("telemetry_runs")
        ),
        "history_telemetry_seed_runs": _optional_number(
            history_summary.get("history_seed_runs")
        ),
        "history_telemetry_seed_run_config_runs": _optional_number(
            history_summary.get("history_seed_run_config_runs")
        ),
        "baseline_runtime_telemetry_history_seed_schema_version": (
            baseline_history_seed.get("schema_version")
        ),
        "candidate_runtime_telemetry_history_seed_schema_version": (
            candidate_history_seed.get("schema_version")
        ),
        "baseline_runtime_telemetry_history_seed_registry_owner": (
            baseline_history_seed.get("registry_owner")
        ),
        "candidate_runtime_telemetry_history_seed_registry_owner": (
            candidate_history_seed.get("registry_owner")
        ),
        "baseline_runtime_telemetry_history_seed_decision_owner": (
            baseline_history_seed.get("decision_owner")
        ),
        "candidate_runtime_telemetry_history_seed_decision_owner": (
            candidate_history_seed.get("decision_owner")
        ),
        "candidate_runtime_telemetry_history_seed_production_monitoring": (
            _optional_bool(candidate_history_seed.get("production_monitoring"))
        ),
        "candidate_runtime_telemetry_history_seed_missing_telemetry_is_failure": (
            _optional_bool(candidate_history_seed.get("missing_telemetry_is_failure"))
        ),
        "candidate_runtime_telemetry_history_seed_point_count": (
            float(len(_list(candidate_history_seed.get("points"))))
            if candidate_history_seed
            else None
        ),
        "runtime_telemetry_history_seed_run_config_marker_fields": list(
            RUN_CONFIG_MARKER_FIELDS
        ),
        "runtime_telemetry_history_seed_run_config_marker_labels": (
            seed_run_config_marker_labels
        ),
        "baseline_runtime_telemetry_history_seed_run_config": (
            baseline_history_seed_run_config
        ),
        "baseline_runtime_telemetry_history_seed_run_config_markers": (
            _history_seed_run_config_markers(baseline_history_seed_run_config)
        ),
        "candidate_runtime_telemetry_history_seed_run_config": (
            candidate_history_seed_run_config
        ),
        "candidate_runtime_telemetry_history_seed_run_config_markers": (
            _history_seed_run_config_markers(candidate_history_seed_run_config)
        ),
        "candidate_runtime_telemetry_history_seed_run_config_present": bool(
            candidate_history_seed_run_config
        ),
        "history_missing_telemetry_runs": _optional_number(
            history_summary.get("missing_telemetry_runs")
        ),
        "history_missing_orchestrator_context_count": float(
            len(missing_orchestrator_contexts)
        ),
        "history_missing_orchestrator_context_run_ids": [
            item["run_id"]
            for item in missing_orchestrator_contexts
            if isinstance(item.get("run_id"), str)
        ],
        "history_missing_orchestrator_contexts": missing_orchestrator_contexts,
        "history_missing_orchestrator_source_repository": (
            first_missing_orchestrator_context.get("source_repository")
        ),
        "history_missing_orchestrator_artifact_role": (
            first_missing_orchestrator_context.get("artifact_role")
        ),
        "history_missing_orchestrator_producer_contract": (
            first_missing_orchestrator_context.get("producer_contract")
        ),
        "history_missing_orchestrator_candidate_context_telemetry_source": (
            first_missing_orchestrator_candidate_context.get("telemetry_source")
        ),
        "history_missing_orchestrator_candidate_context_producer": dict(
            first_missing_orchestrator_producer
        ),
        "history_missing_orchestrator_candidate_producer_sources": _string_list(
            first_missing_orchestrator_producer.get("producer_sources")
        ),
        "history_missing_orchestrator_candidate_device_local_producer_sources": (
            _string_list(
                first_missing_orchestrator_producer.get(
                    "device_local_producer_sources"
                )
            )
        ),
        "history_missing_orchestrator_candidate_producer_sources_by_task": (
            _mapping(first_missing_orchestrator_producer.get("producer_sources_by_task"))
        ),
        "history_missing_orchestrator_candidate_producer_stage_by_task": (
            _mapping(first_missing_orchestrator_producer.get("producer_stage_by_task"))
        ),
        "history_missing_orchestrator_candidate_producer_event_count": (
            _optional_number(
                first_missing_orchestrator_producer.get("producer_event_count")
            )
        ),
        "history_missing_orchestrator_candidate_device_local_event_count": (
            _optional_number(
                first_missing_orchestrator_producer.get("device_local_event_count")
            )
        ),
        "history_missing_orchestrator_candidate_device_local_task_count": (
            _optional_number(
                first_missing_orchestrator_producer.get("device_local_task_count")
            )
        ),
        "history_missing_orchestrator_candidate_operation_context_role": (
            first_missing_orchestrator_producer.get("operation_context_role")
        ),
        "history_missing_orchestrator_remote_runtime_event_summary": dict(
            first_missing_remote_runtime_event_summary
        ),
        "history_missing_orchestrator_remote_runtime_event_summary_present": bool(
            first_missing_remote_runtime_event_summary
        ),
        "history_missing_orchestrator_remote_runtime_event_summary_evidence_role": (
            first_missing_remote_runtime_event_summary.get("evidence_role")
        ),
        "history_missing_orchestrator_remote_runtime_event_summary_operation_boundary": (
            first_missing_remote_runtime_event_summary.get("operation_boundary")
        ),
        "history_missing_orchestrator_remote_runtime_event_summary_production_remote_execution": (
            _optional_bool(
                first_missing_remote_runtime_event_summary.get(
                    "production_remote_execution"
                )
            )
        ),
        "history_missing_orchestrator_operation_risk_summary": dict(
            first_missing_operation_risk_summary
        ),
        "history_missing_orchestrator_operation_risk_summary_present": bool(
            first_missing_operation_risk_summary
        ),
        "history_missing_orchestrator_operation_risk_summary_evidence_role": (
            first_missing_operation_risk_summary.get("evidence_role")
        ),
        "history_missing_orchestrator_operation_risk_summary_decision_owner": (
            first_missing_operation_risk_summary.get("decision_owner")
        ),
        "history_missing_orchestrator_operation_risk_summary_scheduler_owner": (
            first_missing_operation_risk_summary.get("scheduler_owner")
        ),
        "history_missing_orchestrator_operation_risk_summary_not_a_deployment_decision": (
            _optional_bool(
                first_missing_operation_risk_summary.get(
                    "not_a_deployment_decision"
                )
            )
        ),
        "history_missing_orchestrator_edgeenv_mapping_hint": dict(
            first_missing_edgeenv_mapping_hint
        ),
        "history_missing_orchestrator_mapping_hint_aiguard_evidence_candidates": (
            _string_list(
                first_missing_edgeenv_mapping_hint.get("aiguard_evidence_candidates")
            )
        ),
        "history_missing_orchestrator_downstream_guard_alignment": dict(
            first_missing_downstream_guard_alignment
        ),
        "history_missing_orchestrator_guard_alignment_declared_by": (
            first_missing_downstream_guard_alignment.get("declared_by")
        ),
        "history_missing_orchestrator_guard_alignment_producer_lineage_evidence_type": (
            first_missing_downstream_guard_alignment.get(
                "producer_lineage_evidence_type"
            )
        ),
        "history_missing_orchestrator_guard_alignment_operation_evidence_candidates": (
            _string_list(
                first_missing_downstream_guard_alignment.get(
                    "operation_evidence_candidates"
                )
            )
        ),
        "history_missing_orchestrator_guard_alignment_orchestrator_is_final_decision_owner": (
            _optional_bool(
                first_missing_downstream_guard_alignment.get(
                    "orchestrator_is_final_decision_owner"
                )
            )
        ),
        "history_missing_orchestrator_guard_alignment_lab_is_final_decision_owner": (
            _optional_bool(
                first_missing_downstream_guard_alignment.get(
                    "lab_is_final_decision_owner"
                )
            )
        ),
        "telemetry_coverage_source": (
            "history_telemetry_coverage"
            if history_coverage
            else "runtime_telemetry_context"
        ),
        "history_telemetry_coverage_missing_field_run_count": history_missing_field_count,
        "history_telemetry_coverage_missing_field_runs": _history_missing_field_runs(
            history_coverage,
        ),
        "history_telemetry_coverage_run_summaries_present": isinstance(
            history_coverage.get("run_summaries"),
            list,
        ),
        "baseline_telemetry_present": baseline_context.get(
            "result_telemetry_present"
        ),
        "candidate_telemetry_present": candidate_context.get(
            "result_telemetry_present"
        ),
        "baseline_history_entry_present": baseline_context.get(
            "history_entry_present"
        ),
        "candidate_history_entry_present": candidate_context.get(
            "history_entry_present"
        ),
        "baseline_telemetry_coverage_ratio": _optional_number(
            baseline_coverage.get("coverage_ratio")
        ),
        "candidate_telemetry_coverage_ratio": _optional_number(
            candidate_coverage.get("coverage_ratio")
        ),
        "baseline_telemetry_coverage_missing_fields": baseline_coverage_missing_fields,
        "candidate_telemetry_coverage_missing_fields": candidate_coverage_missing_fields,
        "telemetry_coverage_missing_field_count": coverage_missing_field_count,
        "baseline_missing_telemetry_is_failure": _optional_bool(
            baseline_coverage.get("missing_telemetry_is_failure")
        ),
        "candidate_missing_telemetry_is_failure": _optional_bool(
            candidate_coverage.get("missing_telemetry_is_failure")
        ),
        "baseline_execution_sequence_id": baseline_sequence_id,
        "candidate_execution_sequence_id": candidate_sequence_id,
        "execution_sequence_order_valid": _execution_sequence_order_valid(
            baseline_sequence_id,
            candidate_sequence_id,
        ),
        "baseline_orchestrator_context_present": baseline_orchestrator_context_present,
        "candidate_orchestrator_context_present": candidate_orchestrator_context_present,
        "orchestrator_source_repository": candidate_orchestrator_context.get(
            "source_repository"
        ),
        "orchestrator_artifact_role": candidate_orchestrator_context.get(
            "artifact_role"
        ),
        "orchestrator_producer_contract": candidate_orchestrator_context.get(
            "producer_contract"
        ),
        "orchestrator_candidate_context_telemetry_source": (
            candidate_orchestrator_candidate_context.get("telemetry_source")
        ),
        "orchestrator_candidate_context_producer": dict(
            candidate_orchestrator_producer
        ),
        "orchestrator_candidate_producer_sources": _string_list(
            candidate_orchestrator_producer.get("producer_sources")
        ),
        "orchestrator_candidate_device_local_producer_sources": _string_list(
            candidate_orchestrator_producer.get("device_local_producer_sources")
        ),
        "orchestrator_candidate_producer_sources_by_task": _mapping(
            candidate_orchestrator_producer.get("producer_sources_by_task")
        ),
        "orchestrator_candidate_producer_stage_by_task": _mapping(
            candidate_orchestrator_producer.get("producer_stage_by_task")
        ),
        "orchestrator_candidate_producer_event_count": _optional_number(
            candidate_orchestrator_producer.get("producer_event_count")
        ),
        "orchestrator_candidate_device_local_event_count": _optional_number(
            candidate_orchestrator_producer.get("device_local_event_count")
        ),
        "orchestrator_candidate_device_local_task_count": _optional_number(
            candidate_orchestrator_producer.get("device_local_task_count")
        ),
        "orchestrator_candidate_operation_context_role": (
            candidate_orchestrator_producer.get("operation_context_role")
        ),
        "orchestrator_remote_runtime_event_summary": dict(
            candidate_remote_runtime_event_summary
        ),
        "orchestrator_remote_runtime_event_summary_present": bool(
            candidate_remote_runtime_event_summary
        ),
        "orchestrator_remote_runtime_event_summary_evidence_role": (
            candidate_remote_runtime_event_summary.get("evidence_role")
        ),
        "orchestrator_remote_runtime_event_summary_operation_boundary": (
            candidate_remote_runtime_event_summary.get("operation_boundary")
        ),
        "orchestrator_remote_runtime_event_summary_production_remote_execution": (
            _optional_bool(
                candidate_remote_runtime_event_summary.get(
                    "production_remote_execution"
                )
            )
        ),
        "orchestrator_operation_risk_summary": dict(candidate_operation_risk_summary),
        "orchestrator_operation_risk_summary_present": bool(
            candidate_operation_risk_summary
        ),
        "orchestrator_operation_risk_summary_schema_version": (
            candidate_operation_risk_summary.get("schema_version")
        ),
        "orchestrator_operation_risk_summary_evidence_role": (
            candidate_operation_risk_summary.get("evidence_role")
        ),
        "orchestrator_operation_risk_summary_decision_owner": (
            candidate_operation_risk_summary.get("decision_owner")
        ),
        "orchestrator_operation_risk_summary_scheduler_owner": (
            candidate_operation_risk_summary.get("scheduler_owner")
        ),
        "orchestrator_operation_risk_summary_not_a_deployment_decision": (
            _optional_bool(
                candidate_operation_risk_summary.get("not_a_deployment_decision")
            )
        ),
        "orchestrator_operation_risk_summary_queue_pressure_reason": (
            candidate_operation_risk_summary.get("queue_pressure_reason")
        ),
        "orchestrator_operation_risk_summary_max_pressure_task": (
            candidate_operation_risk_summary.get("max_pressure_task")
        ),
        "orchestrator_operation_risk_summary_primary_health_reason": (
            candidate_operation_risk_summary.get("primary_health_reason")
        ),
        "orchestrator_operation_risk_summary_degraded_worker_ids": _string_list(
            candidate_operation_risk_summary.get("degraded_worker_ids")
        ),
        "orchestrator_operation_risk_summary_device_local_event_count": (
            _optional_number(
                candidate_operation_risk_summary.get("device_local_event_count")
            )
        ),
        "orchestrator_operation_risk_summary_producer_event_count": (
            _optional_number(
                candidate_operation_risk_summary.get("producer_event_count")
            )
        ),
        "orchestrator_latency_budget_protection": dict(
            candidate_latency_budget_protection
        ),
        "orchestrator_latency_budget_protection_present": bool(
            candidate_latency_budget_protection
        ),
        "orchestrator_latency_budget_protection_schema_version": (
            candidate_latency_budget_protection.get("schema_version")
        ),
        "orchestrator_latency_budget_protection_evidence_role": (
            candidate_latency_budget_protection.get("evidence_role")
        ),
        "orchestrator_latency_budget_protection_decision_owner": (
            candidate_latency_budget_protection.get("decision_owner")
        ),
        "orchestrator_latency_budget_protection_scheduler_owner": (
            candidate_latency_budget_protection.get("scheduler_owner")
        ),
        "orchestrator_latency_budget_protection_regression_owner": (
            candidate_latency_budget_protection.get("regression_owner")
        ),
        "orchestrator_latency_budget_protection_not_a_deployment_decision": (
            _optional_bool(
                candidate_latency_budget_protection.get(
                    "not_a_deployment_decision"
                )
            )
        ),
        "orchestrator_latency_budget_protection_protected_tasks": (
            _first_string_list(
                candidate_latency_budget_protection.get(
                    "protected_high_priority_tasks"
                ),
                candidate_latency_budget_protection.get(
                    "protected_high_priority_task_candidates"
                ),
                candidate_latency_budget_protection.get("protected_tasks"),
            )
        ),
        "orchestrator_latency_budget_protection_risk_tasks": (
            _first_string_list(
                candidate_latency_budget_protection.get(
                    "tasks_with_latency_budget_risk"
                ),
                candidate_latency_budget_protection.get("budget_risk_tasks"),
                candidate_latency_budget_protection.get("tasks_with_budget_risk"),
            )
        ),
        "orchestrator_latency_budget_protection_risk_reasons": (
            _first_string_list(
                candidate_latency_budget_protection.get("risk_reasons"),
                candidate_latency_budget_protection.get("latency_budget_risk_reasons"),
            )
        ),
        "orchestrator_latency_budget_protection_per_task_budget_context": (
            _mapping(
                candidate_latency_budget_protection.get("per_task_budget_context")
                or candidate_latency_budget_protection.get("task_budget_context")
                or candidate_latency_budget_protection.get("budget_context_by_task")
            )
        ),
        "orchestrator_runtime_task_event_summary": dict(
            candidate_runtime_task_event_summary
        ),
        "orchestrator_runtime_task_event_summary_present": bool(
            candidate_runtime_task_event_summary
        ),
        "orchestrator_tasks_with_deadline_miss": _string_list(
            candidate_orchestrator_operation.get("tasks_with_deadline_miss")
            or candidate_orchestrator_context.get("tasks_with_deadline_miss")
        ),
        "orchestrator_tasks_with_fallback": _string_list(
            candidate_orchestrator_operation.get("tasks_with_fallback")
            or candidate_orchestrator_context.get("tasks_with_fallback")
        ),
        "orchestrator_tasks_with_scheduler_delay": _string_list(
            candidate_orchestrator_operation.get("tasks_with_scheduler_delay")
            or candidate_orchestrator_context.get("tasks_with_scheduler_delay")
        ),
        "orchestrator_edgeenv_mapping_hint": dict(candidate_edgeenv_mapping_hint),
        "orchestrator_mapping_hint_copy_candidate_context_to": (
            candidate_edgeenv_mapping_hint.get("copy_candidate_context_to")
        ),
        "orchestrator_mapping_hint_operation_context_role": (
            candidate_edgeenv_mapping_hint.get("operation_context_role")
        ),
        "orchestrator_mapping_hint_coverage_summary_owner": (
            candidate_edgeenv_mapping_hint.get("coverage_summary_owner")
        ),
        "orchestrator_mapping_hint_coverage_summary_path": (
            candidate_edgeenv_mapping_hint.get("coverage_summary_path")
        ),
        "orchestrator_mapping_hint_candidate_context_required_fields": _string_list(
            candidate_edgeenv_mapping_hint.get("candidate_context_required_fields")
        ),
        "orchestrator_mapping_hint_aiguard_evidence_candidates": _string_list(
            candidate_edgeenv_mapping_hint.get("aiguard_evidence_candidates")
        ),
        "orchestrator_downstream_guard_alignment": dict(
            candidate_downstream_guard_alignment
        ),
        "orchestrator_guard_alignment_declared_by": (
            candidate_downstream_guard_alignment.get("declared_by")
        ),
        "orchestrator_guard_alignment_producer_lineage_evidence_type": (
            candidate_downstream_guard_alignment.get(
                "producer_lineage_evidence_type"
            )
        ),
        "orchestrator_guard_alignment_operation_evidence_candidates": (
            _string_list(
                candidate_downstream_guard_alignment.get(
                    "operation_evidence_candidates"
                )
            )
        ),
        "orchestrator_guard_alignment_orchestrator_is_final_decision_owner": (
            _optional_bool(
                candidate_downstream_guard_alignment.get(
                    "orchestrator_is_final_decision_owner"
                )
            )
        ),
        "orchestrator_guard_alignment_lab_is_final_decision_owner": (
            _optional_bool(
                candidate_downstream_guard_alignment.get(
                    "lab_is_final_decision_owner"
                )
            )
        ),
        "baseline_max_temperature_c": baseline_max_temperature_c,
        "candidate_max_temperature_c": candidate_max_temperature_c,
        "baseline_throttling_detected": _telemetry_bool(
            baseline_context,
            "throttling_detected",
            "resource.throttling_detected",
            "orchestrator_operation_context.candidate_context.throttling_detected",
            "orchestrator_operation_context.candidate_context.resource.throttling_detected",
        ),
        "candidate_throttling_detected": _telemetry_bool(
            candidate_context,
            "throttling_detected",
            "resource.throttling_detected",
            "orchestrator_operation_context.candidate_context.throttling_detected",
            "orchestrator_operation_context.candidate_context.resource.throttling_detected",
        ),
        "baseline_queue_depth": _telemetry_number(
            baseline_context,
            "queue_depth",
            "operation.queue_depth",
            "orchestrator_operation_context.candidate_context.queue_depth",
            "orchestrator_operation_context.candidate_context.operation.queue_depth",
        ),
        "candidate_queue_depth": _telemetry_number(
            candidate_context,
            "queue_depth",
            "operation.queue_depth",
            "orchestrator_operation_context.candidate_context.queue_depth",
            "orchestrator_operation_context.candidate_context.operation.queue_depth",
        ),
        "orchestrator_candidate_operation_max_total_queue_depth": _telemetry_number(
            candidate_context,
            "orchestrator_operation_context.candidate_context.operation."
            "max_total_queue_depth",
        ),
        "evidence_gap_count": float(len(gaps)) + missing_coverage_count,
        "evidence_gaps": gaps,
    }


def compute_remote_dispatch_metrics(remote_dispatch_result: dict[str, Any]) -> dict[str, Any]:
    """Compute deterministic reliability metrics from a remote dispatch result."""

    remote_execution = _mapping(remote_dispatch_result.get("remote_execution"))
    remote_plan = _mapping(remote_dispatch_result.get("remote_execution_plan"))
    remote_result = _mapping(remote_dispatch_result.get("remote_execution_result"))
    remote_operation_summary = _mapping(
        remote_dispatch_result.get("remote_operation_summary")
    )
    dispatch_summary = _mapping(remote_dispatch_result.get("dispatch_summary"))
    remote_runtime_event_summary = _mapping(
        remote_dispatch_result.get("remote_runtime_event_summary")
    )
    retry_plan = _mapping(remote_dispatch_result.get("retry_fallback_plan"))
    fallback_result = _mapping(remote_dispatch_result.get("fallback_execution_result"))
    fallback_attempts = _list(fallback_result.get("attempts"))
    runtime_events = _list(remote_dispatch_result.get("runtime_events"))
    dispatch_status = (
        _first_string(
            remote_dispatch_result.get("dispatch_status"),
            dispatch_summary.get("dispatch_status"),
            remote_operation_summary.get("dispatch_status"),
        )
        or "unknown"
    )
    execution_status = _first_string(remote_result.get("status")) or "unknown"
    execution_requested = _bool_value(remote_execution.get("execution_requested")) or _bool_value(
        remote_result.get("execution_requested")
    )
    execution_performed = _bool_value(remote_result.get("execution_performed"))
    error_category = _first_string(remote_result.get("error_category"))
    selected_worker_id = _first_string(
        remote_dispatch_result.get("selected_worker_id"),
        dispatch_summary.get("selected_worker_id"),
        remote_operation_summary.get("selected_worker_id"),
    )
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
    remote_runtime_event_summary_errors = _remote_runtime_event_summary_errors(
        summary=remote_runtime_event_summary,
        runtime_events=runtime_events,
        remote_operation_summary=remote_operation_summary,
        execution_status=execution_status,
        fallback_final_status=fallback_final_status,
    )
    return {
        "schema_version": remote_dispatch_result.get("schema_version"),
        "dispatch_status": dispatch_status,
        "dispatch_failed": dispatch_status != "accepted",
        "selected_worker_id": selected_worker_id,
        "decision_reason": _first_string(
            remote_dispatch_result.get("decision_reason"),
            dispatch_summary.get("decision_reason"),
            remote_operation_summary.get("decision_reason"),
        ),
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
        "remote_operation_summary": remote_operation_summary,
        "remote_runtime_event_summary": remote_runtime_event_summary,
        "operation_boundary": _first_string(
            remote_runtime_event_summary.get("operation_boundary"),
            remote_operation_summary.get("operation_boundary"),
        ),
        "remote_runtime_event_summary_present": bool(remote_runtime_event_summary),
        "remote_runtime_event_summary_schema_version": (
            remote_runtime_event_summary.get("schema_version")
        ),
        "remote_runtime_event_summary_event_count": _optional_non_negative_number(
            remote_runtime_event_summary.get("event_count")
        ),
        "remote_runtime_event_summary_runtime_event_count": (
            _optional_non_negative_number(
                remote_runtime_event_summary.get("runtime_event_count")
            )
        ),
        "remote_runtime_event_summary_event_type_counts": _count_mapping(
            remote_runtime_event_summary.get("event_type_counts")
        ),
        "remote_runtime_event_summary_status_counts": _count_mapping(
            remote_runtime_event_summary.get("status_counts")
        ),
        "remote_runtime_event_summary_error_category_counts": _count_mapping(
            remote_runtime_event_summary.get("error_category_counts")
        ),
        "remote_runtime_event_summary_fallback_event_count": (
            _optional_non_negative_number(
                remote_runtime_event_summary.get("fallback_event_count")
            )
        ),
        "remote_runtime_event_summary_final_status": _first_string(
            remote_runtime_event_summary.get("final_status")
        ),
        "remote_runtime_event_summary_fallback_recovered": _bool_value(
            remote_runtime_event_summary.get("fallback_recovered")
        ),
        "remote_runtime_event_summary_latest_event": _first_string(
            remote_runtime_event_summary.get("latest_event")
        ),
        "remote_runtime_event_summary_evidence_role": _first_string(
            remote_runtime_event_summary.get("evidence_role")
        ),
        "remote_runtime_event_summary_production_remote_execution": _bool_value(
            remote_runtime_event_summary.get("production_remote_execution")
        ),
        "remote_runtime_event_summary_operation_boundary": _first_string(
            remote_runtime_event_summary.get("operation_boundary")
        ),
        "remote_runtime_event_summary_consistent": (
            not remote_runtime_event_summary_errors
        ),
        "remote_runtime_event_summary_errors": remote_runtime_event_summary_errors,
        "production_remote_execution": _bool_value(
            remote_execution.get("production_remote_execution")
        )
        or _bool_value(remote_result.get("production_remote_execution")),
    }


def _remote_runtime_event_summary_errors(
    *,
    summary: dict[str, Any],
    runtime_events: list[dict[str, Any]],
    remote_operation_summary: dict[str, Any],
    execution_status: str,
    fallback_final_status: str | None,
) -> list[str]:
    if not summary:
        return []

    errors: list[str] = []
    if summary.get("schema_version") != REMOTE_RUNTIME_EVENT_SUMMARY_SCHEMA_VERSION:
        errors.append("remote_runtime_event_summary_schema_mismatch")

    event_count = _optional_non_negative_number(summary.get("event_count"))
    if (
        event_count is not None
        and runtime_events
        and int(event_count) != len(runtime_events)
    ):
        errors.append("remote_runtime_event_summary_event_count_mismatch")

    runtime_event_count = _optional_non_negative_number(
        summary.get("runtime_event_count")
    )
    if (
        runtime_event_count is not None
        and runtime_events
        and int(runtime_event_count) != len(runtime_events)
    ):
        errors.append("remote_runtime_event_summary_runtime_event_count_mismatch")
    if (
        event_count is not None
        and runtime_event_count is not None
        and int(event_count) != int(runtime_event_count)
    ):
        errors.append("remote_runtime_event_summary_count_alias_mismatch")

    expected_event_type_counts = _count_event_values(runtime_events, "event")
    observed_event_type_counts = _count_mapping(summary.get("event_type_counts"))
    if (
        observed_event_type_counts
        and runtime_events
        and observed_event_type_counts != expected_event_type_counts
    ):
        errors.append("remote_runtime_event_summary_event_type_counts_mismatch")

    expected_status_counts = _count_event_values(runtime_events, "status")
    observed_status_counts = _count_mapping(summary.get("status_counts"))
    if (
        observed_status_counts
        and runtime_events
        and observed_status_counts != expected_status_counts
    ):
        errors.append("remote_runtime_event_summary_status_counts_mismatch")

    expected_error_counts = _count_event_values(runtime_events, "error_category")
    observed_error_counts = _count_mapping(summary.get("error_category_counts"))
    if (
        observed_error_counts
        and runtime_events
        and observed_error_counts != expected_error_counts
    ):
        errors.append("remote_runtime_event_summary_error_category_counts_mismatch")

    expected_final_status = _first_string(
        remote_operation_summary.get("final_status"),
        fallback_final_status,
        execution_status,
    )
    summary_final_status = _first_string(summary.get("final_status"))
    if (
        summary_final_status
        and expected_final_status
        and summary_final_status != expected_final_status
    ):
        errors.append("remote_runtime_event_summary_final_status_mismatch")

    operation_boundary = _first_string(summary.get("operation_boundary"))
    if _bool_value(summary.get("production_remote_execution")) or (
        operation_boundary
        and operation_boundary != REMOTE_DISPATCH_STARTER_OPERATION_BOUNDARY
    ):
        errors.append("remote_runtime_event_summary_boundary_mismatch")

    evidence_role = _first_string(summary.get("evidence_role"))
    if (
        evidence_role
        and evidence_role != REMOTE_RUNTIME_EVENT_SUMMARY_EVIDENCE_ROLE
    ):
        errors.append("remote_runtime_event_summary_evidence_role_mismatch")

    operation_fallback_recovered = _bool_value(
        remote_operation_summary.get("fallback_recovered")
    )
    summary_fallback_recovered = _bool_value(summary.get("fallback_recovered"))
    if (
        summary_fallback_recovered
        and fallback_final_status
        and fallback_final_status != "succeeded"
    ):
        errors.append("remote_runtime_event_summary_fallback_recovery_mismatch")
    if (
        remote_operation_summary
        and summary_fallback_recovered != operation_fallback_recovered
    ):
        errors.append("remote_runtime_event_summary_operation_fallback_mismatch")

    return errors


def _count_event_values(
    events: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = event.get(key)
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def compute_runtime_operation_metrics(runtime_result: dict[str, Any]) -> dict[str, Any]:
    """Compute deterministic operation metrics from a Runtime result JSON object."""

    health = _runtime_health_snapshot(runtime_result)
    error = _runtime_error_classification(runtime_result)
    operation_summary = _runtime_operation_summary(runtime_result)
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
    retryable = _bool_value(error.get("retryable")) or any(
        _bool_value(event.get("retryable")) for event in events
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
        "runtime_operation_summary": operation_summary,
        "runtime_operation_summary_schema": operation_summary.get("schema_version"),
        "runtime_operation_health_status": _first_string(
            operation_summary.get("health_status"),
            health.get("status"),
        ),
        "runtime_operation_health_reason": _first_string(
            operation_summary.get("health_reason"),
            health.get("health_reason"),
        ),
        "runtime_operation_recommended_action": _first_string(
            operation_summary.get("recommended_action")
        ),
        "runtime_operation_risk_labels": _string_list(
            operation_summary.get("risk_labels")
        ),
        "runtime_operation_evidence_gaps": _string_list(
            operation_summary.get("evidence_gaps")
        ),
        "runtime_operation_decision_owner": _first_string(
            operation_summary.get("decision_owner")
        ),
        "runtime_operation_scheduler_owner": _first_string(
            operation_summary.get("scheduler_owner")
        ),
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
        "runtime_error_retryable": retryable,
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


def _queue_pressure_context_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    pressure_counts = _count_mapping(metrics.get("queue_pressure_reason_counts"))
    concerning_count = sum(
        count
        for reason, count in pressure_counts.items()
        if _queue_pressure_reason_is_concerning(reason)
    )
    queue_pressure_reason = _first_string(metrics.get("queue_pressure_reason"))
    if (
        concerning_count < thresholds["queue_pressure_reason_count_review"]
        and not _queue_pressure_reason_is_concerning(queue_pressure_reason)
    ):
        return None
    observed = max(float(concerning_count), 1.0)
    severity = "medium"
    if _queue_pressure_reason_is_blocking(queue_pressure_reason) or any(
        _queue_pressure_reason_is_blocking(reason) for reason in pressure_counts
    ):
        severity = "medium"
    return build_evidence_item(
        evidence_type="queue_pressure_context",
        metric_name="queue_pressure_reason_count",
        observed_value=observed,
        baseline_value=0,
        threshold=thresholds["queue_pressure_reason_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status="warning",
        why_it_matters=(
            "Queue pressure reason fields explain whether backlog was below, near, "
            "or beyond the configured overload threshold. This is deterministic "
            "operation context for Lab review, not an inferred root cause."
        ),
        suspected_causes=_queue_pressure_suspected_causes(
            queue_pressure_reason,
            pressure_counts,
        ),
        recommendation=(
            "Inspect queue_state_summary, queue_pressure_reason_counts, max pressure "
            "task, and policy/drop reason rollups before treating this operation path "
            "as stable."
        ),
        raw_context={
            "totals": totals,
            "queue_pressure_state": metrics.get("queue_pressure_state"),
            "queue_pressure_reason": queue_pressure_reason,
            "queue_pressure_reason_counts": pressure_counts,
            "max_pressure_task": metrics.get("max_pressure_task"),
            "policy_decision_reason_counts": metrics.get(
                "policy_decision_reason_counts", {}
            ),
            "drop_reason_counts": metrics.get("drop_reason_counts", {}),
        },
    )


def _worker_operation_risk_summary_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    worker_health = _mapping(metrics.get("worker_health"))
    risk_counts = _count_mapping(worker_health.get("operation_risk_summary_counts"))
    risk_counts = {
        risk: count
        for risk, count in risk_counts.items()
        if risk not in {"healthy_without_runtime_risk", "unknown"}
    }
    risk_count = float(sum(risk_counts.values()))
    if risk_count < thresholds["worker_operation_risk_count_review"]:
        return None
    severity = _rate_severity(
        value=risk_count,
        review=thresholds["worker_operation_risk_count_review"],
        blocked=thresholds["worker_operation_risk_count_blocked"],
    )
    status = "failed" if severity == "high" else "warning"
    return build_evidence_item(
        evidence_type="worker_operation_risk_summary",
        metric_name="worker_operation_risk_count",
        observed_value=risk_count,
        baseline_value=0,
        threshold=thresholds["worker_operation_risk_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Worker operation risk summaries preserve Orchestrator's deterministic "
            "per-worker risk labels, such as latency/fallback risk or queue-pressure "
            "watch, so reviewers can see which runtime loops need attention."
        ),
        suspected_causes=sorted(risk_counts),
        recommendation=(
            "Inspect worker primary_health_reason, operation_risk_summary, producer "
            "context, and per-worker drop/deadline/fallback rates before deployment."
        ),
        raw_context={
            "totals": totals,
            "worker_health": worker_health,
            "operation_risk_summary_counts": risk_counts,
            "primary_health_reason_counts": worker_health.get(
                "primary_health_reason_counts", {}
            ),
        },
    )


def _device_local_operation_context_evidence(
    metrics: dict[str, Any],
    totals: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    task_count = metrics.get("device_local_task_count", 0.0)
    if task_count <= 0:
        return None
    event_count = metrics.get("device_local_event_count", 0.0)
    producer_sources = _string_list(metrics.get("device_local_producer_sources"))
    runtime_sources = _string_list(metrics.get("runtime_event_producer_sources"))
    has_coverage = (
        event_count >= thresholds["device_local_event_count_review"]
        and bool(producer_sources or runtime_sources)
    )
    severity = "low" if has_coverage else "medium"
    status = "passed" if has_coverage else "warning"
    return build_evidence_item(
        evidence_type="device_local_operation_context",
        metric_name="device_local_event_count",
        observed_value=event_count,
        baseline_value=None,
        threshold=thresholds["device_local_event_count_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Device-local starter evidence is stronger when Orchestrator records "
            "actual local producer sources and runtime events for the device-local "
            "tasks under review."
        ),
        suspected_causes=[] if has_coverage else ["device_local_evidence_gap"],
        recommendation=(
            "Device-local producer/event coverage is present; preserve it as local "
            "operation evidence for Lab review."
            if has_coverage
            else "Rerun the device-local starter with local input overrides or producer "
            "fixtures so Orchestrator records producer source and runtime event coverage."
        ),
        raw_context={
            "totals": totals,
            "device_local_task_count": task_count,
            "device_local_event_count": event_count,
            "producer_event_count": metrics.get("producer_event_count"),
            "device_local_producer_sources": producer_sources,
            "runtime_event_producer_sources": runtime_sources,
            "producer_sources_by_task": metrics.get("producer_sources_by_task", {}),
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


def _edgeenv_regression_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    comparable = bool(metrics.get("comparable"))
    same_condition = metrics.get("mode") == "same-condition"

    if not comparable or not same_condition:
        evidence.append(_edgeenv_comparability_guardrail_evidence(metrics))
        return evidence

    if metrics.get("regression_detected"):
        latency_evidence = _edgeenv_latency_regression_evidence(metrics, thresholds)
        if latency_evidence is not None:
            evidence.append(latency_evidence)
        fps_evidence = _edgeenv_fps_drop_evidence(metrics, thresholds)
        if fps_evidence is not None:
            evidence.append(fps_evidence)
        memory_evidence = _edgeenv_memory_regression_evidence(metrics, thresholds)
        if memory_evidence is not None:
            evidence.append(memory_evidence)

    telemetry_evidence = _edgeenv_telemetry_context_evidence(metrics, thresholds)
    if telemetry_evidence is not None:
        evidence.append(telemetry_evidence)
    replay_evidence = _edgeenv_telemetry_replay_evidence(metrics, thresholds)
    if replay_evidence is not None:
        evidence.append(replay_evidence)
    producer_lineage_evidence = _edgeenv_orchestrator_producer_lineage_evidence(
        metrics
    )
    if producer_lineage_evidence is not None:
        evidence.append(producer_lineage_evidence)
    operation_risk_evidence = _edgeenv_orchestrator_operation_risk_evidence(metrics)
    if operation_risk_evidence is not None:
        evidence.append(operation_risk_evidence)
    task_event_rollup_evidence = _edgeenv_orchestrator_task_event_rollup_evidence(
        metrics
    )
    if task_event_rollup_evidence is not None:
        evidence.append(task_event_rollup_evidence)
    latency_budget_protection_evidence = (
        _edgeenv_orchestrator_latency_budget_protection_evidence(metrics)
    )
    if latency_budget_protection_evidence is not None:
        evidence.append(latency_budget_protection_evidence)
    seed_run_config_evidence = _edgeenv_history_seed_run_config_evidence(metrics)
    if seed_run_config_evidence is not None:
        evidence.append(seed_run_config_evidence)
    thermal_evidence = _edgeenv_runtime_thermal_telemetry_evidence(
        metrics,
        thresholds,
    )
    if thermal_evidence is not None:
        evidence.append(thermal_evidence)
    queue_evidence = _edgeenv_runtime_queue_telemetry_evidence(metrics, thresholds)
    if queue_evidence is not None:
        evidence.append(queue_evidence)

    if not evidence:
        evidence.append(_edgeenv_regression_pass_evidence(metrics))
    return evidence


def _edgeenv_comparability_guardrail_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="edgeenv_comparability_guardrail",
        metric_name="edgeenv_comparable",
        observed_value=1 if metrics.get("comparable") else 0,
        baseline_value=1,
        threshold=1,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="skipped",
        why_it_matters=(
            "AIGuard does not reinterpret non-comparable EdgeEnv results as "
            "same-condition runtime regressions. Comparability remains owned by "
            "EdgeEnv and final deployment decisions remain owned by Lab."
        ),
        suspected_causes=[],
        recommendation=(
            "Use EdgeEnv mode and comparability reasons as report context, or rerun "
            "with matching model, precision, shape, and benchmark protocol before "
            "diagnosing same-condition runtime regression."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_latency_regression_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    candidates = [
        ("p99_delta_pct", metrics.get("p99_delta_pct"), thresholds["edgeenv_p99_delta_pct_review"]),
        ("mean_delta_pct", metrics.get("mean_delta_pct"), thresholds["edgeenv_mean_delta_pct_review"]),
        ("p95_delta_pct", metrics.get("p95_delta_pct"), thresholds["edgeenv_mean_delta_pct_review"]),
    ]
    observed_name = None
    observed_value = None
    observed_threshold = None
    for name, value, threshold in candidates:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if observed_value is None or float(value) > float(observed_value):
                observed_name = name
                observed_value = float(value)
                observed_threshold = float(threshold)
    if observed_name is None or observed_value is None or observed_threshold is None:
        return None
    severity = "high" if observed_value >= thresholds["edgeenv_p99_delta_pct_review"] else "medium"
    status = "failed" if observed_value >= observed_threshold else "passed"
    if status == "passed":
        severity = "low"
    return build_evidence_item(
        evidence_type="runtime_latency_regression",
        metric_name=observed_name,
        observed_value=observed_value,
        baseline_value=0,
        threshold=observed_threshold,
        delta=None,
        delta_pct=observed_value,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Same-condition latency regression, especially p95/p99 tail latency, "
            "is deployment risk evidence because it can indicate runtime drift, "
            "thermal pressure, scheduler contention, or backend changes."
        ),
        suspected_causes=[
            "runtime_latency_drift",
            "tail_latency_spike",
            "thermal_or_scheduler_contention",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review EdgeEnv comparability judgement, tail latency deltas, runtime "
            "telemetry context, and recent runtime/device changes before deployment."
            if status != "passed"
            else "Latency regression metrics are within configured thresholds."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_fps_drop_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    fps_delta = metrics.get("fps_delta_pct")
    if not isinstance(fps_delta, (int, float)) or isinstance(fps_delta, bool):
        return None
    threshold = thresholds["edgeenv_fps_drop_pct_review"]
    status = "failed" if fps_delta <= threshold else "passed"
    return build_evidence_item(
        evidence_type="runtime_throughput_regression",
        metric_name="fps_delta_pct",
        observed_value=fps_delta,
        baseline_value=0,
        threshold=threshold,
        delta=None,
        delta_pct=fps_delta,
        increase_factor=None,
        severity="medium" if status != "passed" else "low",
        status=status,
        why_it_matters=(
            "FPS drop can reduce edge workload headroom even when mean latency "
            "alone looks acceptable."
        ),
        suspected_causes=[
            "runtime_throughput_drop",
            "device_resource_contention",
            "backend_or_power_mode_change",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review throughput delta together with latency tail and runtime "
            "telemetry before deployment."
            if status != "passed"
            else "Throughput regression is within configured thresholds."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_memory_regression_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    memory_delta = metrics.get("memory_peak_delta_pct")
    if not isinstance(memory_delta, (int, float)) or isinstance(memory_delta, bool):
        return None
    threshold = thresholds["edgeenv_memory_peak_delta_pct_warning"]
    status = "warning" if memory_delta >= threshold else "passed"
    return build_evidence_item(
        evidence_type="runtime_memory_regression",
        metric_name="memory_peak_delta_pct",
        observed_value=memory_delta,
        baseline_value=0,
        threshold=threshold,
        delta=None,
        delta_pct=memory_delta,
        increase_factor=None,
        severity="medium" if status != "passed" else "low",
        status=status,
        why_it_matters=(
            "Higher memory peak can reduce deployment headroom and increase queue "
            "backlog or OOM risk on constrained edge devices."
        ),
        suspected_causes=[
            "memory_pressure",
            "runtime_allocator_or_workspace_change",
            "preprocess_postprocess_memory_growth",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review memory peak delta and runtime telemetry before treating the "
            "candidate as operation-stable."
            if status != "passed"
            else "Memory regression is within configured thresholds."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_telemetry_context_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    gap_count = metrics.get("evidence_gap_count", 0.0)
    coverage_missing_count = metrics.get("telemetry_coverage_missing_field_count")
    status = (
        "warning"
        if gap_count >= thresholds["edgeenv_telemetry_gap_review"]
        else "passed"
    )
    suspected_causes: list[str] = []
    if status != "passed":
        suspected_causes.append("runtime_telemetry_gap")
    if (
        isinstance(coverage_missing_count, (int, float))
        and not isinstance(coverage_missing_count, bool)
        and coverage_missing_count > 0
    ):
        suspected_causes.append("runtime_telemetry_field_gap")
    if (
        metrics.get("baseline_missing_telemetry_is_failure") is True
        or metrics.get("candidate_missing_telemetry_is_failure") is True
    ):
        suspected_causes.append("runtime_telemetry_required_field_missing")
    return build_evidence_item(
        evidence_type="runtime_telemetry_context_coverage",
        metric_name="runtime_telemetry_evidence_gap_count",
        observed_value=gap_count,
        baseline_value=0,
        threshold=thresholds["edgeenv_telemetry_gap_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium" if status != "passed" else "low",
        status=status,
        why_it_matters=(
            "Runtime telemetry context makes regression evidence more explainable. "
            "Missing baseline or candidate telemetry is an evidence gap, not a "
            "failed benchmark by itself."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Inspect telemetry coverage missing fields, rerun telemetry history "
            "export if needed, and preserve runtime_telemetry artifacts for both "
            "baseline and candidate before relying on trend diagnosis."
            if status != "passed"
            else "Telemetry coverage is present for the EdgeEnv regression report."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_telemetry_replay_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    history_missing_count = metrics.get("history_missing_telemetry_runs")
    sequence_order_valid = metrics.get("execution_sequence_order_valid")
    if history_missing_count in (None, 0.0) and sequence_order_valid is not False:
        return None

    missing_value = (
        history_missing_count
        if isinstance(history_missing_count, (int, float))
        and not isinstance(history_missing_count, bool)
        else 0.0
    )
    status = (
        "warning"
        if missing_value >= thresholds["edgeenv_telemetry_gap_review"]
        or sequence_order_valid is False
        else "passed"
    )
    suspected_causes: list[str] = []
    if missing_value >= thresholds["edgeenv_telemetry_gap_review"]:
        suspected_causes.append("telemetry_history_replay_gap")
    if sequence_order_valid is False:
        suspected_causes.append("telemetry_sequence_order_mismatch")

    return build_evidence_item(
        evidence_type="runtime_telemetry_replay_context",
        metric_name="runtime_telemetry_history_missing_run_count",
        observed_value=missing_value,
        baseline_value=0,
        threshold=thresholds["edgeenv_telemetry_gap_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium" if status != "passed" else "low",
        status=status,
        why_it_matters=(
            "EdgeEnv telemetry history is the replay artifact behind runtime "
            "regression context. History-level missing telemetry or out-of-order "
            "baseline/candidate sequence IDs reduce how confidently reviewers can "
            "interpret runtime trend evidence."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Inspect the EdgeEnv telemetry history artifact, confirm baseline and "
            "candidate sequence order, and rerun export-history if replay gaps "
            "should not be present."
            if status != "passed"
            else "Telemetry replay context is present and ordered for this report."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_orchestrator_producer_lineage_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None

    candidate_expected = metrics.get("candidate_orchestrator_context_present") is True
    missing_context_count = metrics.get("history_missing_orchestrator_context_count")
    missing_expected = (
        isinstance(missing_context_count, (int, float))
        and not isinstance(missing_context_count, bool)
        and missing_context_count > 0
    )
    if not candidate_expected and not missing_expected:
        return None

    candidate_shape_ok = _producer_lineage_shape_valid(
        device_local_sources=metrics.get(
            "orchestrator_candidate_device_local_producer_sources"
        ),
        producer_sources=metrics.get("orchestrator_candidate_producer_sources"),
        sources_by_task=metrics.get("orchestrator_candidate_producer_sources_by_task"),
        stage_by_task=metrics.get("orchestrator_candidate_producer_stage_by_task"),
        producer_event_count=metrics.get("orchestrator_candidate_producer_event_count"),
        device_local_event_count=metrics.get(
            "orchestrator_candidate_device_local_event_count"
        ),
        device_local_task_count=metrics.get(
            "orchestrator_candidate_device_local_task_count"
        ),
        operation_context_role=metrics.get(
            "orchestrator_candidate_operation_context_role"
        ),
    )
    candidate_guard_alignment_ok = _producer_lineage_guard_alignment_valid(
        declared_by=metrics.get("orchestrator_guard_alignment_declared_by"),
        producer_lineage_evidence_type=metrics.get(
            "orchestrator_guard_alignment_producer_lineage_evidence_type"
        ),
        operation_evidence_candidates=metrics.get(
            "orchestrator_guard_alignment_operation_evidence_candidates"
        ),
        orchestrator_is_final_decision_owner=metrics.get(
            "orchestrator_guard_alignment_orchestrator_is_final_decision_owner"
        ),
        lab_is_final_decision_owner=metrics.get(
            "orchestrator_guard_alignment_lab_is_final_decision_owner"
        ),
    )
    missing_shape_ok = _producer_lineage_shape_valid(
        device_local_sources=metrics.get(
            "history_missing_orchestrator_candidate_device_local_producer_sources"
        ),
        producer_sources=metrics.get(
            "history_missing_orchestrator_candidate_producer_sources"
        ),
        sources_by_task=metrics.get(
            "history_missing_orchestrator_candidate_producer_sources_by_task"
        ),
        stage_by_task=metrics.get(
            "history_missing_orchestrator_candidate_producer_stage_by_task"
        ),
        producer_event_count=metrics.get(
            "history_missing_orchestrator_candidate_producer_event_count"
        ),
        device_local_event_count=metrics.get(
            "history_missing_orchestrator_candidate_device_local_event_count"
        ),
        device_local_task_count=metrics.get(
            "history_missing_orchestrator_candidate_device_local_task_count"
        ),
        operation_context_role=metrics.get(
            "history_missing_orchestrator_candidate_operation_context_role"
        ),
    )
    missing_guard_alignment_ok = _producer_lineage_guard_alignment_valid(
        declared_by=metrics.get(
            "history_missing_orchestrator_guard_alignment_declared_by"
        ),
        producer_lineage_evidence_type=metrics.get(
            "history_missing_orchestrator_guard_alignment_producer_lineage_evidence_type"
        ),
        operation_evidence_candidates=metrics.get(
            "history_missing_orchestrator_guard_alignment_operation_evidence_candidates"
        ),
        orchestrator_is_final_decision_owner=metrics.get(
            "history_missing_orchestrator_guard_alignment_orchestrator_is_final_decision_owner"
        ),
        lab_is_final_decision_owner=metrics.get(
            "history_missing_orchestrator_guard_alignment_lab_is_final_decision_owner"
        ),
    )
    candidate_ok = (
        bool(metrics.get("orchestrator_candidate_device_local_producer_sources"))
        and candidate_shape_ok
        and candidate_guard_alignment_ok
    )
    missing_ok = (
        bool(
            metrics.get(
                "history_missing_orchestrator_candidate_device_local_producer_sources"
            )
        )
        and missing_shape_ok
        and missing_guard_alignment_ok
    )

    expected_count = int(candidate_expected) + int(missing_expected)
    observed_count = int(candidate_ok) + int(missing_ok)
    status = "passed" if observed_count >= expected_count else "warning"
    suspected_causes = []
    if status != "passed":
        suspected_causes = [
            "device_local_producer_lineage_gap",
            "orchestrator_context_without_producer_metadata",
        ]
        if (
            candidate_expected
            and bool(metrics.get("orchestrator_candidate_device_local_producer_sources"))
            and not candidate_guard_alignment_ok
        ) or (
            missing_expected
            and bool(
                metrics.get(
                    "history_missing_orchestrator_candidate_device_local_producer_sources"
                )
            )
            and not missing_guard_alignment_ok
        ):
            suspected_causes.append("orchestrator_guard_alignment_marker_gap")
    if status == "passed":
        explanation = (
            "Device-local Orchestrator producer lineage is preserved for "
            f"{observed_count} of {expected_count} expected operation contexts."
        )
    else:
        explanation = (
            "Device-local Orchestrator producer lineage is missing for "
            f"{expected_count - observed_count} of {expected_count} expected "
            "operation contexts."
        )

    return build_evidence_item(
        evidence_type="edgeenv_orchestrator_producer_lineage",
        metric_name="device_local_producer_context_count",
        observed_value=observed_count,
        baseline_value=expected_count,
        threshold=expected_count,
        delta=observed_count - expected_count,
        delta_pct=None,
        increase_factor=None,
        severity="medium" if status != "passed" else "low",
        status=status,
        explanation=explanation,
        why_it_matters=(
            "Device-local producer lineage explains which Orchestrator source "
            "created supplemental operation context. Preserving it lets Lab "
            "review runtime evidence traceability without making AIGuard or "
            "Orchestrator the deployment decision owner."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Rebuild the EdgeEnv telemetry history with preserved "
            "candidate_context.producer metadata before relying on operation "
            "context handoff evidence."
            if status != "passed"
            else "Device-local Orchestrator producer lineage is preserved in "
            "the EdgeEnv runtime telemetry context."
        ),
        raw_context={
            "edgeenv_regression": metrics,
            "producer_lineage": {
                "candidate_expected": candidate_expected,
                "candidate_device_local_sources": metrics.get(
                    "orchestrator_candidate_device_local_producer_sources"
                ),
                "candidate_producer_sources": metrics.get(
                    "orchestrator_candidate_producer_sources"
                ),
                "candidate_sources_by_task": metrics.get(
                    "orchestrator_candidate_producer_sources_by_task"
                ),
                "candidate_stage_by_task": metrics.get(
                    "orchestrator_candidate_producer_stage_by_task"
                ),
                "candidate_producer_event_count": metrics.get(
                    "orchestrator_candidate_producer_event_count"
                ),
                "candidate_device_local_event_count": metrics.get(
                    "orchestrator_candidate_device_local_event_count"
                ),
                "candidate_device_local_task_count": metrics.get(
                    "orchestrator_candidate_device_local_task_count"
                ),
                "candidate_lineage_shape_valid": candidate_shape_ok,
                "candidate_guard_alignment": metrics.get(
                    "orchestrator_downstream_guard_alignment"
                ),
                "candidate_guard_alignment_valid": candidate_guard_alignment_ok,
                "candidate_guard_alignment_producer_lineage_evidence_type": (
                    metrics.get(
                        "orchestrator_guard_alignment_producer_lineage_evidence_type"
                    )
                ),
                "candidate_guard_alignment_operation_evidence_candidates": (
                    metrics.get(
                        "orchestrator_guard_alignment_operation_evidence_candidates"
                    )
                ),
                "candidate_remote_runtime_event_summary": metrics.get(
                    "orchestrator_remote_runtime_event_summary"
                ),
                "candidate_remote_runtime_event_summary_evidence_role": (
                    metrics.get(
                        "orchestrator_remote_runtime_event_summary_evidence_role"
                    )
                ),
                "candidate_remote_runtime_event_summary_operation_boundary": (
                    metrics.get(
                        "orchestrator_remote_runtime_event_summary_operation_boundary"
                    )
                ),
                "candidate_remote_runtime_event_summary_production_remote_execution": (
                    metrics.get(
                        "orchestrator_remote_runtime_event_summary_production_remote_execution"
                    )
                ),
                "missing_expected": missing_expected,
                "missing_device_local_sources": metrics.get(
                    "history_missing_orchestrator_candidate_device_local_producer_sources"
                ),
                "missing_producer_sources": metrics.get(
                    "history_missing_orchestrator_candidate_producer_sources"
                ),
                "missing_sources_by_task": metrics.get(
                    "history_missing_orchestrator_candidate_producer_sources_by_task"
                ),
                "missing_stage_by_task": metrics.get(
                    "history_missing_orchestrator_candidate_producer_stage_by_task"
                ),
                "missing_producer_event_count": metrics.get(
                    "history_missing_orchestrator_candidate_producer_event_count"
                ),
                "missing_device_local_event_count": metrics.get(
                    "history_missing_orchestrator_candidate_device_local_event_count"
                ),
                "missing_device_local_task_count": metrics.get(
                    "history_missing_orchestrator_candidate_device_local_task_count"
                ),
                "missing_lineage_shape_valid": missing_shape_ok,
                "missing_guard_alignment": metrics.get(
                    "history_missing_orchestrator_downstream_guard_alignment"
                ),
                "missing_guard_alignment_valid": missing_guard_alignment_ok,
                "missing_guard_alignment_producer_lineage_evidence_type": (
                    metrics.get(
                        "history_missing_orchestrator_guard_alignment_producer_lineage_evidence_type"
                    )
                ),
                "missing_guard_alignment_operation_evidence_candidates": (
                    metrics.get(
                        "history_missing_orchestrator_guard_alignment_operation_evidence_candidates"
                    )
                ),
                "missing_remote_runtime_event_summary": metrics.get(
                    "history_missing_orchestrator_remote_runtime_event_summary"
                ),
                "missing_remote_runtime_event_summary_evidence_role": (
                    metrics.get(
                        "history_missing_orchestrator_remote_runtime_event_summary_evidence_role"
                    )
                ),
                "missing_remote_runtime_event_summary_operation_boundary": (
                    metrics.get(
                        "history_missing_orchestrator_remote_runtime_event_summary_operation_boundary"
                    )
                ),
                "missing_remote_runtime_event_summary_production_remote_execution": (
                    metrics.get(
                        "history_missing_orchestrator_remote_runtime_event_summary_production_remote_execution"
                    )
                ),
                "missing_context_run_ids": metrics.get(
                    "history_missing_orchestrator_context_run_ids"
                ),
                "operation_context_role": metrics.get(
                    "orchestrator_candidate_operation_context_role"
                ),
                "missing_operation_context_role": metrics.get(
                    "history_missing_orchestrator_candidate_operation_context_role"
                ),
            },
        },
    )


def _edgeenv_orchestrator_operation_risk_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    if not metrics.get("orchestrator_operation_risk_summary_present"):
        return None

    degraded_worker_ids = _string_list(
        metrics.get("orchestrator_operation_risk_summary_degraded_worker_ids")
    )
    queue_pressure_reason = metrics.get(
        "orchestrator_operation_risk_summary_queue_pressure_reason"
    )
    primary_health_reason = metrics.get(
        "orchestrator_operation_risk_summary_primary_health_reason"
    )
    max_pressure_task = metrics.get(
        "orchestrator_operation_risk_summary_max_pressure_task"
    )
    boundary_ok = (
        metrics.get("orchestrator_operation_risk_summary_decision_owner") == "lab"
        and metrics.get("orchestrator_operation_risk_summary_scheduler_owner")
        == "orchestrator"
        and metrics.get(
            "orchestrator_operation_risk_summary_not_a_deployment_decision"
        )
        is True
    )
    risk_markers: list[str] = []
    if _queue_pressure_reason_is_concerning(queue_pressure_reason):
        risk_markers.append("queue_pressure")
    if _non_empty_string(primary_health_reason) and primary_health_reason != "healthy":
        risk_markers.append("worker_health")
    if degraded_worker_ids:
        risk_markers.append("degraded_worker")
    if _non_empty_string(max_pressure_task):
        risk_markers.append("max_pressure_task")
    if not boundary_ok:
        risk_markers.append("operation_boundary_marker_gap")

    observed_value = len(risk_markers)
    status = "warning" if observed_value else "passed"
    severity = "medium" if status != "passed" else "low"
    suspected_causes = []
    if "queue_pressure" in risk_markers:
        suspected_causes.append("queue_pressure_context")
    if "worker_health" in risk_markers or "degraded_worker" in risk_markers:
        suspected_causes.append("worker_health_degradation_context")
    if "max_pressure_task" in risk_markers:
        suspected_causes.append("task_specific_queue_pressure_context")
    if "operation_boundary_marker_gap" in risk_markers:
        suspected_causes.append("operation_risk_boundary_marker_gap")

    return build_evidence_item(
        evidence_type="edgeenv_orchestrator_operation_risk_summary",
        metric_name="orchestrator_operation_risk_marker_count",
        observed_value=observed_value,
        baseline_value=0,
        threshold=1,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        explanation=(
            "EdgeEnv preserved Orchestrator operation risk summary with "
            f"{observed_value} deterministic review marker(s)."
        ),
        why_it_matters=(
            "Operation risk summary links queue pressure, worker health, and "
            "device-local producer event context to the Lab report without "
            "making AIGuard or Orchestrator the deployment decision owner."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Review the Orchestrator operation risk summary in Lab alongside "
            "queue, worker health, and device-local producer evidence; Lab "
            "remains the final deployment decision owner."
            if status != "passed"
            else "Orchestrator operation risk summary is present without "
            "deterministic review markers."
        ),
        raw_context={
            "edgeenv_regression": metrics,
            "operation_risk_summary": {
                "summary": metrics.get("orchestrator_operation_risk_summary"),
                "boundary_markers_valid": boundary_ok,
                "risk_markers": risk_markers,
                "degraded_worker_ids": degraded_worker_ids,
                "queue_pressure_reason": queue_pressure_reason,
                "primary_health_reason": primary_health_reason,
                "max_pressure_task": max_pressure_task,
                "device_local_event_count": metrics.get(
                    "orchestrator_operation_risk_summary_device_local_event_count"
                ),
                "producer_event_count": metrics.get(
                    "orchestrator_operation_risk_summary_producer_event_count"
                ),
            },
        },
    )


def _edgeenv_orchestrator_task_event_rollup_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    task_summary = _mapping(metrics.get("orchestrator_runtime_task_event_summary"))
    if not task_summary:
        return None

    tasks_with_deadline_miss = _string_list(
        metrics.get("orchestrator_tasks_with_deadline_miss")
    )
    tasks_with_fallback = _string_list(metrics.get("orchestrator_tasks_with_fallback"))
    tasks_with_scheduler_delay = _string_list(
        metrics.get("orchestrator_tasks_with_scheduler_delay")
    )
    affected_tasks = _task_event_rollup_affected_tasks(
        task_summary=task_summary,
        tasks_with_deadline_miss=tasks_with_deadline_miss,
        tasks_with_fallback=tasks_with_fallback,
        tasks_with_scheduler_delay=tasks_with_scheduler_delay,
    )
    reason_counts = _task_event_rollup_reason_counts(task_summary)
    boundary_ok = (
        metrics.get("orchestrator_guard_alignment_orchestrator_is_final_decision_owner")
        is False
        and metrics.get("orchestrator_guard_alignment_lab_is_final_decision_owner")
        is True
    )
    review_markers: list[str] = []
    if tasks_with_deadline_miss:
        review_markers.append("deadline_miss")
    if tasks_with_fallback:
        review_markers.append("fallback")
    if tasks_with_scheduler_delay:
        review_markers.append("scheduler_delay")
    if any(_queue_pressure_reason_is_concerning(reason) for reason in reason_counts):
        review_markers.append("queue_pressure_reason")
    if not boundary_ok:
        review_markers.append("operation_boundary_marker_gap")

    observed_value = float(len(affected_tasks))
    status = "warning" if review_markers else "passed"
    severity = "medium" if status != "passed" else "low"
    suspected_causes: list[str] = []
    if tasks_with_scheduler_delay:
        suspected_causes.append("scheduler_delay_context")
    if tasks_with_deadline_miss:
        suspected_causes.append("deadline_miss_context")
    if tasks_with_fallback:
        suspected_causes.append("fallback_policy_context")
    if "queue_pressure_reason" in review_markers:
        suspected_causes.append("queue_pressure_context")
    if "operation_boundary_marker_gap" in review_markers:
        suspected_causes.append("operation_boundary_marker_gap")

    return build_evidence_item(
        evidence_type=EDGEENV_ORCHESTRATOR_TASK_EVENT_ROLLUP_EVIDENCE_TYPE,
        metric_name="orchestrator_task_event_affected_task_count",
        observed_value=observed_value,
        baseline_value=0,
        threshold=1,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        explanation=(
            "EdgeEnv preserved Orchestrator task event rollup with "
            f"{int(observed_value)} task-level review target(s)."
        ),
        why_it_matters=(
            "Task-level scheduler delay, deadline miss, and fallback context "
            "explains which workload produced runtime operation risk. AIGuard "
            "preserves this deterministic warning evidence while Lab remains "
            "the deployment decision owner."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Review Orchestrator task event rollup, queue policy, deadline "
            "budget, and fallback behavior in the Lab report before deployment."
            if status != "passed"
            else "Orchestrator task event rollup is present without task-level "
            "review markers."
        ),
        raw_context={
            "edgeenv_regression": metrics,
            "task_event_rollup": {
                "summary": task_summary,
                "tasks_with_deadline_miss": tasks_with_deadline_miss,
                "tasks_with_fallback": tasks_with_fallback,
                "tasks_with_scheduler_delay": tasks_with_scheduler_delay,
                "affected_tasks": affected_tasks,
                "reason_counts": reason_counts,
                "review_markers": review_markers,
                "boundary_markers_valid": boundary_ok,
                "decision_owner": "lab",
                "scheduler_owner": "orchestrator",
                "not_a_deployment_decision": True,
            },
        },
    )


def _edgeenv_orchestrator_latency_budget_protection_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    if not metrics.get("orchestrator_latency_budget_protection_present"):
        return None

    protected_tasks = _string_list(
        metrics.get("orchestrator_latency_budget_protection_protected_tasks")
    )
    risk_tasks = _string_list(
        metrics.get("orchestrator_latency_budget_protection_risk_tasks")
    )
    risk_reasons = _string_list(
        metrics.get("orchestrator_latency_budget_protection_risk_reasons")
    )
    per_task_budget_context = _mapping(
        metrics.get("orchestrator_latency_budget_protection_per_task_budget_context")
    )
    boundary_ok = (
        metrics.get("orchestrator_latency_budget_protection_schema_version")
        == EDGEENV_ORCHESTRATOR_LATENCY_BUDGET_PROTECTION_SCHEMA_VERSION
        and metrics.get("orchestrator_latency_budget_protection_decision_owner")
        == "lab"
        and metrics.get("orchestrator_latency_budget_protection_scheduler_owner")
        == "orchestrator"
        and metrics.get("orchestrator_latency_budget_protection_regression_owner")
        == "edgeenv"
        and metrics.get(
            "orchestrator_latency_budget_protection_not_a_deployment_decision"
        )
        is True
    )

    review_markers: list[str] = []
    if risk_tasks:
        review_markers.append("latency_budget_risk_task")
    if any("deadline" in reason for reason in risk_reasons):
        review_markers.append("deadline_miss_context")
    if any("scheduler" in reason for reason in risk_reasons):
        review_markers.append("scheduler_delay_context")
    if any("queue" in reason or "backlog" in reason for reason in risk_reasons):
        review_markers.append("queue_pressure_context")
    if not boundary_ok:
        review_markers.append("operation_boundary_marker_gap")

    observed_value = len(review_markers)
    status = "warning" if review_markers else "passed"
    severity = "medium" if status != "passed" else "low"
    suspected_causes: list[str] = []
    if risk_tasks:
        suspected_causes.append("latency_budget_pressure_context")
    if "deadline_miss_context" in review_markers:
        suspected_causes.append("deadline_miss_context")
    if "scheduler_delay_context" in review_markers:
        suspected_causes.append("scheduler_delay_context")
    if "queue_pressure_context" in review_markers:
        suspected_causes.append("queue_pressure_context")
    if "operation_boundary_marker_gap" in review_markers:
        suspected_causes.append("operation_boundary_marker_gap")

    return build_evidence_item(
        evidence_type=EDGEENV_ORCHESTRATOR_LATENCY_BUDGET_PROTECTION_EVIDENCE_TYPE,
        metric_name="orchestrator_latency_budget_protection_marker_count",
        observed_value=observed_value,
        baseline_value=0,
        threshold=1,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        explanation=(
            "EdgeEnv preserved Orchestrator latency budget protection context "
            f"with {observed_value} deterministic review marker(s)."
        ),
        why_it_matters=(
            "Latency budget protection shows which high-priority workloads were "
            "protected and which tasks still carried budget risk. AIGuard keeps "
            "this as deterministic warning evidence while Lab remains the final "
            "deployment decision owner."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Review protected tasks, latency-budget risk tasks, deadline/scheduler "
            "reasons, and per-task budget context in the Lab report before "
            "deployment."
            if status != "passed"
            else "Latency budget protection context is present without deterministic "
            "review markers."
        ),
        raw_context={
            "edgeenv_regression": metrics,
            "latency_budget_protection": {
                "context": metrics.get("orchestrator_latency_budget_protection"),
                "boundary_markers_valid": boundary_ok,
                "protected_tasks": protected_tasks,
                "risk_tasks": risk_tasks,
                "risk_reasons": risk_reasons,
                "per_task_budget_context": per_task_budget_context,
                "review_markers": review_markers,
                "decision_owner": "lab",
                "scheduler_owner": "orchestrator",
                "regression_owner": "edgeenv",
                "not_a_deployment_decision": True,
            },
        },
    )


def _edgeenv_history_seed_run_config_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any] | None:
    seed_runs = metrics.get("history_telemetry_seed_runs")
    run_config_runs = metrics.get("history_telemetry_seed_run_config_runs")
    if seed_runs is None and run_config_runs is None:
        return None

    expected_count = (
        int(seed_runs)
        if isinstance(seed_runs, (int, float)) and not isinstance(seed_runs, bool)
        else 0
    )
    observed_count = (
        int(run_config_runs)
        if isinstance(run_config_runs, (int, float))
        and not isinstance(run_config_runs, bool)
        else 0
    )
    status = (
        "passed"
        if expected_count > 0 and observed_count >= expected_count
        else "warning"
    )
    marker_labels = _string_list(
        metrics.get("runtime_telemetry_history_seed_run_config_marker_labels")
    )
    suspected_causes = (
        []
        if status == "passed"
        else ["runtime_history_seed_run_config_traceability_gap"]
    )
    return build_evidence_item(
        evidence_type="runtime_history_seed_run_config_traceability",
        metric_name="runtime_history_seed_run_config_count",
        observed_value=observed_count,
        baseline_value=expected_count,
        threshold=expected_count,
        delta=observed_count - expected_count,
        delta_pct=None,
        increase_factor=None,
        severity="low" if status == "passed" else "medium",
        status=status,
        explanation=(
            "Runtime history seed run_config markers are preserved for "
            f"{observed_count} of {expected_count} EdgeEnv history seed runs."
        ),
        why_it_matters=(
            "Run_config markers such as shape, preprocess, power mode, Jetson "
            "clocks, warmup, and repeat runs explain replay comparability context "
            "without making AIGuard the deployment decision owner."
        ),
        suspected_causes=suspected_causes,
        recommendation=(
            "Preserve Runtime history_seed.run_config in EdgeEnv history before "
            "using AIGuard runtime telemetry reasoning."
            if status != "passed"
            else "Runtime history seed run_config markers are preserved as "
            "traceability context for Lab review."
        ),
        raw_context={
            "edgeenv_regression": metrics,
            "history_seed_run_config": {
                "expected_seed_runs": expected_count,
                "observed_run_config_runs": observed_count,
                "marker_fields": metrics.get(
                    "runtime_telemetry_history_seed_run_config_marker_fields"
                ),
                "marker_labels": marker_labels,
            },
        },
    )


def _edgeenv_runtime_thermal_telemetry_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    candidate_temperature = metrics.get("candidate_max_temperature_c")
    throttling_detected = metrics.get("candidate_throttling_detected") is True
    if candidate_temperature is None and not throttling_detected:
        return None

    observed_value = (
        candidate_temperature
        if isinstance(candidate_temperature, (int, float))
        and not isinstance(candidate_temperature, bool)
        else 1.0
    )
    severity = _rate_severity(
        value=float(observed_value),
        review=thresholds["edgeenv_telemetry_temperature_c_review"],
        blocked=thresholds["edgeenv_telemetry_temperature_c_blocked"],
    )
    if throttling_detected and severity == "low":
        severity = "medium"
    status = _edgeenv_runtime_context_status(severity)
    return build_evidence_item(
        evidence_type="runtime_thermal_instability",
        metric_name=(
            "candidate_throttling_detected"
            if candidate_temperature is None
            else "candidate_max_temperature_c"
        ),
        observed_value=observed_value,
        baseline_value=metrics.get("baseline_max_temperature_c"),
        threshold=thresholds["edgeenv_telemetry_temperature_c_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Thermal pressure or throttling in EdgeEnv telemetry can explain "
            "runtime latency drift and reduce sustained deployment reliability."
        ),
        suspected_causes=[
            "thermal_pressure",
            "thermal_throttling",
            "power_mode_or_cooling_constraint",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Review EdgeEnv telemetry history, power mode, cooling, and sustained "
            "run conditions before treating runtime regression as stable."
            if status != "passed"
            else "Thermal telemetry is within configured thresholds."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_runtime_queue_telemetry_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any] | None:
    if not metrics.get("runtime_telemetry_context_present"):
        return None
    queue_depth = metrics.get("candidate_queue_depth")
    if not isinstance(queue_depth, (int, float)) or isinstance(queue_depth, bool):
        return None

    severity = _rate_severity(
        value=float(queue_depth),
        review=thresholds["edgeenv_telemetry_queue_depth_review"],
        blocked=thresholds["edgeenv_telemetry_queue_depth_blocked"],
    )
    status = _edgeenv_runtime_context_status(severity)
    return build_evidence_item(
        evidence_type="runtime_queue_overload",
        metric_name="candidate_queue_depth",
        observed_value=queue_depth,
        baseline_value=metrics.get("baseline_queue_depth"),
        threshold=thresholds["edgeenv_telemetry_queue_depth_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity=severity,
        status=status,
        why_it_matters=(
            "Queue depth in runtime telemetry is operation context for regression "
            "review because backlog can inflate latency and hide workload pressure."
        ),
        suspected_causes=[
            "queue_overload",
            "scheduler_contention",
            "input_rate_exceeds_runtime_capacity",
        ]
        if status != "passed"
        else [],
        recommendation=(
            "Inspect Orchestrator queue policy, target FPS, drop/fallback behavior, "
            "and runtime telemetry before deployment."
            if status != "passed"
            else "Queue depth telemetry is within configured thresholds."
        ),
        raw_context={"edgeenv_regression": metrics},
    )


def _edgeenv_runtime_context_status(severity: str) -> str:
    if severity == "high":
        return "failed"
    if severity == "medium":
        return "warning"
    return "passed"


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def _producer_lineage_shape_valid(
    *,
    device_local_sources: Any,
    producer_sources: Any,
    sources_by_task: Any,
    stage_by_task: Any,
    producer_event_count: Any,
    device_local_event_count: Any,
    device_local_task_count: Any,
    operation_context_role: Any,
) -> bool:
    device_sources = _string_list(device_local_sources)
    all_sources = set(_string_list(producer_sources))
    task_sources_map = _mapping(sources_by_task)
    stage_map = _mapping(stage_by_task)
    task_sources: set[str] = set()
    for task_name, sources in task_sources_map.items():
        if not isinstance(task_name, str) or not task_name:
            return False
        source_list = _string_list(sources)
        if not source_list:
            return False
        task_sources.update(source_list)
    if not device_sources:
        return False
    if not set(device_sources).issubset(all_sources):
        return False
    if not set(device_sources).issubset(task_sources):
        return False
    if not stage_map:
        return False
    for task_name, stage in stage_map.items():
        if not isinstance(task_name, str) or not task_name:
            return False
        if not isinstance(stage, str) or not stage:
            return False
    return (
        operation_context_role == "supplemental"
        and _positive_number(producer_event_count)
        and _positive_number(device_local_event_count)
        and _positive_number(device_local_task_count)
    )


def _producer_lineage_guard_alignment_valid(
    *,
    declared_by: Any,
    producer_lineage_evidence_type: Any,
    operation_evidence_candidates: Any,
    orchestrator_is_final_decision_owner: Any,
    lab_is_final_decision_owner: Any,
) -> bool:
    operation_candidates = set(_string_list(operation_evidence_candidates))
    required_operation_candidates = set(
        EDGEENV_ORCHESTRATOR_OPERATION_EVIDENCE_CANDIDATES
    )
    producer_lineage_type_matches = (
        producer_lineage_evidence_type
        == EDGEENV_ORCHESTRATOR_PRODUCER_LINEAGE_EVIDENCE_TYPE
    )
    return (
        declared_by == "orchestrator"
        and producer_lineage_type_matches
        and required_operation_candidates.issubset(operation_candidates)
        and orchestrator_is_final_decision_owner is False
        and lab_is_final_decision_owner is True
    )


def _edgeenv_regression_pass_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    return build_evidence_item(
        evidence_type="edgeenv_runtime_regression_health",
        metric_name="edgeenv_runtime_regression_signal_count",
        observed_value=0,
        baseline_value=None,
        threshold=0,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="low",
        status="passed",
        why_it_matters=(
            "EdgeEnv regression report was comparable and did not provide runtime "
            "regression signals above AIGuard review thresholds."
        ),
        suspected_causes=[],
        recommendation="No runtime anomaly evidence was produced from the EdgeEnv report.",
        raw_context={"edgeenv_regression": metrics},
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

    if _runtime_operation_summary_has_review_signal(metrics):
        evidence.append(_runtime_operation_summary_evidence(metrics, thresholds))

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
    if metrics.get("remote_runtime_event_summary_present") and not metrics.get(
        "remote_runtime_event_summary_consistent"
    ):
        evidence.append(_remote_runtime_event_summary_mismatch_evidence(metrics))

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


def _remote_runtime_event_summary_mismatch_evidence(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    errors = _string_list(metrics.get("remote_runtime_event_summary_errors"))
    return build_evidence_item(
        evidence_type="remote_runtime_event_summary_mismatch",
        metric_name="remote_runtime_event_summary_errors",
        observed_value=len(errors),
        baseline_value=0,
        threshold=0,
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium",
        status="warning",
        why_it_matters=(
            "AIGuard consumes Orchestrator's compact remote runtime event summary "
            "as supplemental operation evidence. If the compact summary does not "
            "match the event list or operation summary, downstream reports may "
            "misread fallback or remote execution status."
        ),
        suspected_causes=errors,
        recommendation=(
            "Regenerate the remote dispatch artifact from the current "
            "InferEdgeOrchestrator starter so runtime_events, "
            "remote_operation_summary, and remote_runtime_event_summary align."
        ),
        raw_context={"remote_dispatch": metrics},
    )


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
                "runtime_retryable_error"
                if metrics.get("runtime_error_retryable")
                else None,
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            (
                f"Follow Runtime retry hint: {metrics.get('retry_hint')} "
                "and treat this as retryable Runtime-side failure evidence for Lab review."
            )
            if metrics.get("retry_hint") and metrics.get("runtime_error_retryable")
            else f"Follow Runtime retry hint: {metrics.get('retry_hint')}."
            if metrics.get("retry_hint")
            else "Inspect Runtime error classification and event log before deployment."
        ),
        raw_context={"runtime_operation": metrics},
    )


def _runtime_operation_summary_has_review_signal(metrics: dict[str, Any]) -> bool:
    recommended_action = metrics.get("runtime_operation_recommended_action")
    if isinstance(recommended_action, str) and recommended_action not in {"", "none"}:
        return True
    return bool(metrics.get("runtime_operation_risk_labels"))


def _runtime_operation_summary_evidence(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    risk_labels = _string_list(metrics.get("runtime_operation_risk_labels"))
    evidence_gaps = _string_list(metrics.get("runtime_operation_evidence_gaps"))
    recommended_action = metrics.get("runtime_operation_recommended_action")
    health_reason = metrics.get("runtime_operation_health_reason")
    summary_signal_count = max(
        len(risk_labels),
        1
        if isinstance(recommended_action, str)
        and recommended_action not in {"", "none"}
        else 0,
    )
    return build_evidence_item(
        evidence_type="runtime_operation_health",
        metric_name="runtime_operation_summary_risk_count",
        observed_value=summary_signal_count,
        baseline_value=None,
        threshold=thresholds["runtime_error_severity_review"],
        delta=None,
        delta_pct=None,
        increase_factor=None,
        severity="medium",
        status="warning",
        why_it_matters=(
            "Runtime provided an operation summary with risk labels or a review "
            "action. AIGuard preserves this deterministic Runtime-side warning "
            "without making the final deployment decision."
        ),
        suspected_causes=[
            cause
            for cause in [
                health_reason,
                *risk_labels,
                *evidence_gaps,
            ]
            if isinstance(cause, str) and cause
        ],
        recommendation=(
            str(recommended_action)
            if isinstance(recommended_action, str) and recommended_action
            else "Review Runtime operation summary before Lab deployment decision."
        ),
        raw_context={
            "runtime_operation": metrics,
            "runtime_operation_summary": metrics.get("runtime_operation_summary"),
            "decision_owner": metrics.get("runtime_operation_decision_owner"),
            "scheduler_owner": metrics.get("runtime_operation_scheduler_owner"),
        },
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


def _first_string_list(*values: Any) -> list[str]:
    for value in values:
        strings = _string_list(value)
        if strings:
            return strings
    return []


def _tegrastats_timeline(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("tegrastats_timeline")
    return value if isinstance(value, dict) else {}


def _worker_health_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("worker_health_snapshot")
    return value if isinstance(value, dict) else {}


def _queue_state_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("queue_state_summary")
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


def _runtime_operation_summary(runtime_result: dict[str, Any]) -> dict[str, Any]:
    value = runtime_result.get("runtime_operation_summary")
    return value if isinstance(value, dict) else {}


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


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_string_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    values: list[str] = []
    for item in value:
        if not _non_empty_string(item):
            continue
        normalized = item.strip()
        if normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def _invalid_string_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if not _non_empty_string(item)]


def _non_negative_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return 0.0


def _optional_non_negative_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return None


def _optional_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _max_optional_number(*values: float | None) -> float | None:
    numeric_values = [value for value in values if value is not None]
    return max(numeric_values) if numeric_values else None


def _telemetry_number(context: dict[str, Any], *paths: str) -> float | None:
    for path in paths:
        value = _nested_value(context, path)
        number = _optional_number(value)
        if number is not None:
            return number
    return None


def _telemetry_bool(context: dict[str, Any], *paths: str) -> bool | None:
    for path in paths:
        value = _nested_value(context, path)
        if isinstance(value, bool):
            return value
    return None


def _telemetry_coverage_payload(context: dict[str, Any]) -> dict[str, Any]:
    coverage = context.get("telemetry_coverage")
    if isinstance(coverage, dict):
        return coverage
    coverage = context.get("history_telemetry_coverage")
    if isinstance(coverage, dict):
        return coverage
    return {}


def _history_telemetry_coverage_by_role(
    context: dict[str, Any],
    history_coverage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not history_coverage:
        return {}
    role_by_run_id: dict[str, str] = {}
    for role in ("baseline", "candidate"):
        run_context = _mapping(context.get(role))
        run_id = run_context.get("run_id")
        if isinstance(run_id, str) and run_id:
            role_by_run_id[run_id] = role

    coverage_by_role: dict[str, dict[str, Any]] = {}
    run_summaries = history_coverage.get("run_summaries")
    if isinstance(run_summaries, list):
        for item in run_summaries:
            if not isinstance(item, dict):
                continue
            run_id = item.get("run_id")
            role = role_by_run_id.get(run_id) if isinstance(run_id, str) else None
            if role is not None:
                coverage_by_role[role] = item
    missing_field_runs = history_coverage.get("missing_field_runs")
    if isinstance(missing_field_runs, list):
        for item in missing_field_runs:
            if not isinstance(item, dict):
                continue
            run_id = item.get("run_id")
            role = role_by_run_id.get(run_id) if isinstance(run_id, str) else None
            if role is None:
                continue
            coverage = coverage_by_role.setdefault(role, {"run_id": run_id})
            if "missing_fields" not in coverage:
                coverage["missing_fields"] = _coverage_missing_fields(item)
            if "missing_field_count" not in coverage:
                coverage["missing_field_count"] = item.get("missing_field_count")
            if "missing_telemetry_is_failure" not in coverage:
                coverage["missing_telemetry_is_failure"] = item.get(
                    "missing_telemetry_is_failure"
                )
    return coverage_by_role


def _history_telemetry_seed_by_role(
    context: dict[str, Any],
    history: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    by_role: dict[str, dict[str, Any]] = {}
    role_by_run_id: dict[str, str] = {}
    for role in ("baseline", "candidate"):
        run_context = _mapping(context.get(role))
        run_id = run_context.get("run_id")
        if isinstance(run_id, str) and run_id:
            role_by_run_id[run_id] = role

    for entry in _list(history.get("runs")):
        run_id = entry.get("run_id")
        role = role_by_run_id.get(run_id) if isinstance(run_id, str) else None
        if role is None:
            continue
        seed = _mapping(entry.get("runtime_telemetry_history_seed"))
        if seed:
            by_role[role] = dict(seed)

    for role in ("baseline", "candidate"):
        run_context = _mapping(context.get(role))
        seed = _mapping(run_context.get("runtime_telemetry_history_seed"))
        if seed:
            by_role[role] = dict(seed)
    return by_role


def _history_seed_run_config_marker_labels(
    *,
    baseline_history_seed_run_config: dict[str, Any],
    candidate_history_seed_run_config: dict[str, Any],
) -> list[str]:
    labels: list[str] = []
    if (
        baseline_history_seed_run_config
        and baseline_history_seed_run_config == candidate_history_seed_run_config
    ):
        marker_label = _history_seed_run_config_marker_label(
            baseline_history_seed_run_config
        )
        if marker_label:
            return [f"baseline/candidate={marker_label}"]
    if baseline_history_seed_run_config:
        marker_label = _history_seed_run_config_marker_label(
            baseline_history_seed_run_config
        )
        if marker_label:
            labels.append(f"baseline={marker_label}")
    if candidate_history_seed_run_config:
        marker_label = _history_seed_run_config_marker_label(
            candidate_history_seed_run_config
        )
        if marker_label:
            labels.append(f"candidate={marker_label}")
    return labels


def _history_seed_run_config_markers(
    run_config: dict[str, Any],
) -> dict[str, Any]:
    markers: dict[str, Any] = {}
    shape_label = _history_seed_run_config_shape_label(run_config)
    if shape_label:
        markers["shape"] = shape_label
    for field in RUN_CONFIG_MARKER_FIELDS:
        if field in run_config:
            markers[field] = run_config.get(field)
    return markers


def _history_seed_run_config_marker_label(run_config: dict[str, Any]) -> str:
    markers = _history_seed_run_config_markers(run_config)
    parts = [f"{key}={value}" for key, value in markers.items()]
    return ", ".join(parts)


def _task_event_rollup_affected_tasks(
    *,
    task_summary: dict[str, Any],
    tasks_with_deadline_miss: list[str],
    tasks_with_fallback: list[str],
    tasks_with_scheduler_delay: list[str],
) -> list[str]:
    affected = set(tasks_with_deadline_miss)
    affected.update(tasks_with_fallback)
    affected.update(tasks_with_scheduler_delay)
    for task_name, summary in task_summary.items():
        if not isinstance(task_name, str) or not isinstance(summary, dict):
            continue
        if _optional_number(summary.get("deadline_missed_count")):
            affected.add(task_name)
        if _optional_number(summary.get("fallback_decision_count")):
            affected.add(task_name)
        if _optional_number(summary.get("scheduler_delay_event_count")):
            affected.add(task_name)
        if _task_event_rollup_reason_counts({task_name: summary}):
            affected.add(task_name)
    return sorted(affected)


def _task_event_rollup_reason_counts(
    task_summary: dict[str, Any],
) -> dict[str, float]:
    reason_counts: dict[str, float] = {}
    for summary in task_summary.values():
        if not isinstance(summary, dict):
            continue
        for field in (
            "reason_counts",
            "policy_decision_reason_counts",
            "drop_reason_counts",
        ):
            counts = _mapping(summary.get(field))
            for reason, count in counts.items():
                if not isinstance(reason, str) or not reason:
                    continue
                reason_counts[reason] = reason_counts.get(reason, 0.0) + (
                    _optional_number(count) or 0.0
                )
    return {reason: count for reason, count in reason_counts.items() if count > 0}


def _history_seed_run_config_shape_label(run_config: dict[str, Any]) -> str:
    batch = run_config.get("batch")
    height = run_config.get("height")
    width = run_config.get("width")
    if batch is None and height is None and width is None:
        return ""
    return f"{batch or '-'}x{height or '-'}x{width or '-'}"


def _history_missing_field_runs(history_coverage: dict[str, Any]) -> list[dict[str, Any]]:
    missing_field_runs = history_coverage.get("missing_field_runs")
    if not isinstance(missing_field_runs, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in missing_field_runs:
        if not isinstance(item, dict):
            continue
        run_id = item.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            continue
        normalized.append(
            {
                "run_id": run_id,
                "missing_fields": _coverage_missing_fields(item),
                "missing_field_count": item.get("missing_field_count"),
                "missing_telemetry_is_failure": item.get(
                    "missing_telemetry_is_failure"
                ),
            }
        )
    return normalized


def _history_missing_orchestrator_contexts(
    history: dict[str, Any],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for item in _list(history.get("missing_telemetry")):
        if not isinstance(item, dict):
            continue
        run_id = item.get("run_id")
        context = _mapping(item.get("orchestrator_operation_context"))
        if not context:
            continue
        preserved = dict(context)
        if isinstance(run_id, str) and run_id:
            preserved.setdefault("run_id", run_id)
        contexts.append(preserved)
    return contexts


def _coverage_missing_fields(coverage: dict[str, Any]) -> list[str]:
    missing_fields = coverage.get("missing_fields")
    if not isinstance(missing_fields, list):
        return []
    return [str(item) for item in missing_fields if isinstance(item, str)]


def _nested_value(context: dict[str, Any], path: str) -> Any:
    value: Any = context
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _execution_sequence_order_valid(
    baseline_sequence_id: float | None,
    candidate_sequence_id: float | None,
) -> bool | None:
    if baseline_sequence_id is None or candidate_sequence_id is None:
        return None
    return candidate_sequence_id >= baseline_sequence_id


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
            if any(str(item.get("type", "")).startswith("runtime_telemetry") for item in warnings):
                return "Runtime telemetry context has evidence gaps that require review."
            return "Runtime scheduling evidence requires review."
        return "Runtime scheduling evidence is within configured thresholds."
    first = max(failed, key=lambda item: _severity_rank(item.get("severity")))
    if first.get("type") in {
        "runtime_latency_regression",
        "runtime_throughput_regression",
        "runtime_memory_regression",
    }:
        return (
            "EdgeEnv same-condition runtime regression evidence requires "
            "deterministic AIGuard review."
        )
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


def _producer_sources_by_task(queue_state_summary: dict[str, Any]) -> dict[str, list[str]]:
    raw_value = queue_state_summary.get("producer_sources_by_task")
    if not isinstance(raw_value, dict):
        return {}
    result: dict[str, list[str]] = {}
    for task_name, sources in raw_value.items():
        if not isinstance(task_name, str) or not task_name:
            continue
        result[task_name] = _string_list(sources)
    return result


def _queue_pressure_reason_is_concerning(reason: Any) -> bool:
    if not isinstance(reason, str) or not reason:
        return False
    return any(token in reason for token in ("exceeded", "elevated", "overloaded"))


def _queue_pressure_reason_is_blocking(reason: Any) -> bool:
    if not isinstance(reason, str) or not reason:
        return False
    return "exceeded" in reason or "overloaded" in reason


def _queue_pressure_suspected_causes(
    queue_pressure_reason: str | None,
    pressure_counts: dict[str, int],
) -> list[str]:
    causes: list[str] = []
    for reason in [queue_pressure_reason, *pressure_counts.keys()]:
        if not isinstance(reason, str):
            continue
        if "backlog" in reason and "queue_backlog" not in causes:
            causes.append("queue_backlog")
        if "threshold" in reason and "overload_threshold_pressure" not in causes:
            causes.append("overload_threshold_pressure")
        if "elevated" in reason and "queue_pressure_elevated" not in causes:
            causes.append("queue_pressure_elevated")
    return causes or ["queue_pressure_context"]


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
    primary_reason_counts: dict[str, int] = {}
    operation_risk_counts: dict[str, int] = {}
    producer_sources: list[str] = []
    device_local_worker_count = 0
    for worker_id, worker in workers.items():
        if not isinstance(worker, dict):
            continue
        health_reasons = _string_list(worker.get("health_reasons"))
        for reason in health_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        primary_reason = _first_string(worker.get("primary_health_reason"))
        if primary_reason:
            primary_reason_counts[primary_reason] = (
                primary_reason_counts.get(primary_reason, 0) + 1
            )
        operation_risk = _first_string(worker.get("operation_risk_summary"))
        if operation_risk:
            operation_risk_counts[operation_risk] = (
                operation_risk_counts.get(operation_risk, 0) + 1
            )
        worker_producer_sources = _string_list(worker.get("producer_sources"))
        for source in worker_producer_sources:
            if source not in producer_sources:
                producer_sources.append(source)
        device_local_validation = _bool_value(worker.get("device_local_validation"))
        if device_local_validation:
            device_local_worker_count += 1
        worker_metrics.append(
            {
                "worker_id": worker_id,
                "agent_id": worker.get("agent_id") or worker_id,
                "agent_type": worker.get("agent_type"),
                "health_state": worker.get("health_state"),
                "health_reasons": health_reasons,
                "primary_health_reason": primary_reason,
                "operation_risk_summary": operation_risk,
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
                "device_local_validation": device_local_validation,
                "producer_stage": worker.get("producer_stage"),
                "producer_sources": worker_producer_sources,
                "producer_event_count": _non_negative_number(
                    worker.get("producer_event_count")
                ),
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
        "primary_health_reason_counts": primary_reason_counts,
        "operation_risk_summary_counts": operation_risk_counts,
        "device_local_worker_count": device_local_worker_count,
        "producer_sources": producer_sources,
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
