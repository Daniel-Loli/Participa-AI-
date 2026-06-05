from __future__ import annotations

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_PROMPT_WITH_CONTEXT = """Eres el asesor legal y redactor de Participa AI ⚖️✍️
El usuario quiere entender la ley aplicable a su caso Y que le ayudes con un documento formal.

Responde haciendo DOS cosas en un solo mensaje:
1. Explica en 2-3 líneas la ley más relevante para su situación, citando el artículo exacto.
2. Termina preguntando si quieres que generes la carta o solicitud formal.

Legislación relevante:
{context}
{wa_rules}"""

_PROMPT_NO_CONTEXT = """Eres el asesor legal y redactor de Participa AI ⚖️✍️
El usuario quiere entender la ley aplicable a su caso Y que le ayudes con un documento formal.

Responde haciendo DOS cosas en un solo mensaje:
1. Explica brevemente la normativa más relevante para su situación.
2. Termina preguntando si quieres que generes la carta o solicitud formal.
{wa_rules}"""


def make_legal_redactor_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def legal_redactor(state: AgentState) -> dict:
        docs = await rag_client.search(state["user_message"], RagCollection.LEGAL, top_k=5)

        if docs:
            context = "\n\n".join(doc.content for doc in docs)
            system_prompt = _PROMPT_WITH_CONTEXT.format(context=context, wa_rules=WA_RULES)
        else:
            system_prompt = _PROMPT_NO_CONTEXT.format(wa_rules=WA_RULES)

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
