"""Step executors: llm, tool, transform.

Human-approval steps are handled by the runner because they involve I/O.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from forgeflow.engine.templating import render_text, render_value
from forgeflow.providers import get_provider
from forgeflow.schemas.workflow import Step
from forgeflow.tools.registry import ToolRegistry

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


class StepError(RuntimeError):
    """Raised when a step cannot produce a usable result."""


def _parse_json(content: str) -> Any:
    cleaned = _FENCE.sub("", content.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as err:
        # Last resort: grab the first {...} block.
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match:
            return json.loads(match.group(0))
        raise StepError(f"Step expected JSON but got: {content[:200]!r}") from err


def execute_llm(
    step: Step,
    ctx: dict[str, Any],
    *,
    provider_name: str | None,
    model: str | None,
) -> Any:
    if not step.prompt:
        raise StepError(f"llm step '{step.id}' is missing a prompt")

    provider = get_provider(step.provider or provider_name, step.model or model)
    prompt = render_text(step.prompt, ctx)
    system = render_text(step.system, ctx) if step.system else None

    last_err: Exception | None = None
    for _ in range(step.retries + 1):
        try:
            resp = provider.complete(prompt, system=system, json_fields=step.output)
            if step.output:
                return _parse_json(resp.content)
            return resp.content
        except StepError as err:  # retry only on parse failures
            last_err = err
    raise last_err  # type: ignore[misc]


def execute_tool(step: Step, ctx: dict[str, Any], registry: ToolRegistry) -> Any:
    if not step.tool:
        raise StepError(f"tool step '{step.id}' is missing a tool name")
    args = render_value(step.args, ctx)
    return registry.call(step.tool, args)


def execute_transform(step: Step, ctx: dict[str, Any]) -> Any:
    if step.value is None:
        raise StepError(f"transform step '{step.id}' is missing a value")
    return render_value(step.value, ctx)


def execute_inner(
    step: Step,
    ctx: dict[str, Any],
    *,
    provider_name: str | None,
    registry: ToolRegistry,
) -> Any:
    """Run a single llm/tool/transform step (used for `map` items)."""
    if step.type == "llm":
        return execute_llm(step, ctx, provider_name=provider_name, model=None)
    if step.type == "tool":
        return execute_tool(step, ctx, registry)
    if step.type == "transform":
        return execute_transform(step, ctx)
    raise StepError(f"map inner step type '{step.type}' is not supported")


def execute_map(
    step: Step,
    ctx: dict[str, Any],
    *,
    provider_name: str | None,
    registry: ToolRegistry,
    max_workers: int = 8,
) -> list[Any]:
    """Fan out `step` over a list, concurrently, preserving input order."""
    if step.over is None or step.step is None:
        raise StepError(f"map step '{step.id}' needs both 'over' and 'step'")
    items = render_value(step.over, ctx)
    if not isinstance(items, list):
        raise StepError(f"map step '{step.id}': 'over' must resolve to a list, got {type(items).__name__}")
    if not items:
        return []

    inner = step.step
    as_name = step.item_as

    def run_one(pair: tuple[int, Any]) -> Any:
        index, item = pair
        item_ctx = {**ctx, as_name: item, "item": item, "index": index}
        return execute_inner(inner, item_ctx, provider_name=provider_name, registry=registry)

    workers = max(1, min(max_workers, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run_one, enumerate(items)))
