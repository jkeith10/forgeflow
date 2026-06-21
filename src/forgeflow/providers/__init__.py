"""LLM provider abstraction + factory."""

from __future__ import annotations

import os

from forgeflow.providers.base import LLMResponse, Provider


def get_provider(name: str | None, model: str | None = None) -> Provider:
    """Resolve a provider by name.

    Falls back to ``FORGEFLOW_PROVIDER`` then ``mock``. The mock provider needs
    no API keys and is fully deterministic, which is what powers offline demos
    and the eval suite in CI.
    """
    name = (name or os.environ.get("FORGEFLOW_PROVIDER") or "mock").lower()

    if name == "mock":
        from forgeflow.providers.mock import MockProvider

        return MockProvider(model=model)
    if name == "openai":
        from forgeflow.providers.openai import OpenAIProvider

        return OpenAIProvider(model=model)
    if name == "anthropic":
        from forgeflow.providers.anthropic import AnthropicProvider

        return AnthropicProvider(model=model)

    raise ValueError(
        f"Unknown provider '{name}'. Available: mock, openai, anthropic."
    )


__all__ = ["get_provider", "Provider", "LLMResponse"]
