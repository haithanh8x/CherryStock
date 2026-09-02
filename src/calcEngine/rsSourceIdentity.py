"""Stable source identity helpers for R/S V2.4 research and attribution."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, TypeVar

T = TypeVar("T")


def canonical_source_key(source_code: str) -> str:
    """Return a stable, uppercase research identity for one runtime source code."""
    code = str(source_code).strip().upper()
    if not code:
        raise ValueError("source_code must be non-empty")

    if code.endswith("_CONF"):
        code = code[:-5]

    if re.fullmatch(r"SWING_HIGH_\d{8}", code):
        return "SWING_HIGH"
    if re.fullmatch(r"SWING_LOW_\d{8}", code):
        return "SWING_LOW"
    if re.fullmatch(r"VP_HVN_\d+", code):
        return "VP_HVN"
    if re.fullmatch(r"VP_LVN_\d+", code):
        return "VP_LVN"
    return code


def normalize_source_key_set(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(sorted({canonical_source_key(value) for value in values}))


def source_key_for_object(value: Any) -> str:
    source_code = getattr(value, "source_code", None)
    if source_code is None:
        raise ValueError("source object must expose source_code")
    return canonical_source_key(str(source_code))


def filter_source_objects(
    values: Iterable[T],
    *,
    included_source_keys: Iterable[str] | None = None,
    excluded_source_keys: Iterable[str] | None = None,
) -> list[T]:
    """Apply canonical include/exclude filters without changing object contracts."""
    include = set(normalize_source_key_set(included_source_keys))
    exclude = set(normalize_source_key_set(excluded_source_keys))
    overlap = include & exclude
    if overlap:
        raise ValueError(f"source keys cannot be both included and excluded: {sorted(overlap)}")

    result: list[T] = []
    for value in values:
        key = source_key_for_object(value)
        if include and key not in include:
            continue
        if key in exclude:
            continue
        result.append(value)
    return result
