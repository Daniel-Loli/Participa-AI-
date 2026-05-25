import logging

import httpx
import openai
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.outbound.errors import TtsApiError
from src.domain.ports.i_tts_client import ITtsClient

_PATCH_TARGET = "src.adapters.outbound.openai_tts_adapter.AsyncOpenAI"


def make_mock_client(audio_bytes: bytes = b"fake mp3 audio") -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = audio_bytes
    client = MagicMock()
    client.audio.speech.create = AsyncMock(return_value=mock_response)
    return client


def make_api_error() -> openai.InternalServerError:
    return openai.InternalServerError(
        message="TTS service unavailable",
        response=httpx.Response(
            500,
            request=httpx.Request("POST", "https://api.openai.com/v1/audio/speech"),
        ),
        body={"error": {"message": "TTS service unavailable"}},
    )


class TestOpenAITtsAdapter:
    async def test_synthesize_exitoso_retorna_bytes(self):
        mock_client = make_mock_client(b"fake mp3 audio")
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
            result = await adapter.synthesize("Hola, soy Participa AI")
        assert result == b"fake mp3 audio"
        assert isinstance(result, bytes)

    async def test_texto_corto_no_se_trunca(self):
        mock_client = make_mock_client()
        texto = "Hola mundo"
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
            await adapter.synthesize(texto)
        call_kwargs = mock_client.audio.speech.create.call_args.kwargs
        assert call_kwargs["input"] == texto

    async def test_texto_largo_se_trunca_a_4096(self):
        mock_client = make_mock_client()
        texto_largo = "x" * 5000
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
            await adapter.synthesize(texto_largo)
        call_kwargs = mock_client.audio.speech.create.call_args.kwargs
        assert len(call_kwargs["input"]) == 4096

    async def test_texto_largo_loguea_warning(self, caplog):
        mock_client = make_mock_client()
        texto_largo = "x" * 5000
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
            with caplog.at_level(logging.WARNING):
                await adapter.synthesize(texto_largo)
        assert any("truncado" in record.message.lower() for record in caplog.records)

    async def test_api_error_lanza_tts_api_error(self):
        mock_client = MagicMock()
        mock_client.audio.speech.create = AsyncMock(side_effect=make_api_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
            with pytest.raises(TtsApiError):
                await adapter.synthesize("texto")

    async def test_implementa_i_tts_client(self):
        with patch(_PATCH_TARGET, return_value=MagicMock()):
            from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
            adapter = OpenAITtsAdapter(api_key="sk-test")
        assert isinstance(adapter, ITtsClient)
