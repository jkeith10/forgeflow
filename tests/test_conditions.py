from forgeflow.engine.conditions import evaluate_condition
from forgeflow.engine.templating import render_text, render_value


def _ctx():
    return {
        "inputs": {"message": "hello"},
        "steps": {"classify": {"output": {"urgency": "high", "score": 82}}},
    }


def test_condition_wrapped_and_bare():
    ctx = _ctx()
    assert evaluate_condition("{{ steps.classify.output.urgency == 'high' }}", ctx) is True
    assert evaluate_condition("steps.classify.output.urgency == 'low'", ctx) is False


def test_condition_numeric():
    ctx = _ctx()
    assert evaluate_condition("{{ steps.classify.output.score >= 70 }}", ctx) is True


def test_condition_missing_path_is_falsy():
    ctx = _ctx()
    # ChainableUndefined keeps attribute access from blowing up.
    assert evaluate_condition("{{ steps.missing.output.x == 'y' }}", ctx) is False


def test_render_value_preserves_native_type():
    ctx = _ctx()
    out = render_value("{{ steps.classify.output }}", ctx)
    assert isinstance(out, dict)
    assert out["score"] == 82


def test_render_text_interpolates():
    ctx = _ctx()
    assert render_text("urgency is {{ steps.classify.output.urgency }}", ctx) == "urgency is high"
