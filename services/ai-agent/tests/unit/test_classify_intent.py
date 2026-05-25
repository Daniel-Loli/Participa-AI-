from unittest.mock import AsyncMock, MagicMock

from agents.classify_intent import make_classify_intent_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "hola",
        "intent": None,
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "general") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    return mock


class TestClassifyIntentNode:
    async def test_perfil_vacio_retorna_onboarding_sin_llamar_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={}))
        assert result["intent"] == "onboarding"
        mock_llm.generate.assert_not_called()

    async def test_perfil_sin_nombre_retorna_onboarding_sin_llamar_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"district": "Lima"}))
        assert result["intent"] == "onboarding"
        mock_llm.generate.assert_not_called()

    async def test_llm_responde_legal_retorna_legal(self):
        mock_llm = make_llm("legal")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="¿qué leyes me protegen?",
            user_profile={"name": "Ana"},
        ))
        assert result["intent"] == "legal"

    async def test_llm_responde_texto_invalido_fallback_general(self):
        mock_llm = make_llm("no sé")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"name": "Ana"}))
        assert result["intent"] == "general"

    async def test_llm_responde_con_mayusculas_y_espacios_se_normaliza(self):
        mock_llm = make_llm("  LEGAL  ")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"name": "Ana"}))
        assert result["intent"] == "legal"

    async def test_llm_responde_redactor_retorna_redactor(self):
        mock_llm = make_llm("redactor")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="ayúdame a redactar una carta",
            user_profile={"name": "Luis"},
        ))
        assert result["intent"] == "redactor"

    async def test_excepcion_en_llm_fallback_general(self):
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"name": "Ana"}))
        assert result["intent"] == "general"
