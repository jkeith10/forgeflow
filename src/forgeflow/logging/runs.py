"""Persist and query workflow runs (the audit log)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from forgeflow.db import connect

if TYPE_CHECKING:
    from forgeflow.engine.runner import RunResult


def save_run(result: RunResult) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO runs "
            "(run_id, workflow, status, provider, created_at, inputs, outputs, steps) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result.run_id,
                result.workflow,
                result.status,
                result.provider,
                result.created_at,
                json.dumps(result.inputs),
                json.dumps(result.outputs),
                json.dumps([s.to_dict() for s in result.steps]),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT run_id, workflow, status, provider, created_at "
            "FROM runs ORDER BY created_at DESC, run_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        for k in ("inputs", "outputs", "steps"):
            data[k] = json.loads(data[k])
        return data
    finally:
        conn.close()
