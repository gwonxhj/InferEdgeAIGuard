# InferEdgeAIGuard

언어: [English](README.md) | 한국어

InferEdgeAIGuard는 InferEdge 전체 파이프라인에서 **optional deterministic diagnosis evidence layer** 역할을 맡는 레포입니다.

InferEdge는 Forge build provenance, Runtime execution/result export, Lab analysis/deployment decision, optional AIGuard diagnosis evidence를 연결하는 end-to-end Edge AI inference validation pipeline입니다.

```text
ONNX model
-> InferEdgeForge build/provenance
-> InferEdge-Runtime C++ execution/result export
-> InferEdgeLab compare/API/job/deployment_decision
-> optional InferEdgeAIGuard guard_analysis
```

## 이 레포의 역할

- Lab result, Runtime profiling/provenance, Forge metadata/manifest evidence를 읽어 suspicious inference result를 진단합니다.
- artifact/source hash mismatch, backend/target/precision/shape mismatch, insufficient provenance 등을 rule/evidence 기반으로 감지합니다.
- `guard_analysis`를 optional evidence로 출력해 Lab report/API/deployment decision 흐름에 보존될 수 있게 합니다.
- 최종 deployment decision owner는 InferEdgeLab입니다. AIGuard는 최종 판단을 덮어쓰지 않습니다.

## 중요한 경계

AIGuard는 다음을 하지 않습니다.

- root cause를 확정하지 않습니다.
- 자동 해결 시스템이 아닙니다.
- LLM 추측 기반 진단 도구가 아닙니다.
- 의료/안전/법적 판단 자동화 도구가 아닙니다.
- production SaaS worker가 아닙니다.

대신 deterministic rule과 evidence를 사용해 reviewer가 확인해야 할 suspected cause와 anomaly signal을 좁혀줍니다.

## 빠른 실행

예시 reasoning:

```bash
python -m inferedge_aiguard.cli reason --input examples/lab_compat/lab_compare_realistic.json
python -m inferedge_aiguard.cli reason --input real_device/jetson/compare_fp32_fp16.json
```

테스트:

```bash
python3 -m pytest -q
```

프로젝트 Python에 pytest가 없다면 사용 가능한 venv/Poetry 환경에서 동일하게 실행하면 됩니다.

## 다른 InferEdge 레포와의 관계

- **InferEdgeForge:** build artifact와 source/artifact hash, backend/target/precision/shape provenance를 제공합니다.
- **InferEdge-Runtime:** 실행/profiling result JSON과 runtime provenance를 제공합니다.
- **InferEdgeLab:** AIGuard `guard_analysis`를 optional evidence로 보존하고 최종 deployment decision을 생성합니다.

## 현재 범위와 future work

현재는 fixture와 real-device evidence 기반의 deterministic diagnosis layer입니다. Lab optional contract와 provenance mismatch detector가 구현되어 있습니다.

Future work:

- 더 넓은 detector coverage
- production service/worker packaging
- future SaaS job execution infrastructure와의 깊은 통합
