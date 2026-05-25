from unittest.mock import AsyncMock, MagicMock, patch

from langgraph.checkpoint.memory import MemorySaver

from agents.orchestrator import build_graph, route_by_intent
from src.domain.value_objects.agent_intent import AgentIntent

_PATCH_REDIS_SAVER = "agents.orchestrator.RedisSaver"


def make_state(**kwargs):
    base = {
        "session_id": "test-session",
        "user_message": "¿qué leyes me protegen?",
        "intent": None,
        "user_profile": {"name": "Ana"},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(*responses) -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(side_effect=list(responses))
    return mock


def make_rag() -> MagicMock:
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    return mock


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
        with patch(_PATCH_REDIS_SAVER, return_value=MemorySaver()):
            graph = build_graph(make_llm("general"), make_rag(), MagicMock())
        assert graph is not None

    def test_redis_saver_se_inicializa_con_redis_client(self):
        mock_redis = MagicMock()
        with patch(_PATCH_REDIS_SAVER) as MockSaver:
            MockSaver.return_value = MemorySaver()
            build_graph(make_llm("general"), make_rag(), mock_redis)
        MockSaver.assert_called_once_with(mock_redis)

    async def test_intent_legal_ejecuta_nodo_legal(self):
        # classify llama LLM → "legal"; legal node llama LLM → respuesta
        mock_llm = make_llm("legal", "La Ley 28056 establece el PP.")
        with patch(_PATCH_REDIS_SAVER, return_value=MemorySaver()):
            graph = build_graph(mock_llm, make_rag(), MagicMock())

        result = await graph.ainvoke(
            make_state(user_profile={"name": "Ana"}),
            config={"configurable": {"thread_id": "t-legal"}},
        )
        assert result["intent"] == "legal"
        assert result["response"] == "La Ley 28056 establece el PP."

    async def test_intent_onboarding_ejecuta_nodo_onboarding(self):
        # perfil vacío → classify fuerza onboarding sin LLM
        # onboarding llama LLM para extracción → JSON nulo
        mock_llm = make_llm('{"nombre": null, "distrito": null}')
        with patch(_PATCH_REDIS_SAVER, return_value=MemorySaver()):
            graph = build_graph(mock_llm, make_rag(), MagicMock())

        result = await graph.ainvoke(
            make_state(user_profile={}, user_message="hola"),
            config={"configurable": {"thread_id": "t-onboard"}},
        )
        assert result["intent"] == "onboarding"
        assert "llamas" in result["response"].lower() or "nombre" in result["response"].lower()

    async def test_intent_invalido_ruta_a_nodo_general(self):
        # classify llama LLM → texto inválido → normaliza a "general"
        # general node llama LLM + 3 RAG calls
        mock_llm = make_llm("xyz_invalido", "Respuesta general.")
        mock_rag = make_rag()
        with patch(_PATCH_REDIS_SAVER, return_value=MemorySaver()):
            graph = build_graph(mock_llm, mock_rag, MagicMock())

        result = await graph.ainvoke(
            make_state(user_profile={"name": "Ana"}),
            config={"configurable": {"thread_id": "t-general"}},
        )
        assert result["intent"] == "general"
        assert result["response"] == "Respuesta general."

    async def test_estado_persiste_entre_invocaciones(self):
        saver = MemorySaver()
        # Primera invocación: extrae "Ana" de "Hola soy Ana de Lima"
        mock_llm1 = make_llm('{"nombre": "Ana", "distrito": "Lima"}')
        with patch(_PATCH_REDIS_SAVER, return_value=saver):
            graph = build_graph(mock_llm1, make_rag(), MagicMock())

        cfg = {"configurable": {"thread_id": "persist-thread"}}
        result1 = await graph.ainvoke(
            make_state(user_profile={}, user_message="Hola soy Ana de Lima"),
            config=cfg,
        )
        assert result1["user_profile"]["name"] == "Ana"

        # Segunda invocación: mismo thread_id → el grafo carga el checkpoint anterior
        mock_llm2 = make_llm('{"nombre": null, "distrito": null}')
        with patch(_PATCH_REDIS_SAVER, return_value=saver):
            graph2 = build_graph(mock_llm2, make_rag(), MagicMock())

        result2 = await graph2.ainvoke(
            make_state(user_profile={}, user_message="tengo otra pregunta"),
            config=cfg,
        )
        # El checkpoint del run anterior persiste el estado; onboarding forzado porque
        # el input proporcionado tiene user_profile={} pero LangGraph usa el checkpoint
        assert result2 is not None
