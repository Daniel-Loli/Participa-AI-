from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages

from agents.state import AgentState


class TestAgentState:
    def test_estado_minimo_valido(self):
        state: AgentState = {
            "session_id": "abc123",
            "user_message": "quiero participar",
            "intent": None,
            "user_profile": {},
            "rag_context": [],
            "tool_data": {},
            "response": "",
            "conversation_history": [],
        }
        assert state["session_id"] == "abc123"
        assert state["intent"] is None
        assert state["conversation_history"] == []

    def test_intent_puede_ser_string(self):
        state: AgentState = {
            "session_id": "abc",
            "user_message": "hola",
            "intent": "legal",
            "user_profile": {"name": "Ana", "district": "Miraflores"},
            "rag_context": ["Art. 1 de la Ley 28056..."],
            "tool_data": {"eventos": []},
            "response": "El PP es...",
            "conversation_history": [],
        }
        assert state["intent"] == "legal"
        assert state["user_profile"]["name"] == "Ana"

    def test_rag_context_lista_de_strings(self):
        state: AgentState = {
            "session_id": "abc",
            "user_message": "hola",
            "intent": "legal",
            "user_profile": {},
            "rag_context": ["chunk 1", "chunk 2", "chunk 3"],
            "tool_data": {},
            "response": "",
            "conversation_history": [],
        }
        assert len(state["rag_context"]) == 3
        assert all(isinstance(c, str) for c in state["rag_context"])


class TestAddMessages:
    def test_add_messages_acumula_mensajes(self):
        historial_actual = [HumanMessage(content="hola")]
        nuevos = [AIMessage(content="hola, soy Participa AI")]
        resultado = add_messages(historial_actual, nuevos)
        assert len(resultado) == 2
        assert resultado[0].content == "hola"
        assert resultado[1].content == "hola, soy Participa AI"

    def test_add_messages_sobre_lista_vacia(self):
        resultado = add_messages([], [HumanMessage(content="primer mensaje")])
        assert len(resultado) == 1
        assert resultado[0].content == "primer mensaje"

    def test_add_messages_multiples_turnos(self):
        h = []
        h = add_messages(h, [HumanMessage(content="turno 1")])
        h = add_messages(h, [AIMessage(content="respuesta 1")])
        h = add_messages(h, [HumanMessage(content="turno 2")])
        assert len(h) == 3
        assert h[2].content == "turno 2"

    def test_add_messages_en_estado(self):
        state: AgentState = {
            "session_id": "abc",
            "user_message": "hola",
            "intent": None,
            "user_profile": {},
            "rag_context": [],
            "tool_data": {},
            "response": "",
            "conversation_history": [HumanMessage(content="hola")],
        }
        # Simular actualización como lo haría LangGraph
        state["conversation_history"] = add_messages(
            state["conversation_history"],
            [AIMessage(content="respuesta del agente")],
        )
        assert len(state["conversation_history"]) == 2
