from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI — críticas
    openai_api_key: str

    # OpenAI — modelos LLM por tier de tarea
    openai_model_nano: str = "gpt-4.1-nano"    # classify_intent, onboarding (velocidad)
    openai_model_mini: str = "gpt-4.1-mini"    # legal, estratega, red, oportunidades, general
    openai_model_full: str = "gpt-4.1"         # redactor (documentos formales, mayor calidad)

    # Mantener por compatibilidad con código existente fuera del grafo
    openai_model: str = "gpt-4.1-mini"

    openai_embedding_model: str = "text-embedding-3-small"
    openai_whisper_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "nova"             # voz femenina cálida y amigable

    # Qdrant Cloud — críticas
    qdrant_url: str
    qdrant_api_key: str

    # Qdrant — opcionales con defaults
    qdrant_collection_legal: str = "legal"
    qdrant_collection_ods: str = "ods"
    qdrant_collection_procedimientos: str = "procedimientos"
    qdrant_collection_casos: str = "casos_exito"

    # Redis Cloud — crítica
    redis_url: str

    # Redis — opcional
    redis_password: str = ""

    # LangSmith — opcionales
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "participa-ai"

    # Servicio
    port: int = 8000
    data_dir: str = "../../data"


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Retorna la instancia singleton de Config. Falla al arranque si faltan vars críticas."""
    return Config()
