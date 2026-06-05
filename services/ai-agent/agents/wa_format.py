from __future__ import annotations

import re

WA_RULES = """
FORMATO WHATSAPP (obligatorio):
- Usa *negrita* con UN solo asterisco para destacar lo importante
- Listas informativas: usa guion - (sin asteriscos ni #)
- NUNCA uses listas numeradas (1. 2. 3.) como opciones de navegación — eso confunde el flujo. Solo el menú principal del sistema puede tener números. Si necesitas dar opciones, descríbelas en texto natural.
- NUNCA uses ### ## # ni markdown de headers
- NUNCA uses ** doble asterisco
- Máximo 3-4 puntos por respuesta — si hay más, pregunta si quiere continuar
- Termina siempre con UNA pregunta corta para guiar el siguiente paso
- Tono cercano, directo y motivador para jóvenes de 15-29 años
- Usa emojis con moderación (1-2 por mensaje máximo)"""


def clean(text: str) -> str:
    """Elimina markdown que no renderiza en WhatsApp."""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"_\1_", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
