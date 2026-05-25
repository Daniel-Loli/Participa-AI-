#!/usr/bin/env python3
"""
Ingestión de PDFs a Qdrant Cloud.

Uso desde la raíz del proyecto:
    cd services/ai-agent
    python ../../data-pipeline/ingest_rag.py
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

# Forzar UTF-8 en stdout para Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import pypdf
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / "services" / "ai-agent" / ".env")

QDRANT_URL = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
VECTOR_SIZE = 1536

KNOWLEDGE_BASE = ROOT / "knowledge-base"
COLLECTIONS = {
    "legal": KNOWLEDGE_BASE / "legal",
    "ods": KNOWLEDGE_BASE / "ods",
    "procedimientos": KNOWLEDGE_BASE / "procedimientos",
}


def content_id(text: str) -> int:
    """ID determinístico basado en contenido — permite re-ejecutar sin duplicados."""
    return int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 53)


def load_pdf(path: Path) -> list[dict]:
    reader = pypdf.PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if len(text) > 50:
            pages.append({"text": text, "page": i + 1})
    return pages


def main() -> None:
    print("Conectando a Qdrant y OpenAI...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " "],
    )

    existing = {c.name for c in client.get_collections().collections}

    for collection_name, folder in COLLECTIONS.items():
        print(f"\n{'=' * 55}")
        print(f"  Colección: {collection_name}")
        print(f"{'=' * 55}")

        if not folder.exists():
            print(f"  Carpeta no encontrada: {folder}")
            continue

        pdfs = list(folder.glob("*.pdf"))
        if not pdfs:
            print("  Sin PDFs en esta carpeta")
            continue

        if collection_name not in existing:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            print(f"  ✓ Colección creada")
        else:
            print(f"  ✓ Colección ya existente (re-ejecutar es seguro — IDs son determinísticos)")

        for pdf_path in pdfs:
            print(f"\n  PDF: {pdf_path.name}")
            pages = load_pdf(pdf_path)
            print(f"       {len(pages)} páginas con texto extraíble")

            if not pages:
                print("       Sin texto — omitido")
                continue

            chunks = []
            for page_data in pages:
                for chunk in splitter.split_text(page_data["text"]):
                    if len(chunk.strip()) > 60:
                        chunks.append({"text": chunk, "page": page_data["page"]})

            print(f"       {len(chunks)} chunks generados")

            batch_size = 50
            uploaded = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                texts = [c["text"] for c in batch]

                try:
                    vectors = embeddings.embed_documents(texts)
                except Exception as exc:
                    print(f"       Error en batch {i // batch_size + 1}: {exc}")
                    time.sleep(3)
                    continue

                points = [
                    PointStruct(
                        id=content_id(c["text"]),
                        vector=v,
                        payload={
                            "content": c["text"],
                            "source": pdf_path.name,
                            "page": c["page"],
                            "collection": collection_name,
                        },
                    )
                    for c, v in zip(batch, vectors)
                ]

                client.upsert(collection_name=collection_name, points=points)
                uploaded += len(points)
                total_batches = (len(chunks) - 1) // batch_size + 1
                print(f"       Batch {i // batch_size + 1}/{total_batches} — {len(points)} puntos subidos ✓")
                time.sleep(0.4)

            print(f"       Total: {uploaded} puntos en '{collection_name}'")

    print(f"\n{'=' * 55}")
    print("  ✓ Ingestión RAG completada")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
