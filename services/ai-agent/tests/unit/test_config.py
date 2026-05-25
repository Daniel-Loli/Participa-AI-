import pytest
from pydantic import ValidationError

from config import Config


# Variables mínimas requeridas para que Config instancie correctamente
REQUIRED = {
    "OPENAI_API_KEY": "sk-test-key",
    "QDRANT_URL": "https://test.qdrant.io",
    "QDRANT_API_KEY": "qdrant-test-key",
    "REDIS_URL": "redis://localhost:6379",
}


def set_required(monkeypatch, overrides: dict | None = None):
    """Aplica las vars críticas y opcionalmente las sobreescribe."""
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)
    if overrides:
        for k, v in overrides.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)


class TestConfigValid:
    def test_instancia_con_vars_criticas(self, monkeypatch):
        set_required(monkeypatch)
        cfg = Config(_env_file=None)
        assert cfg.openai_api_key == "sk-test-key"
        assert cfg.qdrant_url == "https://test.qdrant.io"
        assert cfg.qdrant_api_key == "qdrant-test-key"
        assert cfg.redis_url == "redis://localhost:6379"

    def test_defaults_cuando_vars_opcionales_ausentes(self, monkeypatch):
        set_required(monkeypatch)
        cfg = Config(_env_file=None)
        assert cfg.openai_model == "gpt-4o-mini"
        assert cfg.openai_embedding_model == "text-embedding-3-small"
        assert cfg.openai_whisper_model == "whisper-1"
        assert cfg.openai_tts_model == "tts-1"
        assert cfg.openai_tts_voice == "alloy"
        assert cfg.qdrant_collection_legal == "legal"
        assert cfg.qdrant_collection_ods == "ods"
        assert cfg.qdrant_collection_procedimientos == "procedimientos"
        assert cfg.qdrant_collection_casos == "casos_exito"
        assert cfg.redis_password == ""
        assert cfg.langchain_tracing_v2 is False
        assert cfg.langchain_project == "participa-ai"
        assert cfg.port == 8000
        assert cfg.data_dir == "../../data"

    def test_vars_opcionales_sobreescritas(self, monkeypatch):
        set_required(monkeypatch, {
            "OPENAI_MODEL": "gpt-4o",
            "PORT": "9000",
            "LANGCHAIN_TRACING_V2": "true",
        })
        cfg = Config(_env_file=None)
        assert cfg.openai_model == "gpt-4o"
        assert cfg.port == 9000
        assert cfg.langchain_tracing_v2 is True


class TestConfigMissingCritical:
    def test_falla_sin_openai_api_key(self, monkeypatch):
        set_required(monkeypatch, {"OPENAI_API_KEY": None})
        with pytest.raises(ValidationError) as exc_info:
            Config(_env_file=None)
        assert "openai_api_key" in str(exc_info.value).lower()

    def test_falla_sin_qdrant_url(self, monkeypatch):
        set_required(monkeypatch, {"QDRANT_URL": None})
        with pytest.raises(ValidationError) as exc_info:
            Config(_env_file=None)
        assert "qdrant_url" in str(exc_info.value).lower()

    def test_falla_sin_qdrant_api_key(self, monkeypatch):
        set_required(monkeypatch, {"QDRANT_API_KEY": None})
        with pytest.raises(ValidationError) as exc_info:
            Config(_env_file=None)
        assert "qdrant_api_key" in str(exc_info.value).lower()

    def test_falla_sin_redis_url(self, monkeypatch):
        set_required(monkeypatch, {"REDIS_URL": None})
        with pytest.raises(ValidationError) as exc_info:
            Config(_env_file=None)
        assert "redis_url" in str(exc_info.value).lower()

    def test_falla_sin_ninguna_var_critica(self, monkeypatch):
        for k in REQUIRED:
            monkeypatch.delenv(k, raising=False)
        with pytest.raises(ValidationError):
            Config(_env_file=None)


class TestGetConfig:
    def test_get_config_retorna_instancia(self, monkeypatch):
        set_required(monkeypatch)
        # Limpiar cache del lru_cache para este test
        from config import get_config
        get_config.cache_clear()
        cfg = get_config()
        assert isinstance(cfg, Config)

    def test_get_config_es_singleton(self, monkeypatch):
        set_required(monkeypatch)
        from config import get_config
        get_config.cache_clear()
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2
