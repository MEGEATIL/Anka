import pytest

from anka.core.errors import PermissionDeniedError, SecurityViolationError
from anka.security.permissions import Permission, PermissionManager
from anka.tools.registry import ToolRegistry


def test_medium_risk_tool_requires_confirmation(tmp_path):
    registry = ToolRegistry(PermissionManager(str(tmp_path / "permissions.json")))
    registry.register("uygulama_ac", "application_open", lambda isim: f"{isim} açıldı")
    with pytest.raises(SecurityViolationError):
        registry.execute("uygulama_ac", {"isim": "chrome"})
    assert registry.execute("uygulama_ac", {"isim": "chrome"}, confirmed=True) == "chrome açıldı"


def test_tool_requires_explicit_permission(tmp_path):
    permissions = PermissionManager(str(tmp_path / "permissions.json"))
    registry = ToolRegistry(permissions)
    registry.register("dosya_oku", "file_learn", lambda yol: yol, permission=Permission.FILES)
    with pytest.raises(PermissionDeniedError):
        registry.execute("dosya_oku", {"yol": "not.txt"}, confirmed=True)
    permissions.set(Permission.FILES, True)
    assert registry.execute("dosya_oku", {"yol": "not.txt"}, confirmed=True) == "not.txt"


def test_model_tool_call_must_match_the_schema(tmp_path):
    registry = ToolRegistry(PermissionManager(str(tmp_path / "permissions.json")))
    registry.register("selamla", "conversation", lambda isim: f"Merhaba {isim}")
    assert registry.execute_model_call('{"tool":"selamla","arguments":{"isim":"Ebru"}}') == "Merhaba Ebru"
    with pytest.raises(SecurityViolationError):
        registry.execute_model_call('{"tool":"selamla","code":"import os"}')


def test_unknown_model_tool_is_blocked(tmp_path):
    registry = ToolRegistry(PermissionManager(str(tmp_path / "permissions.json")))
    with pytest.raises(SecurityViolationError):
        registry.execute_model_call('{"tool":"shell","arguments":{"command":"whoami"}}')


def test_tool_registry_rejects_unexpected_or_missing_arguments(tmp_path):
    registry = ToolRegistry(PermissionManager(str(tmp_path / "permissions.json")))
    registry.register("selamla", "conversation", lambda isim: f"Merhaba {isim}")

    with pytest.raises(SecurityViolationError):
        registry.execute("selamla", {"isim": "Ebru", "yonetici": True})
    with pytest.raises(SecurityViolationError):
        registry.execute("selamla", {})


def test_tool_registry_rejects_unbounded_keyword_handlers(tmp_path):
    registry = ToolRegistry(PermissionManager(str(tmp_path / "permissions.json")))

    with pytest.raises(ValueError):
        registry.register("esnek", "conversation", lambda **kwargs: str(kwargs))
