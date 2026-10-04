from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from threading import RLock

from anka.core.errors import PermissionDeniedError


class Permission(str, Enum):
    MICROPHONE = "microphone"
    CAMERA = "camera"
    FILES = "files"
    SYSTEM = "system"
    WEB = "web"


class PermissionManager:
    """Kullanici onaylarini gizli bilgi yazmadan saklar."""

    DEFAULTS = {
        # Eski ANKA sürümü mikrofonu açılışta etkinleştiriyordu; durum buna
        # uygun görünür ve kullanıcı bu izni sonradan kapatabilir.
        Permission.MICROPHONE.value: True,
        Permission.CAMERA.value: False,
        Permission.FILES.value: False,
        Permission.SYSTEM.value: False,
        Permission.WEB.value: True,
    }

    def __init__(self, path: str = "permissions.json"):
        self.path = Path(path)
        self._lock = RLock()
        self._settings = dict(self.DEFAULTS)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in self.DEFAULTS:
                    if isinstance(data.get(key), bool):
                        self._settings[key] = data[key]
        except (OSError, json.JSONDecodeError):
            return

    def set(self, permission: Permission, allowed: bool) -> None:
        with self._lock:
            self._settings[permission.value] = bool(allowed)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)

    def is_allowed(self, permission: Permission) -> bool:
        return bool(self._settings.get(permission.value, False))

    def check(self, permission: Permission) -> None:
        if not self.is_allowed(permission):
            raise PermissionDeniedError(
                f"{permission.value} izni etkin değil. Gizlilik/izinler ekranından etkinleştirin."
            )

    def snapshot(self) -> dict[str, bool]:
        return dict(self._settings)
