# Examples

이 디렉토리는 InferEdgeAIGuard의 output-level detector와 Lab reasoning CLI를 빠르게 검증하기 위한 fixture를 담고 있습니다.

## Output-Level Examples

- `single/`: 단일 `analyze`와 `compare` 명령용 YOLO output JSON
- `fp32/`: `batch-compare`에서 baseline으로 사용할 FP32 output fixture
- `int8/`: `batch-compare`에서 candidate로 사용할 INT8 output fixture

대표 명령:

```bash
python -m inferedge_aiguard.cli analyze --input examples/single/fp32_normal.json
python -m inferedge_aiguard.cli batch-compare --base-dir examples/fp32 --candidate-dir examples/int8
```

## Lab Reasoning Examples

- `lab_compare/`: `reason-compare`에서 사용할 Lab compare result reasoning fixture
- `lab_result/`: `reason-result`에서 사용할 Lab structured result fixture
- `lab_history/`: `reason-history`에서 사용할 repeated Lab structured result fixture
- `lab_compat/`: 실제 InferEdgeLab 출력에 더 가까운 compatibility fixture

`lab_compat` fixture는 다음 3개입니다.

- `lab_compat/lab_compare_realistic.json`: cross precision FP32 vs INT8 compare result 형태
- `lab_compat/lab_result_realistic.json`: 단일 TensorRT INT8 structured result 형태
- `lab_compat/lab_history_realistic.json`: repeated TensorRT INT8 structured result history 형태

## Recommended Smoke Commands

Output-level detector:

```bash
python -m inferedge_aiguard.cli analyze --input examples/single/fp32_normal.json
python -m inferedge_aiguard.cli batch-compare --base-dir examples/fp32 --candidate-dir examples/int8
```

Unified Lab reasoning:

```bash
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_result_realistic.json
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_history_realistic.json
```

Explicit Lab reasoning commands are still available:

```bash
python -m inferedge_aiguard.cli reason-compare --input examples/lab_compare/cross_precision_latency_only.json
python -m inferedge_aiguard.cli reason-result --input examples/lab_result/suspicious_int8_missing_accuracy.json
python -m inferedge_aiguard.cli reason-history --input examples/lab_history/unstable_int8_history.json
```

이 예제들은 ground truth 기반 정확도 평가가 아니라 output/result-level anomaly signal과 reasoning path 검증용입니다.
