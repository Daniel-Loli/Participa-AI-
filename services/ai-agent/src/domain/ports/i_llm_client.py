from __future__ import annotations

from abc import ABC, abstractmethod


class ILlmClient(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str) -> str:
        """Genera texto usando el LLM configurado."""
