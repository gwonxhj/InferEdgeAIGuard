# Examples

이 디렉토리는 InferEdgeAIGuard CLI 사용 흐름을 바로 확인하기 위한 예제 fixture를 담고 있습니다.

## 구조

- `single/`: 단일 `analyze`와 `compare` 명령용 JSON fixture
- `fp32/`: `batch-compare`에서 baseline으로 사용할 FP32 output fixture
- `int8/`: `batch-compare`에서 candidate로 사용할 INT8 output fixture
- `lab_compare/`: `reason-compare`에서 사용할 InferEdgeLab compare result reasoning fixture
- `lab_result/`: Python API `analyze_structured_result()`에서 사용할 InferEdgeLab structured result fixture

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

저장된 JSON report에는 `guard_version`, `created_at`, `detector_config`가 포함됩니다. 이 metadata는 어떤 InferEdgeAIGuard 버전과 detector threshold로 실험 결과를 만들었는지 재현하기 위한 정보입니다.

`batch-analyze`와 `batch-compare` 결과를 `--save-md`로 저장하면 aggregate summary, failure type counts, sample 또는 pair 목록이 표 형태로 정리된 Markdown report가 생성됩니다.

Lab compare result reasoning 예제도 포함되어 있습니다.

- `lab_compare/cross_precision_latency_only.json`: cross precision latency improvement지만 accuracy 정보가 없어 reasoning warning이 발생하는 예제
- `lab_compare/invalid_shape_mismatch.json`: shape mismatch로 unreliable comparison이 발생하는 예제
- `lab_compare/alias_schema_example.json`: adapter가 alias 필드명을 표준 compare dict로 정규화하는 예제

```bash
python -m inferedge_aiguard.cli reason-compare --input examples/lab_compare/cross_precision_latency_only.json
```

```bash
python -m inferedge_aiguard.cli reason-compare --input examples/lab_compare/alias_schema_example.json
```

Lab structured result reasoning 예제도 포함되어 있습니다.

- `lab_result/valid_fp32_result.json`: anomaly가 없는 정상 FP32 structured result 예제
- `lab_result/suspicious_int8_missing_accuracy.json`: latency instability, missing provenance, missing accuracy warning이 발생하는 INT8 예제

```bash
python -m inferedge_aiguard.cli reason-result \
  --input examples/lab_result/suspicious_int8_missing_accuracy.json
```

`reason-result`는 compare 결과가 아니라 단일 Lab structured result JSON을 분석합니다.
