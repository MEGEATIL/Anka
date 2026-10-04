# -*- coding: utf-8 -*-
"""ANKA AI Günlük Özet Sistemi (Daily Digest System)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from anka.memory.categorized import CategorizedMemory


class DailyDigestSystem:
    """Günlük gerçekleştirilen görevleri, alınan notları, hatırlatıcıları
    ve yeni öğrenilen bilgileri derleyerek rapor hazırlayan sistem."""

    def __init__(self, memory: Optional[CategorizedMemory] = None):
        self.memory = memory or CategorizedMemory()

    def generate_digest(self, notes: Optional[List[str]] = None, tasks: Optional[List[str]] = None) -> Dict[str, Any]:
        now_str = datetime.now().strftime("%d %B %Y, %H:%M")

        # Hafızadan öğrenilen bilgileri çek
        learned = self.memory.get_by_category("learned_facts")
        preferences = self.memory.get_by_category("preferences")

        digest_report = [
            f"# 📅 ANKA AI Günlük Özet Raporu ({now_str})\n",
            "## 📝 Alınan Notlar & Görevler",
        ]

        if notes:
            digest_report.append("**Notlar:**")
            for n in notes:
                digest_report.append(f"  - {n}")
        else:
            digest_report.append("  - Henüz bugün için kayıtlı not yok.")

        if tasks:
            digest_report.append("\n**Tamamlanan/Aktif Görevler:**")
            for t in tasks:
                digest_report.append(f"  - {t}")

        digest_report.append("\n## 🧠 Öğrenilen Bilgiler & Gelişmeler")
        if learned:
            for item in learned[:5]:
                digest_report.append(f"  - {item['value']}")
        else:
            digest_report.append("  - Yeni kaydedilen özel bilgi yok.")

        return {
            "timestamp": now_str,
            "report_text": "\n".join(digest_report),
            "notes_count": len(notes or []),
            "tasks_count": len(tasks or []),
            "learned_count": len(learned),
        }
