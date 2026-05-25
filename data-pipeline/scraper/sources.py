from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceUrl:
    url: str
    content_type: str  # "convocatoria", "programa", "noticia", "voluntariado", "normativa", "general"


@dataclass
class Source:
    id: str
    name: str
    urls: list[SourceUrl]
    collection: str
    css_selectors: list[str]


ALL_SOURCES: list[Source] = [
    Source(
        id="senaju",
        name="SENAJU — Secretaría Nacional de la Juventud",
        collection="procedimientos",
        css_selectors=[
            "main", "article", "section",
            ".entry-content", ".post-content", ".content",
            "h1", "h2", "h3", "h4", "p", "li",
        ],
        urls=[
            SourceUrl("https://juventud.gob.pe", "general"),
            SourceUrl("https://juventud.gob.pe/noticias/", "noticia"),
            SourceUrl("https://juventud.gob.pe/voluntariado-juvenil/", "voluntariado"),
            SourceUrl("https://juventud.gob.pe/participacion-juvenil/", "programa"),
            SourceUrl("https://juventud.gob.pe/organizaciones-juveniles/", "normativa"),
        ],
    ),
]

_SOURCE_BY_ID: dict[str, Source] = {s.id: s for s in ALL_SOURCES}


def get_sources(source_id: str | None) -> list[Source]:
    if source_id is None:
        return ALL_SOURCES
    if source_id not in _SOURCE_BY_ID:
        valid = ", ".join(_SOURCE_BY_ID.keys())
        raise ValueError(f"Fuente '{source_id}' no existe. Válidas: {valid}")
    return [_SOURCE_BY_ID[source_id]]
