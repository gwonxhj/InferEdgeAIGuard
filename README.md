# InferEdgeAIGuard

InferEdgeAIGuard는 Edge AI inference output에서 발생할 수 있는 비정상 출력 패턴을 빠르게 감지하기 위한 경량 Python 도구입니다.

1차 MVP의 목표는 YOLO 계열 detection output JSON을 입력으로 받아, 모델 변환이나 경량화 이후에 나타날 수 있는 출력 실패 징후를 최소한의 규칙 기반 detector로 확인하는 것입니다.

## 핵심 관점

InferEdgeAIGuard는 정답을 추정하는 truth estimation 도구가 아닙니다.

이 프로젝트는 "이 예측이 실제로 맞는가?"를 판단하지 않습니다. 대신 "출력 구조나 분포가 비정상적으로 무너졌는가?"를 감지합니다. 예를 들어 INT8 변환 이후 bbox width/height가 0에 가깝게 collapse되거나, confidence가 0.0 또는 1.0 근처로 과도하게 몰리거나, FP32 기준 대비 detection 수가 크게 달라지는 경우를 failure signal로 봅니다.

## 1차 MVP 범위

- YOLO detection output JSON 최소 스키마 검증
- bbox collapse 감지
- confidence saturation 감지
- FP32 baseline과 candidate output 간 detection count mismatch 감지
- 사람이 읽기 쉬운 CLI report 출력
- pytest 기반 기본 회귀 테스트

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

## CLI 사용 예시

단일 output을 분석합니다.

```bash
python -m inferedge_aiguard.cli analyze --input examples/fp32_normal.json
```

FP32 baseline과 INT8 또는 FP16 candidate output을 비교합니다.

```bash
python -m inferedge_aiguard.cli compare \
  --base examples/fp32_normal.json \
  --candidate examples/int8_count_mismatch.json
```

테스트를 실행합니다.

```bash
python -m pytest -q
```

## 이번 단계에서 하지 않는 것

1차 MVP에서는 다음을 구현하지 않습니다.

- TensorRT 실행
- Jetson 실기기 실행
- ONNX/TensorRT 모델 변환
- UI 또는 SaaS 기능
- ML 학습 또는 calibration 자동화
- ground truth 기반 정확도 평가

이 범위를 의도적으로 작게 유지하면, 이후 TensorRT/Jetson/모델 변환 단계로 확장할 때도 "출력 실패 감지"라는 제품 핵심을 흔들리지 않게 검증할 수 있습니다.
