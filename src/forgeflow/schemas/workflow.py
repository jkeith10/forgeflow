"""Pydantic models for the ForgeFlow workflow spec + a YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

StepType = Literal["llm", "human_approval", "tool", "transform"]


class InputSpec(BaseModel):
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str | None = None


class Step(BaseModel):
    id: str
    type: StepType

    # Conditional execution. Truthy -> run, falsy -> skip. Supports `{{ }}`.
    when: str | None = None

    # llm steps
    prompt: str | None = None
    system: str | None = None
    # When set, the step is parsed as JSON and these keys are expected.
    output: list[str] | None = None
    provider: str | None = None
    model: str | None = None
    retries: int = 0

    # human_approval steps
    message: str | None = None

    # tool steps
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)

    # transform steps (pure templating, no LLM call)
    value: Any = None

    @field_validator("retries")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("retries must be >= 0")
        return v


class Workflow(BaseModel):
    name: str
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    inputs: dict[str, InputSpec] = Field(default_factory=dict)
    # Sample inputs used when `run` is called without explicit inputs (great demos).
    example_inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[Step]
    outputs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("steps")
    @classmethod
    def _unique_step_ids(cls, steps: list[Step]) -> list[Step]:
        seen: set[str] = set()
        for s in steps:
            if s.id in seen:
                raise ValueError(f"duplicate step id: {s.id}")
            seen.add(s.id)
        return steps


def load_workflow(path: str | Path) -> Workflow:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Workflow.model_validate(data)
