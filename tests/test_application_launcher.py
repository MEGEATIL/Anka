import uygulama_acici


class _RunningProcess:
    def poll(self):
        return None


class _StoppedProcess:
    def poll(self):
        return 1


def test_application_launcher_reports_verified_running_process(monkeypatch):
    calls = []
    monkeypatch.setattr(uygulama_acici.os.path, "isfile", lambda _: True)
    monkeypatch.setattr(
        uygulama_acici.subprocess,
        "Popen",
        lambda command: calls.append(command) or _RunningProcess(),
    )

    success, message = uygulama_acici._calistir("Test", "C:/Apps/test.exe")

    assert success is True
    assert len(calls) == 1
    assert calls[0][0].endswith("test.exe")
    assert "doğrulandı" in message


def test_application_launcher_does_not_claim_success_when_process_exits(monkeypatch):
    monkeypatch.setattr(uygulama_acici.os.path, "isfile", lambda _: True)
    monkeypatch.setattr(uygulama_acici.subprocess, "Popen", lambda _: _StoppedProcess())

    success, message = uygulama_acici._calistir("Test", "C:/Apps/test.exe")

    assert success is False
    assert "hemen sonlandı" in message
