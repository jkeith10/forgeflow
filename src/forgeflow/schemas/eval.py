"""Pydantic models for eval suites + a YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    # Mapping of dotted-path -> expected value.
    # Value may be a scalar (equality) or an operator dict, e.g. {contains: "x"}.
    expect: dict[str, Any] = Field(default_factory=dict)


class EvalSuite(BaseModel):
    name: str
    workflow: str
    provider: str | None = None
    cases: list[EvalCase]


def load_eval(path: str | Path) -> EvalSuite:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Eval suite not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EvalSuite.model_validate(data)
