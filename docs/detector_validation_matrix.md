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

## Detector Matrix

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
