import json
from datetime import date, timedelta
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
    mock.generate_with_history = AsyncMock(return_value=response)
    return mock


def make_rag() -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    return mock


# Fechas relativas a hoy para que los tests no caduquen con el tiempo
def _rel(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).isoformat()


_EVENTOS = [
    {"fecha": _rel(-60), "tipo": "pasado", "distrito": "Lima", "descripcion": "Evento pasado 1"},
    {"fecha": _rel(-20), "tipo": "pasado", "distrito": "Lima", "descripcion": "Evento pasado 2"},
    {"fecha": _rel(7), "tipo": "sesion", "distrito": "Lima", "descripcion": "Sesión PP"},
    {"fecha": _rel(20), "tipo": "audiencia", "distrito": "Lima", "descripcion": "Audiencia pública"},
    {"fecha": _rel(35), "tipo": "taller", "distrito": "Lima", "descripcion": "Taller PP"},
    {"fecha": _rel(60), "tipo": "feria", "distrito": "Lima", "descripcion": "Feria juvenil"},
    {"fecha": _rel(90), "tipo": "congreso", "distrito": "Lima", "descripcion": "Congreso"},
]

_EVENTOS_CON_DISTRITO = [
    {"fecha": _rel(7), "tipo": "sesion", "distrito": "Miraflores", "descripcion": "Sesión PP Miraflores"},
    {"fecha": _rel(10), "tipo": "audiencia", "distrito": "San Isidro", "descripcion": "Audiencia SI"},
    {"fecha": _rel(15), "tipo": "taller", "distrito": "Miraflores", "descripcion": "Taller Miraflores"},
    {"fecha": _rel(30), "tipo": "feria", "distrito": "Lima", "descripcion": "Feria general"},
    {"fecha": _rel(50), "tipo": "congreso", "distrito": "Miraflores", "descripcion": "Congreso Miraflores"},
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
            assert evento["fecha"] >= date.today().isoformat()

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
