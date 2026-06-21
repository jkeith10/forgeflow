"""Provider interface shared by mock + real LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    name: str = "base"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.default_model

    @property
    def default_model(self) -> str:  # pragma: no cover - overridden
        return ""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_fields: list[str] | None = None,
    ) -> LLMResponse:
        """Return a completion.

        When ``json_fields`` is provided the provider is expected to return a
        JSON object string containing (at least) those keys.
        """
        raise NotImplementedError
