from __future__ import annotations

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_SYSTEM_PROMPT = """Eres Participa AI, guía de participación ciudadana para jóvenes peruanos 🇵🇪
Solo hablas de: leyes peruanas, participación ciudadana, ODS, organizaciones juveniles, presupuesto participativo.
Nunca opines sobre política, candidatos o partidos.
Si la pregunta está fuera de tu ámbito responde: "Eso está fuera de lo que puedo ayudarte. ¿Te oriento sobre participación ciudadana o leyes?"

{context}
{wa_rules}"""


def make_general_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def general(state: AgentState) -> dict:
        ods_docs, proc_docs, casos_docs = await _fetch_rag(rag_client, state["user_message"])
        all_docs = ods_docs + proc_docs + casos_docs

        context = ""
        if all_docs:
            context = "Contexto:\n" + "\n\n".join(doc.content for doc in all_docs)

        system_prompt = _SYSTEM_PROMPT.format(context=context, wa_rules=WA_RULES)
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "rag_context": [doc.content for doc in all_docs],
        }

    return general


async def _fetch_rag(rag_client: IRagClient, query: str):
    ods = await rag_client.search(query, RagCollection.ODS, top_k=3)
    proc = await rag_client.search(query, RagCollection.PROCEDIMIENTOS, top_k=3)
    casos = await rag_client.search(query, RagCollection.CASOS_EXITO, top_k=2)
    return ods, proc, casos
