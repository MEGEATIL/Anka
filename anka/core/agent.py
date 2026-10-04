"""Planla -> denetle -> onayla -> calistir -> raporla akisi."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Callable, Optional

from anka.core.errors import AnkaError
from anka.core.logging import configure_logging, redact_sensitive_text
from anka.security.policy import RiskLevel, SecurityPolicy


class TaskState(str, Enum):
    PLANNED = "planned"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskPlan:
    request: str
    action: str
    description: str
    risk: RiskLevel
    state: TaskState = TaskState.PLANNED


@dataclass
class AgentResult:
    success: bool
    message: str
    plan: TaskPlan


class TaskAgent:
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        self.policy = policy or SecurityPolicy()
        self.pending: Optional[TaskPlan] = None
        self._logger = configure_logging().getChild("agent")

    def plan(self, request: str) -> TaskPlan:
        normalized = (request or "").casefold().strip()
        if any(text in normalized for text in (
            "bilgisayarı kapat", "bilgisayari kapat", "bilgisayarımı kapat",
            "bilgisayarimi kapat", "sistemi kapat",
        )):
            action, description = "system_shutdown", "Bilgisayar kapatılacak."
        elif any(text in normalized for text in ("yeniden başlat", "yeniden baslat")):
            action, description = "system_restart", "Bilgisayar yeniden başlatılacak."
        elif normalized.startswith(("klasör aç", "klasor ac")):
            action, description = "folder_open", "Yerel bir klasör açılacak."
        elif re.match(r"^(dosya(?:yı|yi)?|klasör(?:ü|u)?)\s+(sil|kaldır|kaldir)", normalized):
            action, description = "file_delete", "Yerel bir dosya veya klasör silinecek."
        elif re.match(r"^(dosya(?:yı|yi)?|klasör(?:ü|u)?)\s+(taşı|tasi|kopyala)", normalized):
            action, description = "file_move", "Yerel bir dosya taşınacak veya kopyalanacak."
        elif normalized.startswith(("dosya aç", "dosya ac", "dosya oluştur", "dosya olustur")):
            action, description = "file_operation", "Bir dosya işlemi yapılacak."
        elif normalized.startswith(("dosya öğret", "dosya ogret")):
            action, description = "file_learn", "Yerel bir dosyadan bilgi çıkarılacak."
        elif normalized.startswith(("cmd ", "powershell ", "terminal ")):
            action, description = "shell_command", "Sistem komutu çalıştırılacak."
        elif normalized.endswith(" aç") or " açabilir misin" in normalized or " açar mısın" in normalized:
            action, description = "application_open", "Bir uygulama veya bağlantı açılacak."
        else:
            action, description = "conversation", "Bilgi veya sohbet isteği işlenecek."
        decision = self.policy.evaluate(action)
        return TaskPlan(request=request, action=action, description=description, risk=decision.risk)

    def submit(self, request: str, executor: Callable[[TaskPlan], str]) -> AgentResult:
        if self.pending:
            return AgentResult(
                False,
                "Önce bekleyen işlemi 'onayla' veya 'iptal' ile sonuçlandırın.",
                self.pending,
            )
        plan = self.plan(request)
        self._logger.info(
            "task_planned action=%s risk=%s request=%r",
            plan.action,
            plan.risk.name,
            redact_sensitive_text(request),
        )
        if self.policy.evaluate(plan.action).requires_confirmation:
            plan.state = TaskState.WAITING_APPROVAL
            self.pending = plan
            return AgentResult(
                False,
                f"Emin misiniz? {plan.description} Risk seviyesi: {plan.risk.name}. "
                "Devam etmek için 'evet' veya 'onayla', vazgeçmek için 'hayır' veya 'iptal' deyin.",
                plan,
            )
        return self._run(plan, executor)

    def approve(self, executor: Callable[[TaskPlan], str]) -> AgentResult:
        if not self.pending:
            plan = self.plan("")
            return AgentResult(False, "Onay bekleyen bir işlem yok.", plan)
        plan = self.pending
        self.pending = None
        return self._run(plan, executor)

    def cancel(self) -> AgentResult:
        if not self.pending:
            plan = self.plan("")
            return AgentResult(False, "İptal edilecek bir işlem yok.", plan)
        plan = self.pending
        self.pending = None
        plan.state = TaskState.CANCELLED
        self._logger.info("task_cancelled action=%s risk=%s", plan.action, plan.risk.name)
        return AgentResult(False, "İşlem iptal edildi.", plan)

    def _run(self, plan: TaskPlan, executor: Callable[[TaskPlan], str]) -> AgentResult:
        plan.state = TaskState.RUNNING
        try:
            report = executor(plan)
            if report is None or report is False or not str(report).strip():
                raise RuntimeError("İşlem sonucu doğrulanamadı.")
            plan.state = TaskState.COMPLETED
            self._logger.info("task_completed action=%s risk=%s", plan.action, plan.risk.name)
            return AgentResult(True, f"İşlem tamamlandı: {report}", plan)
        except AnkaError as exc:
            plan.state = TaskState.FAILED
            self._logger.warning("task_blocked action=%s risk=%s error=%s", plan.action, plan.risk.name, redact_sensitive_text(exc))
            return AgentResult(False, f"İşlem güvenlik nedeniyle tamamlanamadı: {exc}", plan)
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            plan.state = TaskState.FAILED
            self._logger.exception("task_failed action=%s risk=%s", plan.action, plan.risk.name)
            return AgentResult(False, f"İşlem sırasında hata oluştu: {exc}", plan)
        except Exception as exc:
            # Araç eklentileri üçüncü taraf hataları da üretebilir. Bu son sınır,
            # arayüzün çökmesi yerine doğrulanmış başarısızlık döndürür.
            plan.state = TaskState.FAILED
            self._logger.exception("task_unexpected_failure action=%s risk=%s", plan.action, plan.risk.name)
            return AgentResult(False, f"İşlem beklenmeyen bir nedenle tamamlanamadı: {type(exc).__name__}", plan)
