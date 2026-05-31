from __future__ import annotations

import dataclasses
import json
import logging

from redis.asyncio import from_url
from redis.exceptions import RedisError

from src.domain.entities.user_profile import UserProfile
from src.domain.ports.i_session_store import ISessionStore

logger = logging.getLogger(__name__)

_KEY_PREFIX = "session:"
_TTL_SECONDS = 86400  # 24 horas


class RedisSessionAdapter(ISessionStore):
    """Implementa ISessionStore usando Redis Cloud. Degrada sin lanzar excepciones."""

    def __init__(self, redis_url: str, redis_password: str = "") -> None:
        self._redis = from_url(redis_url, password=redis_password, socket_timeout=2)

    async def get_profile(self, session_id: str) -> UserProfile | None:
        try:
            raw = await self._redis.get(f"{_KEY_PREFIX}{session_id}")
            if raw is None:
                return None
            return UserProfile(**json.loads(raw))
        except RedisError as exc:
            logger.warning("Redis get_profile error para session '%s': %s", session_id, exc)
            return None

    async def save_profile(self, profile: UserProfile) -> None:
        try:
            json_str = json.dumps(dataclasses.asdict(profile))
            await self._redis.setex(f"{_KEY_PREFIX}{profile.user_id}", _TTL_SECONDS, json_str)
        except RedisError as exc:
            logger.warning("Redis save_profile error para user '%s': %s", profile.user_id, exc)

    async def delete_session(self, session_id: str) -> None:
        try:
            # Eliminar perfil de sesión (corto plazo)
            await self._redis.delete(f"{_KEY_PREFIX}{session_id}")
            # Eliminar checkpoints LangGraph; excluir profile_lt: que es memoria de largo plazo
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=f"*{session_id}*", count=50)
                if keys:
                    safe = [
                        k for k in keys
                        if not (k.decode() if isinstance(k, bytes) else k).startswith("profile_lt:")
                    ]
                    if safe:
                        await self._redis.delete(*safe)
                if cursor == 0:
                    break
        except RedisError as exc:
            logger.warning("Redis delete_session error para session '%s': %s", session_id, exc)
