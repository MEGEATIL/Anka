"""Bekleyen çok-adımlı diyalogların güvenli yönlendirmesi."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from anka.core.invocation import invoke_command_handler


PendingHandler = tuple[str, Callable[..., Any]]


def dispatch_pending_response(
    target: Any,
    handlers: Iterable[PendingHandler],
    command: str,
    on_error: Callable[[str, Exception], None],
) -> bool:
    """İlk aktif bekleme durumunu yürütür ve hatada durumu temizler."""
    for state_name, handler in handlers:
        if not getattr(target, state_name, None):
            continue
        try:
            invoke_command_handler(handler, command)
        except Exception as error:
            setattr(target, state_name, False)
            on_error(state_name, error)
        return True
    return False
