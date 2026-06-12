import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.domain.ports.i_rag_client import RagDocument
from agents.estratega_node import make_estratega_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "¿cómo presento una queja?",
        "intent": "estratega",
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Paso 1: ...") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    mock.generate_with_history = AsyncMock(return_value=response)
    return mock


def make_rag(docs=None) -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=docs or [])
    return mock


# Fechas relativas a hoy para que los tests no caduquen con el tiempo
def _futura(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).isoformat()


_EVENTOS_MIRAFLORES = [
    {"fecha": _futura(7), "tipo": "sesión", "distrito": "Miraflores", "descripcion": "Sesión PP"},
    {"fecha": _futura(14), "tipo": "audiencia", "distrito": "Miraflores", "descripcion": "Audiencia"},
    {"fecha": _futura(30), "tipo": "taller", "distrito": "Miraflores", "descripcion": "Taller"},
]

_EVENTOS_MIXTOS = _EVENTOS_MIRAFLORES + [
    {"fecha": _futura(45), "tipo": "feria", "distrito": "San Isidro", "descripcion": "Feria"},
]


class TestEstrategaNode:
    async def test_perfil_completo_prompt_incluye_nombre_y_distrito(self, tmp_path):
        (tmp_path / "calendar.json").write_text("[]")
        mock_llm = make_llm()
        node = make_estratega_node(mock_llm, make_rag(), data_dir=str(tmp_path))
        await node(make_state(user_profile={"name": "Ana", "district": "Miraflores"}))

        system_prompt = mock_llm.generate_with_history.call_args[0][0]
        assert "Ana" in system_prompt
        assert "Miraflores" in system_prompt

    async def test_calendar_json_con_eventos_filtrados_por_distrito(self, tmp_path):
        (tmp_path / "calendar.json").write_text(json.dumps(_EVENTOS_MIRAFLORES))
        mock_llm = make_llm()
        node = make_estratega_node(mock_llm, make_rag(), data_dir=str(tmp_path))
        result = await node(make_state(user_profile={"name": "Ana", "district": "Miraflores"}))

        assert len(result["tool_data"]["eventos"]) == 3
        assert all(e["distrito"] == "Miraflores" for e in result["tool_data"]["eventos"])

    async def test_calendar_json_ausente_continua_sin_eventos(self, tmp_path):
        mock_llm = make_llm()
        node = make_estratega_node(mock_llm, make_rag(), data_dir=str(tmp_path))
        result = await node(make_state())
        assert result["tool_data"]["eventos"] == []
        mock_llm.generate_with_history.assert_called_once()

    async def test_rag_chunks_se_incluyen_en_prompt(self, tmp_path):
        (tmp_path / "calendar.json").write_text("[]")
        docs = [RagDocument(content="Manual de participación ciudadana")]
        mock_llm = make_llm()
        node = make_estratega_node(mock_llm, make_rag(docs), data_dir=str(tmp_path))
        await node(make_state())

        system_prompt = mock_llm.generate_with_history.call_args[0][0]
        assert "Manual de participación ciudadana" in system_prompt

    async def test_respuesta_guardada_en_response(self, tmp_path):
        (tmp_path / "calendar.json").write_text("[]")
        mock_llm = make_llm("Paso 1: Presenta tu queja.")
        node = make_estratega_node(mock_llm, make_rag(), data_dir=str(tmp_path))
        result = await node(make_state())
        assert result["response"] == "Paso 1: Presenta tu queja."
