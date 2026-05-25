from __future__ import annotations

from dataclasses import dataclass

from src.domain.value_objects.message_type import MessageType


@dataclass(frozen=True)
class Message:
    from_hash: str          # SHA256 del número — nunca el número real
    type: MessageType
    session_id: str
    timestamp: int
    text_content: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None

    def is_text(self) -> bool:
        return self.type == MessageType.TEXT

    def is_audio(self) -> bool:
        return self.type == MessageType.AUDIO
