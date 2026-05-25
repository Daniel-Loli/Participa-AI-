from __future__ import annotations

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_PROMPT_WITH_CONTEXT = """Eres un asistente legal ciudadano para jóvenes peruanos.
Usa solo la legislación peruana provista en el contexto.
No opines sobre política. Responde en lenguaje simple.
Cita el artículo específico cuando sea relevante.
Si no está en el contexto, dilo honestamente.

Contexto legal:
{context}"""

_PROMPT_NO_CONTEXT = """Eres un asistente legal ciudadano para jóvenes peruanos.
No opines sobre política. Responde en lenguaje simple.
Cita artículos específicos cuando sea relevante.
Si no conoces la respuesta, dilo honestamente."""


def make_legal_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def legal(state: AgentState) -> dict:
        docs = await rag_client.search(state["user_message"], RagCollection.LEGAL, top_k=5)

        if docs:
            context = "\n\n".join(doc.content for doc in docs)
            system_prompt = _PROMPT_WITH_CONTEXT.format(context=context)
        else:
            system_prompt = _PROMPT_NO_CONTEXT

        response = await llm_client.generate_with_history(system_prompt, state["conversation_history"])
        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
            "conversation_history": [AIMessage(content=response)],
        }

    return legal
