"""Komut işleyicilerini iç hataları gizlemeden uyumlu şekilde çağırma."""

from __future__ import annotations

import inspect
from typing import Any, Callable


def invoke_command_handler(handler: Callable[..., Any], command: str) -> Any:
    """İşleyicinin imzasına göre komutu aktarır.

    Eski yaklaşımda ``TypeError`` yakalanıp fonksiyon argümansız yeniden
    çağrılıyordu. Bu, işleyicinin içindeki gerçek ``TypeError`` hatasını
    maskeleyebiliyordu. İmza yalnızca çağrı biçimini belirler; işleyici hatası
    olduğu gibi üst katmana ulaşır.
    """
    try:
        parameters = list(inspect.signature(handler).parameters.values())
    except (TypeError, ValueError):
        # İmzası çıkarılamayan üçüncü taraf çağrılar için mevcut davranışı
        # koru; çalışma hatası kesinlikle burada yutulmaz.
        return handler(command)

    positional = [
        parameter for parameter in parameters
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        }
    ]
    return handler(command) if positional else handler()
