from pathlib import Path

import pytest

from reset_db import reset_database


def test_reset_database_only_deletes_workspace_memory_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    database = tmp_path / "hafiza.db"
    database.write_text("veri", encoding="utf-8")

    assert reset_database(database) is True
    assert not database.exists()


def test_reset_database_rejects_any_other_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    protected = tmp_path / "other.db"
    protected.write_text("veri", encoding="utf-8")

    with pytest.raises(ValueError):
        reset_database(protected)
    assert protected.exists()
