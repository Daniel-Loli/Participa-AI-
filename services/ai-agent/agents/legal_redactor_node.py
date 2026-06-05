from __future__ import annotations

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_PROMPT = """Eres el asesor legal y redactor de Participa AI ⚖️✍️

REGLA CRÍTICA: Solo puedes citar legislación del contexto proporcionado aquí abajo.
NO uses tu conocimiento general, NO inventes artículos, NO cites leyes fuera del contexto.

Responde haciendo DOS cosas en un solo mensaje:
1. Explica en 2-3 líneas la ley más relevante del contexto para su situación, citando el artículo exacto.
2. Pregunta si quiere que generes la carta o solicitud formal.

Legislación de nuestras fuentes:
{context}
{wa_rules}"""

_NO_CONTEXT_RESPONSE = (
    "No encontré legislación relacionada en mis fuentes actuales para preparar el documento.\n\n"
    "¿Puedes describirme más tu situación? Así busco mejor en mis fuentes. "
    "O si prefieres, puedo ayudarte con otro tema. ¿Qué necesitas?"
)


def make_legal_redactor_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def legal_redactor(state: AgentState) -> dict:
        docs = await rag_client.search(state["user_message"], RagCollection.LEGAL, top_k=5)

        if not docs:
            return {"response": _NO_CONTEXT_RESPONSE, "rag_context": []}

        context = "\n\n".join(doc.content for doc in docs)
        system_prompt = _PROMPT.format(context=context, wa_rules=WA_RULES)
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))

        # Marca el perfil para que el siguiente turno sepa que espera confirmación
        profile = dict(state.get("user_profile") or {})
        profile["awaiting_doc_confirmation"] = True

        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
            "user_profile": profile,
        }

    return legal_redactor
