#!/usr/bin/env python3
"""
Scraper diario de fuentes gubernamentales para Participa AI.

Uso:
    python data-pipeline/scraper/run_scraper.py                        # todas las fuentes
    python data-pipeline/scraper/run_scraper.py --source senaju        # una fuente
    python data-pipeline/scraper/run_scraper.py --source senaju --dry-run  # auditar sin subir
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Forzar UTF-8 en stdout para Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Cargar .env del ai-agent si existe (desarrollo local)
_ENV_PATH = Path(__file__).parent.parent.parent / "services" / "ai-agent" / ".env"
if _ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH)

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from sources import get_sources, Source
from fetcher import fetch, FetchError
from parser import parse_html
from pipeline import process_source_text
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(format="%(levelname)s %(name)s — %(message)s", level=logging.INFO)
logger = logging.getLogger("scraper")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: Variable de entorno '{name}' no configurada.", file=sys.stderr)
        sys.exit(1)
    return value


@dataclass
class SourceResult:
    source_id: str
    urls_ok: int
    urls_failed: int
    chunks_uploaded: int
    error: str | None = None


def _dry_run_source(source: Source) -> SourceResult:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150, separators=["\n\n", "\n", ". ", " "]
    )
    urls_ok = 0
    urls_failed = 0
    total_chunks = 0

    for source_url in source.urls:
        logger.info(f"[{source.id}] GET {source_url.url} [{source_url.content_type}]")
        try:
            html = fetch(source_url.url)
        except FetchError as exc:
            logger.error(f"[{source.id}] Falló fetch: {exc}")
            urls_failed += 1
            continue

        text = parse_html(html, source.css_selectors)
        if not text:
            logger.warning(f"[{source.id}] Sin texto extraíble en {source_url.url}")
            urls_failed += 1
            continue

        chunks = [c for c in splitter.split_text(text) if len(c.strip()) >= 60]
        total_chunks += len(chunks)

        print(f"\n{'=' * 55}")
        print(f"  FUENTE    : {source.name}")
        print(f"  URL       : {source_url.url}")
        print(f"  TIPO      : {source_url.content_type}")
        print(f"  COLECCION : {source.collection}")
        print(f"  CHUNKS    : {len(chunks)}")
        print(f"{'=' * 55}")
        for i, chunk in enumerate(chunks, 1):
            print(f"\n  [{i}/{len(chunks)}] [{source_url.content_type}]")
            print(f"  {chunk[:500]}{'...' if len(chunk) > 500 else ''}")

        urls_ok += 1

    return SourceResult(
        source_id=source.id,
        urls_ok=urls_ok,
        urls_failed=urls_failed,
        chunks_uploaded=total_chunks,
    )


def _process_source(
    source: Source,
    embeddings: OpenAIEmbeddings,
    qdrant: QdrantClient,
) -> SourceResult:
    urls_ok = 0
    urls_failed = 0
    total_uploaded = 0

    for source_url in source.urls:
        logger.info(f"[{source.id}] GET {source_url.url} [{source_url.content_type}]")
        try:
            html = fetch(source_url.url)
        except FetchError as exc:
            logger.error(f"[{source.id}] Falló fetch: {exc}")
            urls_failed += 1
            continue

        text = parse_html(html, source.css_selectors)
        if not text:
            logger.warning(f"[{source.id}] Sin texto extraíble en {source_url.url}")
            urls_failed += 1
            continue

        uploaded = process_source_text(
            text, source_url.url, source.collection, embeddings, qdrant, source_url.content_type
        )
        logger.info(f"[{source.id}] {uploaded} puntos subidos desde {source_url.url}")
        total_uploaded += uploaded
        urls_ok += 1

    return SourceResult(
        source_id=source.id,
        urls_ok=urls_ok,
        urls_failed=urls_failed,
        chunks_uploaded=total_uploaded,
    )


def _print_summary(results: list[SourceResult], elapsed: float) -> None:
    total_chunks = sum(r.chunks_uploaded for r in results)
    total_ok = sum(1 for r in results if r.urls_failed == 0)
    total_failed_urls = sum(r.urls_failed for r in results)
    minutes, seconds = divmod(int(elapsed), 60)

    print("\n" + "=" * 45)
    print("  Scraper Participa AI — Resumen")
    print("=" * 45)
    print(f"  Fuentes procesadas : {total_ok}/{len(results)}")
    print(f"  Puntos subidos     : {total_chunks}")
    print(f"  URLs con error     : {total_failed_urls}")
    print(f"  Tiempo total       : {minutes}m {seconds}s")

    if total_failed_urls > 0:
        print("\n  Fuentes con errores:")
        for r in results:
            if r.urls_failed > 0:
                print(f"    - {r.source_id}: {r.urls_failed} URL(s) fallida(s)")

    print("=" * 45 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper diario Participa AI")
    parser.add_argument("--source", type=str, default=None, help="ID de fuente específica")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el texto extraído y los chunks sin subir nada a Qdrant",
    )
    args = parser.parse_args()

    try:
        sources = get_sources(args.source)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"\n{'=' * 55}")
        print("  MODO DRY-RUN — solo lectura, nada se sube a Qdrant")
        print(f"{'=' * 55}")
        start = time.time()
        results: list[SourceResult] = []
        for source in sources:
            result = _dry_run_source(source)
            results.append(result)
        elapsed = time.time() - start
        print(f"\n{'=' * 55}")
        print(f"  Total chunks que se subirían: {sum(r.chunks_uploaded for r in results)}")
        print(f"  Tiempo: {int(elapsed)}s")
        print(f"{'=' * 55}\n")
        return

    openai_api_key = _require_env("OPENAI_API_KEY")
    qdrant_url = _require_env("QDRANT_URL")
    qdrant_api_key = _require_env("QDRANT_API_KEY")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    logger.info(f"Iniciando scraper — {len(sources)} fuente(s)")

    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=openai_api_key)
    qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)

    start = time.time()
    results: list[SourceResult] = []

    for source in sources:
        logger.info(f"Procesando: {source.name}")
        result = _process_source(source, embeddings, qdrant)
        results.append(result)

    _print_summary(results, time.time() - start)


if __name__ == "__main__":
    main()
