"""Kayan konuşma bağlamı ve SQLite tabanlı kalıcı ANKA hafızası."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from threading import RLock
from typing import Iterable


_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class MemoryManager:
    """Konuşma geçmişini bütçe içinde tutar, önemli bilgiyi kalıcı saklar."""

    def __init__(self, database_path: str = "anka_context.db", context_token_limit: int = 2_400):
        self.database_path = Path(database_path)
        self.context_token_limit = context_token_limit
        self._lock = RLock()
        self._history: list[ChatMessage] = []
        self._initialize()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Model tokenizer'ı bilinmiyorsa güvenli yaklaşık token sayısı."""
        return max(1, len(_TOKEN_RE.findall(text or "")))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )"""
            )

    def add_message(self, role: str, content: str) -> None:
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError("Geçersiz konuşma rolü.")
        message = ChatMessage(role, str(content).strip()[:12_000])
        if not message.content:
            return
        with self._lock:
            self._history.append(message)
            self._trim_history()

    def _trim_history(self) -> None:
        while self._history and self._history_token_count() > self.context_token_limit:
            # Sistem yönergesi varsa korunur; en eski normal mesaj kaldırılır.
            index = next((i for i, item in enumerate(self._history) if item.role != "system"), 0)
            self._history.pop(index)

    def _history_token_count(self) -> int:
        return sum(self.estimate_tokens(message.content) + 4 for message in self._history)

    def remember(self, kind: str, content: str, metadata: dict | None = None) -> None:
        if kind not in {"profile", "preference", "knowledge", "note", "task"}:
            raise ValueError("Geçersiz kalıcı hafıza türü.")
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO memories(kind, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (kind, str(content)[:8_000], json.dumps(metadata or {}, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
            )

    def relevant_memories(self, query: str, limit: int = 5) -> list[str]:
        terms = {item.casefold() for item in _TOKEN_RE.findall(query or "") if len(item) > 2}
        if not terms:
            return []
        with self._connect() as connection:
            rows = connection.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 250").fetchall()
        scored = []
        for row in rows:
            content = row["content"]
            score = len(terms & {item.casefold() for item in _TOKEN_RE.findall(content)})
            if score:
                scored.append((score, content))
        return [content for _, content in sorted(scored, reverse=True)[:limit]]

    def clear(self) -> None:
        """Konuşma penceresini ve kalıcı hafıza kayıtlarını temizler."""
        with self._lock, self._connect() as connection:
            self._history.clear()
            connection.execute("DELETE FROM memories")

    def build_context(self, user_input: str, system_prompt: str = "") -> list[dict[str, str]]:
        """Sistem yönergesi + ilgili kalıcı hafıza + token-bütçeli geçmiş üretir."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        memories = self.relevant_memories(user_input)
        if memories:
            summary = "\n".join(f"- {memory[:350]}" for memory in memories)
            messages.append({"role": "system", "content": f"İlgili kalıcı hafıza:\n{summary}"})
        messages.extend({"role": item.role, "content": item.content} for item in self._history if item.role != "system")
        messages.append({"role": "user", "content": user_input})
        return self._fit_budget(messages)

    def _fit_budget(self, messages: Iterable[dict[str, str]]) -> list[dict[str, str]]:
        result = list(messages)
        while len(result) > 1 and sum(self.estimate_tokens(item["content"]) + 4 for item in result) > self.context_token_limit:
            # Son öğe güncel kullanıcı isteğidir; onu silme. Önce eski sohbeti,
            # ardından ek hafıza yönergelerini kaldır.
            removable = next(
                (index for index, item in enumerate(result[:-1]) if item["role"] != "system"),
                None,
            )
            if removable is None:
                removable = 1 if len(result) > 2 else None
            if removable is None:
                break
            result.pop(removable)
        if result and sum(self.estimate_tokens(item["content"]) + 4 for item in result) > self.context_token_limit:
            # Tek başına çok uzun bir güncel mesaj, bağlam bütçesini delmesin.
            # En yeni bölümü korumak konuşma devamlılığı için daha yararlıdır.
            target = result[-1]
            other_tokens = sum(self.estimate_tokens(item["content"]) + 4 for item in result[:-1])
            allowed = max(1, self.context_token_limit - other_tokens - 4)
            tokens = _TOKEN_RE.findall(target["content"])
            target["content"] = " ".join(tokens[-allowed:])
        return result
