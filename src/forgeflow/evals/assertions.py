"""Assertion helpers for evals.

An expectation maps a dotted path (resolved against the run context) to either a
scalar (equality) or an operator dict such as ``{contains: "x"}`` or ``{gte: 70}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AssertionResult:
    path: str
    passed: bool
    expected: Any
    actual: Any


def resolve_path(ctx: dict[str, Any], path: str) -> Any:
    cur: Any = ctx
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            break
    return cur


def _compare(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and len(expected) == 1:
        (op, value), = expected.items()
        op = op.lower()
        if op == "equals":
            return actual == value
        if op == "contains":
            return value in actual if actual is not None else False
        if op == "icontains":
            return str(value).lower() in str(actual).lower()
        if op == "gte":
            return actual is not None and actual >= value
        if op == "lte":
            return actual is not None and actual <= value
        if op == "in":
            return actual in value
        if op == "not_empty":
            return bool(actual)
        raise ValueError(f"Unknown assertion operator: {op}")
    # Scalar -> equality (case-insensitive for strings).
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


def check(ctx: dict[str, Any], path: str, expected: Any) -> AssertionResult:
    actual = resolve_path(ctx, path)
    return AssertionResult(path=path, passed=_compare(actual, expected), expected=expected, actual=actual)
