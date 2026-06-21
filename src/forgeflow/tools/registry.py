"""A tiny, explicit tool registry.

Tools are plain Python callables registered by name. They are intentionally
pure/safe by default — ForgeFlow does NOT ship a shell or arbitrary-eval tool.
Users opt into their own tools via `register`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

ToolFn = Callable[[dict[str, Any]], Any]


@dataclass
class Tool:
    name: str
    fn: ToolFn
    description: str = ""


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, name: str, fn: ToolFn, description: str = "") -> None:
        self._tools[name] = Tool(name=name, fn=fn, description=description)

    def tool(self, name: str, description: str = "") -> Callable[[ToolFn], ToolFn]:
        def deco(fn: ToolFn) -> ToolFn:
            self.register(name, fn, description)
            return fn

        return deco

    def call(self, name: str, args: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool '{name}'. Registered: {', '.join(sorted(self._tools)) or '(none)'}")
        return self._tools[name].fn(args)

    def list(self) -> list[Tool]:
        return [self._tools[k] for k in sorted(self._tools)]


def _build_default_registry() -> ToolRegistry:
    from forgeflow.tools import builtins

    reg = ToolRegistry()
    builtins.register_builtins(reg)
    return reg


default_registry = _build_default_registry()
