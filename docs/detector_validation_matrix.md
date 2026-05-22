# Detector Validation Matrix

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
| detection disappearance | `detection_count_drop_pct`, `zero_detection_frame_ratio` | stable count | drop `>= 50%` | drop `>= 80%` or zero-frame ratio `> 0.30` | `candidate_summary.comparison`, `candidate_summary.temporal` |
| baseline deviation | invalid/collapse/saturation factor | near baseline | factor `> 5x` | factor `> 10x` | `evidence[].increase_factor` |
| temporal consistency | count CV, bbox center jump, class flip | stable sequence | count CV `> 1.0`, class flip `> 0.30`, or center jump p95 `> 0.50` image diagonal | zero-frame ratio `> 0.30` | `candidate_summary.temporal` |
| provenance consistency | source/artifact/backend/target/precision identity | exact handoff match | warning mismatch | error mismatch | `guard_analysis.anomalies`, `guard_analysis.status` |
| EdgeEnv runtime regression | p99/mean/FPS/memory deltas and telemetry coverage | comparable report without threshold breach | same-condition regression or telemetry gap | high tail-latency regression | `candidate_summary.edgeenv_regression` |

## Implemented Detector Details

| Detector | Evidence | Threshold | Normal Expected | Problem Expected | Report Field |
|---|---|---:|---|---|---|
| bbox validity | `invalid_bbox_rate` | review `0.05`, blocked `0.20` | `pass` | `review_required` / `blocked` | `evidence[].metric_name` |
| bbox collapse | `bbox_collapse_ratio` | review `0.05`, high `0.10` | `pass` | `review_required` / `blocked` | `evidence[].type`, `evidence[].observed_value` |
| score range | `score_range_violation_count` | `> 0` | `pass` | `blocked` | `evidence[].metric_name`, `evidence[].severity` |
| score distribution | `saturation_ratio` | review `0.70`, high `0.85` | `pass` | `review_required` / `blocked` | `evidence[].observed_value` |
| detection count drift | `detection_count_drop_pct` | review `0.50`, blocked `0.80` | `pass` | `review_required` / `blocked` | `evidence[].delta_pct`, `candidate_summary.comparison` |
| baseline deviation | `invalid_bbox_rate_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| baseline deviation | `bbox_collapse_ratio_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| baseline deviation | `score_saturation_factor` | review `5x`, blocked `10x` | `pass` | `review_required` / `blocked` | `evidence[].increase_factor` |
| temporal consistency | `frame_to_frame_detection_count_cv` | review `1.0` | `pass` | `review_required` | `evidence[].metric_name`, `candidate_summary.temporal` |
| temporal consistency | `bbox_center_jump_p95` | review `0.50` image diagonal | `pass` | `review_required` | `evidence[].observed_value` |
| temporal consistency | `class_flip_rate` | review `0.30` | `pass` | `review_required` | `evidence[].observed_value` |
| temporal consistency | `zero_detection_frame_ratio` | blocked `0.30` | `pass` | `blocked` | `candidate_summary.temporal` |
| provenance | artifact/source/backend/target/precision mismatch | exact identity expected | `pass` / `ok` | `warning` / `error` | `guard_analysis.anomalies`, `guard_analysis.status` |
| EdgeEnv regression | `p99_delta_pct` | review/high `25.0` | `pass` | `blocked` for high same-condition tail latency regression | `evidence[].type=runtime_latency_regression` |
| EdgeEnv regression | `fps_delta_pct` | review `<= -20.0` | `pass` | `review_required` | `evidence[].type=runtime_throughput_regression` |
| EdgeEnv regression | `memory_peak_delta_pct` | warning `30.0` | `pass` | `suspicious` / `review_required` | `evidence[].type=runtime_memory_regression` |
| EdgeEnv telemetry context | `runtime_telemetry_evidence_gap_count` | warning `>= 1` | `pass` | `suspicious` | `evidence[].type=runtime_telemetry_context_coverage` |
| EdgeEnv telemetry replay | `runtime_telemetry_history_missing_run_count` | warning `>= 1` or sequence order mismatch | `pass` | `suspicious` | `evidence[].type=runtime_telemetry_replay_context` |

## Next Candidate Detectors

These items are documented roadmap candidates for the remaining development
window. They should stay deterministic and evidence based; they are not LLM
root-cause inference.

| Candidate | Purpose | Suggested evidence | Expected use |
|---|---|---|---|
| per-class detection drift | catch class-specific disappearance even when total count looks stable | per-class count delta, per-class zero ratio | review when one important class collapses against baseline |
| detection disappearance hardening | make empty-frame behavior more explicit in reports | zero-detection frame streak, zero-frame ratio, first missing frame | review/block depending on repeated disappearance |
| calibration drift | detect score distribution shift against a known-good baseline | score histogram delta, mean/std shift, saturation delta | review when confidence scale changes without accuracy explanation |
| baseline profile stability | document whether a baseline itself is stable enough to trust | baseline variance, repeated-run p95, profile sample count | warn when comparison baseline is too noisy |

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
