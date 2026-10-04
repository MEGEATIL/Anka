# -*- coding: utf-8 -*-
"""ANKA AI Kategorize Kalıcı Hafıza Motoru."""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class CategorizedMemory:
    """Kullanıcı tercihlerini, öğrenilen bilgileri, görev geçmişini ve kişisel detayları
    kategorize ederek (preferences, learned_facts, tasks, conversations) saklayan ve yöneten sistem."""

    CATEGORIES = ("preferences", "learned_facts", "tasks", "conversations", "general")

    def __init__(self, db_path: str = "anka_categorized_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT,
                value TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)
            conn.commit()

    def add(self, category: str, value: str, key: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> int:
        cat = category.lower() if category.lower() in self.CATEGORIES else "general"
        now = datetime.now().isoformat()
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if key:
                cursor.execute(
                    "SELECT id FROM memory_items WHERE category = ? AND key = ?",
                    (cat, key),
                )
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE memory_items SET value = ?, metadata = ?, updated_at = ? WHERE id = ?",
                        (value, meta_str, now, row[0]),
                    )
                    conn.commit()
                    return row[0]

            cursor.execute(
                "INSERT INTO memory_items (category, key, value, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (cat, key, value, meta_str, now, now),
            )
            conn.commit()
            return cursor.lastrowid

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memory_items WHERE category = ? ORDER BY id DESC",
                (category.lower(),),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "category": r["category"],
                    "key": r["key"],
                    "value": r["value"],
                    "metadata": json.loads(r["metadata"] or "{}"),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def query_about_user(self) -> str:
        return self.get_user_summary()

    def get_user_summary(self) -> str:
        """'Benim hakkımda ne biliyorsun?' sorusuna detaylı ve kategorize yanıt döner."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value FROM memory_items ORDER BY category, id DESC")
            rows = cursor.fetchall()

        if not rows:
            return "Hafızamda henüz sizinle ilgili kaydedilmiş bilgi bulunmuyor."

        by_cat: Dict[str, List[str]] = {}
        for r in rows:
            cat = r["category"]
            val = r["value"]
            k = f" ({r['key']})" if r["key"] else ""
            by_cat.setdefault(cat, []).append(f"{val}{k}")

        cat_names = {
            "preferences": "Tercihler ve İzinler",
            "learned_facts": "Öğrenilen Bilgiler",
            "tasks": "Görev Geçmişi",
            "conversations": "Önemli Konuşmalar",
            "general": "Genel Bilgiler",
        }

        output = ["Sizin hakkınızda bildiklerim:\n"]
        for cat, items in by_cat.items():
            title = cat_names.get(cat, cat.capitalize())
            output.append(f"**{title}**:")
            for item in items[:10]:
                output.append(f"  - {item}")

        return "\n".join(output)

    def search(self, query: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            q = f"%{query.strip()}%"
            cursor.execute(
                "SELECT * FROM memory_items WHERE value LIKE ? OR key LIKE ? ORDER BY id DESC LIMIT 20",
                (q, q),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "category": r["category"],
                    "key": r["key"],
                    "value": r["value"],
                    "metadata": json.loads(r["metadata"] or "{}"),
                }
                for r in rows
            ]

    def delete_item(self, item_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_category(self, category: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_items WHERE category = ?", (category.lower(),))
            conn.commit()
            return cursor.rowcount

    def clear_all(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_items")
            conn.commit()
            return cursor.rowcount
