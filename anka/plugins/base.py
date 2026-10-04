# -*- coding: utf-8 -*-
"""ANKA AI Modüler Plugin / Skill Taban Sınıfı."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BasePlugin(ABC):
    """Tüm ANKA yetenek eklentileri (Plugin/Skill) için temel soyut sınıf."""

    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
        self.enabled = True

    @abstractmethod
    def initialize(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Eklenti ilk yüklendiğinde çalışacak kurulum mantığı."""
        pass

    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Eklenti aksiyonunu yürütür."""
        pass

    def shutdown(self) -> None:
        """Eklenti sonlandırılırken temizlik işlemleri."""
        pass
