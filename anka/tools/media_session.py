"""Windows medya oturumundan oynatılan parçayı güvenli biçimde okur."""

from __future__ import annotations

import asyncio
import ctypes
import os
import platform
from typing import Any


def _platform_name(source_app_id: str, preferred: str) -> str:
    source = source_app_id.lower()
    if "spotify" in source:
        return "Spotify"
    if "youtube" in source or "chrome" in source or "msedge" in source:
        return "YouTube Music" if preferred == "ytmusic" else "Tarayıcı"
    return "Medya oturumu"


async def _read_session(preferred: str) -> dict[str, Any]:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaSessionManager,
    )

    manager = await MediaSessionManager.request_async()
    session = manager.get_current_session()
    if session is None:
        return {"available": False}
    properties = await session.try_get_media_properties_async()
    title = (properties.title or "").strip()
    artist = (properties.artist or "").strip()
    if not title:
        return {"available": False}
    source_name = _platform_name(session.source_app_user_model_id or "", preferred)
    if source_name == "YouTube Music":
        title = title.removesuffix(" | YouTube Music").strip()
        if artist.casefold() in {"google chrome", "microsoft edge", "chrome", "edge"}:
            artist = "YouTube Music"
    return {
        "available": True,
        "title": title,
        "artist": artist or "Bilinmeyen sanatçı",
        "platform": source_name,
    }


def current_media_session(preferred: str = "") -> dict[str, Any]:
    """Bir Windows medya oturumu varsa parça bilgisini döndürür.

    `winsdk` isteğe bağlıdır; yüklü değilse çağıran katman mevcut ANKA
    müzik bilgisini korur.
    """
    if platform.system() != "Windows":
        return {"available": False}
    try:
        session = asyncio.run(_read_session(preferred))
        if session.get("available"):
            return session
    except (ImportError, RuntimeError):
        pass
    return _youtube_music_window_title()


async def _control_session(action: str) -> bool:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaSessionManager,
    )

    manager = await MediaSessionManager.request_async()
    session = manager.get_current_session()
    if session is None:
        return False
    methods = {
        "playpause": "try_toggle_play_pause_async",
        "next": "try_skip_next_async",
        "previous": "try_skip_previous_async",
    }
    method_name = methods.get(action)
    if method_name is None:
        return False
    return bool(await getattr(session, method_name)())


def _send_media_key(action: str) -> bool:
    """Windows medya oturumu paketi yoksa global medya tuşunu gönderir."""
    if os.name != "nt":
        return False
    virtual_keys = {"playpause": 0xB3, "next": 0xB0, "previous": 0xB1}
    key = virtual_keys.get(action)
    if key is None:
        return False
    try:
        user32 = ctypes.windll.user32
        key_up = 0x0002
        user32.keybd_event(key, 0, 0, 0)
        user32.keybd_event(key, 0, key_up, 0)
        return True
    except (AttributeError, OSError):
        return False


def control_media_session(action: str) -> dict[str, Any]:
    """Aktif medya oturumunu kontrol eder ve kullanılan yolu bildirir."""
    if action not in {"playpause", "next", "previous"}:
        return {"ok": False, "message": "Desteklenmeyen medya komutu."}
    if platform.system() == "Windows":
        try:
            if asyncio.run(_control_session(action)):
                return {"ok": True, "method": "media_session"}
        except (ImportError, RuntimeError, AttributeError, OSError):
            pass
    if _send_media_key(action):
        return {"ok": True, "method": "media_key"}
    return {"ok": False, "message": "Aktif bir medya oturumu bulunamadı."}


def _youtube_music_window_title() -> dict[str, Any]:
    """Ek paket olmadan açık YouTube Music tarayıcı başlığını okur.

    Chrome ve Edge pencere başlığı, oynatılan parça için çoğunlukla
    ``Parça - Sanatçı - YouTube Music`` biçimindedir. Bu yalnızca kullanıcının
    açık pencere başlıklarını yerelde okur; ağ erişimi ya da hesap verisi yoktur.
    """
    if os.name != "nt":
        return {"available": False}

    titles: list[str] = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def collect(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if "youtube music" in title.casefold():
            titles.append(title)
        return True

    try:
        user32.EnumWindows(collect, 0)
    except (AttributeError, OSError):
        return {"available": False}
    if not titles:
        return {"available": False}

    raw_title = titles[0]
    track_info = raw_title
    # Chrome/Edge, YouTube Music'i farklı başlık biçimleriyle ekleyebilir.
    # Sadece bilinen uygulama soneklerini temizleriz; parça adındaki tireler
    # olduğu gibi korunur.
    for suffix in (
        " - Google Chrome",
        " - Microsoft Edge",
        " | YouTube Music",
        " - YouTube Music",
    ):
        if track_info.casefold().endswith(suffix.casefold()):
            track_info = track_info[: -len(suffix)].strip()
    title = track_info
    artist = "YouTube Music"
    return {
        "available": bool(title),
        "title": title or "Bilinmeyen parça",
        "artist": artist,
        "platform": "YouTube Music",
    }
