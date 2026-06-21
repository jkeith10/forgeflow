from forgeflow.engine.runner import run_workflow
from forgeflow.schemas.workflow import load_workflow


def test_map_classifies_each_in_order(examples_dir):
    wf = load_workflow(examples_dir / "bulk_triage.yaml")
    result = run_workflow(wf, mock=True)

    out = result.step("classify_all").output
    assert isinstance(out, list)
    assert len(out) == 3
    # Order is preserved despite concurrent execution.
    assert out[0]["category"] == "complaint"
    assert out[0]["urgency"] == "high"
    assert out[1]["category"] == "question"
    assert out[2]["category"] == "billing"
    assert result.outputs["results"][2]["category"] == "billing"


def test_map_over_empty_list_returns_empty(examples_dir):
    wf = load_workflow(examples_dir / "bulk_triage.yaml")
    result = run_workflow(wf, {"messages": []}, mock=True)
    assert result.step("classify_all").output == []
