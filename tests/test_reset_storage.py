import sqlite3

from anka.storage.reset import clear_sqlite_user_tables, remove_personal_data_files


def test_reset_removes_records_without_removing_schema(tmp_path):
    database = sqlite3.connect(tmp_path / "memory.db")
    database.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, text TEXT)")
    database.execute("INSERT INTO notes(text) VALUES ('gizli not')")
    database.commit()

    assert clear_sqlite_user_tables(database) == 1
    assert database.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    database.execute("INSERT INTO notes(text) VALUES ('yeni not')")
    assert database.execute("SELECT text FROM notes").fetchone()[0] == "yeni not"


def test_reset_removes_only_allowlisted_personal_data_files(tmp_path):
    memory = tmp_path / "anka_memory.json"
    temporary_memory = tmp_path / "anka_memory.json.tmp"
    memory.write_text("{}", encoding="utf-8")
    temporary_memory.write_text('{"yarım":"kişisel veri"}', encoding="utf-8")
    source = tmp_path / "mainyapayzeka1.py"
    source.write_text("kod", encoding="utf-8")

    removed = remove_personal_data_files(tmp_path, ("anka_memory.json",))

    assert removed == [memory, temporary_memory]
    assert not memory.exists()
    assert not temporary_memory.exists()
    assert source.read_text(encoding="utf-8") == "kod"
