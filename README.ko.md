# InferEdgeAIGuard

Optional deterministic diagnosis evidence layer  
(provenance mismatch · suspicious result signals · guard_analysis)

언어: [English](README.md) | 한국어

## 요약

- InferEdge validation pipeline의 optional deterministic diagnosis layer입니다.
- Lab compare/result/history JSON과 Runtime/Forge provenance evidence를 읽습니다.
- suspicious inference signal, provenance mismatch, 약한 validation evidence를 감지합니다.
- Lab report/API bundle에 보존 가능한 `guard_analysis`를 optional evidence로 출력합니다.
- InferEdgeLab의 최종 decision owner 역할을 대체하지 않고 review decision을 보조합니다.

## InferEdgeAIGuard의 차별점

InferEdgeAIGuard는 LLM 추측 기반 진단 도구가 아닙니다.

이 레포는 rule/evidence 기반으로:

- latency, accuracy, provenance, output pattern, run-history signal을 점검하고
- suspected cause를 deterministic evidence와 함께 설명하며
- warning/error를 structured `guard_analysis` contract로 보존하고
- Lab이 최종 deployment decision owner로 남도록 optional evidence 역할만 수행합니다.

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

현재는 fixture와 real-device evidence 기반의 deterministic diagnosis layer입니다.
Lab optional contract, provenance mismatch detector, bbox/score evidence detectors, baseline comparison, initial temporal consistency evidence, JSON/Markdown report 저장, portfolio diagnosis demo bundle이 구현되어 있습니다.
Local Studio는 Lab에서 demo evidence를 불러와 normal/pass, bbox collapse/blocked, score saturation/blocked, temporal instability/review_required, provenance mismatch 계열 사례를 표시할 수 있습니다.

Future work:

- 더 넓은 detector coverage
- production service/worker packaging
- future SaaS job execution infrastructure와의 깊은 통합
