import json
from unittest.mock import AsyncMock, MagicMock

from agents.oportunidades_node import make_oportunidades_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "¿qué eventos hay próximamente?",
        "intent": "oportunidades",
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Hay 3 oportunidades próximas.") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    return mock


def make_rag() -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    return mock


# Hoy es 2026-05-24 según el contexto del sistema
_EVENTOS = [
    {"fecha": "2026-04-01", "tipo": "pasado", "distrito": "Lima", "descripcion": "Evento pasado 1"},
    {"fecha": "2026-05-01", "tipo": "pasado", "distrito": "Lima", "descripcion": "Evento pasado 2"},
    {"fecha": "2026-06-01", "tipo": "sesion", "distrito": "Lima", "descripcion": "Sesión PP"},
    {"fecha": "2026-06-15", "tipo": "audiencia", "distrito": "Lima", "descripcion": "Audiencia pública"},
    {"fecha": "2026-07-01", "tipo": "taller", "distrito": "Lima", "descripcion": "Taller PP"},
    {"fecha": "2026-08-01", "tipo": "feria", "distrito": "Lima", "descripcion": "Feria juvenil"},
    {"fecha": "2026-09-01", "tipo": "congreso", "distrito": "Lima", "descripcion": "Congreso"},
]

_EVENTOS_CON_DISTRITO = [
    {"fecha": "2026-06-01", "tipo": "sesion", "distrito": "Miraflores", "descripcion": "Sesión PP Miraflores"},
    {"fecha": "2026-06-05", "tipo": "audiencia", "distrito": "San Isidro", "descripcion": "Audiencia SI"},
    {"fecha": "2026-06-10", "tipo": "taller", "distrito": "Miraflores", "descripcion": "Taller Miraflores"},
    {"fecha": "2026-07-01", "tipo": "feria", "distrito": "Lima", "descripcion": "Feria general"},
    {"fecha": "2026-08-01", "tipo": "congreso", "distrito": "Miraflores", "descripcion": "Congreso Miraflores"},
]


class TestOportunidadesNode:
    async def test_cinco_eventos_futuros_retorna_solo_tres_proximos(self, tmp_path):
        (tmp_path / "calendar.json").write_text(json.dumps(_EVENTOS))
        node = make_oportunidades_node(make_llm(), make_rag(), data_dir=str(tmp_path))
        result = await node(make_state())
        assert len(result["tool_data"]["oportunidades"]) == 3
        fechas = [e["fecha"] for e in result["tool_data"]["oportunidades"]]
        assert fechas == sorted(fechas)

    async def test_eventos_pasados_excluidos(self, tmp_path):
        (tmp_path / "calendar.json").write_text(json.dumps(_EVENTOS))
        node = make_oportunidades_node(make_llm(), make_rag(), data_dir=str(tmp_path))
        result = await node(make_state())
        for evento in result["tool_data"]["oportunidades"]:
            assert evento["fecha"] >= "2026-05-24"

    async def test_sin_distrito_retorna_todos_sin_filtrar(self, tmp_path):
        (tmp_path / "calendar.json").write_text(json.dumps(_EVENTOS_CON_DISTRITO))
        node = make_oportunidades_node(make_llm(), make_rag(), data_dir=str(tmp_path))
        result = await node(make_state(user_profile={}))
        # Sin filtro de distrito, retorna los 3 más próximos de todos
        assert len(result["tool_data"]["oportunidades"]) == 3

    async def test_con_distrito_filtra_primero(self, tmp_path):
        (tmp_path / "calendar.json").write_text(json.dumps(_EVENTOS_CON_DISTRITO))
        node = make_oportunidades_node(make_llm(), make_rag(), data_dir=str(tmp_path))
        result = await node(make_state(user_profile={"name": "Ana", "district": "Miraflores"}))
        # Hay 3 eventos de Miraflores: 2026-06-01, 2026-06-10, 2026-08-01
        assert len(result["tool_data"]["oportunidades"]) == 3
        assert all(
            e["distrito"] == "Miraflores"
            for e in result["tool_data"]["oportunidades"]
        )

    async def test_calendar_ausente_retorna_respuesta_sin_crash(self, tmp_path):
        node = make_oportunidades_node(make_llm(), make_rag(), data_dir=str(tmp_path))
        result = await node(make_state())
        assert result["tool_data"]["oportunidades"] == []
        assert isinstance(result["response"], str)
