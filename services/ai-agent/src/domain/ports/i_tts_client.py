from __future__ import annotations

from abc import ABC, abstractmethod


class ITtsClient(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Sintetiza texto a audio MP3. Retorna bytes."""
