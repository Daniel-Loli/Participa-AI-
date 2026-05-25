from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage

from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_SYSTEM_PROMPT = """Eres el estratega de Participa AI 🗺️
Das rutas de acción concretas para que jóvenes peruanos logren cambios reales en su comunidad.
Máximo 4 pasos. Cada paso: una sola acción clara y alcanzable.
{profile_context}
{calendar_context}
{rag_context}
{wa_rules}"""


def _load_calendar(data_dir: Path, district: str | None = None) -> list[dict]:
    try:
        events = json.loads((data_dir / "calendar.json").read_text(encoding="utf-8"))
        today = date.today().isoformat()
        future = [e for e in events if e.get("fecha", "") >= today]
        if district:
            by_district = [e for e in future if e.get("distrito", "").lower() == district.lower()]
            future = by_district if len(by_district) >= 3 else future
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
            lines = [f"- {e.get('fecha')} | {e.get('tipo')} | {e.get('descripcion', '')}" for e in events]
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
        response = await llm_client.generate_with_history(system_prompt, state["conversation_history"])
        return {
            "response": response,
            "rag_context": [doc.content for doc in docs],
            "tool_data": {"eventos": events},
            "conversation_history": [AIMessage(content=response)],
        }

    return estratega
