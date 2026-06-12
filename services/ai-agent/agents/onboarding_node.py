from __future__ import annotations

import json

from agents.menu_node import MAIN_MENU
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


# Mensajes que no son una problemática real (saludos, muletillas)
_NON_ISSUE = {"hola", "buenas", "buenos días", "buenas tardes", "gracias",
              "ok", "okay", "si", "sí", "no", "no sé", "no se", "hey"}


def _resolve_issue(message: str) -> str | None:
    """Mapea número de opción a la problemática, o devuelve el texto libre."""
    stripped = message.strip()
    if stripped in _OPTION_MAP:
        return _OPTION_MAP[stripped]
    # Si eligió opción 7 u otro texto libre, usarlo directamente (sin el "7.")
    if stripped == "7":
        return None  # pedir que lo escriba
    if stripped.lower() in _NON_ISSUE:
        return None
    if len(stripped) > 3:
        return stripped
    return None


def make_onboarding_node(llm_client: ILlmClient):
    async def onboarding(state: AgentState) -> dict:
        profile = dict(state.get("user_profile") or {})

        # Intentar extraer nombre y/o distrito del mensaje actual
        had_name = bool(profile.get("name"))
        had_district = bool(profile.get("district"))
        if not had_name or not had_district:
            try:
                raw = await llm_client.generate(_EXTRACT_PROMPT, state["user_message"])
                data = json.loads(raw)
                if data.get("nombre"):
                    profile["name"] = data["nombre"]
                if data.get("distrito"):
                    profile["district"] = data["distrito"]
            except Exception:
                pass
        # Si el mensaje actual se usó para dar nombre o distrito, no reutilizarlo como problemática
        just_extracted = (not had_name and bool(profile.get("name"))) or (
            not had_district and bool(profile.get("district"))
        )

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
            # Si el nombre o distrito se acaba de extraer de ESTE mensaje, no usar el
            # mismo mensaje para extraer el issue — mostrar el menú en el próximo turno
            issue = None if just_extracted else _resolve_issue(state["user_message"])
            if issue:
                profile["issue"] = issue
                profile["conversation_stage"] = "ACTIVE"
                response = (
                    f"Entendido, *{issue}* en {profile['district']} 📍\n\n"
                    f"Estoy listo para ayudarte. ¿Por dónde quieres empezar?\n\n{MAIN_MENU}"
                )
            elif state["user_message"].strip() == "7":
                response = "Cuéntame con tus palabras, ¿cuál es el problema que te preocupa?"
            else:
                response = (
                    f"¡Perfecto! {profile['name']} de *{profile['district']}* — ya te tengo ubicado/a 📍\n\n"
                    + _PROBLEM_MENU
                )

        # Ya completó el onboarding — mostrar el menú principal, no repetir el de problemáticas
        else:
            profile["conversation_stage"] = "ACTIVE"
            response = (
                f"¡Listo, {profile['name']}! Ya tengo tus datos 📍\n\n"
                f"¿En qué te puedo ayudar?\n\n{MAIN_MENU}"
            )

        return {
            "response": response,
            "user_profile": profile,
            "skip_tone": True,
        }

    return onboarding
