"""Adapters for external validation result schemas."""

from __future__ import annotations

from typing import Any


def normalize_lab_compare_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize likely InferEdgeLab compare result aliases into AIGuard keys."""

    source = _first_nested_source(raw)
    normalized = dict(raw)

    _set_first_present(
        normalized,
        "shape_match",
        source,
        raw,
        ("shape_match", "shape_matched", "shapes_match", "input_shape_match"),
    )
    _set_first_present(
        normalized,
        "run_config_match",
        source,
        raw,
        (
            "run_config_match",
            "run_config_matched",
            "config_match",
            "run_configuration_match",
        ),
    )
    _set_first_present(
        normalized,
        "latency_delta_pct",
        source,
        raw,
        (
            "latency_delta_pct",
            "mean_delta_pct",
            "mean_latency_delta_pct",
            "latency_change_pct",
        ),
    )
    _set_first_present(
        normalized,
        "overall_judgement",
        source,
        raw,
        ("overall_judgement", "overall_judgment", "judgement", "judgment"),
    )
    _set_first_present(
        normalized,
        "mean_judgement",
        source,
        raw,
        ("mean_judgement", "mean_judgment", "latency_judgement", "latency_judgment"),
    )
    _set_first_present(
        normalized,
        "comparison_mode",
        source,
        raw,
        ("comparison_mode", "mode"),
    )
    _set_first_present(
        normalized,
        "precision_pair",
        source,
        raw,
        ("precision_pair", "precision_comparison", "precision_mode"),
    )

    _normalize_accuracy_fields(normalized, source, raw)
    return normalized


def _first_nested_source(raw: dict[str, Any]) -> dict[str, Any]:
    for key in ("compare_result", "comparison", "result"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def _set_first_present(
    normalized: dict[str, Any],
    standard_key: str,
    source: dict[str, Any],
    raw: dict[str, Any],
    aliases: tuple[str, ...],
) -> None:
    value = _first_present(source, raw, aliases)
    if value is not None:
        normalized[standard_key] = value


def _first_present(
    source: dict[str, Any],
    raw: dict[str, Any],
    aliases: tuple[str, ...],
) -> Any:
    for data in (source, raw):
        for alias in aliases:
            if alias in data:
                return data.get(alias)
    return None


def _normalize_accuracy_fields(
    normalized: dict[str, Any],
    source: dict[str, Any],
    raw: dict[str, Any],
) -> None:
    accuracy = _first_present(source, raw, ("accuracy",))
    if accuracy is not None:
        normalized["accuracy"] = accuracy

    base_accuracy = _first_accuracy_value(
        source,
        raw,
        direct_keys=("base_accuracy",),
        nested_paths=(
            ("base", "accuracy"),
            ("metrics", "base_accuracy"),
            ("accuracy", "base"),
        ),
    )
    candidate_accuracy = _first_accuracy_value(
        source,
        raw,
        direct_keys=("candidate_accuracy", "new_accuracy"),
        nested_paths=(
            ("candidate", "accuracy"),
            ("new", "accuracy"),
            ("metrics", "candidate_accuracy"),
            ("metrics", "new_accuracy"),
            ("accuracy", "candidate"),
            ("accuracy", "new"),
        ),
    )
    accuracy_delta = _first_accuracy_value(
        source,
        raw,
        direct_keys=("accuracy_delta",),
        nested_paths=(
            ("metrics", "accuracy_delta"),
            ("accuracy", "delta"),
        ),
    )

    if base_accuracy is not None:
        normalized["base_accuracy"] = base_accuracy
    if candidate_accuracy is not None:
        normalized["candidate_accuracy"] = candidate_accuracy
    if accuracy_delta is None and _is_number(base_accuracy) and _is_number(candidate_accuracy):
        accuracy_delta = candidate_accuracy - base_accuracy
    if accuracy_delta is not None:
        normalized["accuracy_delta"] = accuracy_delta


def _first_accuracy_value(
    source: dict[str, Any],
    raw: dict[str, Any],
    direct_keys: tuple[str, ...],
    nested_paths: tuple[tuple[str, str], ...],
) -> Any:
    direct_value = _first_present(source, raw, direct_keys)
    if direct_value is not None:
        return direct_value

    for data in (source, raw):
        for parent_key, child_key in nested_paths:
            value = data.get(parent_key)
            if isinstance(value, dict) and child_key in value:
                return value.get(child_key)
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
