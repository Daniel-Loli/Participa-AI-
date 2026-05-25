from unittest.mock import AsyncMock, MagicMock

from agents.onboarding_node import make_onboarding_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "hola",
        "intent": "onboarding",
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(extraction_json: str = '{"nombre": null, "distrito": null}') -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=extraction_json)
    return mock


class TestOnboardingNode:
    async def test_sin_nombre_respuesta_pide_nombre(self):
        mock_llm = make_llm('{"nombre": null, "distrito": null}')
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(user_profile={}))
        assert "name" not in result["user_profile"] or not result["user_profile"].get("name")
        assert "llamas" in result["response"].lower() or "nombre" in result["response"].lower()

    async def test_con_nombre_sin_distrito_respuesta_pide_distrito(self):
        mock_llm = make_llm('{"nombre": null, "distrito": null}')
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(
            user_message="soy de Lima",
            user_profile={"name": "Ana"},
        ))
        assert result["user_profile"].get("name") == "Ana"
        assert not result["user_profile"].get("district")
        assert "distrito" in result["response"].lower()

    async def test_con_nombre_y_distrito_pone_stage_active(self):
        mock_llm = make_llm()
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(
            user_message="el tráfico es terrible",
            user_profile={"name": "Ana", "district": "Miraflores"},
        ))
        assert result["user_profile"]["conversation_stage"] == "ACTIVE"
        mock_llm.generate.assert_not_called()

    async def test_extrae_nombre_y_distrito_del_mensaje(self):
        mock_llm = make_llm('{"nombre": "Ana", "distrito": "San Isidro"}')
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(
            user_message="Hola soy Ana de San Isidro",
            user_profile={},
        ))
        assert result["user_profile"]["name"] == "Ana"
        assert result["user_profile"]["district"] == "San Isidro"

    async def test_extrae_solo_nombre_sin_distrito(self):
        mock_llm = make_llm('{"nombre": "Carlos", "distrito": null}')
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(
            user_message="Me llamo Carlos",
            user_profile={},
        ))
        assert result["user_profile"]["name"] == "Carlos"
        assert not result["user_profile"].get("district")

    async def test_json_invalido_del_llm_no_falla(self):
        mock_llm = make_llm("texto sin json")
        node = make_onboarding_node(mock_llm)
        result = await node(make_state(user_profile={}))
        assert "response" in result
        assert isinstance(result["response"], str)
