import sys
import types
import json


# DijiDost modülü yüklendiğinde pywebview kurulmamış test ortamlarında küçük
# bir arayüz taklidi yeterlidir; API davranışını gerçek pencere açmadan test eder.
if "webview" not in sys.modules:
    sys.modules["webview"] = types.SimpleNamespace(windows=[])

import dijidost_entegrasyon
from anka.security.permissions import Permission, PermissionManager


class _Groq:
    def chat(self, message):
        return f"yanıt: {message}"


def test_bridge_uses_groq_when_main_assistant_is_unavailable(monkeypatch):
    messages = []
    monkeypatch.setattr(dijidost_entegrasyon, "_asis", None)
    monkeypatch.setattr(dijidost_entegrasyon, "_groq", _Groq())
    monkeypatch.setattr(
        dijidost_entegrasyon,
        "arayuze_mesaj_gonder",
        lambda text, sender="Anka": messages.append((text, sender)),
    )

    dijidost_entegrasyon.API().asistan_komut("merhaba")

    assert messages == [("yanıt: merhaba", "Anka")]


def test_bridge_rejects_blank_messages_without_calling_the_model(monkeypatch):
    messages = []
    monkeypatch.setattr(dijidost_entegrasyon, "_asis", None)
    monkeypatch.setattr(dijidost_entegrasyon, "_groq", _Groq())
    monkeypatch.setattr(
        dijidost_entegrasyon,
        "arayuze_mesaj_gonder",
        lambda text, sender="Anka": messages.append((text, sender)),
    )

    dijidost_entegrasyon.API().asistan_komut("   ")

    assert messages == [("Lütfen bir mesaj yazın.", "Anka")]


class _Window:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class _Timer:
    started = 0

    def __init__(self, _delay, _callback):
        self.callback = _callback

    def start(self):
        type(self).started += 1


class _RunningProcess:
    def poll(self):
        return None


def test_bridge_serializes_message_content_for_javascript(monkeypatch):
    window = _Window()
    monkeypatch.setattr(dijidost_entegrasyon.webview, "windows", [window])

    dijidost_entegrasyon.arayuze_mesaj_gonder("'); window.pwned=true; //", "Kullanıcı")

    assert window.scripts == ['mesajEkle("Kullanıcı", "\'); window.pwned=true; //")']


def test_system_information_skips_ping_when_web_permission_is_disabled(monkeypatch, tmp_path):
    permissions = PermissionManager(str(tmp_path / "permissions.json"))
    permissions.set(Permission.WEB, False)
    monkeypatch.setattr(dijidost_entegrasyon, "_asis", types.SimpleNamespace(permissions=permissions))
    monkeypatch.setattr(
        dijidost_entegrasyon.socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ağ çağrısı yapılmamalı")),
    )

    result = dijidost_entegrasyon.API().sistem_bilgisi()

    assert result["ping"] == "Kullanılamıyor"


def test_voice_preference_is_persisted_before_memory_state_changes(monkeypatch, tmp_path):
    settings_path = tmp_path / "ses_ayari.json"
    monkeypatch.setattr(dijidost_entegrasyon, "SES_AYAR_DOSYASI", str(settings_path))
    monkeypatch.setattr(dijidost_entegrasyon, "_ses_cinsiyeti", "kadin")

    assert dijidost_entegrasyon.ses_cinsiyeti_ayarla("erkek") is True
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {"cinsiyet": "erkek"}
    assert dijidost_entegrasyon.ses_cinsiyeti_getir() == "erkek"


def test_voice_preference_does_not_claim_success_when_persistence_fails(monkeypatch, tmp_path):
    invalid_parent = tmp_path / "missing" / "ses_ayari.json"
    monkeypatch.setattr(dijidost_entegrasyon, "SES_AYAR_DOSYASI", str(invalid_parent))
    monkeypatch.setattr(dijidost_entegrasyon, "_ses_cinsiyeti", "kadin")

    assert dijidost_entegrasyon.ses_cinsiyeti_ayarla("erkek") is False
    assert dijidost_entegrasyon.ses_cinsiyeti_getir() == "kadin"


def test_ui_state_round_trip_uses_persistent_storage(monkeypatch, tmp_path):
    state_path = tmp_path / "dijidost_state.json"
    monkeypatch.setattr(dijidost_entegrasyon, "UI_STATE_DOSYASI", str(state_path))
    api = dijidost_entegrasyon.API()

    assert api.save_ui_state('{"notlar":["kalıcı not"],"gorevler":[{"metin":"test"}]}') is True
    assert json.loads(api.load_ui_state()) == {
        "notlar": ["kalıcı not"],
        "gorevler": [{"metin": "test"}],
    }


def test_external_values_are_json_serialized_before_webview_evaluation(monkeypatch):
    window = _Window()
    monkeypatch.setattr(dijidost_entegrasyon.webview, "windows", [window])
    hostile = '\"); window.pwned=true; //'

    dijidost_entegrasyon.hava_durumu_guncelle(hostile, hostile)
    dijidost_entegrasyon.kripto_guncelle(hostile, hostile, hostile, hostile, hostile, hostile)

    assert json.dumps(hostile, ensure_ascii=False) in window.scripts[0]
    assert "textContent = values.btc" in window.scripts[1]
    assert f'"btc": {json.dumps(hostile, ensure_ascii=False)}' in window.scripts[1]


def test_restart_keeps_current_application_alive_when_child_cannot_start(monkeypatch, tmp_path):
    entrypoint = tmp_path / "app.py"
    entrypoint.write_text("pass", encoding="utf-8")
    monkeypatch.setattr(dijidost_entegrasyon.sys, "argv", [str(entrypoint)])
    monkeypatch.setattr(
        dijidost_entegrasyon.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("engellendi")),
    )
    _Timer.started = 0
    monkeypatch.setattr(dijidost_entegrasyon.threading, "Timer", _Timer)

    result = dijidost_entegrasyon.API().uygulamayi_yeniden_baslat()

    assert result["ok"] is False
    assert _Timer.started == 0


def test_restart_schedules_current_close_only_after_child_process_starts(monkeypatch, tmp_path):
    entrypoint = tmp_path / "app.py"
    entrypoint.write_text("pass", encoding="utf-8")
    monkeypatch.setattr(dijidost_entegrasyon.sys, "argv", [str(entrypoint)])
    monkeypatch.setattr(dijidost_entegrasyon.subprocess, "Popen", lambda *_args, **_kwargs: _RunningProcess())
    _Timer.started = 0
    monkeypatch.setattr(dijidost_entegrasyon.threading, "Timer", _Timer)

    result = dijidost_entegrasyon.API().uygulamayi_yeniden_baslat()

    assert result == {"ok": True}
    assert _Timer.started == 1


def test_privacy_sensitive_status_indicators_are_not_rendered():
    assert 'id="status-network"' not in dijidost_entegrasyon.DIJIDOST_HTML
    assert 'id="status-battery"' not in dijidost_entegrasyon.DIJIDOST_HTML
