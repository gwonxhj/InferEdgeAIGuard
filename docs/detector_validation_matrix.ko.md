# Detector Validation Matrix 한국어 Quick Guide

언어: [English](detector_validation_matrix.md) | 한국어

이 문서는 한국어 빠른 안내서입니다. 대표/canonical 문서는
[Detector Validation Matrix](detector_validation_matrix.md)입니다.

InferEdgeAIGuard는 optional deterministic diagnosis evidence provider입니다.
`guard_verdict`는 Lab이 참고할 수 있는 진단 evidence이며, 최종
`deployment_decision`은 InferEdgeLab이 소유합니다.

## 핵심 해석

AIGuard detector matrix는 "AI가 자동으로 배포 여부를 판단한다"는 문서가
아닙니다. 각 detector는 관측 metric, threshold, severity, suspected cause,
recommendation을 deterministic evidence로 남깁니다.

```text
Runtime / Lab / EdgeEnv / Orchestrator evidence
-> AIGuard deterministic guard_analysis
-> Lab-owned deployment decision context
```

## 대표 case

| Case | Signal | Expected `guard_verdict` | 의미 |
|---|---|---|---|
| `normal_pass` | bbox/score/count 안정 | `pass` | AIGuard 기준 위험 evidence 없음 |
| `bbox_collapse_blocked` | near-zero area bbox 증가 | `blocked` | decoder/postprocess/quantization 문제 가능 |
| `score_saturation_blocked` | score가 0 또는 1 근처에 몰림 | `blocked` | calibration/postprocess 문제 가능 |
| `temporal_instability_review` | frame 간 count/bbox 이동 불안정 | `review_required` | runtime output 안정성 검토 필요 |
| `provenance_mismatch` | Forge/Runtime artifact identity 불일치 | `blocked` / `error` | 검토 중인 evidence와 artifact가 다를 수 있음 |
| `edgeenv_runtime_regression` | same-condition runtime regression | `blocked` / `suspicious` | deployment risk evidence로 Lab 검토 필요 |
| `remote_dispatch_starter` | remote worker starter/fallback evidence | `review_required` / `pass` | production remote execution 증명이 아님 |

## Detector family 요약

| Detector family | Primary evidence | Review / Block 방향 |
|---|---|---|
| bbox validity | `invalid_bbox_rate` | invalid box 비율이 높으면 review/block |
| bbox collapse | `bbox_collapse_ratio` | baseline 대비 collapse 증가 시 review/block |
| confidence saturation | `saturation_ratio` | confidence가 극단값에 몰리면 review/block |
| calibration drift | `histogram_distance`, `mean_score_delta`, `std_score_delta`, `saturation_delta` | baseline 대비 score distribution shift가 있으면 review |
| detection disappearance | `detection_count_drop_pct`, `detection_disappearance_flag`, `zero_detection_frame_ratio` | candidate zero detection이나 반복 disappearance가 있으면 review/block |
| per-class detection drift | `per_class_detection_drop_pct`, dropped class IDs | 총 detection 수가 유지되어도 특정 class가 사라지면 review/block |
| baseline deviation | invalid/collapse/saturation factor | baseline 대비 급격한 변화 시 review/block |
| temporal consistency | count CV, bbox jump, class flip | frame 간 instability가 크면 review |
| provenance consistency | source/artifact/backend/precision identity | identity mismatch 시 warning/error |
| EdgeEnv runtime regression | p99/mean/FPS/memory delta | comparability-first regression evidence만 해석 |
| remote dispatch starter | worker selection, starter/fallback status | starter evidence로만 해석 |

## Baseline profile stability metadata

Saved baseline profile에는 additive `profile_stability` audit metadata가
포함됩니다. 이 metadata는 calibration drift 같은 baseline-comparison evidence를
신뢰하기 전에 baseline profile의 sample count와 histogram/class coverage를
확인하기 위한 것입니다. Lab `deployment_decision`이나 diagnosis report
schema는 변경하지 않습니다.

| Field | 의미 | 경계 |
|---|---|---|
| `profile_stability.sample_count` | saved baseline profile이 대표하는 sample 수 | single-output profile은 기본 `1` |
| `profile_stability.min_sample_count_review` | review policy에서 요구하는 최소 sample 수 | 기본 `1`; 더 엄격한 review workflow는 높일 수 있음 |
| `profile_stability.score_histogram_total_scores` | saved score histogram이 대표하는 confidence score 수 | calibration drift coverage audit용 |
| `profile_stability.class_distribution_total_predictions` | class-count metadata가 대표하는 detection 수 | per-class drift coverage audit용 |
| `profile_stability.compatibility_status` | current profile metadata인지 legacy backfill인지 표시 | legacy backfill은 audit metadata이며 schema break가 아님 |

기존 saved profile에 stability metadata가 없으면 AIGuard는 baseline summary에
`compatibility_status=legacy_profile_missing_profile_stability`를 backfill해서
reviewer가 profile 생성 시점을 구분할 수 있게 합니다.

## Calibration drift evidence policy

Calibration drift는 additive baseline-comparison evidence로 구현되어 있습니다.
단일 output만 보고 root-cause를 확정하지 않고, known-good baseline profile 또는
직접 baseline output과 candidate score distribution을 비교하는 방식으로만
다룹니다.

| Policy item | Deterministic evidence | Review trigger | 경계 |
|---|---|---|---|
| histogram shift | 고정 bin score histogram distance | 같은 output schema/class scope에서 histogram distance `>= 0.30` | calibrated probability 증명이 아님 |
| mean score shift | baseline profile 대비 `mean_score_delta` | accuracy 또는 threshold 설명 없이 absolute mean score delta `>= 0.20` | accuracy 대체 지표가 아님 |
| spread collapse or expansion | `std_score_delta`, candidate `std_score` | candidate std `< 0.05` 또는 std 변화 `>= 0.20` | model-wide calibration certification이 아님 |
| saturation drift | candidate saturation ratio - baseline saturation ratio | saturation delta `>= 0.30` 또는 기존 saturation threshold 진입 | 기존 confidence saturation block과 중복되면 그 evidence를 재사용 |

구현은 `evidence[].type=calibration_drift`를 additive로 추가합니다. diagnosis
report schema, Lab `deployment_decision`, Runtime result contract는 변경하지
않습니다.

## 반드시 유지할 경계

- AIGuard `guard_verdict`는 Lab `deployment_decision`이 아닙니다.
- AIGuard는 LLM-based root-cause certainty를 주장하지 않습니다.
- `suspected_causes`는 review 후보이며 automatic remediation이 아닙니다.
- EdgeEnv comparability와 runtime regression 계산을 재수행하지 않습니다.
- Orchestrator scheduler, queue/drop/fallback owner가 아닙니다.
- production remote execution proof를 만들지 않습니다.
- production observability platform이나 general monitoring SaaS가 아닙니다.
- public leaderboard나 모든 model family 자동 진단 도구가 아닙니다.

## Report contract에서 봐야 할 값

각 evidence item은 reviewer가 이유를 확인할 수 있도록 아래 값을 보존해야 합니다.

- `type`
- `metric_name`
- `observed_value`
- `baseline_value`
- `threshold`
- `delta` / `delta_pct`
- `increase_factor`
- `severity`
- `explanation`
- `why_it_matters`
- `suspected_causes`
- `recommendation`
- `raw_context`

## Jetson 필요 여부

이 문서를 읽거나 링크를 검증하는 작업에는 Jetson 기기가 필요 없습니다. 새로운
Jetson runtime output, live telemetry, device-local sustained evidence를 생성해
detector evidence를 갱신할 때만 Jetson 기기가 필요합니다.
