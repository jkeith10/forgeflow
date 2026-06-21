"""ForgeFlow command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure Unicode output works on legacy Windows consoles (cp1252) so Rich's
# ✓/→ glyphs don't crash the CLI.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from forgeflow import __version__
from forgeflow.engine.runner import RunResult, run_workflow
from forgeflow.evals.runner import run_eval_file
from forgeflow.scaffold import init_project, list_templates
from forgeflow.schemas.workflow import load_workflow

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ForgeFlow — turn prompt chains into tested, observable, human-gated AI workflows.",
)
memory_app = typer.Typer(no_args_is_help=True, help="Local key/value memory (facts, policies, notes).")
app.add_typer(memory_app, name="memory")

console = Console()

_STATUS_STYLE = {
    "completed": "green",
    "halted": "yellow",
    "error": "red",
    "skipped": "dim",
    "rejected": "red",
}


def _parse_inputs(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(f"--input expects key=value, got: {pair!r}")
        key, value = pair.split("=", 1)
        out[key.strip()] = value
    return out


def _render_run(result: RunResult) -> None:
    for s in result.steps:
        if s.status == "completed":
            console.print(f"[green]✓[/] step [bold]{s.id}[/] [dim]({s.type})[/]")
        elif s.status == "skipped":
            console.print(f"[dim]→ step {s.id} skipped (condition not met)[/]")
        elif s.status == "rejected":
            console.print(f"[red]✗[/] approval rejected at [bold]{s.id}[/] — run halted")
        elif s.status == "error":
            console.print(f"[red]✗[/] step [bold]{s.id}[/] errored: {s.detail}")

    style = _STATUS_STYLE.get(result.status, "white")
    console.print()
    console.print(
        Panel.fit(
            f"Run ID: [bold]{result.run_id}[/]\n"
            f"Status: [{style}]{result.status}[/]\n"
            f"Provider: {result.provider}",
            title="Result",
            border_style=style,
        )
    )
    if result.outputs:
        console.print("[bold]Outputs[/]")
        console.print(Syntax(json.dumps(result.outputs, indent=2), "json", theme="ansi_dark"))


def _approver(message: str) -> bool:
    console.print(f"[yellow]![/] [bold]Human approval required:[/] {message}")
    return typer.confirm("Approve and continue?", default=True)


@app.command()
def version() -> None:
    """Print the ForgeFlow version."""
    console.print(f"ForgeFlow [bold]{__version__}[/]")


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to scaffold the project into."),
) -> None:
    """Scaffold a new ForgeFlow project (examples + a starter workflow)."""
    created = init_project(Path(path))
    console.print(
        Panel.fit(
            "\n".join(f"[green]+[/] {p}" for p in created)
            or "[dim]Nothing to create — files already exist.[/]",
            title="ForgeFlow project initialized",
            border_style="green",
        )
    )
    console.print("\nNext: [bold]forgeflow run examples/support_triage.yaml --mock[/]")


@app.command()
def run(
    workflow_path: str = typer.Argument(..., help="Path to a workflow YAML file."),
    input: list[str] = typer.Option(  # noqa: A002 - matches CLI surface
        [], "--input", "-i", help="Input as key=value (repeatable)."
    ),
    mock: bool = typer.Option(False, "--mock", help="Use the deterministic mock provider (no API keys)."),
    provider: str | None = typer.Option(None, "--provider", help="Override provider: mock|openai|anthropic."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-approve all human-approval gates."),
) -> None:
    """Run a workflow."""
    workflow = load_workflow(workflow_path)
    console.print(Panel.fit(f"Running workflow: [bold]{workflow.name}[/]", border_style="cyan"))

    approver = (lambda _: True) if yes else _approver
    result = run_workflow(
        workflow,
        _parse_inputs(input),
        provider=provider,
        mock=mock,
        approver=approver,
    )
    _render_run(result)
    if result.status == "error":
        raise typer.Exit(code=1)


@app.command()
def eval(  # noqa: A001 - intentional command name
    eval_path: str = typer.Argument(..., help="Path to an eval suite YAML file."),
    mock: bool = typer.Option(True, "--mock/--live", help="Run evals against the mock provider (default)."),
) -> None:
    """Run an eval suite and report pass/fail."""
    suite = run_eval_file(eval_path, mock=mock)

    table = Table(title=f"Eval: {suite.name}", show_lines=False)
    table.add_column("Case", style="bold")
    table.add_column("Result")
    table.add_column("Assertions")
    for case in suite.cases:
        if case.error:
            table.add_row(case.name, "[red]ERROR[/]", case.error)
            continue
        mark = "[green]PASS[/]" if case.passed else "[red]FAIL[/]"
        details = "  ".join(
            f"[green]✓[/]{a.path}" if a.passed else f"[red]✗[/]{a.path}(={a.actual!r})"
            for a in case.assertions
        )
        table.add_row(case.name, mark, details)
    console.print(table)

    style = "green" if suite.all_passed else "red"
    console.print(Panel.fit(f"{suite.passed}/{suite.total} cases passed", border_style=style))
    if not suite.all_passed:
        raise typer.Exit(code=1)


@app.command()
def runs(limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show.")) -> None:
    """List recent workflow runs."""
    from forgeflow.logging.runs import list_runs

    rows = list_runs(limit)
    if not rows:
        console.print("[dim]No runs yet. Try: forgeflow run examples/support_triage.yaml --mock[/]")
        return
    table = Table(title="Recent runs")
    table.add_column("Run ID", style="bold", no_wrap=True, overflow="fold")
    table.add_column("Workflow")
    table.add_column("Status")
    table.add_column("Provider")
    table.add_column("When")
    for r in rows:
        style = _STATUS_STYLE.get(r["status"], "white")
        table.add_row(r["run_id"], r["workflow"], f"[{style}]{r['status']}[/]", r["provider"] or "-", r["created_at"])
    console.print(table)


@app.command()
def inspect(run_id: str = typer.Argument(..., help="Run ID to inspect.")) -> None:
    """Show the full trace of a previous run."""
    from forgeflow.logging.runs import get_run

    data = get_run(run_id)
    if not data:
        console.print(f"[red]No run found with id {run_id}[/]")
        raise typer.Exit(code=1)

    console.print(Panel.fit(
        f"[bold]{data['workflow']}[/]\nStatus: {data['status']}  Provider: {data['provider']}\n{data['created_at']}",
        title=run_id, border_style=_STATUS_STYLE.get(data["status"], "white"),
    ))
    console.print("[bold]Inputs[/]")
    console.print(Syntax(json.dumps(data["inputs"], indent=2), "json", theme="ansi_dark"))
    console.print("[bold]Steps[/]")
    table = Table()
    table.add_column("Step", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Output (truncated)")
    for s in data["steps"]:
        out = json.dumps(s.get("output"))
        out = out if len(out) <= 80 else out[:77] + "..."
        table.add_row(s["id"], s["type"], s["status"], out)
    console.print(table)
    if data["outputs"]:
        console.print("[bold]Outputs[/]")
        console.print(Syntax(json.dumps(data["outputs"], indent=2), "json", theme="ansi_dark"))


@app.command()
def templates() -> None:
    """List built-in workflow templates and registered tools."""
    tmpls = list_templates()
    table = Table(title="Workflow templates")
    table.add_column("Template", style="bold")
    table.add_column("Description")
    for name, desc in tmpls:
        table.add_row(name, desc)
    console.print(table)

    from forgeflow.tools.registry import default_registry

    ttable = Table(title="Built-in tools")
    ttable.add_column("Tool", style="bold")
    ttable.add_column("Description")
    for tool in default_registry.list():
        ttable.add_row(tool.name, tool.description)
    console.print(ttable)


@memory_app.command("set")
def memory_set_cmd(key: str, value: str) -> None:
    """Store a fact: forgeflow memory set <key> <value>"""
    from forgeflow.memory.sqlite import memory_set

    memory_set(key, value)
    console.print(f"[green]✓[/] saved [bold]{key}[/]")


@memory_app.command("get")
def memory_get_cmd(key: str) -> None:
    """Read a fact by key."""
    from forgeflow.memory.sqlite import memory_get

    value = memory_get(key)
    if value is None:
        console.print(f"[yellow]No value for[/] {key}")
        raise typer.Exit(code=1)
    console.print(value)


@memory_app.command("list")
def memory_list_cmd() -> None:
    """List all stored facts."""
    from forgeflow.memory.sqlite import memory_list

    items = memory_list()
    if not items:
        console.print("[dim]Memory is empty.[/]")
        return
    table = Table(title="Memory")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_column("Updated")
    for item in items:
        table.add_row(item.key, item.value, item.updated_at)
    console.print(table)


@memory_app.command("delete")
def memory_delete_cmd(key: str) -> None:
    """Delete a fact by key."""
    from forgeflow.memory.sqlite import memory_delete

    if memory_delete(key):
        console.print(f"[green]✓[/] deleted [bold]{key}[/]")
    else:
        console.print(f"[yellow]No value for[/] {key}")


if __name__ == "__main__":  # pragma: no cover
    app()
