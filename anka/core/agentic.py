# -*- coding: utf-8 -*-
"""ANKA AI Otonom Bilgisayar Kontrolü ve Canlı Adım Takibi."""

import enum
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("anka.core.agentic")


class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FAILED = "FAILED"


class AgenticStep:
    """Tek bir otonom adımın temsilcisi."""

    def __init__(self, step_id: int, action: str, description: str, requires_approval: bool = False):
        self.step_id = step_id
        self.action = action
        self.description = description
        self.requires_approval = requires_approval
        self.status = StepStatus.PENDING
        self.result: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


class AgenticComputerController:
    """Karmaşık görevleri alt adımlara bölen, kullanıcıya canlı olarak adım durumunu sunan
    ve riskli eylemlerde onay mekanizmasını çalıştıran otonom bilgisayar kontrolörü."""

    def __init__(self, status_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.status_callback = status_callback
        self.current_plan: List[AgenticStep] = []
        self.current_step_index = -1

    def create_plan(self, goal: str) -> List[AgenticStep]:
        """İsteğe göre adım planı oluşturur."""
        steps = []
        goal_lower = goal.lower()

        if "web" in goal_lower or "araştır" in goal_lower:
            steps.append(AgenticStep(1, "web_search", f"İnternette '{goal}' için bilgi aranıyor.", False))
            steps.append(AgenticStep(2, "summarize", "Bulunan içerik özetleniyor.", False))
        elif "dosya" in goal_lower or "kod" in goal_lower:
            steps.append(AgenticStep(1, "scan_files", "İlgili dosyalar taranıyor ve analiz ediliyor.", False))
            steps.append(AgenticStep(2, "modify_files", "Dosya düzenlemeleri hazırlanıyor.", True))
        else:
            steps.append(AgenticStep(1, "analyze_request", f"İstek analiz ediliyor: {goal}", False))
            steps.append(AgenticStep(2, "execute_task", "Görev adımları uygulanıyor.", False))

        self.current_plan = steps
        self.current_step_index = 0
        self._notify_status("PLAN_CREATED", {"total_steps": len(steps)})
        return steps

    def execute_next_step(self, executor_func: Callable[[AgenticStep], Any]) -> Dict[str, Any]:
        if self.current_step_index < 0 or self.current_step_index >= len(self.current_plan):
            return {"status": "completed", "message": "Tüm adımlar tamamlandı."}

        step = self.current_plan[self.current_step_index]

        if step.requires_approval and step.status != StepStatus.SUCCESS:
            step.status = StepStatus.WAITING_APPROVAL
            self._notify_status("WAITING_APPROVAL", step.to_dict())
            return {"status": "waiting_approval", "step": step.to_dict()}

        step.status = StepStatus.RUNNING
        self._notify_status("STEP_RUNNING", step.to_dict())

        try:
            res = executor_func(step)
            step.status = StepStatus.SUCCESS
            step.result = str(res)
            self._notify_status("STEP_SUCCESS", step.to_dict())
            self.current_step_index += 1
            return {"status": "success", "step": step.to_dict()}
        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            self._notify_status("STEP_FAILED", step.to_dict())
            return {"status": "failed", "step": step.to_dict(), "error": str(exc)}

    def approve_current_step(self) -> bool:
        if self.current_step_index >= 0 and self.current_step_index < len(self.current_plan):
            step = self.current_plan[self.current_step_index]
            if step.status == StepStatus.WAITING_APPROVAL:
                step.status = StepStatus.PENDING
                step.requires_approval = False
                return True
        return False

    def _notify_status(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = {"event": event_type, "data": data, "plan": [s.to_dict() for s in self.current_plan]}
        if self.status_callback:
            try:
                self.status_callback(payload)
            except Exception as exc:
                logger.warning("Status callback çağrısı başarısız: %s", exc)
