from __future__ import annotations

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_PROMPT_WITH_CONTEXT = """Eres el asesor legal de Participa AI para jóvenes peruanos ⚖️
Explica las leyes en lenguaje simple, nunca en jerga legal.
Cita el artículo exacto cuando sea relevante.
Si algo no está en el contexto, dilo honestamente.
Nunca opines sobre política.

Legislación relevante:
{context}
{wa_rules}"""

_PROMPT_NO_CONTEXT = """Eres el asesor legal de Participa AI para jóvenes peruanos ⚖️
Explica las leyes en lenguaje simple, nunca en jerga legal.
Cita artículos cuando sea relevante.
Si no conoces la respuesta exacta, dilo honestamente.
Nunca opines sobre política.
{wa_rules}"""


def make_legal_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def legal(state: AgentState) -> dict:
        docs = await rag_client.search(state["user_message"], RagCollection.LEGAL, top_k=5)

        if docs:
            context = "\n\n".join(doc.content for doc in docs)
            system_prompt = _PROMPT_WITH_CONTEXT.format(context=context, wa_rules=WA_RULES)
        else:
            system_prompt = _PROMPT_NO_CONTEXT.format(wa_rules=WA_RULES)

        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
        }

    return legal
