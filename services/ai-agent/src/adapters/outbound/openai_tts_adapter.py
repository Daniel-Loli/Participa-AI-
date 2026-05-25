from __future__ import annotations

import logging

import openai
from openai import AsyncOpenAI

from src.adapters.outbound.errors import TtsApiError
from src.domain.ports.i_tts_client import ITtsClient

logger = logging.getLogger(__name__)

_MAX_TTS_CHARS = 4096


class OpenAITtsAdapter(ITtsClient):
    """Implementa ITtsClient usando OpenAI TTS API."""

    def __init__(self, api_key: str, model: str = "tts-1", voice: str = "alloy") -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=30)
        self._model = model
        self._voice = voice

    async def synthesize(self, text: str) -> bytes:
        if len(text) > _MAX_TTS_CHARS:
            logger.warning("Texto TTS truncado de %d a %d caracteres", len(text), _MAX_TTS_CHARS)
            text = text[:_MAX_TTS_CHARS]
        try:
            response = await self._client.audio.speech.create(
                model=self._model,
                voice=self._voice,
                input=text,
                response_format="mp3",
            )
            return response.content
        except openai.APIError as exc:
            raise TtsApiError(str(exc)) from exc
