from __future__ import annotations

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.value_objects.agent_intent import AgentIntent

_SYSTEM_PROMPT = """Clasifica la intención del mensaje de un usuario joven peruano.
Responde con UNA SOLA PALABRA de esta lista: onboarding, legal, estratega, oportunidades, red, redactor, general

Ejemplos:
"¿qué leyes me protegen?" → legal
"ayúdame a redactar una carta" → redactor
"hola, quiero participar" (sin perfil) → onboarding
"¿cuándo es la próxima sesión municipal?" → oportunidades
"¿hay organizaciones en mi zona?" → red
"¿cómo planteo mi queja a la municipalidad?" → estratega
"¿qué es el ODS 16?" → general"""

_VALID_INTENTS = {i.value for i in AgentIntent}

# Detección de intención compuesta legal + documento
_DOC_TERMS = {"carta", "redactar", "solicitud", "documento", "escrib", "generar", "genera"}
_LEGAL_TERMS = {"ley", "leyes", "legal", "derecho", "derechos", "artículo", "norma", "normativa"}

# Respuestas afirmativas para confirmar generación de documento
_AFIRMATIVO = {"si", "sí", "dale", "ok", "okay", "claro", "yes", "hazlo", "bueno", "adelante",
               "genérala", "generala", "1"}

# Menú post-onboarding: opciones del menú que aparece al terminar el onboarding
_POST_ONBOARDING_MAP = {
    "1": AgentIntent.LEGAL.value,
    "2": AgentIntent.ESTRATEGA.value,
    "3": AgentIntent.REDACTOR.value,
    "4": AgentIntent.RED.value,
}

# Menú post-documento
_POST_DOC_MAP = {
    "1": AgentIntent.ESTRATEGA.value,   # Cómo presentarla → estratega explica pasos
    "2": AgentIntent.RED.value,          # Ver organizaciones → nodo red
    "3": AgentIntent.GENERAL.value,      # Consultar otro tema → general
}


def _is_compound_legal_doc(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _LEGAL_TERMS) and any(t in msg for t in _DOC_TERMS)


def make_classify_intent_node(llm_client: ILlmClient):
    async def classify_intent(state: AgentState) -> dict:
        # Mejora #1: forzar onboarding hasta tener nombre Y distrito
        profile = state.get("user_profile") or {}
        if not profile.get("name") or not profile.get("district"):
            return {"intent": AgentIntent.ONBOARDING.value}

        msg = state["user_message"].strip()

        # Menú post-documento: opciones 1/2/3 después de generar carta
        if profile.get("awaiting_next_action"):
            if msg in _POST_DOC_MAP:
                intent = _POST_DOC_MAP[msg]
                updated_profile = {**profile, "awaiting_next_action": False}
                return {"intent": intent, "user_profile": updated_profile}

        # Menú post-onboarding: opciones 1/2/3/4 al terminar el onboarding
        if profile.get("conversation_stage") == "ACTIVE" and not profile.get("issue"):
            if msg in _POST_ONBOARDING_MAP:
                return {"intent": _POST_ONBOARDING_MAP[msg]}

        # Confirmación de generación de documento
        if profile.get("awaiting_doc_confirmation"):
            if any(p in msg.lower() for p in _AFIRMATIVO):
                return {"intent": AgentIntent.REDACTOR.value, "doc_confirmed": True}

        try:
            raw = await llm_client.generate(_SYSTEM_PROMPT, state["user_message"])
            intent = raw.strip().lower()
            if intent not in _VALID_INTENTS:
                intent = AgentIntent.GENERAL.value
        except Exception:
            intent = AgentIntent.GENERAL.value

        # Mejora #2: detectar intención compuesta legal + redactor
        if intent == AgentIntent.LEGAL.value and _is_compound_legal_doc(state["user_message"]):
            return {"intent": AgentIntent.LEGAL_REDACTOR.value}

        return {"intent": intent}

    return classify_intent
