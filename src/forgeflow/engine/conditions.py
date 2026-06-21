"""Evaluate `when:` conditions to a boolean."""

from __future__ import annotations

import re
from typing import Any

from jinja2 import ChainableUndefined, Environment

_env = Environment(undefined=ChainableUndefined, autoescape=False)
_SINGLE = re.compile(r"^\s*\{\{(.+?)\}\}\s*$", re.S)


def evaluate_condition(expr: str, ctx: dict[str, Any]) -> bool:
    """Return the truthiness of a `when` expression.

    Accepts both wrapped (`{{ a == b }}`) and bare (`a == b`) forms.
    """
    expr = expr.strip()
    m = _SINGLE.match(expr)
    if m:
        expr = m.group(1).strip()
    result = _env.compile_expression(expr)(**ctx)
    return bool(result)
