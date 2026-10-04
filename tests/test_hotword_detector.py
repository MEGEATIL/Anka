from pathlib import Path

import hotword_detector


class _RunningProcess:
    def poll(self):
        return None


def test_hotword_launch_uses_project_entrypoint_without_shell(monkeypatch, tmp_path):
    entrypoint = tmp_path / "mainyapayzeka1.py"
    entrypoint.write_text("pass", encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        hotword_detector.subprocess,
        "Popen",
        lambda command, cwd: calls.append((command, cwd)) or _RunningProcess(),
    )

    assert hotword_detector._launch_assistant(entrypoint) is True
    assert calls[0][0][1] == str(entrypoint)
    assert calls[0][1] == str(tmp_path)


def test_hotword_does_not_launch_for_missing_entrypoint(tmp_path):
    assert hotword_detector._launch_assistant(Path(tmp_path / "missing.py")) is False
