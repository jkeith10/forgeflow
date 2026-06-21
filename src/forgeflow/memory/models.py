"""Lightweight dataclasses for memory records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryItem:
    key: str
    value: str
    updated_at: str
