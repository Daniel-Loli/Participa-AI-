from __future__ import annotations

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_PROMPT = """Eres el asesor legal de Participa AI para jóvenes peruanos ⚖️

REGLA CRÍTICA: Solo puedes usar la legislación del contexto proporcionado aquí abajo.
NO uses tu conocimiento general, NO inventes artículos, NO cites leyes que no estén en el contexto.
Si el contexto no contiene la respuesta, dilo explícitamente.

Explica en lenguaje simple. SIEMPRE indica de qué ley sale cada derecho o afirmación,
con el artículo si el contexto lo muestra (ej: *Ley N.° 26300, art. 2*) — una lista de
derechos sin su fuente legal no le sirve al usuario para reclamarlos.
Nunca opines sobre política.

Legislación de nuestras fuentes:
{context}
{wa_rules}"""

_NO_CONTEXT_RESPONSE = (
    "No encontré información sobre ese tema en mis fuentes legales actuales.\n\n"
    "Intenta preguntar con otras palabras, o consulta directamente en:\n"
    "- *MINJUSDH* — Ministerio de Justicia: minjus.gob.pe\n"
    "- *Defensoría del Pueblo*: defensoria.gob.pe\n\n"
    "¿Quieres que te ayude con otro tema legal?"
)


def make_legal_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def legal(state: AgentState) -> dict:
        docs = await rag_client.search(state["user_message"], RagCollection.LEGAL, top_k=5)

        if not docs:
            return {"response": _NO_CONTEXT_RESPONSE, "rag_context": [], "skip_tone": True}

        context = "\n\n".join(doc.content for doc in docs)
        system_prompt = _PROMPT.format(context=context, wa_rules=WA_RULES)
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
        }

    return legal
