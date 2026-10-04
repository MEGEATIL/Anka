from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4


class MemoryStore:
    VALID_KINDS = {"profile", "conversation", "knowledge", "note", "task"}

    def __init__(self, path: str = "anka_memory.json"):
        self.path = Path(path)
        self._lock = RLock()
        self._items: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            raw_items = value.get("items", []) if isinstance(value, dict) else []
            if not isinstance(raw_items, list):
                self._items = []
                return
            self._items = [
                item for item in raw_items[-5_000:]
                if isinstance(item, dict)
                and item.get("kind") in self.VALID_KINDS
                and isinstance(item.get("content"), str)
                and isinstance(item.get("metadata", {}), dict)
            ]
        except (OSError, json.JSONDecodeError):
            self._items = []

    def _save(self) -> None:
        payload = {"version": 1, "items": self._items}
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def remember(self, kind: str, content: str, metadata: dict | None = None) -> dict:
        if kind not in self.VALID_KINDS:
            raise ValueError("Geçersiz hafıza türü.")
        item = {
            "id": uuid4().hex, "kind": kind, "content": str(content)[:8000],
            "metadata": metadata or {}, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._items.append(item)
            # Konuşma kaydı sınırsız büyümesin; en eski kayıtlar döngüsel silinir.
            self._items = self._items[-5_000:]
            self._save()
        return item

    def list(self, kind: str | None = None, limit: int = 50) -> list[dict]:
        items = self._items if kind is None else [i for i in self._items if i.get("kind") == kind]
        return list(reversed(items[-max(1, limit):]))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        needle = query.casefold().strip()
        if not needle:
            return []
        return [item for item in self.list(limit=10_000) if needle in item.get("content", "").casefold()][:limit]

    def forget(self, query: str) -> int:
        needle = query.casefold().strip()
        if not needle:
            return 0
        with self._lock:
            old = len(self._items)
            self._items = [item for item in self._items if needle not in item.get("content", "").casefold()]
            removed = old - len(self._items)
            if removed:
                self._save()
            return removed

    def clear(self) -> None:
        with self._lock:
            self._items = []
            self._save()
