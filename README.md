# InferEdgeAIGuard

InferEdgeAIGuard는 Edge AI inference output에서 발생할 수 있는 비정상 출력 패턴을 빠르게 감지하기 위한 경량 Python 도구입니다.

1차 MVP의 목표는 YOLO 계열 detection output JSON을 입력으로 받아, 모델 변환이나 경량화 이후에 나타날 수 있는 출력 실패 징후를 최소한의 규칙 기반 detector로 확인하는 것입니다. 1.1단계에서는 기능 범위를 넓히기보다 각 failure definition을 수치 기반으로 더 명확하게 정리합니다.

## 핵심 관점

InferEdgeAIGuard는 정답을 추정하는 truth estimation 도구가 아닙니다.

이 프로젝트는 "이 예측이 실제로 맞는가?"를 판단하지 않습니다. 대신 "출력 구조나 분포가 비정상적으로 무너졌는가?"를 감지합니다. 즉 InferEdgeAIGuard의 failure는 정답 오류가 아니라 output-level anomaly/failure signal입니다.

예를 들어 INT8 변환 이후 bbox width/height가 0에 가깝게 collapse되거나, confidence가 0.0 또는 1.0 근처로 과도하게 몰리거나, FP32 기준 대비 detection 수가 크게 달라지는 경우를 failure signal로 봅니다.

## InferEdgeLab reasoning layer

2.0단계부터 InferEdgeAIGuard는 InferEdgeLab validation pipeline 위에서 동작하는 reasoning layer로 확장됩니다.

- InferEdgeLab: measurement + comparison
- InferEdgeAIGuard: anomaly detection + explanation + suspected cause

AIGuard는 Lab 결과를 덮어쓰지 않습니다. 대신 Lab compare result dict 위에 anomaly 판단, 설명, 의심 원인, 권장 조치를 추가합니다.

Python API는 `analyze_compare_result(compare_result)`입니다. 반환 구조는 다음 필드를 포함합니다.

- `status`: `ok`, `warning`, `error`
- `anomalies`: rule 기반 anomaly 목록
- `explanations`: 사람이 읽을 수 있는 설명
- `suspected_causes`: 의심 원인 목록
- `confidence`: rule engine 판단 confidence이며 모델 정확도 confidence가 아님
- `recommendations`: 후속 확인 권장 사항

초기 rule은 다음을 다룹니다.

- shape mismatch
- run_config mismatch
- latency improvement + accuracy missing
- latency improvement + accuracy drop
- cross precision large latency delta

이 단계는 Lab structured result와 결합하기 위한 시작점입니다. 아직 CLI 명령과 실제 Lab 파일 파싱은 추가하지 않습니다.

## 1차 MVP 범위

- YOLO detection output JSON 최소 스키마 검증
- bbox collapse 감지
- confidence saturation 감지
- FP32 baseline과 candidate output 간 detection count mismatch 감지
- 디렉토리 단위 batch output failure signal 집계
- 디렉토리 단위 FP32 baseline 대비 candidate output failure signal 비교
- 사람이 읽기 쉬운 CLI report 출력
- pytest 기반 기본 회귀 테스트

## Failure definition

현재 detector는 3개입니다.

### bbox collapse

`bbox`의 `w` 또는 `h`가 `threshold` 이하로 작아진 detection을 감지합니다.

- 기본 `threshold`: `1e-6`
- `affected_count`: collapse된 bbox 수
- `total_count`: 전체 detection 수
- `collapse_ratio`: `affected_count / total_count`

`detections`가 비어 있으면 bbox collapse failure로 보지 않습니다.

### confidence saturation

confidence가 0.0 근처 또는 1.0 근처에 과도하게 몰리는 경우를 감지합니다.

- 기본 `low_threshold`: `0.01`
- 기본 `high_threshold`: `0.99`
- 기본 `ratio_threshold`: `0.8`
- `affected_count`: low/high saturation 구간에 들어간 detection 수
- `total_count`: 전체 detection 수
- `saturation_ratio`: `affected_count / total_count`

`detections`가 비어 있으면 confidence saturation failure로 보지 않습니다.

### detection count mismatch

FP32 baseline과 candidate output의 detection 개수가 크게 달라지는 경우를 감지합니다.

- 기본 `threshold`: `0.5`
- `affected_count`: detection count 차이의 절대값
- `base_count`: FP32 baseline detection 수
- `candidate_count`: candidate detection 수
- `mismatch_ratio`: `abs(base_count - candidate_count) / base_count`

`base_count`가 0이고 `candidate_count`도 0이면 정상입니다. `base_count`가 0인데 `candidate_count`가 있으면 `mismatch_ratio=1.0`으로 failure 처리합니다.

## Severity 산정

1.1단계부터 severity는 고정값이 아니라 failure ratio 기반으로 산정합니다.

- bbox collapse: `collapse_ratio >= 0.5`이면 `high`, `>= 0.1`이면 `medium`, 그 외 감지된 failure는 `low`
- confidence saturation: `saturation_ratio >= 0.95`이면 `high`, `>= ratio_threshold`이면 `medium`
- detection count mismatch: `mismatch_ratio >= 0.8`이면 `high`, `>= threshold`이면 `medium`

이 방식은 detector 결과가 단순 경고 문자열이 아니라 `affected_count`, `total_count`, `ratio`, `threshold`를 함께 가진 연구/분석 가능한 failure signal이 되도록 하기 위한 기준입니다.

## Summary metadata

모든 summary 결과에는 실험 재현성을 위한 metadata가 포함됩니다.

- `guard_version`: 실험에 사용한 InferEdgeAIGuard 버전
- `created_at`: summary 생성 시각의 UTC ISO-8601 문자열
- `detector_config`: failure 판단에 사용된 threshold/config snapshot

`detector_config`에는 `bbox_collapse`, `confidence_saturation`, `detection_count_mismatch`의 기준값이 저장됩니다. 이 metadata는 논문/포트폴리오 실험 로그에서 "어떤 버전과 어떤 threshold로 failure signal을 판단했는가"를 나중에 재현하기 위한 정보입니다.

## 입력 JSON 형식

```json
{
  "model": "yolov8n",
  "precision": "fp32",
  "image_id": "sample_001",
  "detections": [
    {
      "class_id": 0,
      "confidence": 0.91,
      "bbox": [12.0, 24.0, 120.0, 80.0]
    }
  ]
}
```

- `bbox`는 `[x, y, w, h]` 형식입니다.
- `confidence`는 `0.0` 이상 `1.0` 이하의 숫자여야 합니다.
- `detections`는 빈 배열일 수 있습니다.

## Examples 구조

예제 fixture는 CLI 사용 흐름에 맞게 나뉘어 있습니다.

- `examples/single`: 단일 `analyze`와 `compare` 명령용 fixture
- `examples/fp32`: `batch-compare` baseline용 FP32 fixture
- `examples/int8`: `batch-compare` candidate용 INT8 fixture

## CLI 사용 예시

단일 output을 분석합니다.

```bash
python -m inferedge_aiguard.cli analyze --input examples/single/fp32_normal.json
```

단일 output 분석은 하나의 JSON에 대해 bbox collapse와 confidence saturation 같은 output-level failure signal을 확인합니다.

FP32 baseline과 INT8 또는 FP16 candidate output을 비교합니다.

```bash
python -m inferedge_aiguard.cli compare \
  --base examples/single/fp32_normal.json \
  --candidate examples/single/int8_count_mismatch.json
```

여러 output JSON을 한 번에 분석합니다.

```bash
python -m inferedge_aiguard.cli batch-analyze --input-dir examples/single
```

batch output 분석은 디렉토리 안의 `*.json` 파일을 파일명 기준으로 정렬해 각각 분석한 뒤, 실험 세트 전체에서 failure signal이 얼마나 자주 나타났는지 집계합니다. 이 기능도 ground truth 평가가 아니라 output-level failure signal 집계입니다.

batch summary는 다음 지표를 제공합니다.

- `sample_count`: 분석한 JSON sample 수
- `failure_sample_count`: 하나 이상의 failure가 감지된 sample 수
- `failure_rate`: `failure_sample_count / sample_count`
- `failure_type_counts`: failure type별 발생 횟수

FP32 baseline 디렉토리와 INT8 또는 FP16 candidate 디렉토리를 파일명 기준으로 비교합니다.

```bash
python -m inferedge_aiguard.cli batch-compare \
  --base-dir examples/fp32 \
  --candidate-dir examples/int8
```

`batch-analyze`는 단일 디렉토리의 output JSON들을 각각 분석해 failure signal 발생률을 집계합니다. `batch-compare`는 두 디렉토리의 공통 파일명을 pair로 묶은 뒤, FP32 baseline 대비 candidate output에서 어떤 failure pattern이 나타나는지 집계합니다.

`batch-compare`는 파일명 기준으로만 pair를 매칭합니다. 한쪽 디렉토리에만 있는 파일은 비교하지 않고 `unmatched_base_files` 또는 `unmatched_candidate_files`로 따로 보고합니다.

batch compare summary는 다음 지표를 제공합니다.

- `pair_count`: 공통 파일명으로 비교한 pair 수
- `failure_pair_count`: 하나 이상의 failure가 감지된 pair 수
- `failure_rate`: `failure_pair_count / pair_count`
- `failure_type_counts`: failure type별 발생 횟수
- `unmatched_base_files`: baseline 디렉토리에만 있는 JSON 파일명
- `unmatched_candidate_files`: candidate 디렉토리에만 있는 JSON 파일명

이 기능은 ground truth 정확도 평가가 아니라 FP32 baseline 대비 candidate output-level failure signal 비교입니다. RQ1 "FP32 대비 INT8/FP16 inference는 어떤 failure pattern을 보이는가?"를 최소한의 실험 단위로 확인하기 위한 구조입니다.

CLI 결과를 JSON 또는 Markdown 파일로 저장할 수 있습니다.

```bash
python -m inferedge_aiguard.cli analyze \
  --input examples/single/fp32_normal.json \
  --save-json reports/analyze_normal.json \
  --save-md reports/analyze_normal.md
```

```bash
python -m inferedge_aiguard.cli batch-analyze \
  --input-dir examples/single \
  --save-json reports/batch_analyze.json \
  --save-md reports/batch_analyze.md
```

`--save-json`은 summary dict를 그대로 저장하므로 후속 분석, 표 작성, 논문/포트폴리오 실험 로그 누적에 적합합니다. `--save-md`는 사람이 읽기 쉬운 실험 리포트를 남길 때 사용합니다.

`--save-md`로 batch 결과를 저장하면 표 형태의 Markdown report가 생성됩니다. `batch-analyze` report에는 `Metadata`, `Aggregate Summary`, `Failure Type Counts`, `Samples` 섹션이 포함됩니다. `batch-compare` report에는 `Metadata`, `Aggregate Summary`, `Failure Type Counts`, `Unmatched Files`, `Pairs` 섹션이 포함됩니다. 두 report 모두 `Raw CLI Summary`를 함께 포함하므로 CLI 출력과 문서형 요약을 동시에 확인할 수 있습니다.

저장 기능 역시 ground truth 평가가 아니라 output-level failure signal 기록입니다. 즉 "정답 대비 정확도"를 저장하는 것이 아니라, InferEdgeAIGuard가 감지한 출력 레벨 failure signal과 집계 결과를 재현 가능한 파일로 남기는 기능입니다.

테스트를 실행합니다.

```bash
python -m pytest -q
```

## 이번 단계에서 하지 않는 것

1차 MVP와 1.1단계에서는 다음을 구현하지 않습니다.

- TensorRT 실행
- Jetson 실기기 실행
- ONNX/TensorRT 모델 변환
- UI 또는 SaaS 기능
- ML 학습 또는 calibration 자동화
- ground truth 기반 정확도 평가

이 범위를 의도적으로 작게 유지하면, 이후 TensorRT/Jetson/모델 변환 단계로 확장할 때도 "출력 실패 감지"라는 제품 핵심을 흔들리지 않게 검증할 수 있습니다.
