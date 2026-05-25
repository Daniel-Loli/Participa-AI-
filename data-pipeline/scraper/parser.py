from __future__ import annotations

import re

from bs4 import BeautifulSoup

_TAGS_TO_REMOVE = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "form"]


def parse_html(html: str, css_selectors: list[str]) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_TAGS_TO_REMOVE):
        tag.decompose()

    parts: list[str] = []
    seen: set[str] = set()

    for selector in css_selectors:
        for element in soup.select(selector):
            text = element.get_text(separator=" ", strip=True)
            if text and text not in seen:
                seen.add(text)
                parts.append(text)

    raw = "\n".join(parts)
    cleaned = re.sub(r"[ \t]+", " ", raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
