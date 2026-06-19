# Detector Validation Matrix

Language: English | [한국어](detector_validation_matrix.ko.md)

InferEdgeAIGuard is an optional deterministic diagnosis evidence provider.
It does not make the final deployment decision. InferEdgeLab remains the
deployment decision owner and may use `guard_analysis` as one input signal.

This matrix documents how the implemented detectors are expected to behave for
the current portfolio demo cases and local-first validation workflow.

## Portfolio Demo Cases

| Case | Signal | Expected `guard_verdict` | Severity | Meaning |
|---|---|---|---|---|
| `normal_pass` | stable bbox, score, and detection count | `pass` | `low` | No deployment-risk evidence from AIGuard |
| `bbox_collapse_blocked` | near-zero area boxes increase against baseline | `blocked` | `high` | Possible bbox decoder, postprocess, or quantization issue |
| `score_saturation_blocked` | confidence scores concentrate near 0 or 1 | `blocked` | `critical` / `high` | Possible score decoder, calibration, or postprocess issue |
| `temporal_instability_review` | frame-level detection count or bbox movement is unstable | `review_required` | `medium` / `high` | Runtime output stability should be reviewed |
| `provenance_mismatch` | Forge/Runtime source or artifact identity does not match | `blocked` or Lab `error` mapping | `high` / `critical` | Candidate evidence may not describe the artifact under review |
| `edgeenv_runtime_regression` | EdgeEnv same-condition runtime regression and telemetry context | `blocked` / `suspicious` depending on evidence | `high` / `medium` | Runtime regression should be reviewed as deployment risk evidence |
| `remote_dispatch_starter` | Orchestrator remote worker selection, starter execution, fallback, and compact event-summary evidence | `review_required` / `pass` depending on starter status | `medium` / `low` | Remote dispatch remains starter evidence; it is not production remote execution or a Lab deployment decision |

## Detector Matrix

This is the high-level pass/review/block matrix that should stay visible in
README, portfolio material, and generated reports. It is a diagnosis policy,
not the final Lab deployment policy.

| Detector family | Primary evidence | Pass | Review | Block | Main report field |
|---|---|---|---|---|---|
| bbox validity | `invalid_bbox_rate` | `<= 0.05` | `> 0.05` | `> 0.20` | `evidence[].metric_name` |
| bbox collapse | `bbox_collapse_ratio` | `<= 0.05` | `> 0.05` or baseline factor `> 5x` | severe collapse or baseline factor `> 10x` | `evidence[].observed_value` |
| confidence score range | `score_range_violation_count` | `0` | n/a | `> 0` | `evidence[].severity` |
| confidence saturation | `saturation_ratio` | `< 0.70` | `>= 0.70` | `>= 0.85` with quality drift | `evidence[].observed_value` |
| calibration drift | `histogram_distance`, `mean_score_delta`, `std_score_delta`, `saturation_delta` | stable score distribution | bounded score-distribution shift | blocked only through existing score range or saturation evidence | `candidate_summary.comparison.calibration_drift` |
| detection disappearance | `detection_count_drop_pct`, `detection_disappearance_flag`, `zero_detection_frame_ratio`, `max_zero_detection_streak` | stable count | drop `>= 50%` or zero-frame streak `>= 2` | drop `>= 80%`, candidate zero detections, zero-frame ratio `> 0.30`, or zero-frame streak `>= 3` | `candidate_summary.comparison`, `candidate_summary.temporal` |
| per-class detection drift | `per_class_detection_drop_pct`, dropped class IDs | stable class counts | one baseline class drops `>= 50%` | one baseline class drops `100%` | `candidate_summary.comparison.per_class_detection_drift` |
| baseline deviation | invalid/collapse/saturation factor | near baseline | factor `> 5x` | factor `> 10x` | `evidence[].increase_factor` |
| temporal consistency | count CV, bbox center jump, class flip, disappearance streak | stable sequence | count CV `> 1.0`, class flip `> 0.30`, center jump p95 `> 0.50` image diagonal, or zero-frame streak `>= 2` | zero-frame ratio `> 0.30` or zero-frame streak `>= 3` | `candidate_summary.temporal` |
| provenance consistency | source/artifact/backend/target/precision identity | exact handoff match | warning mismatch | error mismatch | `guard_analysis.anomalies`, `guard_analysis.status` |
| EdgeEnv runtime regression | p99/mean/FPS/memory deltas, telemetry coverage, preserved Orchestrator operation context | comparable report without threshold breach | same-condition regression, telemetry gap, or operation risk summary marker | high tail-latency regression | `candidate_summary.edgeenv_regression` |
| remote dispatch starter | worker-selection, plan-only/execution status, fallback recovery, compact event-summary consistency | starter success or consistent plan-only evidence | plan-only context, failed starter, fallback recovery, or summary mismatch | n/a | `candidate_summary.remote_dispatch` |

## Implemented Detector Details

| Detector | Evidence | Threshold | Normal Expected | Problem Expected | Report Field |
|---|---|---:|---|---|---|
| bbox validity | `invalid_bbox_rate` | review `0.05`, blocked `0.20` | `pass` | `review_required` / `blocked` | `evidence[].metric_name` |
| bbox collapse | `bbox_collapse_ratio` | review `0.05`, high `0.10` | `pass` | `review_required` / `blocked` | `evidence[].type`, `evidence[].observed_value` |
| score range | `score_range_violation_count` | `> 0` | `pass` | `blocked` | `evidence[].metric_name`, `evidence[].severity` |
| score distribution | `saturation_ratio` | review `0.70`, high `0.85` | `pass` | `review_required` / `blocked` | `evidence[].observed_value` |
| calibration drift | `calibration_drift_trigger_count` | histogram `0.30`, mean `0.20`, std floor `0.05`, std delta `0.20`, saturation delta `0.30` | `pass` | `review_required` | `evidence[].type=calibration_drift`, `candidate_summary.comparison.calibration_drift` |
| detection count drift | `detection_count_drop_pct` | review `0.50`, blocked `0.80` | `pass` | `review_required` / `blocked` | `evidence[].delta_pct`, `candidate_summary.comparison` |
| detection disappearance | `detection_disappearance_flag` | blocked `1.0` | `pass` | `blocked` | `evidence[].type=detection_disappearance`, `candidate_summary.comparison` |
| per-class detection drift | `per_class_detection_drop_pct` | review `0.50`, blocked `1.0` | `pass` | `review_required` / `blocked` | `evidence[].type=per_class_detection_drift`, `candidate_summary.comparison.per_class_detection_drift` |
| baseline deviation | `invalid_bbox_rate_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| baseline deviation | `bbox_collapse_ratio_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| baseline deviation | `score_saturation_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| temporal consistency | `frame_to_frame_detection_count_cv` | review `1.0` | `pass` | `review_required` | `evidence[].metric_name`, `candidate_summary.temporal` |
| sequence disappearance | `max_zero_detection_streak` | review `2`, blocked `3` | `pass` | `review_required` / `blocked` | `evidence[].type=sequence_disappearance`, `candidate_summary.temporal.zero_detection_streaks` |
| temporal consistency | `bbox_center_jump_p95` | review `0.50` image diagonal | `pass` | `review_required` | `evidence[].observed_value` |
| temporal consistency | `class_flip_rate` | review `0.30` | `pass` | `review_required` | `evidence[].observed_value` |
| temporal consistency | `zero_detection_frame_ratio` | blocked `0.30` | `pass` | `blocked` | `candidate_summary.temporal` |
| provenance | artifact/source/backend/target/precision mismatch | exact identity expected | `pass` / `ok` | `warning` / `error` | `guard_analysis.anomalies`, `guard_analysis.status` |
| EdgeEnv regression | `p99_delta_pct` | review/high `25.0` | `pass` | `blocked` for high same-condition tail latency regression | `evidence[].type=runtime_latency_regression` |
| EdgeEnv regression | `fps_delta_pct` | review `<= -20.0` | `pass` | `review_required` | `evidence[].type=runtime_throughput_regression` |
| EdgeEnv regression | `memory_peak_delta_pct` | warning `30.0` | `pass` | `suspicious` / `review_required` | `evidence[].type=runtime_memory_regression` |
| EdgeEnv telemetry context | `runtime_telemetry_evidence_gap_count` | warning `>= 1` | `pass` | `suspicious` | `evidence[].type=runtime_telemetry_context_coverage` |
| EdgeEnv telemetry replay | `runtime_telemetry_history_missing_run_count` | warning `>= 1` or sequence order mismatch | `pass` | `suspicious` | `evidence[].type=runtime_telemetry_replay_context` |
| EdgeEnv Orchestrator producer lineage | `device_local_producer_context_count` | warning when preserved Orchestrator context lacks device-local producer metadata or `downstream_guard_alignment.producer_lineage_evidence_type=edgeenv_orchestrator_producer_lineage` | `pass` | `suspicious` | `evidence[].type=edgeenv_orchestrator_producer_lineage` |
| Remote dispatch plan-only | `execution_requested` | warning when `false` | `suspicious` | `evidence[].type=remote_execution_plan_only` |
| Remote dispatch starter failure | `remote_execution_status` / `error_category` | warning when explicit starter fails | `suspicious` | `evidence[].type=remote_execution_failed` |
| Remote dispatch fallback recovery | `fallback_recovered` | warning when fallback recovered after primary failure | `suspicious` | `evidence[].type=remote_execution_recovered_by_fallback` |
| Remote dispatch event summary | `remote_runtime_event_summary_consistent` | warning when compact summary does not match producer events | `suspicious` | `evidence[].type=remote_runtime_event_summary_mismatch` |

## Sequence Disappearance Evidence

Sequence-level disappearance is implemented as additive temporal evidence. It
records repeated zero-detection frame streaks without adding a tracking
dependency and without claiming automatic root cause. It is not LLM root-cause
inference.

| Policy item | Deterministic evidence | Review / block trigger | Boundary |
|---|---|---|---|
| repeated disappearance streak | `max_zero_detection_streak` | review `>= 2`, blocked `>= 3` | not object tracking |
| first disappearance frame | `first_zero_detection_frame_id`, `first_zero_detection_frame_index` | preserved for reviewer navigation | not a causal diagnosis |
| disappearance streak list | `zero_detection_streaks[]` with start/end frame IDs and length | preserves where repeated zero detections occurred | not a Lab deployment decision |

## Baseline Profile Stability Metadata

Saved baseline profiles include additive `profile_stability` audit metadata. It
records whether the baseline profile has enough sample and coverage context to
trust later baseline-comparison evidence such as calibration drift. This is not
a Lab deployment decision and does not change the diagnosis report schema.
This baseline profile stability layer is audit metadata, not automatic
root-cause proof.

| Field | Meaning | Boundary |
|---|---|---|
| `profile_stability.sample_count` | number of samples represented by the saved baseline profile | defaults to `1` for single-output profiles |
| `profile_stability.min_sample_count_review` | configured minimum sample count for review policy | default is `1`; stricter review workflows can raise it |
| `profile_stability.score_histogram_total_scores` | confidence scores represented by the saved score histogram | used to audit calibration drift coverage |
| `profile_stability.class_distribution_total_predictions` | detections represented by class-count metadata | used to audit per-class drift coverage |
| `profile_stability.compatibility_status` | whether the metadata came from a current profile or was backfilled for a legacy profile | legacy backfill is audit metadata, not a schema break |

If a saved profile is missing stability metadata, AIGuard backfills
`compatibility_status=legacy_profile_missing_profile_stability` in the
baseline summary so reviewers can see that the profile predates this audit
metadata.

## Calibration Drift Evidence Policy

Calibration drift is implemented as additive baseline-comparison evidence. It
compares a candidate score distribution against a known-good baseline profile
or direct baseline output. It does not infer root cause from a single output.

| Policy item | Deterministic evidence | Review trigger | Boundary |
|---|---|---|---|
| histogram shift | fixed-bin score histogram distance | histogram distance `>= 0.30` across the same output schema and class scope | not a calibrated probability proof |
| mean score shift | `mean_score_delta` from baseline profile to candidate | absolute mean score delta `>= 0.20` without matching accuracy or threshold explanation | not accuracy replacement |
| spread collapse or expansion | `std_score_delta` and candidate `std_score` | score std drops below `0.05` or changes by `>= 0.20` | not model-wide calibration certification |
| saturation drift | candidate saturation ratio minus baseline saturation ratio | saturation delta `>= 0.30` or candidate saturation ratio crosses implemented saturation thresholds | reuse confidence saturation evidence when it already blocks |

Implementation shape:

- Additive `evidence[].type=calibration_drift`; it does not change the diagnosis report schema.
- Preserve `baseline_summary.score`, `candidate_summary.score`, histogram bin
  policy, thresholds, and raw metric deltas.
- Emit `review_required` for calibration drift unless the same output also
  triggers an existing blocking detector such as score range violation or
  confidence saturation.
- Keep `suspected_causes` as review candidates, not automatic root-cause proof.
- Do not make AIGuard a Lab `deployment_decision` owner.

## Report Contract Fields

Each evidence item should preserve enough numeric context for a reviewer to
understand why AIGuard raised the signal.

Required or expected fields:

- `type`
- `metric_name`
- `observed_value`
- `baseline_value`
- `threshold`
- `delta`
- `delta_pct`
- `increase_factor`
- `severity`
- `status`
- `explanation`
- `why_it_matters`
- `suspected_causes`
- `recommendation`
- `raw_context`

`baseline_value` may be `null` for single-output validation. Baseline comparison
reports should fill it whenever a known-good baseline is available.

## Interpretation Rules

- AIGuard `guard_verdict` is not the same thing as Lab `deployment_decision`.
- `suspected_causes` are review candidates, not automatic root-cause proof.
- LLM guessing is not used for evidence or recommendations.
- Thresholds are deterministic and should be visible in the report.
- New evidence types should be backward-compatible extensions of the
  diagnosis report contract.

## Validation Commands

```bash
python -m pytest -q

python -m inferedge_aiguard.cli portfolio-demo \
  --save-json reports/portfolio_demo.json \
  --save-md reports/portfolio_demo.md
```

The portfolio demo should include the normal/pass, bbox collapse/blocked, score
saturation/blocked, and temporal instability/review_required cases.
