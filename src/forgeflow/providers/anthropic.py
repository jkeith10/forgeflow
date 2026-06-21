"""Anthropic provider — thin, optional adapter.

Requires `pip install forgeflow[anthropic]` and ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import os

from forgeflow.providers.base import LLMResponse, Provider


class AnthropicProvider(Provider):
    name = "anthropic"

    @property
    def default_model(self) -> str:
        return os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_fields: list[str] | None = None,
    ) -> LLMResponse:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The Anthropic provider needs the anthropic package. "
                "Install with: pip install 'forgeflow[anthropic]'"
            ) from exc

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Use --mock for an offline demo.")

        sys_prompt = system or ""
        if json_fields:
            sys_prompt += (
                "\nReturn ONLY a JSON object (no prose, no code fences) with these keys: "
                + ", ".join(json_fields)
                + "."
            )

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=sys_prompt.strip() or None,
            messages=[{"role": "user", "content": prompt}],
        )
        content = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(content=content, model=self.model)
