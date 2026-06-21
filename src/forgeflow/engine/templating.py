"""Jinja2-backed templating.

Two modes:
- `render_text`  -> always returns a string (used for prompts / messages).
- `render_value` -> if the value is exactly one `{{ expr }}`, the native Python
   result is preserved (dict, list, number). Otherwise it renders as a string.
   Recurses into dicts/lists so the `outputs:` mapping can mix both.
"""

from __future__ import annotations

import re
from typing import Any

from jinja2 import ChainableUndefined, Environment

_env = Environment(undefined=ChainableUndefined, autoescape=False)
_SINGLE = re.compile(r"^\s*\{\{(.+?)\}\}\s*$", re.S)


def render_text(template: str, ctx: dict[str, Any]) -> str:
    return _env.from_string(template).render(**ctx)


def _eval_expr(expr: str, ctx: dict[str, Any]) -> Any:
    return _env.compile_expression(expr)(**ctx)


def render_value(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: render_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [render_value(v, ctx) for v in value]
    if not isinstance(value, str):
        return value

    m = _SINGLE.match(value)
    if m:  # single expression -> keep native type
        return _eval_expr(m.group(1).strip(), ctx)
    if "{{" in value:
        return render_text(value, ctx)
    return value
