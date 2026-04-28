"""Forge/Runtime provenance mismatch reasoning."""

from __future__ import annotations

from typing import Any


JsonDict = dict[str, Any]


def analyze_forge_runtime_provenance(
    runtime_result: JsonDict,
    forge_metadata: JsonDict | None = None,
    forge_manifest: JsonDict | None = None,
) -> JsonDict:
    """Compare Runtime result provenance with Forge metadata/manifest evidence.

    This detector is intentionally rule based. It does not execute artifacts or
    infer missing values; it only compares explicit provenance values already
    recorded by Forge and Runtime.
    """

    expected = _normalize_forge_provenance(forge_metadata, forge_manifest)
    observed = _normalize_runtime_provenance(runtime_result)

    anomalies: list[JsonDict] = []
    explanations: list[str] = []
    suspected_causes: list[str] = []
    recommendations: list[str] = []

    def add_anomaly(
        anomaly_type: str,
        severity: str,
        message: str,
        evidence: JsonDict,
        suspected_cause: str,
        recommendation: str,
    ) -> None:
        anomalies.append(
            {
                "type": anomaly_type,
                "severity": severity,
                "message": message,
                "evidence": evidence,
            }
        )
        explanations.append(message)
        _append_unique(suspected_causes, suspected_cause)
        _append_unique(recommendations, recommendation)

    missing_fields = []
    for field in _COMPARISON_FIELDS:
        expected_value = expected[field]["value"]
        observed_value = observed[field]["value"]
        if _is_missing(expected_value) or _is_missing(observed_value):
            missing_fields.append(
                {
                    "field": field,
                    "expected": expected_value,
                    "observed": observed_value,
                    "expected_source": expected[field]["source"],
                    "observed_source": observed[field]["source"],
                }
            )

    if missing_fields:
        add_anomaly(
            "insufficient_provenance",
            "medium",
            "Forge/Runtime provenance comparison is incomplete because required fields are missing.",
            {"missing_fields": missing_fields},
            "incomplete_forge_runtime_provenance",
            (
                "Record Forge metadata/manifest and Runtime result provenance before "
                "using artifact mismatch reasoning for deployment decisions."
            ),
        )

    for field in ("artifact_sha256", "source_model_sha256"):
        expected_value = expected[field]["value"]
        observed_value = observed[field]["value"]
        if _is_missing(expected_value) or _is_missing(observed_value):
            continue
        if _normalize_hash(expected_value) != _normalize_hash(observed_value):
            add_anomaly(
                f"{field}_mismatch",
                "high",
                f"Runtime {field} does not match Forge {field}.",
                _comparison_evidence(field, expected, observed),
                "runtime_result_does_not_match_forge_artifact",
                (
                    "Block or review deployment until Runtime profiling is repeated "
                    "against the Forge-built artifact."
                ),
            )

    for field in ("artifact_path", "backend", "target", "precision", "batch", "height", "width"):
        expected_value = expected[field]["value"]
        observed_value = observed[field]["value"]
        if _is_missing(expected_value) or _is_missing(observed_value):
            continue
        if not _same_value(field, expected_value, observed_value):
            add_anomaly(
                _config_mismatch_type(field),
                "medium",
                f"Runtime {field} does not match Forge handoff provenance.",
                _comparison_evidence(field, expected, observed),
                "forge_runtime_configuration_mismatch",
                (
                    "Review Forge handoff metadata and Runtime launch configuration "
                    "before trusting the profiling result."
                ),
            )

    expected_artifact_type = expected.get("artifact_type", {}).get("value")
    observed_artifact_type = observed.get("artifact_type", {}).get("value")
    if not _is_missing(expected_artifact_type) and not _is_missing(observed_artifact_type):
        if not _same_value("artifact_type", expected_artifact_type, observed_artifact_type):
            add_anomaly(
                "artifact_type_mismatch",
                "medium",
                "Runtime artifact_type does not match Forge handoff provenance.",
                _comparison_evidence("artifact_type", expected, observed),
                "forge_runtime_artifact_type_mismatch",
                "Review Forge artifact format and Runtime worker response provenance before deployment.",
            )

    status = _status_from_anomalies(anomalies)
    return {
        "mode": "forge_runtime_provenance_reasoning",
        "status": status,
        "anomalies": anomalies,
        "explanations": explanations,
        "suspected_causes": suspected_causes,
        "confidence": _confidence_for_status(status),
        "recommendations": recommendations,
    }


def analyze_worker_provenance(
    forge_summary: JsonDict,
    runtime_worker_response: JsonDict,
) -> JsonDict:
    """Compare Forge worker/runtime summary with Runtime worker response evidence."""

    runtime_result = _runtime_result_from_worker_response(runtime_worker_response)
    analysis = analyze_forge_runtime_provenance(
        runtime_result,
        forge_metadata=normalize_forge_summary_provenance(forge_summary),
    )
    _rewrite_evidence_sources(
        analysis,
        expected_source="forge_worker_runtime_summary",
        observed_source="runtime_worker_response",
    )
    return analysis


def normalize_forge_summary_provenance(summary: JsonDict) -> JsonDict:
    """Project a Forge worker/runtime summary into provenance comparison fields."""

    if not isinstance(summary, dict):
        return {}
    return {
        "source_model_sha256": summary.get("source_model_sha256"),
        "primary_artifact_sha256": summary.get("artifact_sha256"),
        "primary_artifact_path": summary.get("artifact_path"),
        "artifact_type": summary.get("artifact_type"),
        "backend": summary.get("backend"),
        "target": summary.get("target"),
        "precision": summary.get("precision"),
        "batch": summary.get("batch"),
        "height": summary.get("height"),
        "width": summary.get("width"),
        "preset_name": summary.get("preset_name"),
        "build_id": summary.get("build_id"),
    }


compare_forge_summary_with_runtime_response = analyze_worker_provenance


_COMPARISON_FIELDS = (
    "artifact_sha256",
    "artifact_path",
    "source_model_sha256",
    "backend",
    "target",
    "precision",
    "batch",
    "height",
    "width",
)


def _runtime_result_from_worker_response(response: JsonDict) -> JsonDict:
    if not isinstance(response, dict):
        return {}
    runtime_result = response.get("runtime_result")
    return runtime_result if isinstance(runtime_result, dict) else {}


def _rewrite_evidence_sources(
    analysis: JsonDict,
    *,
    expected_source: str,
    observed_source: str,
) -> None:
    for anomaly in analysis.get("anomalies", []):
        evidence = anomaly.get("evidence")
        if not isinstance(evidence, dict):
            continue
        if "expected_source" in evidence:
            evidence["expected_source"] = expected_source
        if "observed_source" in evidence:
            evidence["observed_source"] = observed_source
        missing_fields = evidence.get("missing_fields")
        if not isinstance(missing_fields, list):
            continue
        for field in missing_fields:
            if not isinstance(field, dict):
                continue
            if "expected_source" in field:
                field["expected_source"] = expected_source
            if "observed_source" in field:
                field["observed_source"] = observed_source


def _normalize_forge_provenance(
    metadata: JsonDict | None,
    manifest: JsonDict | None,
) -> JsonDict:
    sources: list[tuple[str, JsonDict]] = []
    if isinstance(manifest, dict):
        sources.append(("forge_manifest", manifest))
    if isinstance(metadata, dict):
        sources.append(("forge_metadata", metadata))

    return {
        "artifact_sha256": _first_value(
            sources,
            (
                ("primary_artifact_sha256",),
                ("artifact", "sha256"),
                ("primary_artifact", "sha256"),
                ("artifacts", 0, "sha256"),
            ),
        ),
        "artifact_path": _first_value(
            sources,
            (
                ("primary_artifact_path",),
                ("artifact", "path"),
                ("primary_artifact", "path"),
                ("artifacts", 0, "path"),
            ),
        ),
        "source_model_sha256": _first_value(
            sources,
            (
                ("source_model_sha256",),
                ("source_model", "sha256"),
                ("source_model", "hash"),
                ("source", "sha256"),
            ),
        ),
        "backend": _first_value(
            sources,
            (
                ("backend",),
                ("build", "backend"),
                ("runtime_compat", "backend"),
                ("lab_compat", "backend"),
            ),
        ),
        "target": _first_value(
            sources,
            (
                ("target",),
                ("device",),
                ("build", "target"),
                ("runtime_compat", "target"),
                ("runtime_compat", "device"),
                ("lab_compat", "target"),
                ("lab_compat", "device"),
            ),
        ),
        "precision": _first_value(
            sources,
            (
                ("precision",),
                ("build", "precision"),
                ("runtime_compat", "precision"),
                ("lab_compat", "precision"),
                ("preset_snapshot", "build_options", "precision"),
            ),
        ),
        "batch": _first_value(sources, _SHAPE_PATHS["batch"]),
        "height": _first_value(sources, _SHAPE_PATHS["height"]),
        "width": _first_value(sources, _SHAPE_PATHS["width"]),
        "artifact_type": _first_value(
            sources,
            (
                ("artifact_type",),
                ("artifact", "type"),
                ("artifact", "format"),
                ("primary_artifact", "type"),
                ("primary_artifact", "format"),
                ("artifacts", 0, "type"),
                ("artifacts", 0, "format"),
            ),
        ),
    }


def _normalize_runtime_provenance(runtime_result: JsonDict) -> JsonDict:
    extra = runtime_result.get("extra") if isinstance(runtime_result.get("extra"), dict) else {}
    run_config = (
        runtime_result.get("run_config")
        if isinstance(runtime_result.get("run_config"), dict)
        else {}
    )
    engine = runtime_result.get("engine")
    device = runtime_result.get("device")
    engine_backend = engine.get("backend") if isinstance(engine, dict) else engine
    device_target = device.get("target") if isinstance(device, dict) else device

    sources = [
        ("runtime_result.extra", extra),
        ("runtime_result.run_config", run_config),
        ("runtime_result", runtime_result),
    ]

    return {
        "artifact_sha256": _first_value(
            sources,
            (
                ("runtime_artifact_sha256",),
                ("artifact_sha256",),
            ),
        ),
        "artifact_path": _first_value(
            sources,
            (
                ("runtime_artifact_path",),
                ("artifact_path",),
                ("model_path",),
            ),
        ),
        "source_model_sha256": _first_value(
            sources,
            (
                ("source_model_sha256",),
                ("model_sha256",),
            ),
        ),
        "backend": _literal_or_first(
            engine_backend,
            "runtime_result.engine",
            _first_value(sources, (("backend",), ("engine_backend",))),
        ),
        "target": _literal_or_first(
            device_target,
            "runtime_result.device",
            _first_value(sources, (("target",), ("device",), ("device_name",))),
        ),
        "precision": _first_value(sources, (("precision",),)),
        "batch": _first_value(sources, (("batch",),)),
        "height": _first_value(sources, (("height",),)),
        "width": _first_value(sources, (("width",),)),
        "artifact_type": _first_value(sources, (("artifact_type",),)),
    }


_SHAPE_PATHS = {
    "batch": (
        ("batch",),
        ("requested_batch",),
        ("shape", "batch"),
        ("requested_shape", "batch"),
        ("input_shape", "batch"),
        ("runtime_compat", "batch"),
        ("lab_compat", "batch"),
    ),
    "height": (
        ("height",),
        ("requested_height",),
        ("shape", "height"),
        ("requested_shape", "height"),
        ("input_shape", "height"),
        ("runtime_compat", "height"),
        ("lab_compat", "height"),
    ),
    "width": (
        ("width",),
        ("requested_width",),
        ("shape", "width"),
        ("requested_shape", "width"),
        ("input_shape", "width"),
        ("runtime_compat", "width"),
        ("lab_compat", "width"),
    ),
}


def _first_value(
    sources: list[tuple[str, JsonDict]],
    paths: tuple[tuple[str | int, ...], ...],
) -> JsonDict:
    for source_name, source in sources:
        for path in paths:
            value = _get_path(source, path)
            if not _is_missing(value):
                return {"value": value, "source": source_name}
    return {"value": None, "source": None}


def _literal_or_first(value: Any, source_name: str, fallback: JsonDict) -> JsonDict:
    if not _is_missing(value):
        return {"value": value, "source": source_name}
    return fallback


def _get_path(data: Any, path: tuple[str | int, ...]) -> Any:
    current = data
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
            continue
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _comparison_evidence(field: str, expected: JsonDict, observed: JsonDict) -> JsonDict:
    return {
        "field": field,
        "expected": expected[field]["value"],
        "observed": observed[field]["value"],
        "expected_source": expected[field]["source"],
        "observed_source": observed[field]["source"],
    }


def _config_mismatch_type(field: str) -> str:
    if field == "artifact_path":
        return "artifact_path_mismatch"
    if field in {"batch", "height", "width"}:
        return "shape_mismatch"
    return "runtime_config_mismatch"


def _same_value(field: str, expected: Any, observed: Any) -> bool:
    if field in {"batch", "height", "width"}:
        return _normalize_int(expected) == _normalize_int(observed)
    if field in {"backend", "target", "precision"}:
        return str(expected).strip().lower() == str(observed).strip().lower()
    return str(expected).strip() == str(observed).strip()


def _normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _normalize_hash(value: Any) -> str:
    return str(value).strip().lower()


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _status_from_anomalies(anomalies: list[JsonDict]) -> str:
    severities = {anomaly.get("severity") for anomaly in anomalies}
    if "high" in severities:
        return "error"
    if severities:
        return "warning"
    return "ok"


def _confidence_for_status(status: str) -> float:
    if status == "error":
        return 0.9
    if status == "warning":
        return 0.7
    return 0.5


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
