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


def make_classify_intent_node(llm_client: ILlmClient):
    async def classify_intent(state: AgentState) -> dict:
        if not (state.get("user_profile") or {}).get("name"):
            return {"intent": AgentIntent.ONBOARDING.value}

        try:
            raw = await llm_client.generate(_SYSTEM_PROMPT, state["user_message"])
            intent = raw.strip().lower()
            if intent not in _VALID_INTENTS:
                intent = AgentIntent.GENERAL.value
        except Exception:
            intent = AgentIntent.GENERAL.value

        return {"intent": intent}

    return classify_intent
