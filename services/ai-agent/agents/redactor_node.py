from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient

_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

_DOC_KEYWORDS: dict[str, list[str]] = {
    "carta": ["carta"],
    "solicitud": ["solicitud", "información", "informacion"],
    "propuesta": ["propuesta", "pp", "presupuesto participativo"],
    "inscripcion": ["inscripción", "inscripcion", "mesa"],
}

_SYSTEM_PROMPT = """Genera {tipo_documento} formal en español peruano.
Datos del remitente: {nombre}, vecino/a de {distrito}.
Destinatario: {funcionario} - {cargo} - {municipio}
Mesa de partes: {mesa_partes}
Fecha: {fecha}
Problemática: {issue}
Formato: encabezado formal, cuerpo con exposición del problema y petición concreta, cierre, firma."""


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
        profile = state.get("user_profile") or {}
        doc_type = _detect_doc_type(state["user_message"])
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
        )
        response = await llm_client.generate_with_history(system_prompt, state["conversation_history"])
        return {
            "response": response,
            "tool_data": {"municipio": municipio, "tipo_documento": doc_type},
            "conversation_history": [AIMessage(content=response)],
        }

    return redactor
