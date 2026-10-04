"""Küçük kullanıcı arayüzü durumları için atomik JSON depolama."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("Durum verisi nesne olmalıdır.")
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except (OSError, TypeError, ValueError):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def load(self, default: dict[str, Any] | None = None) -> dict[str, Any]:
        fallback = dict(default or {})
        if not self.path.exists():
            return fallback
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback
        return value if isinstance(value, dict) else fallback
