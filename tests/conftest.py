"""Shared test fixtures.

Adds `src/` to the path (so tests run without an editable install) and points
ForgeFlow's local state at a throwaway temp dir per test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXAMPLES = ROOT / "examples"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEFLOW_HOME", str(tmp_path / ".forgeflow"))
    monkeypatch.setenv("FORGEFLOW_PROVIDER", "mock")
    yield


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES
