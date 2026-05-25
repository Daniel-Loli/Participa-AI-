import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from src.domain.ports.i_rag_client import IRagClient, RagDocument
from src.domain.value_objects.rag_collection import RagCollection

_PATCH_EMBEDDINGS = "src.adapters.outbound.qdrant_rag_adapter.OpenAIEmbeddings"
_PATCH_QDRANT_CLIENT = "src.adapters.outbound.qdrant_rag_adapter.QdrantClient"
_PATCH_VECTOR_STORE = "src.adapters.outbound.qdrant_rag_adapter.QdrantVectorStore"

_ADAPTER_KWARGS = dict(
    qdrant_url="https://qdrant.example.com",
    qdrant_api_key="api-key",
    openai_api_key="sk-test",
)


class TestQdrantRagAdapter:
    async def test_search_exitoso_retorna_rag_documents(self):
        mock_docs = [
            Document(page_content="El PP es...", metadata={"source": "ley_28056.pdf"}),
            Document(page_content="Participación ciudadana", metadata={"source": "ley_27783.pdf"}),
        ]
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                patch(_PATCH_VECTOR_STORE) as MockStore:
            MockStore.return_value.asimilarity_search = AsyncMock(return_value=mock_docs)
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
            result = await adapter.search("presupuesto participativo", RagCollection.LEGAL)

        assert len(result) == 2
        assert all(isinstance(doc, RagDocument) for doc in result)
        assert result[0].content == "El PP es..."
        assert result[0].metadata["source"] == "ley_28056.pdf"

    async def test_coleccion_inexistente_retorna_lista_vacia(self):
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                patch(_PATCH_VECTOR_STORE) as MockStore:
            MockStore.return_value.asimilarity_search = AsyncMock(
                side_effect=Exception("Collection 'ods' not found: 404")
            )
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
            result = await adapter.search("query", RagCollection.ODS)

        assert result == []

    async def test_timeout_retorna_lista_vacia(self):
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                patch(_PATCH_VECTOR_STORE) as MockStore:
            MockStore.return_value.asimilarity_search = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
            result = await adapter.search("query", RagCollection.LEGAL)

        assert result == []

    async def test_mapeo_rag_collection_legal_usa_nombre_legal(self):
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                patch(_PATCH_VECTOR_STORE) as MockStore:
            MockStore.return_value.asimilarity_search = AsyncMock(return_value=[])
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
            await adapter.search("query", RagCollection.LEGAL)

        assert MockStore.call_args.kwargs["collection_name"] == "legal"

    async def test_mapeo_todas_las_colecciones(self):
        colecciones_esperadas = {
            RagCollection.LEGAL: "legal",
            RagCollection.ODS: "ods",
            RagCollection.PROCEDIMIENTOS: "procedimientos",
            RagCollection.CASOS_EXITO: "casos_exito",
        }
        for coleccion, nombre_esperado in colecciones_esperadas.items():
            with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                    patch(_PATCH_VECTOR_STORE) as MockStore:
                MockStore.return_value.asimilarity_search = AsyncMock(return_value=[])
                from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
                adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
                await adapter.search("query", coleccion)
            assert MockStore.call_args.kwargs["collection_name"] == nombre_esperado

    async def test_search_respeta_top_k(self):
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT), \
                patch(_PATCH_VECTOR_STORE) as MockStore:
            MockStore.return_value.asimilarity_search = AsyncMock(return_value=[])
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
            await adapter.search("query", RagCollection.PROCEDIMIENTOS, top_k=3)

        assert MockStore.return_value.asimilarity_search.call_args.kwargs.get("k") == 3

    async def test_implementa_i_rag_client(self):
        with patch(_PATCH_EMBEDDINGS), patch(_PATCH_QDRANT_CLIENT):
            from src.adapters.outbound.qdrant_rag_adapter import QdrantRagAdapter
            adapter = QdrantRagAdapter(**_ADAPTER_KWARGS)
        assert isinstance(adapter, IRagClient)
