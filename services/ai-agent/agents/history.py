from __future__ import annotations

_MAX_HISTORY = 20


def trim_history(history: list) -> list:
    """Limita el historial a los últimos _MAX_HISTORY mensajes para evitar overflow de contexto."""
    if len(history) <= _MAX_HISTORY:
        return history
    return history[-_MAX_HISTORY:]
