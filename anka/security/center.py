# -*- coding: utf-8 -*-
"""ANKA AI Security Center & Audit Logger."""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from anka.security.permissions import Permission, PermissionManager
from anka.security.policy import RiskLevel, SecurityPolicy

logger = logging.getLogger("anka.security.center")


class SecurityCenter:
    """Mikrofon, kamera, dosya, web ve sistem izinlerini tek merkezden yöneten,
    yapılan tüm işlemleri güvenlik günlüğüne (Audit Log) kaydeden güvenlik sistemi."""

    def __init__(self, permissions_file: str = "permissions.json", audit_db: str = "anka_security_audit.db"):
        self.permission_manager = PermissionManager(permissions_file)
        self.risk_policy = SecurityPolicy()
        self.audit_db = audit_db
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.audit_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                permission_used TEXT,
                status TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
            """)
            conn.commit()

    def log_action(self, action: str, risk_level: str, status: str, permission_used: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> int:
        now = datetime.now().isoformat()
        details_str = json.dumps(details or {}, ensure_ascii=False)

        with sqlite3.connect(self.audit_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (action, risk_level, permission_used, status, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (action, risk_level, permission_used or "NONE", status, details_str, now),
            )
            conn.commit()
            return cursor.lastrowid

    def get_permission_status(self) -> Dict[str, bool]:
        """Tüm izinlerin anlık durumunu döndürür."""
        return self.permission_manager.snapshot()

    def set_permission(self, permission: Permission, allowed: bool) -> None:
        """İzin ayarını günceller ve güvenlik günlüğüne kaydeder."""
        self.permission_manager.set(permission, allowed)
        self.log_action(
            action=f"PERM_CHANGE_{permission.value.upper()}",
            risk_level="MEDIUM",
            status="SUCCESS",
            permission_used=permission.value,
            details={"allowed": allowed},
        )

    def evaluate_request(self, action_name: str, required_permission: Optional[Permission] = None) -> Dict[str, Any]:
        """Aksiyonun risk derecesini ve izin durumunu değerlendirir."""
        if required_permission and not self.permission_manager.is_allowed(required_permission):
            self.log_action(action_name, "HIGH", "BLOCKED", required_permission.value, {"reason": "Permission denied"})
            return {"allowed": False, "requires_approval": False, "reason": f"İzin kapalı: {required_permission.value}"}

        decision = self.risk_policy.evaluate(action_name)
        requires_appr = decision.requires_confirmation

        self.log_action(
            action=action_name,
            risk_level=decision.risk.name,
            status="APPROVED" if not requires_appr else "PENDING_APPROVAL",
            permission_used=required_permission.value if required_permission else "NONE",
        )

        return {
            "allowed": True,
            "risk_level": decision.risk.name,
            "requires_approval": requires_appr,
        }

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.audit_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "action": r["action"],
                    "risk_level": r["risk_level"],
                    "permission_used": r["permission_used"],
                    "status": r["status"],
                    "details": json.loads(r["details"] or "{}"),
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]
