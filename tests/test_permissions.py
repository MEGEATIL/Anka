from anka.security.permissions import Permission, PermissionManager


def test_permission_snapshot_and_persistence(tmp_path):
    path = tmp_path / "permissions.json"
    manager = PermissionManager(str(path))
    assert manager.snapshot()["camera"] is False
    manager.set(Permission.CAMERA, True)
    assert PermissionManager(str(path)).is_allowed(Permission.CAMERA)


def test_permission_file_with_invalid_json_uses_safe_defaults(tmp_path):
    path = tmp_path / "permissions.json"
    path.write_text("{not-json", encoding="utf-8")
    manager = PermissionManager(str(path))
    assert manager.is_allowed(Permission.CAMERA) is False
    assert manager.is_allowed(Permission.SYSTEM) is False
