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

_SYSTEM_PROMPT = """Eres el estratega de Participa AI 🗺️
Das rutas de acción concretas para que jóvenes peruanos logren cambios reales en su comunidad.
Máximo 4 pasos. Cada paso: una sola acción clara y alcanzable.

REGLA CRÍTICA: Basa tu respuesta ÚNICAMENTE en los procedimientos y eventos del contexto proporcionado.
NO inventes pasos, plazos, instituciones ni contactos que no aparezcan en el contexto.
Si el contexto no tiene suficiente información para armar una ruta concreta, dilo honestamente.

REGLA DE DISTRITO: Si un evento NO es del distrito del usuario, dilo explícitamente
(ej: "es en Miraflores, no en tu distrito") y menciona sus requisitos — NUNCA lo
presentes como si fuera del distrito del usuario ni omitas requisitos de residencia.

{profile_context}
{calendar_context}
{rag_context}
{wa_rules}"""


def _load_calendar(data_dir: Path, district: str | None = None) -> list[dict]:
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
            return (by_district + others)[:3]
        return future[:3]
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


def make_estratega_node(llm_client: ILlmClient, rag_client: IRagClient, data_dir=None):
    _data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    async def estratega(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}
        docs = await rag_client.search(state["user_message"], RagCollection.PROCEDIMIENTOS, top_k=5)
        events = _load_calendar(_data_dir, profile.get("district"))

        parts = []
        if profile.get("name"):
            parts.append(f"Nombre: {profile['name']}")
        if profile.get("district"):
            parts.append(f"Distrito: {profile['district']}")
        if profile.get("issue"):
            parts.append(f"Problemática: {profile['issue']}")
        profile_ctx = "\n".join(parts)

        calendar_ctx = ""
        if events:
            lines = [
                f"- {e.get('fecha')} | {e.get('titulo', e.get('tipo', ''))} | "
                f"Distrito: {e.get('distrito', 'no especificado')} | "
                f"Requisitos: {e.get('requisitos', 'ninguno')} | {e.get('descripcion', '')}"
                for e in events
            ]
            calendar_ctx = "Próximos eventos:\n" + "\n".join(lines)

        rag_ctx = ""
        if docs:
            rag_ctx = "Procedimientos:\n" + "\n\n".join(doc.content for doc in docs)

        system_prompt = _SYSTEM_PROMPT.format(
            profile_context=profile_ctx,
            calendar_context=calendar_ctx,
            rag_context=rag_ctx,
            wa_rules=WA_RULES,
        )
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
            "tool_data": {"eventos": events},
        }

    return estratega
