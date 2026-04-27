# Examples

이 디렉토리는 InferEdgeAIGuard CLI 사용 흐름을 바로 확인하기 위한 예제 fixture를 담고 있습니다.

## 구조

- `single/`: 단일 `analyze`와 `compare` 명령용 JSON fixture
- `fp32/`: `batch-compare`에서 baseline으로 사용할 FP32 output fixture
- `int8/`: `batch-compare`에서 candidate로 사용할 INT8 output fixture

## 실행 예시

단일 output을 분석합니다.

```bash
python -m inferedge_aiguard.cli analyze --input examples/single/fp32_normal.json
```

FP32 baseline과 INT8 candidate output을 비교합니다.

```bash
python -m inferedge_aiguard.cli compare \
  --base examples/single/fp32_normal.json \
  --candidate examples/single/int8_count_mismatch.json
```

단일 fixture 디렉토리를 batch 분석합니다.

```bash
python -m inferedge_aiguard.cli batch-analyze --input-dir examples/single
```

FP32 baseline 디렉토리와 INT8 candidate 디렉토리를 batch 비교합니다.

```bash
python -m inferedge_aiguard.cli batch-compare \
  --base-dir examples/fp32 \
  --candidate-dir examples/int8
```

이 예제는 ground truth 기반 정확도 평가가 아니라 output-level failure signal 검증용입니다.
