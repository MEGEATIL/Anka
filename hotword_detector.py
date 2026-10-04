"""İsteğe bağlı, kullanıcı tarafından başlatılan ANKA hotword dinleyicisi."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any

from anka.security.permissions import Permission, PermissionManager

try:
    import speech_recognition as sr
except ImportError:
    sr = None


HOTWORDS = ("dijidost", "diji", "dihjidost")
ENTRYPOINT = Path(__file__).with_name("mainyapayzeka1.py")


def _launch_assistant(entrypoint: Path = ENTRYPOINT) -> bool:
    """Komut satırı üretmeden, proje içindeki sabit giriş noktasını başlatır."""
    if not entrypoint.is_file():
        return False
    try:
        process = subprocess.Popen([sys.executable, str(entrypoint)], cwd=str(entrypoint.parent))
    except OSError:
        return False
    return process.poll() is None


def listen_for_hotword(recognizer: Any, microphone: Any) -> None:
    """Mikrofon hatasında kapanmadan kullanıcıya kısa durum mesajı verir."""
    print("Hotword dinleyici aktif: 'dijidost' deyin. Çıkmak için Ctrl+C.")
    while True:
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language="tr-TR").casefold()
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError:
            print("Ses tanıma servisine erişilemedi; yeniden denenecek.")
            continue
        except OSError:
            print("Mikrofon kullanılamıyor; dinleyici durduruldu.")
            return

        if any(word in text for word in HOTWORDS):
            if _launch_assistant():
                print("ANKA başlatıldı.")
            else:
                print("ANKA başlatılamadı; giriş dosyasını ve Python ortamını kontrol edin.")


def main() -> int:
    if sr is None:
        print("SpeechRecognition kurulu değil. requirements.txt dosyasını yükleyin.")
        return 2
    if not PermissionManager(ENTRYPOINT.with_name("permissions.json")).is_allowed(Permission.WEB):
        print("Bulut ses tanıma için web izni kapalı. Ayarlar > Gizlilik bölümünden etkinleştirin.")
        return 4
    try:
        microphone = sr.Microphone()
    except OSError:
        print("Mikrofon erişilemez veya işletim sistemi izni kapalı.")
        return 3
    try:
        listen_for_hotword(sr.Recognizer(), microphone)
    except KeyboardInterrupt:
        print("Hotword dinleyici kapatıldı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
