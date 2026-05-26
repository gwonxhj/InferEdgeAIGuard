# Runtime Reliability Signals

InferEdgeAIGuard can read InferEdgeOrchestrator's
`inferedge-orchestration-summary-v1` output and InferEdge Runtime's additive
`inferedge-runtime-result-v1` operation evidence fields, then convert the
deterministic signals into the existing `inferedge-aiguard-diagnosis-v1` guard
analysis contract.

This is an optional evidence path. AIGuard does not become the deployment
decision owner; InferEdgeLab still owns the final deployment decision.

## Input

Expected input:

- `schema_version: inferedge-orchestration-summary-v1`
- `agent_runtime_summary.totals`
- `policy_decision_log` or `policy_decisions`
- optional `drop_events` / `overload_events`
- optional `sustained_runtime_summary`
- optional `queue_depth_timeline`
- optional `latency_timeline`
- optional `multi_workload_sustained_summary`
- optional `tegrastats_timeline`
- optional `worker_health_snapshot`
- optional `runtime_event_summary`
- optional `runtime_event_timeline`
- optional embedded `runtime_result` / `runtime_results`

The summary is produced by InferEdgeOrchestrator's 3-agent scheduling and
sustained workload demos. It connects Forge `agent_manifest.json` and Runtime
`result.agent` metadata to runtime policy evidence. AIGuard interprets only the
deterministic signals that are present in the summary; it does not infer real
hardware bottlenecks unless those signals are provided by runtime telemetry.

Runtime result input is also supported directly when the JSON includes:

- `schema_version: inferedge-runtime-result-v1`
- optional `runtime_health_snapshot`
- optional `runtime_error_classification`
- optional `runtime_events`
- optional `runtime_operation_summary`

AIGuard treats these fields as Runtime-provided operation evidence. It does not
guess a root cause from missing logs.

EdgeEnv runtime regression reports are also supported when the JSON includes:

- `regression_detected`
- `mode`
- `comparable`
- `evidence.mean_delta_pct`
- `evidence.p95_delta_pct`
- `evidence.p99_delta_pct`
- `evidence.fps_delta_pct`
- `evidence.memory_peak_delta_pct`
- optional `runtime_telemetry_context`
- optional `runtime_telemetry_context.<run>.orchestrator_operation_context`

EdgeEnv remains the comparability and regression calculation owner. AIGuard
only turns same-condition EdgeEnv regression, telemetry coverage, and preserved
Orchestrator operation context signals into deterministic diagnosis evidence for
Lab review.

## Evidence Mapping

| Evidence type | Metric | Review threshold | Block threshold | Meaning |
|---|---|---:|---:|---|
| `repeated_deadline_miss` | `deadline_miss_rate` | `>= 0.05` | `>= 0.20` | Agent tasks miss latency budgets under load |
| `excessive_drop_rate` | `drop_rate` | `>= 0.20` | `>= 0.50` | Work is being dropped to protect the system |
| `fallback_overuse` | `fallback_rate` | `>= 0.20` | `>= 0.50` | Fallback path is used too often |
| `queue_backlog_risk` | `queue_backlog_policy_decision_count` | `>= 1` | n/a | Scheduler had to intervene because backlog grew |
| `sustained_overload_risk` | `max_total_queue_depth` | `>= 3` | `>= 8` | Sustained queue depth indicates multi-agent overload pressure |
| `profiled_workload_pressure` | `profiled_workload_risk_count` | `>= 1` | `>= 3` | Sustained workload profiles show which runtime loops are under pressure |
| `thermal_resource_pressure` | `max_temperature_c` | `>= 70.0` | `>= 85.0` | Tegrastats indicates thermal/resource pressure during sustained execution |
| `worker_health_degradation` | `degraded_or_constrained_worker_count` | `>= 1` | `>= 3` degraded workers or any constrained worker | Worker health snapshot explains degraded/constrained runtime loops |
| `scheduler_delay_pattern` | `scheduler_delay_event_count` | `>= 1` | `>= 3` | Runtime event timeline shows tasks delayed across scheduler cycles |
| `queue_pressure_context` | `queue_pressure_reason_count` | `>= 1` concerning reason | n/a | Queue pressure reason explains whether backlog was near or beyond the overload threshold |
| `worker_operation_risk_summary` | `worker_operation_risk_count` | `>= 1` | `>= 3` | Worker operation risk summary identifies latency/fallback/drop/queue-pressure risk labels |
| `device_local_operation_context` | `device_local_event_count` | `>= 1` when device-local tasks exist | n/a | Device-local starter records local producer sources and runtime event coverage |
| `runtime_backend_unavailable` | `engine_available` | `0` | n/a | Runtime could not confirm backend/engine availability |
| `runtime_latency_budget_overrun` | `latency_budget_exceeded` | `true` | n/a | Runtime exceeded the latency budget or missed a deadline |
| `runtime_error_classification` | `runtime_error_severity` | present | n/a | Runtime classified an execution warning/error with a retry hint |
| `runtime_operation_health` | `runtime_operation_summary_risk_count` | `>= 1` risk label or review action | n/a | Runtime provided operation summary risk labels, evidence gaps, or a review action |
| `runtime_thermal_memory_evidence_missing` | `thermal_memory_evidence_available` | `false` on Jetson | n/a | Jetson result lacks thermal/memory context for sustained review |
| `runtime_latency_regression` | `p99_delta_pct` / `mean_delta_pct` / `p95_delta_pct` | p99 `>= 25.0` or mean/p95 `>= 15.0` | n/a | EdgeEnv same-condition regression indicates latency drift or tail latency spike |
| `runtime_throughput_regression` | `fps_delta_pct` | `<= -20.0` | n/a | EdgeEnv same-condition regression indicates FPS drop |
| `runtime_memory_regression` | `memory_peak_delta_pct` | `>= 30.0` | n/a | EdgeEnv same-condition regression indicates memory headroom risk |
| `runtime_telemetry_context_coverage` | `runtime_telemetry_evidence_gap_count` | `>= 1` | n/a | EdgeEnv telemetry context is present but baseline/candidate coverage, history entries, or `telemetry_coverage.missing_fields` have gaps |
| `runtime_telemetry_replay_context` | `runtime_telemetry_history_missing_run_count` | `>= 1` or baseline/candidate sequence order mismatch | n/a | EdgeEnv telemetry history replay has missing telemetry or ordering concerns |
| `runtime_history_seed_run_config_traceability` | `runtime_history_seed_run_config_count` | warning when preserved Runtime history seeds lack run_config markers | n/a | EdgeEnv preserved Runtime history seed run_config markers as replay/comparability traceability evidence |
| `edgeenv_orchestrator_producer_lineage` | `device_local_producer_context_count` | warning when preserved Orchestrator context lacks device-local producer metadata | n/a | EdgeEnv preserved device-local Orchestrator producer lineage as traceability evidence |
| `runtime_thermal_instability` | `candidate_max_temperature_c` / `candidate_throttling_detected` | temperature `>= 70.0` or throttling `true` | temperature `>= 85.0` | EdgeEnv telemetry or attached Orchestrator feed indicates thermal/throttling pressure |
| `runtime_queue_overload` | `candidate_queue_depth` | `>= 3.0` | `>= 8.0` | EdgeEnv telemetry or attached Orchestrator feed indicates queue backlog pressure |
| `edgeenv_comparability_guardrail` | `edgeenv_comparable` | skipped when not comparable or not same-condition | n/a | AIGuard refuses to reinterpret non-comparable EdgeEnv reports as same-condition regression |

These thresholds are intentionally deterministic and local-first. They are
review signals, not production SLOs.

When EdgeEnv provides
`runtime_telemetry_context.history.telemetry_coverage`, AIGuard prefers that
producer-side replay summary for `baseline_telemetry_coverage_ratio`,
`candidate_telemetry_coverage_ratio`, missing field runs, and
`missing_telemetry_is_failure` in the evidence `raw_context`. If the history
summary is absent, AIGuard falls back to per-run `runtime_telemetry.coverage`.
Missing coverage fields become deterministic warning context only; AIGuard does
not convert them into a final deployment decision.

## Sustained Scenario Fields

When Orchestrator emits sustained demo telemetry, AIGuard also preserves:

- `scenario_mode` from `run.scenario_mode` or `sustained_runtime_summary`
- `max_total_queue_depth` from `sustained_runtime_summary` or
  `queue_depth_timeline`
- `policy_decision_reasons` from `decision_reason`, `reason`, or `decision`
- `queue_depth_sample_count`
- `latency_sample_count`

This lets the report explain not only that work was dropped, but also why the
scheduler intervened and whether queue depth kept growing under sustained
multi-agent load.

## Orchestrator Operation Telemetry Fields

When Orchestrator emits Phase 2 operation telemetry, AIGuard preserves and
reasons over:

- `worker_health_snapshot.health_state_counts`
- `worker_health_snapshot.degraded_workers`
- `worker_health_snapshot.constrained_workers`
- per-worker `health_reasons`, `drop_rate`, `deadline_miss_rate`,
  `fallback_rate`, `queue_pressure_ratio`, `runtime_loop`, and
  `ingress_profile`
- per-worker `primary_health_reason`, `operation_risk_summary`,
  `device_local_validation`, `producer_stage`, `producer_sources`, and
  `producer_event_count`
- `queue_state_summary.queue_pressure_reason`
- `queue_state_summary.max_pressure_task`
- `queue_state_summary.device_local_producer_sources`
- `queue_state_summary.producer_sources_by_task`
- `runtime_event_summary.policy_decision_reason_counts`
- `runtime_event_summary.drop_reason_counts`
- `runtime_event_summary.reason_counts`
- `runtime_event_summary.queue_pressure_reason_counts`
- `runtime_event_summary.fallback_decision_count`
- `runtime_event_summary.scheduler_delay_event_count`
- `runtime_event_summary.producer_sources`
- `runtime_event_summary.producer_event_count`
- `runtime_event_summary.device_local_event_count`
- `runtime_event_timeline[].scheduler_delay_cycles`
- `runtime_event_timeline[].queue_wait_ms`

`worker_health_degradation` is emitted when Orchestrator marks one or more
workers as degraded or constrained. Degraded workers are warning evidence;
constrained workers or a high degraded count increase severity. This keeps
AIGuard as an evidence provider while letting Lab and reviewers see which
runtime loops were affected.

`scheduler_delay_pattern` is emitted only when scheduler delay events are
observed. Policy and drop reason counts are also preserved in raw context so the
warning can explain whether delay was associated with backlog, load shedding,
fallback, or another scheduler reason.

`queue_pressure_context` is emitted when Orchestrator reports a concerning
queue pressure reason, such as threshold exceeded or elevated pressure. AIGuard
preserves the pressure reason, max pressure task, policy reason counts, and drop
reason counts as review evidence without inferring a root cause.

`worker_operation_risk_summary` is emitted when Orchestrator records non-healthy
operation risk labels such as `latency_or_fallback_risk` or
`drop_or_queue_pressure_risk`. It complements `worker_health_degradation` by
preserving the concise per-worker risk labels intended for Lab reports.

`device_local_operation_context` is emitted when device-local tasks are present.
It passes when Orchestrator records producer sources and device-local runtime
event coverage, and warns when device-local tasks exist but producer/event
coverage is missing. This is local starter evidence, not proof of long-running
device operation.

## Multi-Workload Sustained Fields

When Orchestrator emits `multi_workload_sustained_summary`, AIGuard preserves
and reasons over:

- `workload_profiles` for Vision / Voice-Command / Safety-Monitor profiles
- `runtime_loop` such as `yolo_detection_loop`, `whisper_command_burst`, or
  `safety_monitor_loop`
- `ingress_profile` such as `frame_queue`, `fastapi_concurrent_request`, or
  `periodic_monitor`
- per-workload `dropped`, `deadline_missed`, `fallback_used`, and
  `max_queue_backlog`
- `observed_runtime_signals` such as executed/drop/deadline/fallback counts,
  policy decision reasons, max total queue depth, `local_profile_adapter_count`,
  `local_profile_elapsed_ms`, and `local_profile_kinds`

If any workload profile shows dropped work, deadline misses, fallback usage, or
queue backlog, AIGuard emits `profiled_workload_pressure`. When Orchestrator
uses lightweight local CPU profile adapters, AIGuard preserves adapter count,
elapsed profile time, implementation, work units, and profile kinds in the raw
context. This explains which
runtime loop was affected instead of only reporting an aggregate drop or
deadline miss rate.

## Tegrastats Fields

When Orchestrator includes `tegrastats_timeline.summary`, AIGuard records:

- `tegrastats_sample_count`
- `max_temperature_c`
- `max_gpu_percent`
- `max_ram_used_mb`

`thermal_resource_pressure` is emitted only when temperature evidence is
present. This keeps synthetic local demos compatible while allowing Jetson
sustained runs to explain thermal/resource degradation signals.

## Runtime Operation Fields

When Runtime emits additive health/error/event fields, AIGuard preserves and
reasons over:

- `runtime_health_snapshot.engine_available`
- `runtime_health_snapshot.latency_budget_ms`
- `runtime_health_snapshot.latency_budget_exceeded`
- `runtime_health_snapshot.deadline_missed`
- `runtime_health_snapshot.thermal_memory_evidence_available`
- `runtime_error_classification.category`
- `runtime_error_classification.severity`
- `runtime_error_classification.retryable`
- `runtime_error_classification.retry_hint`
- `runtime_events[].retryable`
- `runtime_events[].latency_budget_exceeded`
- `runtime_events[].deadline_missed`
- `runtime_operation_summary.health_reason`
- `runtime_operation_summary.risk_labels`
- `runtime_operation_summary.evidence_gaps`
- `runtime_operation_summary.recommended_action`
- `runtime_operation_summary.decision_owner`
- `runtime_operation_summary.scheduler_owner`

These fields are interpreted as operation evidence. For example, a Runtime
result with `engine_available: false`, `latency_budget_exceeded: true`, and a
retryable `retry_hint` produces deterministic guard evidence such as
`runtime_backend_unavailable`, `runtime_latency_budget_overrun`, and
`runtime_error_classification`. AIGuard preserves `retryable` as deterministic
Runtime-side failure evidence for Lab review; it does not perform retries or
claim production worker behavior.
When `runtime_operation_summary` is present, AIGuard preserves Runtime-provided
`risk_labels`, `evidence_gaps`, and `recommended_action` as
`runtime_operation_health` warning evidence while keeping Lab as the final
deployment decision owner.

## CLI

```bash
python -m inferedge_aiguard.cli reason-orchestration \
  --input reports/agent_orchestration_summary.json
```

Runtime operation results can be analyzed directly:

```bash
python -m inferedge_aiguard.cli reason-runtime \
  --input reports/runtime_result.json
```

The unified `reason` command also auto-routes Orchestrator summaries:

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/agent_orchestration_summary.json
```

It also auto-routes Runtime results that include `schema_version:
inferedge-runtime-result-v1` or the additive Runtime operation fields.

Remote dispatch starter results can also be analyzed directly:

```bash
python -m inferedge_aiguard.cli reason-remote-dispatch \
  --input reports/remote_dispatch_result.json
```

The unified `reason` command auto-routes `schema_version:
inferedge-remote-dispatch-result-v1` as well. AIGuard interprets worker
selection status and explicit HTTP/SSH starter execution status as
`remote_execution_plan_only`, `remote_execution_starter_success`, or
`remote_execution_failed` evidence. If Orchestrator includes additive
`fallback_execution_result` evidence, AIGuard also emits
`remote_execution_recovered_by_fallback` or `remote_fallback_execution_failed`.
Recovered fallback remains review evidence because it proves the resilience path
worked, but also shows that the primary worker path was unstable. This remains
starter evidence, not a claim of production remote execution.

When Orchestrator includes additive `remote_runtime_event_summary`, AIGuard
preserves it in deterministic raw context and checks that its compact event,
status, error, fallback, and final-status counts match the original
`runtime_events` / `remote_operation_summary`. It also preserves the
Lab-facing `runtime_event_count` alias and the
`operation_boundary: remote dispatch starter evidence only` marker so the
starter boundary remains visible downstream. A mismatch becomes
`remote_runtime_event_summary_mismatch` warning evidence so downstream Lab
reports do not accidentally trust stale compact summaries.

EdgeEnv runtime regression reports can be analyzed directly:

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input reports/edgeenv_runtime_regression.json
```

The unified `reason` command auto-routes EdgeEnv regression reports as well:

```bash
python -m inferedge_aiguard.cli reason \
  --input reports/edgeenv_runtime_regression.json
```

For the Runtime Intelligence chain smoke, AIGuard can also export the
precomputed artifact that Lab ingests as optional evidence:

```bash
python -m inferedge_aiguard.cli reason-edgeenv-regression \
  --input examples/runtime_intelligence/edgeenv_runtime_regression_with_orchestrator_feed.json \
  --save-json examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
python -m inferedge_aiguard.cli check-edgeenv-handoff-alignment \
  --edgeenv-handoff reports/edgeenv_runtime_intelligence_lab_handoff.json \
  --guard-analysis examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json
```

This path emits deterministic runtime anomaly evidence such as
`runtime_latency_regression`, `runtime_throughput_regression`,
`runtime_memory_regression`, `runtime_telemetry_context_coverage`, and
`runtime_telemetry_replay_context`, and
`edgeenv_orchestrator_producer_lineage`. If EdgeEnv preserved an
`orchestrator_operation_context` under the baseline or candidate telemetry
context, AIGuard reads queue depth, thermal, and throttling hints from that
nested context as supplemental operation evidence. It does not treat the feed as
an Orchestrator verdict, an EdgeEnv comparability gate, or a Lab deployment
decision.
AIGuard also preserves the producer `edgeenv_mapping_hint` in its deterministic
raw context, including `coverage_summary_owner=edgeenv`,
`coverage_summary_path=runtime_telemetry_context.history.telemetry_coverage`,
and `operation_context_role=supplemental`. These fields document ownership; they
do not make AIGuard recompute EdgeEnv coverage or own Lab deployment policy.
AIGuard also carries through the Orchestrator producer markers
`source_repository=InferEdgeOrchestrator`,
`artifact_role=orchestrator-supplemental-operation-context`, and
`producer_contract=inferedge-orchestrator-edgeenv-runtime-telemetry-feed-v1`
when EdgeEnv provides them. These markers keep the Lab artifact bundle traceable
without making AIGuard the Orchestrator feed producer.
When EdgeEnv preserves `candidate_context.producer`, AIGuard emits
`edgeenv_orchestrator_producer_lineage` to show device-local producer sources,
per-task source mapping, task stage mapping, and positive event/task coverage.
This is a traceability evidence item, not a new deployment decision or
comparability gate.
When the preserved Orchestrator context includes
`downstream_guard_alignment.producer_lineage_evidence_type=edgeenv_orchestrator_producer_lineage`,
AIGuard validates that marker and keeps producer-lineage reasoning separate
from queue/thermal operation evidence candidates.
When the nested candidate context also includes a producer lineage block,
AIGuard preserves `candidate_context.producer` and flattened device-local
markers such as `producer_sources`, `device_local_producer_sources`,
`producer_sources_by_task`, `producer_stage_by_task`, `producer_event_count`,
and `operation_context_role=supplemental` in
`raw_context.edgeenv_regression`. This keeps device-local input override
provenance visible to Lab without making AIGuard a registry or comparability
owner.
Candidate telemetry gaps and baseline/candidate execution sequence inversion
are preserved as EdgeEnv replay-context warnings, not recomputed
comparability decisions.
If EdgeEnv attaches an Orchestrator operation context to
`runtime_telemetry_context.history.missing_telemetry[]`, AIGuard keeps the
missing-run context run IDs, producer markers, and mapping hints in
`raw_context.edgeenv_regression`. The missing telemetry entry remains replay
evidence gap context; it is not promoted to successful Runtime telemetry or a
deployment decision.
AIGuard prefers EdgeEnv's
`runtime_telemetry_context.history.telemetry_coverage` summary for coverage
missing-field runs and uses per-run coverage only as a backward-compatible
fallback.
When EdgeEnv preserves Runtime's `runtime_telemetry_history_seed`, AIGuard keeps
the `inferedge-runtime-telemetry-history-seed-v1`, `registry_owner=edgeenv`, and
`decision_owner=lab` markers in deterministic raw context. If the seed includes
a `run_config` snapshot, AIGuard preserves compact shape, input
mode/preprocess, power mode, Jetson clocks, warmup, and repeat-run markers as
`runtime_history_seed_run_config_traceability` evidence. This only explains
replay traceability; it does not make AIGuard the registry or deployment
decision owner.
`tests/fixtures/edgeenv_regression/` mirrors the committed EdgeEnv replay
fixtures as small CLI smoke inputs.
`examples/runtime_intelligence/aiguard_runtime_operation_guard_analysis.json`
is the precomputed `guard_analysis` artifact example aligned with Lab bundle
naming. AIGuard provides runtime anomaly evidence there; it does not produce a
Lab-owned deployment decision.
`check-edgeenv-handoff-alignment` verifies that EdgeEnv's
`external_aiguard_required_evidence_types` are present in
`guard_analysis.evidence`. It also checks the handoff boundary flags that keep
AIGuard external and Lab as final decision owner. When EdgeEnv exposes
`edgeenv_report_summary.producer_lineage_guard_alignment_run_ids`, the same
gate compares that summary with AIGuard's
`edgeenv_orchestrator_producer_lineage` raw context so producer-lineage marker
handoff cannot drift silently. This is a deterministic smoke gate for artifact
alignment, not a new deployment decision path.
AIGuard does not recompute comparability; if EdgeEnv marks the report as
non-comparable or not same-condition, AIGuard emits
`edgeenv_comparability_guardrail` as skipped evidence.

## Output

The output uses the existing diagnosis report schema:

```json
{
  "schema_version": "inferedge-aiguard-diagnosis-v1",
  "guard_verdict": "blocked",
  "severity": "high",
  "primary_reason": "drop_rate indicates runtime reliability risk under orchestrated multi-agent load.",
  "evidence": [
    {
      "type": "excessive_drop_rate",
      "metric_name": "drop_rate",
      "observed_value": 0.58,
      "threshold": 0.2,
      "severity": "high",
      "status": "failed"
    },
    {
      "type": "sustained_overload_risk",
      "metric_name": "max_total_queue_depth",
      "observed_value": 6,
      "threshold": 3,
      "severity": "medium",
      "status": "failed"
    },
    {
      "type": "profiled_workload_pressure",
      "metric_name": "profiled_workload_risk_count",
      "observed_value": 2,
      "threshold": 1,
      "severity": "medium",
      "status": "failed"
    },
    {
      "type": "thermal_resource_pressure",
      "metric_name": "max_temperature_c",
      "observed_value": 76.2,
      "threshold": 70.0,
      "severity": "medium",
      "status": "failed"
    }
  ]
}
```

## Boundary

- AIGuard explains runtime reliability risk.
- Orchestrator records scheduling and policy evidence.
- Lab remains the final deployment decision owner.
- This does not add production queue/cloud orchestration or an LLM agent
  framework.
