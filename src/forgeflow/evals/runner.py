"""Run eval suites against workflows and report pass/fail."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forgeflow.engine.runner import run_workflow
from forgeflow.evals.assertions import AssertionResult, check
from forgeflow.schemas.eval import EvalSuite, load_eval
from forgeflow.schemas.workflow import load_workflow


@dataclass
class CaseResult:
    name: str
    passed: bool
    assertions: list[AssertionResult] = field(default_factory=list)
    run_id: str = ""
    error: str | None = None


@dataclass
class SuiteResult:
    name: str
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total and self.total > 0


def _assertion_context(result: Any) -> dict[str, Any]:
    return {
        "inputs": result.inputs,
        "outputs": result.outputs,
        "steps": {s.id: {"output": s.output} for s in result.steps},
    }


def run_eval_suite(suite: EvalSuite, *, base_dir: Path, mock: bool = True) -> SuiteResult:
    workflow_path = (base_dir / suite.workflow).resolve()
    workflow = load_workflow(workflow_path)
    provider = None if mock else suite.provider

    out = SuiteResult(name=suite.name)
    for case in suite.cases:
        try:
            run = run_workflow(
                workflow,
                case.inputs,
                provider=provider,
                mock=mock,
                store=False,
            )
        except Exception as err:  # case fails loudly but suite continues
            out.cases.append(CaseResult(name=case.name, passed=False, error=str(err)))
            continue

        ctx = _assertion_context(run)
        asserts = [check(ctx, path, expected) for path, expected in case.expect.items()]
        passed = all(a.passed for a in asserts) and run.status != "error"
        out.cases.append(
            CaseResult(name=case.name, passed=passed, assertions=asserts, run_id=run.run_id)
        )
    return out


def run_eval_file(path: str | Path, *, mock: bool = True) -> SuiteResult:
    path = Path(path)
    suite = load_eval(path)
    return run_eval_suite(suite, base_dir=path.parent, mock=mock)
