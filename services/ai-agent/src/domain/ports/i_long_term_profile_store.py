from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.long_term_profile import LongTermProfile


class ILongTermProfileStore(ABC):
    @abstractmethod
    async def get_profile(self, user_id: str) -> LongTermProfile | None: ...

    @abstractmethod
    async def save_profile(self, profile: LongTermProfile) -> None: ...
