from __future__ import annotations

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_GUARDRAIL_PROMPT = """Eres Participa AI, asistente de participación ciudadana para jóvenes peruanos.
Solo puedes hablar sobre: leyes peruanas, participación ciudadana, ODS, organizaciones juveniles, presupuesto participativo.
NUNCA emitas opiniones políticas ni sobre candidatos o partidos.
Si la consulta está fuera de tu ámbito responde exactamente:
"Eso está fuera de lo que puedo ayudarte. ¿Te puedo orientar sobre participación ciudadana, leyes o cómo conectarte con organizaciones juveniles?"
Responde en lenguaje simple, accesible para jóvenes de 15-29 años.

{context}"""


def make_general_node(llm_client: ILlmClient, rag_client: IRagClient):
    async def general(state: AgentState) -> dict:
        ods_docs, proc_docs, casos_docs = await _fetch_rag(rag_client, state["user_message"])
        all_docs = ods_docs + proc_docs + casos_docs

        context = ""
        if all_docs:
            context = "Contexto relevante:\n" + "\n\n".join(doc.content for doc in all_docs)

        system_prompt = _GUARDRAIL_PROMPT.format(context=context)
        response = await llm_client.generate_with_history(system_prompt, state["conversation_history"])
        return {
            "response": response,
            "rag_context": [doc.content for doc in all_docs],
            "conversation_history": [AIMessage(content=response)],
        }

    return general


async def _fetch_rag(rag_client: IRagClient, query: str):
    ods = await rag_client.search(query, RagCollection.ODS, top_k=3)
    proc = await rag_client.search(query, RagCollection.PROCEDIMIENTOS, top_k=3)
    casos = await rag_client.search(query, RagCollection.CASOS_EXITO, top_k=2)
    return ods, proc, casos
