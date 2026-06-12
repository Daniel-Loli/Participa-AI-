from unittest.mock import AsyncMock, MagicMock

from langgraph.checkpoint.memory import MemorySaver

from agents.orchestrator import build_graph, route_by_intent
from src.domain.value_objects.agent_intent import AgentIntent


def make_state(**kwargs):
    base = {
        "session_id": "test-session",
        "user_message": "¿qué leyes me protegen?",
        "intent": None,
        "user_profile": {"name": "Ana", "district": "Lima", "conversation_stage": "ACTIVE"},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(*responses) -> MagicMock:
    """LLM mock: cada llamada (generate o generate_with_history) consume una respuesta."""
    mock = MagicMock()
    queue = list(responses)

    async def _next(*args, **kwargs):
        return queue.pop(0) if queue else "respuesta"

    mock.generate = AsyncMock(side_effect=_next)
    mock.generate_with_history = AsyncMock(side_effect=_next)
    return mock


def make_rag(docs=None) -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=docs or [])
    return mock


def build(nano=None, mini=None, full=None, rag=None, saver=None):
    return build_graph(
        nano or make_llm(),
        mini or make_llm(),
        full or make_llm(),
        rag or make_rag(),
        saver or MemorySaver(),
    )


class TestRouteByIntent:
    def test_intent_legal_retorna_legal(self):
        assert route_by_intent(make_state(intent="legal")) == "legal"

    def test_intent_onboarding_retorna_onboarding(self):
        assert route_by_intent(make_state(intent="onboarding")) == "onboarding"

    def test_intent_invalido_retorna_general(self):
        assert route_by_intent(make_state(intent="xyz_invalido")) == "general"

    def test_intent_none_retorna_general(self):
        assert route_by_intent(make_state(intent=None)) == "general"

    def test_todos_los_intents_validos_son_enrutados(self):
        for intent in AgentIntent:
            result = route_by_intent(make_state(intent=intent.value))
            assert result == intent.value


class TestBuildGraph:
    def test_build_graph_compila_sin_errores(self):
        graph = build()
        assert graph is not None

    async def test_intent_legal_ejecuta_nodo_legal(self):
        from src.domain.ports.i_rag_client import RagDocument

        # nano: classify → "legal"
        nano = make_llm("legal")
        # mini: legal node → respuesta; tone_review → misma respuesta revisada
        mini = make_llm("La Ley 28056 establece el PP.", "La Ley 28056 establece el PP.")
        rag = make_rag([RagDocument(content="Art. 1 Ley 28056")])
        graph = build(nano=nano, mini=mini, rag=rag)

        result = await graph.ainvoke(
            make_state(),
            config={"configurable": {"thread_id": "t-legal"}},
        )
        assert result["intent"] == "legal"
        assert result["response"] == "La Ley 28056 establece el PP."

    async def test_intent_onboarding_ejecuta_nodo_onboarding(self):
        # perfil vacío → classify fuerza onboarding sin LLM
        # onboarding llama LLM (nano) para extracción → JSON nulo
        nano = make_llm('{"nombre": null, "distrito": null}')
        graph = build(nano=nano)

        result = await graph.ainvoke(
            make_state(user_profile={}, user_message="hola"),
            config={"configurable": {"thread_id": "t-onboard"}},
        )
        assert result["intent"] == "onboarding"
        assert "llamas" in result["response"].lower() or "nombre" in result["response"].lower()

    async def test_intent_invalido_ruta_a_nodo_general(self):
        # classify → texto inválido → normaliza a "general"
        # general sin contexto RAG → respuesta honesta sin llamar al LLM
        nano = make_llm("xyz_invalido")
        graph = build(nano=nano)

        result = await graph.ainvoke(
            make_state(user_message="cuéntame algo raro"),
            config={"configurable": {"thread_id": "t-general"}},
        )
        assert result["intent"] == "general"
        assert "No tengo información" in result["response"]

    async def test_estado_persiste_entre_invocaciones(self):
        saver = MemorySaver()
        # Primera invocación: extrae "Ana" y "Lima" de un solo mensaje
        nano1 = make_llm('{"nombre": "Ana", "distrito": "Lima"}')
        graph = build(nano=nano1, saver=saver)

        cfg = {"configurable": {"thread_id": "persist-thread"}}
        result1 = await graph.ainvoke(
            make_state(user_profile={}, user_message="Hola soy Ana de Lima"),
            config=cfg,
        )
        assert result1["user_profile"]["name"] == "Ana"
        assert result1["user_profile"]["district"] == "Lima"

        # Segunda invocación: mismo thread_id → el grafo carga el checkpoint anterior
        nano2 = make_llm('{"nombre": null, "distrito": null}')
        graph2 = build(nano=nano2, saver=saver)
        result2 = await graph2.ainvoke(
            make_state(user_profile={}, user_message="tengo otra pregunta"),
            config=cfg,
        )
        assert result2 is not None

    async def test_menu_responde_sin_llm(self):
        # Saludo con perfil completo → menú directo, sin clasificación LLM
        nano = make_llm()
        mini = make_llm()
        graph = build(nano=nano, mini=mini)

        result = await graph.ainvoke(
            make_state(user_message="hola"),
            config={"configurable": {"thread_id": "t-menu"}},
        )
        assert result["intent"] == "menu"
        assert "1." in result["response"]
        nano.generate_with_history.assert_not_called()
        # El menú es plantilla — tone_review no debe llamar al LLM
        mini.generate.assert_not_called()
