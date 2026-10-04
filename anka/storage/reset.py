"""Kullanıcı verilerini koddan ayrı, doğrulanabilir biçimde temizleme yardımcıları."""

from __future__ import annotations

from pathlib import Path
import sqlite3


def clear_sqlite_user_tables(connection: sqlite3.Connection) -> int:
    """SQLite şemalarını koruyup tüm kullanıcı tablosu satırlarını siler."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (table_name,) in rows:
        safe_name = str(table_name).replace('"', '""')
        connection.execute(f'DELETE FROM "{safe_name}"')
    connection.commit()
    return len(rows)


def remove_personal_data_files(root: str | Path, names: tuple[str, ...]) -> list[Path]:
    """Yalnızca allowlist'teki kullanıcı veri dosyalarını ve atomik yazım kalıntılarını kaldırır."""
    base = Path(root).resolve()
    removed: list[Path] = []
    for name in names:
        candidate = (base / name).resolve()
        if candidate.parent != base or candidate.name != name:
            raise ValueError("Geçersiz kişisel veri dosyası adı.")
        for target in (candidate, candidate.with_suffix(candidate.suffix + ".tmp")):
            if target.is_file():
                target.unlink()
                removed.append(target)
    return removed
