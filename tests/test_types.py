"""Run mypy as part of the test suite (settings in pyproject.toml)."""

from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")
ROOT = Path(__file__).resolve().parent.parent


def test_mypy_passes(monkeypatch):
    monkeypatch.chdir(ROOT)
    stdout, stderr, exit_status = api.run([])
    assert exit_status == 0, stdout + stderr
