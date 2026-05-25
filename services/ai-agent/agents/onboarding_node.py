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


def make_onboarding_node(llm_client: ILlmClient):
    async def onboarding(state: AgentState) -> dict:
        profile = dict(state.get("user_profile") or {})

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

        if not profile.get("name"):
            response = "¡Hola! Soy Participa AI. ¿Cómo te llamas?"
        elif not profile.get("district"):
            response = f"¡Hola {profile['name']}! ¿De qué distrito eres? Así te ayudo mejor."
        else:
            profile["conversation_stage"] = "ACTIVE"
            response = (
                f"¡Perfecto {profile['name']} de {profile['district']}! "
                "¿Cuál es la problemática que más te preocupa en tu comunidad?"
            )

        return {
            "response": response,
            "user_profile": profile,
            "conversation_history": [AIMessage(content=response)],
        }

    return onboarding
