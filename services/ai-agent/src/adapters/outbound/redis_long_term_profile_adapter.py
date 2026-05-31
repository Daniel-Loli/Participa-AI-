from __future__ import annotations

import dataclasses
import json
import logging

from redis.asyncio import from_url
from redis.exceptions import RedisError

from src.domain.entities.long_term_profile import LongTermProfile
from src.domain.ports.i_long_term_profile_store import ILongTermProfileStore

logger = logging.getLogger(__name__)

_KEY_PREFIX = "profile_lt:"
_TTL_SECONDS = 2_592_000  # 30 días


class RedisLongTermProfileAdapter(ILongTermProfileStore):
    def __init__(self, redis_url: str, redis_password: str = "") -> None:
        self._redis = from_url(redis_url, password=redis_password, socket_timeout=2)

    async def get_profile(self, user_id: str) -> LongTermProfile | None:
        try:
            raw = await self._redis.get(f"{_KEY_PREFIX}{user_id}")
            if raw is None:
                return None
            data = json.loads(raw)
            # Filtrar campos desconocidos para compatibilidad hacia adelante
            valid = {f.name for f in dataclasses.fields(LongTermProfile)}
            return LongTermProfile(**{k: v for k, v in data.items() if k in valid})
        except RedisError as exc:
            logger.warning("Redis LT get_profile error para '%s': %s", user_id, exc)
            return None

    async def save_profile(self, profile: LongTermProfile) -> None:
        try:
            json_str = json.dumps(dataclasses.asdict(profile))
            await self._redis.setex(f"{_KEY_PREFIX}{profile.user_id}", _TTL_SECONDS, json_str)
        except RedisError as exc:
            logger.warning("Redis LT save_profile error para '%s': %s", profile.user_id, exc)
