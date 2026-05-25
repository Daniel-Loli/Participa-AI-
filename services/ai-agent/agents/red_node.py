from __future__ import annotations

import json
from pathlib import Path

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_SYSTEM_PROMPT = """Eres un conector de redes juveniles para jóvenes peruanos.
Presenta las organizaciones juveniles relevantes con: nombre, área de trabajo y contacto.
Si hay casos de éxito similares, explícalos brevemente.
Usa lenguaje accesible y motivador para jóvenes de 15-29 años.

{orgs_context}
{cases_context}"""


def _load_organizations(data_dir: Path, district: str | None = None) -> list[dict]:
    try:
        orgs = json.loads((data_dir / "directorio.json").read_text(encoding="utf-8"))
        if district:
            by_district = [o for o in orgs if o.get("distrito", "").lower() == district.lower()]
            if len(by_district) >= 3:
                return by_district[:3]
            others = [o for o in orgs if o.get("distrito", "").lower() != district.lower()]
            return (by_district + others)[:3]
        return orgs[:3]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def make_red_node(llm_client: ILlmClient, rag_client: IRagClient, data_dir=None):
    _data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    async def red(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}
        orgs = _load_organizations(_data_dir, profile.get("district"))
        cases = await rag_client.search(state["user_message"], RagCollection.CASOS_EXITO, top_k=3)

        if orgs:
            lines = [
                f"- {o.get('nombre', 'N/A')} ({o.get('area', 'N/A')}) | {o.get('contacto', 'N/A')}"
                for o in orgs
            ]
            orgs_ctx = "Organizaciones:\n" + "\n".join(lines)
        else:
            orgs_ctx = "No se encontraron organizaciones en el directorio."

        cases_ctx = ""
        if cases:
            cases_ctx = "Casos de éxito:\n" + "\n\n".join(c.content for c in cases)

        system_prompt = _SYSTEM_PROMPT.format(orgs_context=orgs_ctx, cases_context=cases_ctx)
        response = await llm_client.generate(system_prompt, state["user_message"])
        return {
            "response": response,
            "tool_data": {"organizaciones": orgs},
            "rag_context": [c.content for c in cases],
        }

    return red
