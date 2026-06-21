"""Project scaffolding (`forgeflow init`) and the template catalog."""

from __future__ import annotations

from pathlib import Path

# Catalog shown by `forgeflow templates`. These ship in the repo's examples/.
TEMPLATE_CATALOG: list[tuple[str, str]] = [
    ("support_triage", "Classify an inbound customer message, gate urgent cases on human approval, draft a reply."),
    ("sales_lead_qualifier", "Score a lead, recommend the next action, draft a tailored follow-up."),
    ("meeting_notes_to_action_plan", "Turn rough meeting notes into decisions, owners, and an action plan."),
    ("home_service_dispatch", "Triage an HVAC/plumbing/electrical request into CSR booking + tech notes."),
]

_STARTER_WORKFLOW = """\
name: hello_triage
description: Starter workflow — classify a message and draft a reply (mock-friendly).

example_inputs:
  message: "My AC is broken, there's no cooling at all, and no one has called me back after three days."

inputs:
  message:
    type: string
    required: true

steps:
  - id: classify
    type: llm
    output: [category, urgency, summary]
    prompt: |
      Read the customer message below and classify it.
      Message:
      {{ inputs.message }}

  - id: approval
    type: human_approval
    when: "{{ steps.classify.output.urgency == 'high' }}"
    message: "High-urgency issue detected — approve before drafting a reply."

  - id: draft_reply
    type: llm
    prompt: |
      Write a short, professional reply for this classified message:
      {{ steps.classify.output }}

outputs:
  category: "{{ steps.classify.output.category }}"
  urgency: "{{ steps.classify.output.urgency }}"
  reply: "{{ steps.draft_reply.output }}"
"""

_STARTER_EVAL = """\
name: hello_triage_eval
workflow: ../hello_triage.yaml

cases:
  - name: hot_ac_complaint
    inputs:
      message: "My AC is broken, there's no cooling at all, and no one has called me back after three days."
    expect:
      steps.classify.output.urgency: high
      steps.classify.output.category: complaint
"""


def _write(path: Path, content: str, created: list[str]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def init_project(target: Path) -> list[str]:
    target = Path(target)
    created: list[str] = []
    _write(target / "examples" / "hello_triage.yaml", _STARTER_WORKFLOW, created)
    _write(target / "examples" / "evals" / "hello_triage_eval.yaml", _STARTER_EVAL, created)
    return created


def list_templates() -> list[tuple[str, str]]:
    return TEMPLATE_CATALOG
