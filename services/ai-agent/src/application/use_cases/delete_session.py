from __future__ import annotations

from src.domain.ports.i_session_store import ISessionStore


class DeleteSessionUseCase:
    def __init__(self, session_store: ISessionStore) -> None:
        self._session_store = session_store

    async def execute(self, session_id: str) -> None:
        await self._session_store.delete_session(session_id)
