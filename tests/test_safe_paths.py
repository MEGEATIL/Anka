from pathlib import Path

import pytest

from anka.core.errors import FileProcessingError
from anka.security.paths import resolve_user_file


def test_relative_creation_stays_under_user_documents(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    path = resolve_user_file("notlar/gunluk.txt", for_creation=True)

    assert path == tmp_path / "Documents" / "ANKA" / "notlar" / "gunluk.txt"
    assert path.parent.is_dir()


def test_system_and_parent_escape_paths_are_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    with pytest.raises(FileProcessingError):
        resolve_user_file("C:/Windows/system32/secret.txt")
    with pytest.raises(FileProcessingError):
        resolve_user_file("../../outside.txt")
