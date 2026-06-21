"""Adapter tests for the real providers.

These inject a fake SDK client so we exercise request-building and response
parsing without API keys or network. They're skipped if the optional SDK isn't
installed (e.g. in the default CI matrix), and run locally with
`pip install -e ".[all]"`.
"""

from __future__ import annotations

import pytest

from forgeflow.providers.anthropic import AnthropicProvider
from forgeflow.providers.openai import OpenAIProvider


def test_openai_requires_key(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIProvider().complete("hi")


def test_openai_builds_request_and_parses(monkeypatch):
    openai = pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            msg = type("M", (), {"content": '{"category": "billing"}'})()
            choice = type("C", (), {"message": msg})()
            return type("R", (), {"choices": [choice]})()

    class FakeClient:
        def __init__(self, *a, **k):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(openai, "OpenAI", FakeClient)

    resp = OpenAIProvider(model="gpt-test").complete(
        "Classify it", system="sys", json_fields=["category"]
    )

    assert resp.content == '{"category": "billing"}'
    assert captured["model"] == "gpt-test"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["messages"][0]["role"] == "system"
    assert "category" in captured["messages"][0]["content"]
    assert captured["messages"][-1]["content"] == "Classify it"


def test_anthropic_requires_key(monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider().complete("hi")


def test_anthropic_builds_request_and_parses(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured: dict = {}

    block = type("Block", (), {"type": "text", "text": '{"urgency": "high"}'})()

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"content": [block]})()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)

    resp = AnthropicProvider(model="claude-test").complete("Classify", json_fields=["urgency"])

    assert resp.content == '{"urgency": "high"}'
    assert captured["model"] == "claude-test"
    assert "urgency" in captured["system"]
    assert captured["messages"][0]["content"] == "Classify"
