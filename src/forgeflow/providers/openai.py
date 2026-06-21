"""OpenAI provider — thin, optional adapter.

Requires `pip install forgeflow[openai]` and ``OPENAI_API_KEY``. Kept minimal on
purpose: it shows the extension point without locking the project to one vendor.
"""

from __future__ import annotations

import os

from forgeflow.providers.base import LLMResponse, Provider


class OpenAIProvider(Provider):
    name = "openai"

    @property
    def default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_fields: list[str] | None = None,
    ) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The OpenAI provider needs the openai package. "
                "Install with: pip install 'forgeflow[openai]'"
            ) from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Use --mock for an offline demo.")

        messages = []
        sys_prompt = system or ""
        if json_fields:
            sys_prompt += (
                "\nReturn ONLY a JSON object with these keys: "
                + ", ".join(json_fields)
                + "."
            )
        if sys_prompt.strip():
            messages.append({"role": "system", "content": sys_prompt.strip()})
        messages.append({"role": "user", "content": prompt})

        client = OpenAI()
        kwargs = {"model": self.model, "messages": messages}
        if json_fields:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        return LLMResponse(content=content, model=self.model)
