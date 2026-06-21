"""Regenerate docs/demo.svg — a real terminal recording of the mock demo.

Runs the support_triage workflow with the deterministic mock provider and
exports the exact CLI rendering to an SVG (no external tools, no API keys):

    python scripts/gen_demo_svg.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Use a throwaway state dir so generating the asset never pollutes real runs.
os.environ.setdefault("FORGEFLOW_HOME", str(Path(tempfile.mkdtemp()) / ".forgeflow"))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402

import forgeflow.cli as cli  # noqa: E402
from forgeflow.engine.runner import run_workflow  # noqa: E402
from forgeflow.schemas.workflow import load_workflow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo.svg"


def main() -> None:
    rec = Console(record=True, width=74, file=open(os.devnull, "w", encoding="utf-8"))
    cli.console = rec  # the CLI's renderers read this module-level console

    rec.print("$ forgeflow run examples/support_triage.yaml --mock\n", style="dim")
    rec.print(Panel.fit("Running workflow: [bold]support_triage[/]", border_style="cyan"))

    wf = load_workflow(ROOT / "examples" / "support_triage.yaml")
    result = run_workflow(wf, mock=True, approver=lambda _: True)
    cli._render_run(result)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    rec.save_svg(str(OUT), title="ForgeFlow — mock demo")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
