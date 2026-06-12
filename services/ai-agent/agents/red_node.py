from __future__ import annotations

import asyncio
import json
import unicodedata
from pathlib import Path

from agents.history import trim_history
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.ports.i_rag_client import IRagClient
from src.domain.value_objects.rag_collection import RagCollection

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_SYSTEM_PROMPT = """Eres el conector de redes de Participa AI 🤝
Presenta máximo 3 organizaciones juveniles: nombre, área, de dónde son y cómo contactarlas.
Sé motivador — muestra que hay jóvenes como ellos haciendo cosas reales.

El usuario es de {district}.

REGLAS DE HONESTIDAD (obligatorias):
- Indica SIEMPRE de qué distrito/región es cada organización.
- Si una organización NO es del distrito del usuario, dilo claramente — NUNCA la presentes como local.
- NO afirmes cobertura nacional, actividades virtuales ni formas de participar que no estén en los datos. Si no sabes si atienden su zona, sugiere escribirles para preguntarlo.

IMPORTANTE: Tu única función aquí es conectar al joven con organizaciones.
- NO ofrezcas redactar cartas ni mensajes — eso se hace desde la opción 3 del menú.
- Cierra siempre con una pregunta sobre las organizaciones mostradas o sobre su problemática, NUNCA con una oferta de redacción.

{orgs_context}
{scraped_context}
{cases_context}
{wa_rules}"""


def _normalize(text: str) -> str:
    """minúsculas y sin tildes — "San Martín de Porres" == "san martin de porres"."""
    return unicodedata.normalize("NFD", text.lower().strip()).encode("ascii", "ignore").decode()


def _is_lima_metro(data_dir: Path, district_norm: str) -> bool:
    """municipios.json solo contiene distritos de Lima Metropolitana y Callao."""
    try:
        municipios = json.loads((data_dir / "municipios.json").read_text(encoding="utf-8"))
        return any(_normalize(m.get("distrito", "")) == district_norm for m in municipios)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _load_organizations(data_dir: Path, district: str | None = None) -> list[dict]:
    try:
        orgs = json.loads((data_dir / "directorio.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if not district:
        return orgs[:3]

    district_norm = _normalize(district)
    by_district = [o for o in orgs if _normalize(o.get("distrito", "")) == district_norm]
    if len(by_district) >= 3:
        return by_district[:3]

    # Completar con otras: si el distrito es de Lima Metropolitana, priorizar la región
    # Lima/Callao — sin esto se rellenaba en orden de archivo (Amazonas primero)
    others = [o for o in orgs if o not in by_district]
    if _is_lima_metro(data_dir, district_norm):
        others.sort(key=lambda o: o.get("region") not in ("Lima", "Callao"))
    return (by_district + others)[:3]


def make_red_node(llm_client: ILlmClient, rag_client: IRagClient, data_dir=None):
    _data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    async def red(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}
        orgs = _load_organizations(_data_dir, profile.get("district"))
        # Casos de éxito (RAG) + convocatorias/voluntariado scrapeados a diario de SENAJU
        cases, scraped = await asyncio.gather(
            rag_client.search(state["user_message"], RagCollection.CASOS_EXITO, top_k=3),
            rag_client.search(state["user_message"], RagCollection.PROCEDIMIENTOS, top_k=3),
        )

        if orgs:
            lines = [
                f"- *{o.get('nombre', 'N/A')}* ({o.get('area', 'N/A')}) — "
                f"{o.get('distrito', 'sin distrito')}, {o.get('region', 'sin región')} — "
                f"contacto: {o.get('contacto', 'N/A')}"
                for o in orgs
            ]
            orgs_ctx = "Organizaciones del directorio RENOJ:\n" + "\n".join(lines)
        else:
            orgs_ctx = "No se encontraron organizaciones en el directorio."

        scraped_ctx = ""
        if scraped:
            scraped_ctx = "Convocatorias y voluntariado de fuentes oficiales (SENAJU):\n" + "\n\n".join(
                doc.content for doc in scraped
            )

        cases_ctx = ""
        if cases:
            cases_ctx = "Casos de éxito:\n" + "\n\n".join(c.content for c in cases)

        system_prompt = _SYSTEM_PROMPT.format(
            district=profile.get("district", "no especificado"),
            orgs_context=orgs_ctx,
            scraped_context=scraped_ctx,
            cases_context=cases_ctx,
            wa_rules=WA_RULES,
        )
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))
        return {
            "response": response,
            "tool_data": {"organizaciones": orgs},
            "rag_context": [c.content for c in cases] + [d.content for d in scraped],
        }

    return red
