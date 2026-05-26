from __future__ import annotations

import logging

from langgraph.checkpoint.redis import AsyncRedisSaver

from agents.orchestrator import build_graph
from config import Config
from src.adapters.outbound.openai_llm_adapter import OpenAILlmAdapter
from src.adapters.outbound.openai_stt_adapter import OpenAISttAdapter
from src.adapters.outbound.openai_tts_adapter import OpenAITtsAdapter
from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
from src.application.use_cases.process_message import ProcessMessageUseCase

logger = logging.getLogger(__name__)

_use_case: ProcessMessageUseCase | None = None
_checkpointer: AsyncRedisSaver | None = None


def _build_redis_url(config: Config) -> str:
    """Construye la URL de Redis incluyendo usuario y contraseña correctamente."""
    from urllib.parse import urlparse, urlunparse
    password = config.redis_password
    if not password:
        return config.redis_url
    parsed = urlparse(config.redis_url)
    username = parsed.username or "default"
    netloc = f"{username}:{password}@{parsed.hostname}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))



async def init_dependencies(config: Config) -> None:
    global _use_case, _checkpointer

    llm_nano = OpenAILlmAdapter(api_key=config.openai_api_key, model=config.openai_model_nano)
    llm_mini = OpenAILlmAdapter(api_key=config.openai_api_key, model=config.openai_model_mini)
    llm_full = OpenAILlmAdapter(api_key=config.openai_api_key, model=config.openai_model_full)

    stt = OpenAISttAdapter(
        api_key=config.openai_api_key,
        model=config.openai_whisper_model,
    )
    tts = OpenAITtsAdapter(
        api_key=config.openai_api_key,
        model=config.openai_tts_model,
        voice=config.openai_tts_voice,
    )
    rag = QdrantRagAdapter(
        qdrant_url=config.qdrant_url,
        qdrant_api_key=config.qdrant_api_key,
        openai_api_key=config.openai_api_key,
        embedding_model=config.openai_embedding_model,
    )

    session_store = RedisSessionAdapter(
        redis_url=config.redis_url,
        redis_password=config.redis_password,
    )

    redis_url = _build_redis_url(config)
    _checkpointer = AsyncRedisSaver(redis_url=redis_url)
    await _checkpointer.asetup()

    graph = build_graph(llm_nano, llm_mini, llm_full, rag, _checkpointer)

    _use_case = ProcessMessageUseCase(stt, tts, session_store, graph)
    logger.info("Dependencias inicializadas correctamente")


async def cleanup_dependencies() -> None:
    global _checkpointer
    if _checkpointer is not None:
        try:
            await _checkpointer.aclose()
        except Exception:
            pass
        logger.info("Checkpointer Redis cerrado")


def get_process_message_use_case() -> ProcessMessageUseCase:
    if _use_case is None:
        raise RuntimeError("Dependencias no inicializadas. Llama a init_dependencies() primero.")
    return _use_case
