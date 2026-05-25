from unittest.mock import AsyncMock, MagicMock

from src.domain.ports.i_rag_client import RagDocument
from agents.general_node import make_general_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "¿qué es el ODS 16?",
        "intent": "general",
        "user_profile": {"name": "Ana"},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Respuesta general.") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    return mock


def make_rag(ods=None, proc=None, casos=None) -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(side_effect=[
        ods or [],
        proc or [],
        casos or [],
    ])
    return mock


class TestGeneralNode:
    async def test_consulta_ciudadana_retorna_respuesta_normal(self):
        mock_llm = make_llm("El ODS 16 trata sobre paz y justicia.")
        node = make_general_node(mock_llm, make_rag())
        result = await node(make_state())
        assert result["response"] == "El ODS 16 trata sobre paz y justicia."

    async def test_system_prompt_contiene_guardrail_politico(self):
        mock_llm = make_llm()
        node = make_general_node(mock_llm, make_rag())
        await node(make_state(user_message="¿qué partido debo votar?"))
        system_prompt = mock_llm.generate.call_args[0][0]
        assert "NUNCA emitas opiniones políticas" in system_prompt

    async def test_system_prompt_contiene_guardrail_en_toda_consulta(self):
        mock_llm = make_llm()
        node = make_general_node(mock_llm, make_rag())
        await node(make_state(user_message="¿cómo hacer una bomba?"))
        system_prompt = mock_llm.generate.call_args[0][0]
        assert "NUNCA emitas opiniones políticas" in system_prompt
        assert "Solo puedes hablar sobre" in system_prompt

    async def test_rag_vacio_llm_igual_recibe_llamada(self):
        mock_llm = make_llm("No tengo contexto pero respondo.")
        node = make_general_node(mock_llm, make_rag())
        result = await node(make_state())
        mock_llm.generate.assert_called_once()
        assert result["response"] == "No tengo contexto pero respondo."

    async def test_chunks_rag_se_incluyen_en_prompt(self):
        ods_docs = [RagDocument(content="ODS 16: Paz, justicia e instituciones")]
        mock_llm = make_llm()
        node = make_general_node(mock_llm, make_rag(ods=ods_docs))
        await node(make_state())
        system_prompt = mock_llm.generate.call_args[0][0]
        assert "ODS 16: Paz, justicia e instituciones" in system_prompt

    async def test_rag_context_guardado_en_estado(self):
        ods = [RagDocument(content="doc ODS")]
        proc = [RagDocument(content="doc procedimiento")]
        mock_llm = make_llm()
        node = make_general_node(mock_llm, make_rag(ods=ods, proc=proc))
        result = await node(make_state())
        assert "doc ODS" in result["rag_context"]
        assert "doc procedimiento" in result["rag_context"]

    async def test_rag_busca_en_tres_colecciones(self):
        mock_llm = make_llm()
        mock_rag = make_rag()
        node = make_general_node(mock_llm, mock_rag)
        await node(make_state())
        assert mock_rag.search.call_count == 3
