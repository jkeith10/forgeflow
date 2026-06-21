"""Built-in, safe tools available to every workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from forgeflow.tools.registry import ToolRegistry


def _echo(args: dict[str, Any]) -> Any:
    return args.get("value", args)


def _word_count(args: dict[str, Any]) -> int:
    return len(str(args.get("text", "")).split())


def _uppercase(args: dict[str, Any]) -> str:
    return str(args.get("text", "")).upper()


def _memory_get(args: dict[str, Any]) -> Any:
    from forgeflow.memory.sqlite import memory_get

    return memory_get(str(args["key"]))


def _memory_set(args: dict[str, Any]) -> str:
    from forgeflow.memory.sqlite import memory_set

    memory_set(str(args["key"]), str(args["value"]))
    return "ok"


def register_builtins(reg: ToolRegistry) -> None:
    reg.register("echo", _echo, "Return the provided value unchanged.")
    reg.register("word_count", _word_count, "Count words in `text`.")
    reg.register("uppercase", _uppercase, "Uppercase `text`.")
    reg.register("memory_get", _memory_get, "Read a value from local memory by `key`.")
    reg.register("memory_set", _memory_set, "Write `value` to local memory under `key`.")
