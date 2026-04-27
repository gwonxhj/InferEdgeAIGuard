"""Minimal schema utilities for YOLO-style detection output JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


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
