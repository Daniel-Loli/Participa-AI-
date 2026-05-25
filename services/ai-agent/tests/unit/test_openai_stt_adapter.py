import base64
import httpx
import openai
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.outbound.errors import SttInvalidAudioError, SttTimeoutError
from src.domain.ports.i_stt_client import ISttClient

_PATCH_TARGET = "src.adapters.outbound.openai_stt_adapter.AsyncOpenAI"


def make_audio_b64(content: bytes = b"fake audio bytes") -> str:
    return base64.b64encode(content).decode()


def make_mock_client(text: str = "texto transcrito") -> MagicMock:
    mock_transcription = MagicMock()
    mock_transcription.text = text
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
    return client


def make_timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
    )


def make_bad_request_error() -> openai.BadRequestError:
    return openai.BadRequestError(
        message="Invalid audio format",
        response=httpx.Response(
            400,
            request=httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions"),
        ),
        body={"error": {"message": "Invalid audio format"}},
    )


class TestOpenAISttAdapter:
    async def test_transcribe_exitoso_retorna_texto(self):
        mock_client = make_mock_client("texto transcrito")
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
            result = await adapter.transcribe(make_audio_b64(), "audio/ogg")
        assert result == "texto transcrito"

    async def test_transcribe_verifica_nombre_archivo_audio_ogg(self):
        mock_client = make_mock_client()
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
            await adapter.transcribe(make_audio_b64(), "audio/ogg")
        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["file"].name == "audio.ogg"

    async def test_timeout_lanza_stt_timeout_error(self):
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(side_effect=make_timeout_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
            with pytest.raises(SttTimeoutError):
                await adapter.transcribe(make_audio_b64(), "audio/ogg")

    async def test_bad_request_lanza_stt_invalid_audio_error(self):
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(side_effect=make_bad_request_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
            with pytest.raises(SttInvalidAudioError):
                await adapter.transcribe(make_audio_b64(), "audio/ogg")

    async def test_implementa_i_stt_client(self):
        with patch(_PATCH_TARGET, return_value=MagicMock()):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
        assert isinstance(adapter, ISttClient)

    async def test_decodifica_base64_correctamente(self):
        original_bytes = b"contenido de audio real"
        audio_b64 = base64.b64encode(original_bytes).decode()
        mock_client = make_mock_client()
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
            adapter = OpenAISttAdapter(api_key="sk-test")
            await adapter.transcribe(audio_b64, "audio/ogg")
        file_arg = mock_client.audio.transcriptions.create.call_args.kwargs["file"]
        assert file_arg.getvalue() == original_bytes
