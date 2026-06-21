"""Shared SQLite connection helpers and local-state path resolution."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def home_dir() -> Path:
    """Directory that holds ForgeFlow local state (DB, logs).

    Honours ``FORGEFLOW_HOME`` env var, otherwise ``./.forgeflow`` in the cwd.
    """
    raw = os.environ.get("FORGEFLOW_HOME", ".forgeflow")
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return home_dir() / "forgeflow.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id     TEXT PRIMARY KEY,
            workflow   TEXT NOT NULL,
            status     TEXT NOT NULL,
            provider   TEXT,
            created_at TEXT NOT NULL,
            inputs     TEXT NOT NULL,
            outputs    TEXT NOT NULL,
            steps      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
