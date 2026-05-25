import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.entities.user_profile import UserProfile
from src.domain.ports.i_session_store import ISessionStore

_PATCH_FROM_URL = "src.adapters.outbound.redis_session_adapter.from_url"


def make_mock_redis() -> MagicMock:
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock(return_value=True)
    return mock


def encode_profile(user_id: str = "abc123", **kwargs) -> bytes:
    data = {
        "user_id": user_id,
        "name": "Ana García",
        "district": "Miraflores",
        "issue": "transporte",
        "conversation_stage": "ACTIVE",
        **kwargs,
    }
    return json.dumps(data).encode()


class TestRedisSessionAdapter:
    async def test_get_profile_existente_retorna_user_profile(self):
        mock_redis = make_mock_redis()
        mock_redis.get = AsyncMock(return_value=encode_profile("abc123"))
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            result = await adapter.get_profile("abc123")

        assert isinstance(result, UserProfile)
        assert result.user_id == "abc123"
        assert result.name == "Ana García"
        assert result.district == "Miraflores"
        assert result.issue == "transporte"
        assert result.conversation_stage == "ACTIVE"

    async def test_get_profile_clave_inexistente_retorna_none(self):
        mock_redis = make_mock_redis()
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            result = await adapter.get_profile("no-existe")

        assert result is None

    async def test_get_profile_usa_prefijo_session(self):
        mock_redis = make_mock_redis()
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            await adapter.get_profile("abc123")

        mock_redis.get.assert_called_once_with("session:abc123")

    async def test_save_profile_llama_setex_con_ttl_24h(self):
        mock_redis = make_mock_redis()
        profile = UserProfile(user_id="abc123", name="Ana", district="Miraflores")
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            await adapter.save_profile(profile)

        mock_redis.setex.assert_called_once()
        key, ttl, _ = mock_redis.setex.call_args.args
        assert key == "session:abc123"
        assert ttl == 86400

    async def test_save_profile_serializa_campos_correctamente(self):
        mock_redis = make_mock_redis()
        profile = UserProfile(user_id="u1", name="Luis", district="San Isidro", issue="agua")
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            await adapter.save_profile(profile)

        _, _, json_guardado = mock_redis.setex.call_args.args
        data = json.loads(json_guardado)
        assert data["user_id"] == "u1"
        assert data["name"] == "Luis"
        assert data["district"] == "San Isidro"
        assert data["issue"] == "agua"

    async def test_redis_error_en_get_retorna_none_sin_excepcion(self):
        from redis.exceptions import RedisError
        mock_redis = make_mock_redis()
        mock_redis.get = AsyncMock(side_effect=RedisError("connection refused"))
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            result = await adapter.get_profile("abc123")

        assert result is None

    async def test_redis_error_en_save_no_propaga_excepcion(self):
        from redis.exceptions import RedisError
        mock_redis = make_mock_redis()
        mock_redis.setex = AsyncMock(side_effect=RedisError("connection refused"))
        profile = UserProfile(user_id="abc123", name="Ana", district="Lima")
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            await adapter.save_profile(profile)  # no debe lanzar

    async def test_redis_error_en_save_loguea_warning(self, caplog):
        from redis.exceptions import RedisError
        mock_redis = make_mock_redis()
        mock_redis.setex = AsyncMock(side_effect=RedisError("connection refused"))
        profile = UserProfile(user_id="abc123", name="Ana", district="Lima")
        with patch(_PATCH_FROM_URL, return_value=mock_redis):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")
            with caplog.at_level(logging.WARNING):
                await adapter.save_profile(profile)

        assert any("abc123" in record.message for record in caplog.records)

    async def test_implementa_i_session_store(self):
        with patch(_PATCH_FROM_URL, return_value=make_mock_redis()):
            from src.adapters.outbound.redis_session_adapter import RedisSessionAdapter
            adapter = RedisSessionAdapter(redis_url="redis://localhost", redis_password="")

        assert isinstance(adapter, ISessionStore)
