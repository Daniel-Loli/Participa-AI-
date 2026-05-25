from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_SYSTEM_PROMPT = """Eres un asistente de participación ciudadana para jóvenes peruanos.
Lista las oportunidades de participación más próximas con:
- Fecha exacta
- Tipo de evento
- Qué debe hacer el usuario para participar
Sé conciso y usa lenguaje accesible para jóvenes de 15-29 años.

{calendar_context}"""


def _load_opportunities(data_dir: Path, district: str | None = None) -> list[dict]:
    try:
        events = json.loads((data_dir / "calendar.json").read_text(encoding="utf-8"))
        today = date.today().isoformat()
        future = sorted(
            [e for e in events if e.get("fecha", "") >= today],
            key=lambda e: e.get("fecha", ""),
        )
        if district:
            by_district = [e for e in future if e.get("distrito", "").lower() == district.lower()]
            result = by_district if len(by_district) >= 3 else future
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

        calendar_ctx = ""
        if events:
            lines = [f"- {e.get('fecha')} | {e.get('tipo')} | {e.get('descripcion', '')}" for e in events]
            calendar_ctx = "Oportunidades próximas:\n" + "\n".join(lines)

        system_prompt = _SYSTEM_PROMPT.format(calendar_context=calendar_ctx)
        response = await llm_client.generate_with_history(system_prompt, state["conversation_history"])
        return {
            "response": response,
            "tool_data": {"oportunidades": events},
            "conversation_history": [AIMessage(content=response)],
        }

    return oportunidades
