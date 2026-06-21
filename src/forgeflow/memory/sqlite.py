"""Key/value memory backed by SQLite.

Simple by design: store reusable facts, policies, and notes that workflows and
tools can read at run time (e.g. `Refunds over $500 require approval`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from forgeflow.db import connect
from forgeflow.memory.models import MemoryItem


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def memory_set(key: str, value: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO memory (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def memory_get(key: str) -> str | None:
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM memory WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def memory_list() -> list[MemoryItem]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT key, value, updated_at FROM memory ORDER BY key"
        ).fetchall()
        return [MemoryItem(r["key"], r["value"], r["updated_at"]) for r in rows]
    finally:
        conn.close()


def memory_delete(key: str) -> bool:
    conn = connect()
    try:
        cur = conn.execute("DELETE FROM memory WHERE key = ?", (key,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
