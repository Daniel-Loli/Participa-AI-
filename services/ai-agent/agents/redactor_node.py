from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agents.history import trim_history
from agents.pdf_generator import letter_to_base64
from agents.state import AgentState
from agents.wa_format import WA_RULES
from src.domain.ports.i_llm_client import ILlmClient

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_DOC_KEYWORDS: dict[str, list[str]] = {
    "carta": ["carta"],
    "solicitud": ["solicitud", "información", "informacion"],
    "propuesta": ["propuesta", "pp", "presupuesto participativo"],
    "inscripcion": ["inscripción", "inscripcion", "mesa"],
}

_SYSTEM_PROMPT = """Eres el redactor de Participa AI ✍️
Genera {tipo_documento} formal y efectiva en español peruano.
Remitente: {nombre}, vecino/a de {distrito}.
Destinatario: {funcionario} ({cargo}) — {municipio}
Mesa de partes: {mesa_partes}
Fecha: {fecha}
Problemática: {issue}

Estructura: encabezado formal → exposición del problema (2-3 líneas) → petición concreta → cierre → firma.
Sin relleno, sin repetición. Directo y respetuoso.
{wa_rules}"""

_CONFIRM_MSG = (
    "Antes de generarla, confirma 👇\n\n"
    "¿Quieres que prepare la *{tipo_documento}* formal para presentar en mesa de partes?\n\n"
    "1. ✅ Sí, genérala\n"
    "2. ❌ No, tengo más dudas"
)

_POST_DOC_MSG = (
    "\n\n---\n"
    "¿Qué quieres hacer ahora?\n\n"
    "1. 📋 Cómo presentarla en mesa de partes\n"
    "2. 🤝 Ver organizaciones de apoyo en mi distrito\n"
    "3. 💬 Consultar otro tema"
)


def _detect_doc_type(message: str) -> str:
    msg_lower = message.lower()
    for doc_type, keywords in _DOC_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return doc_type
    return "carta"


def _load_municipio(data_dir: Path, district: str | None) -> dict:
    try:
        municipios = json.loads((data_dir / "municipios.json").read_text(encoding="utf-8"))
        if district:
            for m in municipios:
                if m.get("distrito", "").lower() == district.lower():
                    return m
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def make_redactor_node(llm_client: ILlmClient, data_dir=None):
    _data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    async def redactor(state: AgentState) -> dict:
        profile = dict(state.get("user_profile") or {})
        doc_type = _detect_doc_type(state["user_message"])

        # Pedir confirmación antes de generar
        if not state.get("doc_confirmed"):
            profile["awaiting_doc_confirmation"] = True
            response = _CONFIRM_MSG.format(tipo_documento=doc_type)
            return {
                "response": response,
                "user_profile": profile,
            }

        # Confirmación recibida: generar el documento
        profile["awaiting_doc_confirmation"] = False
        municipio = _load_municipio(_data_dir, profile.get("district"))

        system_prompt = _SYSTEM_PROMPT.format(
            tipo_documento=doc_type,
            nombre=profile.get("name", "Ciudadano/a"),
            distrito=profile.get("district", "Lima"),
            funcionario=municipio.get("funcionario", "Señor/a Alcalde/sa"),
            cargo=municipio.get("cargo", "Alcalde/sa"),
            municipio=municipio.get("municipio", "Municipalidad"),
            mesa_partes=municipio.get("mesa_partes", "Mesa de Partes Municipal"),
            fecha=date.today().strftime("%d de %B de %Y"),
            issue=profile.get("issue", "problemática ciudadana"),
            wa_rules=WA_RULES,
        )
        response = await llm_client.generate_with_history(system_prompt, trim_history(state["conversation_history"]))

        # Añadir menú de próximos pasos al final
        response_with_menu = response + _POST_DOC_MSG
        profile["awaiting_next_action"] = True

        pdf_b64 = letter_to_base64(
            response,
            doc_type,
            profile.get("name", "Ciudadano"),
            profile.get("district", "Lima"),
        )
        safe_district = (profile.get("district") or "Lima").lower().replace(" ", "_")
        pdf_filename = f"{doc_type}_{safe_district}_{date.today().strftime('%Y%m%d')}.pdf"

        return {
            "response": response_with_menu,
            "tool_data": {"municipio": municipio, "tipo_documento": doc_type},
            "user_profile": profile,
            "pdf_base64": pdf_b64,
            "pdf_filename": pdf_filename,
        }

    return redactor
