from __future__ import annotations

import json

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient

_EXTRACT_PROMPT = """Extrae del mensaje el nombre y/o distrito del usuario peruano.
Responde SOLO con JSON válido (sin explicaciones):
{"nombre": "valor o null", "distrito": "valor o null"}

Ejemplos:
"Hola soy Ana de San Isidro" → {"nombre": "Ana", "distrito": "San Isidro"}
"Me llamo Carlos" → {"nombre": "Carlos", "distrito": null}
"Hola, quiero participar" → {"nombre": null, "distrito": null}"""

_PROBLEM_MENU = (
    "¿Cuál es el problema que más te preocupa en tu comunidad?\n\n"
    "1. Seguridad / violencia\n"
    "2. Infraestructura (calles, parques, alumbrado)\n"
    "3. Basura / medio ambiente\n"
    "4. Educación\n"
    "5. Salud\n"
    "6. Corrupción / transparencia\n"
    "7. Otro (escríbelo)"
)

_OPTION_MAP: dict[str, str] = {
    "1": "seguridad y violencia",
    "2": "infraestructura (calles, parques, alumbrado)",
    "3": "basura y medio ambiente",
    "4": "educación",
    "5": "salud",
    "6": "corrupción y transparencia",
}


def _resolve_issue(message: str) -> str | None:
    """Mapea número de opción a la problemática, o devuelve el texto libre."""
    stripped = message.strip()
    if stripped in _OPTION_MAP:
        return _OPTION_MAP[stripped]
    # Si eligió opción 7 u otro texto libre, usarlo directamente (sin el "7.")
    if stripped == "7":
        return None  # pedir que lo escriba
    if len(stripped) > 3:
        return stripped
    return None


def make_onboarding_node(llm_client: ILlmClient):
    async def onboarding(state: AgentState) -> dict:
        profile = dict(state.get("user_profile") or {})

        # Intentar extraer nombre y/o distrito del mensaje actual
        had_district = bool(profile.get("district"))
        if not profile.get("name") or not profile.get("district"):
            try:
                raw = await llm_client.generate(_EXTRACT_PROMPT, state["user_message"])
                data = json.loads(raw)
                if data.get("nombre"):
                    profile["name"] = data["nombre"]
                if data.get("distrito"):
                    profile["district"] = data["distrito"]
            except Exception:
                pass
        just_got_district = not had_district and bool(profile.get("district"))

        # Paso 1: pedir nombre
        if not profile.get("name"):
            response = (
                "¡Hola! Soy *Participa AI* 🇵🇪\n\n"
                "Te ayudo a participar en tu comunidad de forma concreta y legal.\n\n"
                "¿Cómo te llamas?"
            )

        # Paso 2: pedir distrito
        elif not profile.get("district"):
            response = (
                f"¡Buenísimo, {profile['name']}! 👋\n\n"
                "¿De qué distrito eres? Así te conecto con las oportunidades más cercanas a ti."
            )

        # Paso 3: pedir problemática (con menú si aún no la tiene)
        elif not profile.get("issue"):
            # Si el distrito se acaba de extraer de ESTE mensaje, no usar el mismo
            # mensaje para extraer el issue — mostrar el menú en el próximo turno
            issue = None if just_got_district else _resolve_issue(state["user_message"])
            if issue:
                profile["issue"] = issue
                profile["conversation_stage"] = "ACTIVE"
                response = (
                    f"Entendido, *{issue}* en {profile['district']} 📍\n\n"
                    "Estoy listo para ayudarte. ¿Por dónde quieres empezar?\n\n"
                    "1. Conocer mis derechos y leyes\n"
                    "2. Ver qué acciones puedo tomar\n"
                    "3. Redactar una carta o solicitud\n"
                    "4. Conectar con organizaciones juveniles"
                )
            elif state["user_message"].strip() == "7":
                response = "Cuéntame con tus palabras, ¿cuál es el problema que te preocupa?"
            else:
                response = (
                    f"¡Perfecto! {profile['name']} de *{profile['district']}* — ya te tengo ubicado/a 📍\n\n"
                    + _PROBLEM_MENU
                )

        # Ya completó el onboarding
        else:
            profile["conversation_stage"] = "ACTIVE"
            response = (
                f"¡Perfecto! {profile['name']} de *{profile['district']}* — ya te tengo ubicado/a 📍\n\n"
                + _PROBLEM_MENU
            )

        return {
            "response": response,
            "user_profile": profile,
            "conversation_history": [AIMessage(content=response)],
        }

    return onboarding
