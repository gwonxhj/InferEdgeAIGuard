"""Minimal schema utilities for InferEdgeAIGuard JSON contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]
DIAGNOSIS_SCHEMA_VERSION = "inferedge-aiguard-diagnosis-v1"


class SchemaValidationError(ValueError):
    """Raised when an inference output JSON does not match the MVP schema."""


def load_output_json(path: str | Path) -> JsonDict:
    """Load and validate a YOLO detection output JSON file."""

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    return validate_output(data)


def validate_output(data: Any) -> JsonDict:
    """Validate the minimal output schema and return the original dict."""

    if not isinstance(data, dict):
        raise SchemaValidationError("output must be a JSON object")

    for field in ("model", "precision", "image_id"):
        if field not in data:
            raise SchemaValidationError(f"missing required field: {field}")
        if not isinstance(data[field], str) or not data[field]:
            raise SchemaValidationError(f"{field} must be a non-empty string")

    detections = data.get("detections")
    if detections is None:
        raise SchemaValidationError("missing required field: detections")
    if not isinstance(detections, list):
        raise SchemaValidationError("detections must be a list")

    for index, detection in enumerate(detections):
        _validate_detection(detection, index)

    return data


def validate_guard_analysis(data: Any) -> JsonDict:
    """Validate the Lab deployment_decision guard_analysis contract.

    InferEdgeLab intentionally treats AIGuard as optional and currently consumes
    only guard_analysis.status for deployment decisions. AIGuard still validates
    the surrounding evidence shape so saved reasoning output remains reviewable.
    """

    if not isinstance(data, dict):
        raise SchemaValidationError("guard_analysis must be a JSON object")

    status = data.get("status")
    if status not in {"ok", "warning", "error", "skipped"}:
        raise SchemaValidationError(
            "guard_analysis.status must be one of: ok, warning, error, skipped"
        )

    if "mode" in data and not isinstance(data["mode"], str):
        raise SchemaValidationError("guard_analysis.mode must be a string")

    _validate_optional_list(data, "anomalies", item_type=dict)
    _validate_optional_list(data, "suspected_causes", item_type=str)
    _validate_optional_list(data, "recommendations", item_type=str)

    confidence = data.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise SchemaValidationError("guard_analysis.confidence must be a number")
        if not 0.0 <= float(confidence) <= 1.0:
            raise SchemaValidationError(
                "guard_analysis.confidence must be between 0.0 and 1.0"
            )

    return data


def validate_diagnosis_report(data: Any) -> JsonDict:
    """Validate the evidence-based diagnosis report v1 contract."""

    if not isinstance(data, dict):
        raise SchemaValidationError("diagnosis report must be a JSON object")

    if data.get("schema_version") != DIAGNOSIS_SCHEMA_VERSION:
        raise SchemaValidationError(
            "diagnosis_report.schema_version must be "
            f"{DIAGNOSIS_SCHEMA_VERSION}"
        )

    if not isinstance(data.get("source", {}), dict):
        raise SchemaValidationError("diagnosis_report.source must be an object")

    if data.get("guard_verdict") not in {
        "pass",
        "suspicious",
        "review_required",
        "blocked",
    }:
        raise SchemaValidationError(
            "diagnosis_report.guard_verdict must be one of: "
            "pass, suspicious, review_required, blocked"
        )

    if data.get("severity") not in {"low", "medium", "high", "critical"}:
        raise SchemaValidationError(
            "diagnosis_report.severity must be one of: low, medium, high, critical"
        )

    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise SchemaValidationError("diagnosis_report.confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise SchemaValidationError(
            "diagnosis_report.confidence must be between 0.0 and 1.0"
        )

    for field in ("primary_reason", "created_at"):
        if not isinstance(data.get(field), str):
            raise SchemaValidationError(f"diagnosis_report.{field} must be a string")

    _validate_optional_list(
        data, "suspected_causes", item_type=str, prefix="diagnosis_report"
    )
    _validate_optional_list(
        data, "recommendations", item_type=str, prefix="diagnosis_report"
    )

    for field in ("thresholds", "baseline_summary", "candidate_summary"):
        if not isinstance(data.get(field, {}), dict):
            raise SchemaValidationError(f"diagnosis_report.{field} must be an object")

    evidence = data.get("evidence")
    if not isinstance(evidence, list):
        raise SchemaValidationError("diagnosis_report.evidence must be a list")
    for index, item in enumerate(evidence):
        _validate_diagnosis_evidence_item(item, index)

    return data


def _validate_detection(detection: Any, index: int) -> None:
    if not isinstance(detection, dict):
        raise SchemaValidationError(f"detections[{index}] must be an object")

    class_id = detection.get("class_id")
    if not isinstance(class_id, int) or isinstance(class_id, bool):
        raise SchemaValidationError(f"detections[{index}].class_id must be an integer")

    confidence = detection.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise SchemaValidationError(f"detections[{index}].confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise SchemaValidationError(
            f"detections[{index}].confidence must be between 0.0 and 1.0"
        )

    bbox = detection.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise SchemaValidationError(f"detections[{index}].bbox must be [x, y, w, h]")
    for bbox_index, value in enumerate(bbox):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaValidationError(
                f"detections[{index}].bbox[{bbox_index}] must be a number"
            )


def _validate_diagnosis_evidence_item(item: Any, index: int) -> None:
    if not isinstance(item, dict):
        raise SchemaValidationError(
            f"diagnosis_report.evidence[{index}] must be an object"
        )

    for field in (
        "type",
        "metric_name",
        "observed_value",
        "baseline_value",
        "threshold",
        "delta",
        "delta_pct",
        "increase_factor",
        "severity",
        "status",
        "explanation",
        "why_it_matters",
        "suspected_causes",
        "recommendation",
        "raw_context",
    ):
        if field not in item:
            raise SchemaValidationError(
                f"diagnosis_report.evidence[{index}].{field} is required"
            )

    for field in (
        "type",
        "metric_name",
        "severity",
        "status",
        "explanation",
        "why_it_matters",
        "recommendation",
    ):
        if not isinstance(item[field], str):
            raise SchemaValidationError(
                f"diagnosis_report.evidence[{index}].{field} must be a string"
            )

    if item["severity"] not in {"low", "medium", "high", "critical"}:
        raise SchemaValidationError(
            f"diagnosis_report.evidence[{index}].severity is invalid"
        )
    if item["status"] not in {"passed", "warning", "failed", "skipped"}:
        raise SchemaValidationError(
            f"diagnosis_report.evidence[{index}].status is invalid"
        )
    if not isinstance(item.get("suspected_causes", []), list):
        raise SchemaValidationError(
            f"diagnosis_report.evidence[{index}].suspected_causes must be a list"
        )
    for cause_index, cause in enumerate(item.get("suspected_causes", [])):
        if not isinstance(cause, str):
            raise SchemaValidationError(
                "diagnosis_report.evidence"
                f"[{index}].suspected_causes[{cause_index}] must be a string"
            )
    if not isinstance(item.get("raw_context", {}), dict):
        raise SchemaValidationError(
            f"diagnosis_report.evidence[{index}].raw_context must be an object"
        )


def _validate_optional_list(
    data: JsonDict,
    field: str,
    *,
    item_type: type,
    prefix: str = "guard_analysis",
) -> None:
    if field not in data:
        return

    values = data[field]
    if not isinstance(values, list):
        raise SchemaValidationError(f"{prefix}.{field} must be a list")

    for index, value in enumerate(values):
        if not isinstance(value, item_type):
            expected = "object" if item_type is dict else item_type.__name__
            raise SchemaValidationError(
                f"{prefix}.{field}[{index}] must be a {expected}"
            )
