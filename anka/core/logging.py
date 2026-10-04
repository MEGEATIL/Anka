"""ANKA icin dosyaya yazilan, donusumlu uygulama gunlugu."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re


_SENSITIVE_VALUE = re.compile(
    r"(?i)(api[_ -]?key|token|secret|password|parola|şifre)\s*([:=])\s*([^\s,;]+)"
)


def redact_sensitive_text(value: object, limit: int = 240) -> str:
    """Günlüklere yazılabilecek metinden sırları ve aşırı uzun girdiyi çıkarır."""
    text = str(value or "")
    text = _SENSITIVE_VALUE.sub(lambda match: f"{match.group(1)}{match.group(2)}[MASKELENDİ]", text)
    return text[:limit]


def configure_logging(log_dir: str = "logs") -> logging.Logger:
    logger = logging.getLogger("anka")
    if logger.handlers:
        return logger
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        Path(log_dir) / "anka.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
