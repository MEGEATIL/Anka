"""Model çağrılarını doğrulanmış ve izin denetimli araçlara bağlar."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import json
from typing import Any, Callable

from anka.core.errors import SecurityViolationError
from anka.security.permissions import Permission, PermissionManager
from anka.security.policy import SecurityPolicy


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    action: str
    permission: Permission | None
    handler: Callable[..., str]
    accepted_arguments: frozenset[str]
    required_arguments: frozenset[str]


class ToolRegistry:
    """Araçları allowlist ile çalıştırır; modelin serbest kod yürütmesine izin vermez."""

    def __init__(self, permissions: PermissionManager, policy: SecurityPolicy | None = None):
        self.permissions = permissions
        self.policy = policy or SecurityPolicy()
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, action: str, handler: Callable[..., str], permission: Permission | None = None) -> None:
        if not name.replace("_", "").isalnum() or name in self._tools:
            raise ValueError("Geçersiz veya tekrarlanan araç adı.")
        try:
            parameters = inspect.signature(handler).parameters.values()
        except (TypeError, ValueError) as exc:
            raise ValueError("Araç işleyicisinin doğrulanabilir bir imzası olmalı.") from exc
        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters):
            raise ValueError("Araç işleyicisi sınırsız anahtar kelime parametresi kabul edemez.")
        accepted = {
            parameter.name for parameter in parameters
            if parameter.kind in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }
        required = {
            parameter.name for parameter in parameters
            if parameter.kind in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and parameter.default is inspect.Parameter.empty
        }
        self._tools[name] = ToolDefinition(
            name,
            action,
            permission,
            handler,
            frozenset(accepted),
            frozenset(required),
        )

    def execute(self, name: str, arguments: dict[str, Any], confirmed: bool = False) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise SecurityViolationError("İzin verilmeyen araç çağrısı.")
        if not isinstance(arguments, dict):
            raise SecurityViolationError("Araç parametreleri nesne olmalıdır.")
        unexpected = set(arguments) - tool.accepted_arguments
        missing = tool.required_arguments - set(arguments)
        if unexpected or missing:
            raise SecurityViolationError("Araç parametreleri araç şemasıyla eşleşmiyor.")
        decision = self.policy.evaluate(tool.action)
        if decision.requires_confirmation and not confirmed:
            raise SecurityViolationError(f"Onay gerekli: {decision.explanation}")
        if tool.permission:
            self.permissions.check(tool.permission)
        try:
            return str(tool.handler(**arguments))
        except TypeError as exc:
            raise SecurityViolationError("Araç parametreleri geçersiz.") from exc

    def execute_model_call(self, raw_call: str, confirmed: bool = False) -> str:
        """Modelin yapılandırılmış çağrısını allowlist üzerinden çalıştırır.

        Beklenen biçim: ``{"tool": "web_arastir", "arguments": {"soru": "..."}}``.
        Serbest Python, shell komutu veya beklenmeyen alanlar kabul edilmez.
        """
        try:
            payload = json.loads(raw_call)
        except json.JSONDecodeError as exc:
            raise SecurityViolationError("Model araç çağrısı geçerli JSON değil.") from exc
        if not isinstance(payload, dict) or set(payload) - {"tool", "arguments"}:
            raise SecurityViolationError("Model araç çağrısı beklenen şemada değil.")
        tool_name = payload.get("tool")
        arguments = payload.get("arguments", {})
        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            raise SecurityViolationError("Araç adı veya parametreleri geçersiz.")
        return self.execute(tool_name, arguments, confirmed=confirmed)
