from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.domain.value_objects.rag_collection import RagCollection


@dataclass
class RagDocument:
    content: str
    metadata: dict = field(default_factory=dict)


class IRagClient(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        collection: RagCollection,
        top_k: int = 5,
    ) -> list[RagDocument]:
        """Busca en Qdrant por similitud semántica."""
