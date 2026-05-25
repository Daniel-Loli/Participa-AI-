import httpx
import openai
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import SystemMessage

from src.adapters.outbound.errors import LlmApiError, LlmTimeoutError
from src.domain.ports.i_llm_client import ILlmClient

# Ruta de import del ChatOpenAI usado dentro del adapter
_PATCH_TARGET = "src.adapters.outbound.openai_llm_adapter.ChatOpenAI"


def make_mock_client(content: str = "Respuesta del LLM") -> MagicMock:
    """Crea un mock de ChatOpenAI que devuelve `content` al invocar."""
    mock_response = MagicMock()
    mock_response.content = content
    client = MagicMock()
    client.ainvoke = AsyncMock(return_value=mock_response)
    return client


def make_timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    )


def make_rate_limit_error() -> openai.RateLimitError:
    return openai.RateLimitError(
        message="Rate limit exceeded",
        response=httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        ),
        body={"error": {"message": "Rate limit exceeded"}},
    )


def make_connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    )


class TestOpenAILlmAdapter:
    async def test_generate_exitoso_retorna_string(self):
        mock_client = make_mock_client("Respuesta del LLM")
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test", model="gpt-4o-mini")
            result = await adapter.generate("eres un asistente", "¿qué es el PP?")
        assert result == "Respuesta del LLM"

    async def test_generate_pasa_system_message(self):
        mock_client = make_mock_client("ok")
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test", model="gpt-4o-mini")
            await adapter.generate("mi system prompt", "user msg")

        mensajes_enviados = mock_client.ainvoke.call_args[0][0]
        assert any(
            isinstance(m, SystemMessage) and m.content == "mi system prompt"
            for m in mensajes_enviados
        )

    async def test_timeout_lanza_llm_timeout_error(self):
        mock_client = MagicMock()
        mock_client.ainvoke = AsyncMock(side_effect=make_timeout_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test")
            with pytest.raises(LlmTimeoutError):
                await adapter.generate("system", "user")

    async def test_api_status_error_lanza_llm_api_error_con_status_code(self):
        mock_client = MagicMock()
        mock_client.ainvoke = AsyncMock(side_effect=make_rate_limit_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test")
            with pytest.raises(LlmApiError) as exc_info:
                await adapter.generate("system", "user")
        assert exc_info.value.status_code == 429

    async def test_api_error_generico_lanza_llm_api_error_sin_status(self):
        mock_client = MagicMock()
        mock_client.ainvoke = AsyncMock(side_effect=make_connection_error())
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test")
            with pytest.raises(LlmApiError) as exc_info:
                await adapter.generate("system", "user")
        assert exc_info.value.status_code is None

    async def test_implementa_i_llm_client(self):
        with patch(_PATCH_TARGET, return_value=MagicMock()):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test")
        assert isinstance(adapter, ILlmClient)

    async def test_retorna_string_aunque_content_sea_numerico(self):
        mock_response = MagicMock()
        mock_response.content = 42
        mock_client = MagicMock()
        mock_client.ainvoke = AsyncMock(return_value=mock_response)
        with patch(_PATCH_TARGET, return_value=mock_client):
            from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
            adapter = OpenAILlmAdapter(api_key="sk-test")
            result = await adapter.generate("system", "user")
        assert isinstance(result, str)
        assert result == "42"
