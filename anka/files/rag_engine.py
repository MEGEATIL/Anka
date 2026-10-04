# -*- coding: utf-8 -*-
"""ANKA AI Gelişmiş RAG Belge Analiz Engine."""

import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from anka.core.errors import FileProcessingError


class AdvancedRAGEngine:
    """PDF, DOCX, TXT, MD ve CSV belgelerini indeksleyen, sayfa/kaynak atfı (citation) sunan,
    birden fazla belgeyi karşılaştıran ve içerik analizi yapan RAG altyapısı."""

    def __init__(self, db_path: str = "anka_rag_index.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                filetype TEXT NOT NULL,
                total_chunks INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                FOREIGN KEY(doc_id) REFERENCES rag_documents(id) ON DELETE CASCADE
            )
            """)
            conn.commit()

    def index_document(self, filepath: str, text: str, page_map: Optional[List[Tuple[int, str]]] = None) -> int:
        """Belge metnini parçalara (chunks) bölerek SQLite indeksine ekler."""
        if not os.path.exists(filepath):
            raise FileProcessingError(f"Dosya bulunamadı: {filepath}")

        filename = os.path.basename(filepath)
        filetype = os.path.splitext(filename)[1].lower().replace(".", "")
        now = datetime.now().isoformat()

        chunks = self._chunk_text(text, chunk_size=800, overlap=100)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rag_documents WHERE filepath = ?", (filepath,))
            cursor.execute(
                "INSERT INTO rag_documents (filename, filepath, filetype, total_chunks, created_at) VALUES (?, ?, ?, ?, ?)",
                (filename, filepath, filetype, len(chunks), now),
            )
            doc_id = cursor.lastrowid

            for idx, chunk in enumerate(chunks):
                page_num = self._find_page_number(idx, page_map) if page_map else (idx // 3) + 1
                cursor.execute(
                    "INSERT INTO rag_chunks (doc_id, chunk_index, content, page_number) VALUES (?, ?, ?, ?)",
                    (doc_id, idx, chunk, page_num),
                )
            conn.commit()
            return doc_id

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_size - overlap
        return chunks

    def _find_page_number(self, chunk_idx: int, page_map: List[Tuple[int, str]]) -> int:
        if not page_map:
            return 1
        idx = min(chunk_idx, len(page_map) - 1)
        return page_map[idx][0]

    def search_with_citation(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Sorgu ile en alakalı belge parçalarını bulur ve kaynak/sayfa atfıyla döner."""
        words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        if not words:
            return []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Basit TF/Anahtar kelime eşleşmesi
            results = []
            cursor.execute("""
            SELECT c.id, c.content, c.page_number, d.filename, d.filepath, d.filetype
            FROM rag_chunks c
            JOIN rag_documents d ON c.doc_id = d.id
            """)
            rows = cursor.fetchall()

            for r in rows:
                content_lower = r["content"].lower()
                score = sum(content_lower.count(w) for w in words)
                if score > 0:
                    results.append({
                        "filename": r["filename"],
                        "filepath": r["filepath"],
                        "page_number": r["page_number"],
                        "content": r["content"],
                        "score": score,
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

    def compare_documents(self, filepaths: List[str]) -> Dict[str, Any]:
        """Verilen iki veya daha fazla belgenin özet istatistiklerini ve içerik karşılaştırmasını döner."""
        summary = {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for path in filepaths:
                cursor.execute(
                    "SELECT d.filename, d.total_chunks, COUNT(c.id) as chunk_count FROM rag_documents d JOIN rag_chunks c ON d.id = c.doc_id WHERE d.filepath = ?",
                    (path,),
                )
                row = cursor.fetchone()
                if row:
                    summary[row["filename"]] = {
                        "total_chunks": row["total_chunks"],
                        "chunk_count": row["chunk_count"],
                    }

        return {"document_count": len(summary), "documents": summary}

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rag_documents ORDER BY id DESC")
            return [dict(r) for r in cursor.fetchall()]
