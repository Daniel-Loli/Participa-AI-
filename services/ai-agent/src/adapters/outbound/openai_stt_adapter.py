from __future__ import annotations

import base64
import io

import openai
from openai import AsyncOpenAI

from src.adapters.outbound.errors import SttInvalidAudioError, SttTimeoutError
from src.domain.ports.i_stt_client import ISttClient


class OpenAISttAdapter(ISttClient):
    """Implementa ISttClient usando OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=20)
        self._model = model

    async def transcribe(self, audio_base64: str, mime_type: str) -> str:
        audio_bytes = base64.b64decode(audio_base64)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"
        try:
            transcription = await self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                language="es",
            )
            return transcription.text
        except openai.APITimeoutError as exc:
            raise SttTimeoutError("Whisper no respondió en 20s") from exc
        except openai.BadRequestError as exc:
            raise SttInvalidAudioError("Audio inválido o no transcribible") from exc
