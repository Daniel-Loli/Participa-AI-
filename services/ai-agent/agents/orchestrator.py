from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.classify_intent import make_classify_intent_node
from agents.estratega_node import make_estratega_node
from agents.general_node import make_general_node
from agents.legal_node import make_legal_node
from agents.onboarding_node import make_onboarding_node
from agents.oportunidades_node import make_oportunidades_node
from agents.red_node import make_red_node
from agents.redactor_node import make_redactor_node
from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.agent_intent import AgentIntent

_VALID_INTENTS = {i.value for i in AgentIntent}


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent") or ""
    return intent if intent in _VALID_INTENTS else AgentIntent.GENERAL.value


def build_graph(llm_client: ILlmClient, rag_client: IRagClient, checkpointer):
    """Construye el grafo LangGraph. checkpointer ya debe estar inicializado (setup)."""
    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", make_classify_intent_node(llm_client))
    builder.add_node("onboarding", make_onboarding_node(llm_client))
    builder.add_node("legal", make_legal_node(llm_client, rag_client))
    builder.add_node("estratega", make_estratega_node(llm_client, rag_client))
    builder.add_node("oportunidades", make_oportunidades_node(llm_client, rag_client))
    builder.add_node("red", make_red_node(llm_client, rag_client))
    builder.add_node("redactor", make_redactor_node(llm_client))
    builder.add_node("general", make_general_node(llm_client, rag_client))

    builder.set_entry_point("classify_intent")

    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "onboarding": "onboarding",
            "legal": "legal",
            "estratega": "estratega",
            "oportunidades": "oportunidades",
            "red": "red",
            "redactor": "redactor",
            "general": "general",
        },
    )

    for node_name in ["onboarding", "legal", "estratega", "oportunidades", "red", "redactor", "general"]:
        builder.add_edge(node_name, END)

    return builder.compile(checkpointer=checkpointer)
