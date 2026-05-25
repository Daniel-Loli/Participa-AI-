from __future__ import annotations

import asyncio
import logging

import httpx
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.adapters.outbound.errors import RagTimeoutError
from src.domain.ports.i_rag_client import IRagClient, RagDocument
from src.domain.value_objects.rag_collection import RagCollection

logger = logging.getLogger(__name__)


class QdrantRagAdapter(IRagClient):
    """Implementa IRagClient usando Qdrant Cloud + LangChain."""

    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: str,
        openai_api_key: str,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._embeddings = OpenAIEmbeddings(model=embedding_model, api_key=openai_api_key)
        self._qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=5.0)

    async def search(
        self,
        query: str,
        collection: RagCollection,
        top_k: int = 5,
    ) -> list[RagDocument]:
        collection_name = collection.value
        try:
            store = QdrantVectorStore(
                client=self._qdrant_client,
                collection_name=collection_name,
                embedding=self._embeddings,
            )
            docs = await store.asimilarity_search(query, k=top_k)
            return [
                RagDocument(content=doc.page_content, metadata=doc.metadata)
                for doc in docs
            ]
        except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
            logger.warning("Qdrant timeout en colección '%s': %s", collection_name, exc)
            return []
        except Exception as exc:
            logger.warning("Error al buscar en Qdrant colección '%s': %s", collection_name, exc)
            return []
