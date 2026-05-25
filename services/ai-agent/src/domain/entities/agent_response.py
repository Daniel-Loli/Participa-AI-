from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentResponse:
    response_type: str                      # "text" | "audio"
    response_text: str | None = None
    response_audio_base64: str | None = None
