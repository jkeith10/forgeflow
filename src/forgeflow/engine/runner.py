"""The workflow engine.

Runs steps in order, evaluating conditions, executing each step type, recording
every output, and persisting the whole run as an audit log. Human-approval steps
call an `approver` callback; the default auto-approves so non-interactive runs
(CI, evals, mock demos) never block.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from forgeflow.engine.conditions import evaluate_condition
from forgeflow.engine.steps import (
    execute_llm,
    execute_tool,
    execute_transform,
)
from forgeflow.engine.templating import render_value
from forgeflow.schemas.workflow import Step, Workflow
from forgeflow.tools.registry import ToolRegistry, default_registry

Approver = Callable[[str], bool]


def _auto_approve(_: str) -> bool:
    return True


@dataclass
class StepResult:
    id: str
    type: str
    status: str  # completed | skipped | rejected | error
    output: Any = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunResult:
    run_id: str
    workflow: str
    status: str  # completed | halted | error
    provider: str
    created_at: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)
    steps: list[StepResult] = field(default_factory=list)

    def step(self, step_id: str) -> StepResult | None:
        return next((s for s in self.steps if s.id == step_id), None)


def _make_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"run_{stamp}_{uuid.uuid4().hex[:6]}"


def _resolve_inputs(workflow: Workflow, inputs: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = dict(workflow.example_inputs)
    resolved.update({k: v for k, v in inputs.items() if v is not None})

    for name, spec in workflow.inputs.items():
        if name not in resolved or resolved[name] is None:
            if spec.default is not None:
                resolved[name] = spec.default
            elif spec.required:
                raise ValueError(
                    f"Missing required input '{name}'. "
                    f"Pass it with --input {name}=... or add it to example_inputs."
                )
    return resolved


def run_workflow(
    workflow: Workflow,
    inputs: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
    mock: bool = False,
    approver: Approver | None = None,
    registry: ToolRegistry | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    store: bool = True,
) -> RunResult:
    """Execute a workflow and return a :class:`RunResult`.

    Parameters mirror the CLI: ``mock=True`` forces the deterministic provider,
    ``approver`` decides human-approval gates, ``on_event`` streams progress.
    """
    inputs = inputs or {}
    registry = registry or default_registry
    approver = approver or _auto_approve
    provider_name = "mock" if mock else (provider or workflow.provider)
    emit = on_event or (lambda *_: None)

    resolved_inputs = _resolve_inputs(workflow, inputs)
    result = RunResult(
        run_id=_make_run_id(),
        workflow=workflow.name,
        status="completed",
        provider=provider_name or "mock",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        inputs=resolved_inputs,
    )
    emit("run_start", {"workflow": workflow.name, "run_id": result.run_id})

    ctx: dict[str, Any] = {
        "inputs": resolved_inputs,
        "steps": {},
        "memory": _MemoryView(),
    }

    for step in workflow.steps:
        if step.when is not None and not evaluate_condition(step.when, ctx):
            result.steps.append(StepResult(step.id, step.type, "skipped"))
            ctx["steps"][step.id] = {"output": None, "skipped": True}
            emit("step_skipped", {"id": step.id})
            continue

        if step.type == "human_approval":
            message = render_value(step.message or "Approval required.", ctx)
            emit("approval_required", {"id": step.id, "message": message})
            approved = approver(str(message))
            if not approved:
                result.steps.append(
                    StepResult(step.id, step.type, "rejected", detail=str(message))
                )
                ctx["steps"][step.id] = {"output": False, "approved": False}
                result.status = "halted"
                emit("run_halted", {"id": step.id})
                break
            result.steps.append(StepResult(step.id, step.type, "completed", output=True))
            ctx["steps"][step.id] = {"output": True, "approved": True}
            emit("step_done", {"id": step.id, "type": step.type})
            continue

        try:
            output = _execute(step, ctx, provider_name, registry)
        except Exception as err:  # surface a clean, inspectable failure
            result.steps.append(StepResult(step.id, step.type, "error", detail=str(err)))
            ctx["steps"][step.id] = {"output": None, "error": str(err)}
            result.status = "error"
            emit("step_error", {"id": step.id, "error": str(err)})
            break

        result.steps.append(StepResult(step.id, step.type, "completed", output=output))
        ctx["steps"][step.id] = {"output": output}
        emit("step_done", {"id": step.id, "type": step.type})

    if result.status == "completed":
        result.outputs = render_value(workflow.outputs, ctx) if workflow.outputs else {}

    if store:
        from forgeflow.logging.runs import save_run

        save_run(result)
    emit("run_end", {"status": result.status, "run_id": result.run_id})
    return result


def _execute(
    step: Step,
    ctx: dict[str, Any],
    provider_name: str | None,
    registry: ToolRegistry,
) -> Any:
    if step.type == "llm":
        return execute_llm(step, ctx, provider_name=provider_name, model=None)
    if step.type == "tool":
        return execute_tool(step, ctx, registry)
    if step.type == "transform":
        return execute_transform(step, ctx)
    raise ValueError(f"Unsupported step type: {step.type}")


class _MemoryView:
    """Read-only memory access inside templates: ``{{ memory['policy'] }}``."""

    def __getitem__(self, key: str) -> Any:
        from forgeflow.memory.sqlite import memory_get

        return memory_get(key)

    def get(self, key: str, default: Any = None) -> Any:
        from forgeflow.memory.sqlite import memory_get

        val = memory_get(key)
        return val if val is not None else default
