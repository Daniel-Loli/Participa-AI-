from unittest.mock import AsyncMock, MagicMock

from src.domain.ports.i_rag_client import RagDocument
from agents.legal_node import make_legal_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "¿qué es la Ley 28056?",
        "intent": "legal",
        "user_profile": {"name": "Ana"},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Respuesta legal") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    return mock


def make_rag(docs: list[RagDocument] | None = None) -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=docs or [])
    return mock


class TestLegalNode:
    async def test_rag_retorna_chunks_se_incluyen_en_prompt(self):
        docs = [
            RagDocument(content="Art. 1 Ley 28056: El PP es..."),
            RagDocument(content="Art. 2 Ley 28056: Los ciudadanos..."),
        ]
        mock_llm = make_llm("La Ley 28056 establece...")
        mock_rag = make_rag(docs)
        node = make_legal_node(mock_llm, mock_rag)
        result = await node(make_state())

        system_prompt = mock_llm.generate.call_args[0][0]
        assert "Art. 1 Ley 28056" in system_prompt
        assert "Art. 2 Ley 28056" in system_prompt

    async def test_rag_retorna_vacio_llm_igual_recibe_mensaje(self):
        mock_llm = make_llm("No tengo información específica.")
        mock_rag = make_rag([])
        node = make_legal_node(mock_llm, mock_rag)
        result = await node(make_state())

        mock_llm.generate.assert_called_once()
        assert result["response"] == "No tengo información específica."

    async def test_respuesta_llm_se_guarda_en_response(self):
        mock_llm = make_llm("Respuesta legal detallada")
        mock_rag = make_rag([])
        node = make_legal_node(mock_llm, mock_rag)
        result = await node(make_state())
        assert result["response"] == "Respuesta legal detallada"

    async def test_chunks_rag_se_guardan_en_rag_context(self):
        docs = [RagDocument(content="chunk 1"), RagDocument(content="chunk 2")]
        mock_llm = make_llm()
        mock_rag = make_rag(docs)
        node = make_legal_node(mock_llm, mock_rag)
        result = await node(make_state())
        assert result["rag_context"] == ["chunk 1", "chunk 2"]

    async def test_rag_vacio_no_incluye_contexto_en_prompt(self):
        mock_llm = make_llm()
        mock_rag = make_rag([])
        node = make_legal_node(mock_llm, mock_rag)
        await node(make_state())

        system_prompt = mock_llm.generate.call_args[0][0]
        assert "Contexto legal:" not in system_prompt
