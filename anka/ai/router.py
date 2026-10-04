# -*- coding: utf-8 -*-
"""ANKA AI Dahili Model Yönlendirme Motoru (Internal Model Router)."""

from enum import Enum
from typing import Any, Dict


class TaskType(str, Enum):
    CHAT = "chat"
    CODING = "coding"
    RAG = "rag"
    VISION = "vision"
    INTENT = "intent"
    SUMMARY = "summary"


class InternalModelRouter:
    """Kullanıcıya harici model seçimi sunmadan, gelen isteğin niteliğine göre
    parametre (temperature, max_tokens, system_prompt) ve çalışma profilini otomatik seçer."""

    def __init__(self):
        self._profiles = {
            TaskType.CHAT: {
                "temperature": 0.7,
                "max_tokens": 1024,
                "description": "Genel Türkçe sohbet ve günlük asistan yanıtları.",
            },
            TaskType.CODING: {
                "temperature": 0.2,
                "max_tokens": 4096,
                "description": "Hassas kodlama, hata tespiti ve yazılım projeleri.",
            },
            TaskType.RAG: {
                "temperature": 0.3,
                "max_tokens": 2048,
                "description": "Geniş bağlamlı belge analizi, kaynak atfı ve doküman sorgulama.",
            },
            TaskType.VISION: {
                "temperature": 0.4,
                "max_tokens": 2048,
                "description": "Ekran görüntüsü, yazılım hatası ve görsel anlayış analizi.",
            },
            TaskType.INTENT: {
                "temperature": 0.1,
                "max_tokens": 256,
                "description": "Kullanıcı niyet analizi ve semantik bölümleme.",
            },
            TaskType.SUMMARY: {
                "temperature": 0.4,
                "max_tokens": 1500,
                "description": "Günlük özet ve metin derleme.",
            },
        }

    def route(self, task_type: str, user_input: str = "") -> Dict[str, Any]:
        """Gelen eylem türüne göre en uygun parametre profilini döndürür."""
        try:
            enum_type = TaskType(task_type)
        except ValueError:
            enum_type = TaskType.CHAT

        profile = dict(self._profiles[enum_type])
        profile["task_type"] = enum_type.value

        # Girdi bazlı dinamik token ayarlaması
        if len(user_input) > 2000 and profile["max_tokens"] < 2048:
            profile["max_tokens"] = 2048

        return profile
