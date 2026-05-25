import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.adapters.inbound.agent_router import (
    get_process_message_use_case,
    router,
)
from src.application.errors import OrchestratorError, SttTranscriptionError
from src.domain.entities.agent_response import AgentResponse


def make_use_case(response: AgentResponse | None = None) -> MagicMock:
    mock = MagicMock()
    mock.execute = AsyncMock(
        return_value=response
        or AgentResponse(response_type="text", response_text="Respuesta del agente.")
    )
    return mock


def make_app(use_case_mock: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_process_message_use_case] = lambda: use_case_mock
    return app


@pytest.fixture
def text_payload() -> dict:
    return {
        "from": "abc123sha256",
        "type": "text",
        "session_id": "session-1",
        "timestamp": 1700000000,
        "message": "¿qué leyes me protegen?",
    }


@pytest.fixture
def audio_payload() -> dict:
    return {
        "from": "abc123sha256",
        "type": "audio",
        "session_id": "session-1",
        "timestamp": 1700000000,
        "audio_base64": base64.b64encode(b"fake-audio").decode(),
        "audio_mime_type": "audio/ogg",
    }


class TestAgentRouterPost:
    async def test_texto_valido_retorna_200(self, text_payload):
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=text_payload)
        assert resp.status_code == 200

    async def test_texto_retorna_response_type_y_texto(self, text_payload):
        resp_obj = AgentResponse(response_type="text", response_text="La Ley 28056 establece el PP.")
        app = make_app(make_use_case(resp_obj))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=text_payload)
        data = resp.json()
        assert data["response_type"] == "text"
        assert data["response_text"] == "La Ley 28056 establece el PP."

    async def test_audio_valido_retorna_200(self, audio_payload):
        resp_obj = AgentResponse(response_type="audio", response_audio_base64="bXAzYXVkaW8=")
        app = make_app(make_use_case(resp_obj))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=audio_payload)
        assert resp.status_code == 200
        assert resp.json()["response_type"] == "audio"

    async def test_texto_sin_message_retorna_422(self):
        payload = {
            "from": "abc123",
            "type": "text",
            "session_id": "s1",
            "timestamp": 1700000000,
        }
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=payload)
        assert resp.status_code == 422

    async def test_audio_sin_audio_base64_retorna_422(self):
        payload = {
            "from": "abc123",
            "type": "audio",
            "session_id": "s1",
            "timestamp": 1700000000,
        }
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=payload)
        assert resp.status_code == 422

    async def test_type_invalido_retorna_422(self):
        payload = {
            "from": "abc123",
            "type": "imagen",
            "session_id": "s1",
            "timestamp": 1700000000,
            "message": "hola",
        }
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=payload)
        assert resp.status_code == 422

    async def test_stt_transcription_error_retorna_422_con_mensaje_amigable(self, text_payload):
        mock_uc = make_use_case()
        mock_uc.execute = AsyncMock(side_effect=SttTranscriptionError("whisper crash"))
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=text_payload)
        assert resp.status_code == 422
        assert "detail" in resp.json()
        assert "whisper crash" not in resp.text

    async def test_orchestrator_error_retorna_500(self, text_payload):
        mock_uc = make_use_case()
        mock_uc.execute = AsyncMock(side_effect=OrchestratorError("LangGraph crash"))
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=text_payload)
        assert resp.status_code == 500

    async def test_orchestrator_error_no_expone_detalles_internos(self, text_payload):
        mock_uc = make_use_case()
        mock_uc.execute = AsyncMock(side_effect=OrchestratorError("internal stack trace details"))
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/agent", json=text_payload)
        assert "internal stack trace details" not in resp.text

    async def test_use_case_llamado_con_session_id_correcto(self, text_payload):
        mock_uc = make_use_case()
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/agent", json=text_payload)
        msg = mock_uc.execute.call_args[0][0]
        assert msg.session_id == "session-1"

    async def test_use_case_llamado_con_contenido_texto(self, text_payload):
        mock_uc = make_use_case()
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/agent", json=text_payload)
        msg = mock_uc.execute.call_args[0][0]
        assert msg.text_content == "¿qué leyes me protegen?"
        assert msg.is_text()

    async def test_use_case_llamado_con_tipo_audio(self, audio_payload):
        mock_uc = make_use_case(AgentResponse(response_type="text", response_text="ok"))
        app = make_app(mock_uc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/agent", json=audio_payload)
        msg = mock_uc.execute.call_args[0][0]
        assert msg.is_audio()
        assert msg.audio_mime_type == "audio/ogg"


class TestAgentRouterHealth:
    async def test_health_retorna_200(self):
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_retorna_status_ok(self):
        app = make_app(make_use_case())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-agent"
        assert "timestamp" in data
