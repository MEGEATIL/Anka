from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class SecurityDecision:
    action: str
    risk: RiskLevel
    requires_confirmation: bool
    explanation: str


class SecurityPolicy:
    RULES = {
        "conversation": (RiskLevel.LOW, "Sohbet ve bilgi isteği"),
        "web_research": (RiskLevel.LOW, "Web kaynaklarında araştırma"),
        "application_open": (RiskLevel.MEDIUM, "Bilgisayarda bir uygulama açma"),
        "folder_open": (RiskLevel.MEDIUM, "Yerel bir klasör açma"),
        "file_learn": (RiskLevel.MEDIUM, "Yerel bir dosyadan bilgi çıkarma"),
        "file_operation": (RiskLevel.HIGH, "Dosya açma, oluşturma veya değiştirme"),
        "file_delete": (RiskLevel.HIGH, "Yerel dosya veya klasör silme"),
        "file_move": (RiskLevel.HIGH, "Yerel dosya taşıma veya kopyalama"),
        "shell_command": (RiskLevel.HIGH, "Sistem kabuğu komutu çalıştırma"),
        "system_shutdown": (RiskLevel.CRITICAL, "Bilgisayarı kapatma"),
        "system_restart": (RiskLevel.CRITICAL, "Bilgisayarı yeniden başlatma"),
    }

    def evaluate(self, action: str) -> SecurityDecision:
        risk, explanation = self.RULES.get(action, (RiskLevel.HIGH, "Bilinmeyen sistem işlemi"))
        return SecurityDecision(action, risk, risk >= RiskLevel.MEDIUM, explanation)
