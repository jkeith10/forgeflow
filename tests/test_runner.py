from forgeflow.engine.runner import run_workflow
from forgeflow.schemas.workflow import load_workflow


def test_support_triage_runs_end_to_end(examples_dir):
    wf = load_workflow(examples_dir / "support_triage.yaml")
    result = run_workflow(wf, mock=True)  # uses example_inputs (high urgency)

    assert result.status == "completed"
    classify = result.step("classify").output
    assert classify["urgency"] == "high"
    assert classify["category"] == "complaint"
    # High urgency -> approval step ran and auto-approved.
    assert result.step("approval").status == "completed"
    assert result.outputs["reply"]


def test_low_urgency_skips_approval(examples_dir):
    wf = load_workflow(examples_dir / "support_triage.yaml")
    result = run_workflow(wf, {"message": "What are your hours on Saturday?"}, mock=True)

    assert result.step("classify").output["urgency"] == "low"
    assert result.step("approval").status == "skipped"
    assert result.status == "completed"


def test_rejected_approval_halts_run(examples_dir):
    wf = load_workflow(examples_dir / "support_triage.yaml")
    result = run_workflow(wf, mock=True, approver=lambda _: False)

    assert result.status == "halted"
    assert result.step("approval").status == "rejected"
    # draft_response never ran
    assert result.step("draft_response") is None


def test_run_is_persisted(examples_dir):
    from forgeflow.logging.runs import get_run

    wf = load_workflow(examples_dir / "home_service_dispatch.yaml")
    result = run_workflow(wf, mock=True)
    stored = get_run(result.run_id)

    assert stored is not None
    assert stored["workflow"] == "home_service_dispatch"
    assert stored["outputs"]["trade"] == "hvac"
