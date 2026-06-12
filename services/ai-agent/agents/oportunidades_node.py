from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_SYSTEM_PROMPT = """Eres el radar de oportunidades de Participa AI 📅
Presenta las oportunidades más próximas con: fecha, qué es y cómo participar.
Sé directo — el joven tiene que saber exactamente qué hacer.

REGLA CRÍTICA: Usa ÚNICAMENTE las oportunidades del contexto. NO inventes fechas,
eventos ni convocatorias.

REGLA DE DISTRITO: El usuario es de {district}. Si una oportunidad NO es de su
distrito, dilo explícitamente (ej: "es en Miraflores") y menciona sus requisitos
(ej: ser vecino empadronado) — NUNCA la presentes como si fuera de su distrito.

{calendar_context}
{scraped_context}
{wa_rules}"""


def _load_opportunities(data_dir: Path, district: str | None = None) -> list[dict]:
    try:
        events = json.loads((data_dir / "calendar.json").read_text(encoding="utf-8"))
        today = date.today().isoformat()
        future = sorted(
            [e for e in events if e.get("fecha", "") >= today],
            key=lambda e: e.get("fecha", ""),
        )
        if district:
            # Priorizar eventos del distrito; completar con otros (el prompt obliga
            # a indicar el distrito real de cada evento)
            by_district = [e for e in future if e.get("distrito", "").lower() == district.lower()]
            others = [e for e in future if e not in by_district]
            result = by_district + others
        else:
            result = future
        return result[:3]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def make_oportunidades_node(llm_client: ILlmClient, rag_client: IRagClient, data_dir=None):
    _data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    async def oportunidades(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}
        events = _load_opportunities(_data_dir, profile.get("district"))
        # Convocatorias y voluntariado scrapeados a diario de fuentes oficiales (SENAJU)
        docs = await rag_client.search(state["user_message"], RagCollection.PROCEDIMIENTOS, top_k=3)

        calendar_ctx = ""
        if events:
            lines = [
                f"- {e.get('fecha')} | {e.get('titulo', e.get('tipo', ''))} | "
                f"Distrito: {e.get('distrito', 'no especificado')} | "
                f"Requisitos: {e.get('requisitos', 'ninguno')} | {e.get('descripcion', '')}"
                for e in events
            ]
            calendar_ctx = "Oportunidades próximas (calendario):\n" + "\n".join(lines)
        else:
            calendar_ctx = "No hay eventos próximos registrados en el calendario."

        scraped_ctx = ""
        if docs:
            scraped_ctx = "Convocatorias y programas de fuentes oficiales:\n" + "\n\n".join(
                doc.content for doc in docs
            )

        system_prompt = _SYSTEM_PROMPT.format(
            district=profile.get("district", "no especificado"),
            calendar_context=calendar_ctx,
            scraped_context=scraped_ctx,
            wa_rules=WA_RULES,
        )
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "tool_data": {"oportunidades": events},
            "rag_context": [doc.content for doc in docs],
        }

    return oportunidades
