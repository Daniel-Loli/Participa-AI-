from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 150
_MIN_CHUNK_LEN = 60
_BATCH_SIZE = 50
_VECTOR_SIZE = 1536
_BATCH_SLEEP = 0.4


def content_id(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**53)


def _ensure_collection(client: QdrantClient, collection: str) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("coleccion_creada", collection=collection)


def process_source_text(
    text: str,
    source_url: str,
    collection: str,
    embeddings: OpenAIEmbeddings,
    qdrant_client: QdrantClient,
    content_type: str = "general",
) -> int:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = [c for c in splitter.split_text(text) if len(c.strip()) >= _MIN_CHUNK_LEN]

    if not chunks:
        logger.warning("sin_chunks_utiles", url=source_url)
        return 0

    _ensure_collection(qdrant_client, collection)

    scraped_at = datetime.now(timezone.utc).isoformat()
    total_uploaded = 0

    for i in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[i : i + _BATCH_SIZE]
        try:
            vectors = embeddings.embed_documents(batch)
        except Exception as exc:
            logger.warning("error_embedding_batch", batch_index=i, error=str(exc))
            continue

        points = [
            PointStruct(
                id=content_id(chunk),
                vector=vector,
                payload={
                    "content": chunk,
                    "source": source_url,
                    "scraped_at": scraped_at,
                    "collection": collection,
                    "type": "scraped",
                    "content_type": content_type,
                },
            )
            for chunk, vector in zip(batch, vectors)
        ]

        try:
            qdrant_client.upsert(collection_name=collection, points=points)
            total_uploaded += len(points)
        except Exception as exc:
            logger.warning("error_upsert_batch", batch_index=i, error=str(exc))

        time.sleep(_BATCH_SLEEP)

    return total_uploaded
