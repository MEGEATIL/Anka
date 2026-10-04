"""Kullanıcıdan gelen dosya yolları için merkezi güvenlik denetimi."""

from __future__ import annotations

from pathlib import Path

from anka.core.errors import FileProcessingError


def resolve_user_file(raw_path: str, *, for_creation: bool = False) -> Path:
    """Yolu kullanıcının standart klasörleriyle sınırlar.

    Göreli dosya adları ``Belgeler/ANKA`` altında çözülür. Böylece bir sesli
    komut proje dizinine veya sistem klasörlerine istemeden yazamaz.
    """
    value = str(raw_path or "").strip()
    if not value or "\x00" in value:
        raise FileProcessingError("Geçerli bir dosya yolu belirtin.")

    home = Path.home().resolve()
    anka_documents = home / "Documents" / "ANKA"
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = anka_documents / candidate
    resolved = candidate.resolve(strict=False)
    allowed_roots = (home / "Desktop", home / "Documents", home / "Downloads")
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed_roots):
        raise FileProcessingError("Güvenlik nedeniyle yalnızca Masaüstü, Belgeler veya İndirilenler kullanılabilir.")
    if for_creation:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
