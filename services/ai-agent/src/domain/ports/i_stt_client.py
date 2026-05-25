from __future__ import annotations

from abc import ABC, abstractmethod


class ISttClient(ABC):
    @abstractmethod
    async def transcribe(self, audio_base64: str, mime_type: str) -> str:
        """Transcribe audio a texto en español."""
