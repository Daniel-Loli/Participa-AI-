from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.user_profile import UserProfile


class ISessionStore(ABC):
    @abstractmethod
    async def get_profile(self, session_id: str) -> UserProfile | None:
        """Recupera el perfil del usuario desde Redis."""

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> None:
        """Persiste el perfil del usuario en Redis (TTL 24h)."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Elimina perfil y checkpoint LangGraph de Redis."""
