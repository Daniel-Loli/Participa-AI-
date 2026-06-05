from __future__ import annotations

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient
from src.domain.value_objects.agent_intent import AgentIntent

_SYSTEM_PROMPT = """Clasifica la intención del ÚLTIMO mensaje de un usuario joven peruano.
Usa el contexto de los mensajes anteriores para interpretar preguntas como "¿y qué más?", "continúa", "explícame eso", "¿cómo lo hago?".
Responde con UNA SOLA PALABRA de esta lista: onboarding, menu, legal, estratega, oportunidades, red, redactor, general

Ejemplos:
"¿qué leyes me protegen?" → legal
"ayúdame a redactar una carta" → redactor
"hola, quiero participar" (sin perfil) → onboarding
"¿cuándo es la próxima sesión municipal?" → oportunidades
"¿hay organizaciones en mi zona?" → red
"¿cómo planteo mi queja a la municipalidad?" → estratega
"¿qué es el ODS 16?" → general
"hola" / "buenas" / "¿en qué me ayudas?" → menu
"¿y qué más puedo hacer?" (luego de hablar de estrategia) → estratega
"¿cómo lo presento?" (luego de hablar de un documento) → redactor"""

_VALID_INTENTS = {i.value for i in AgentIntent}

# Palabras clave para intención compuesta legal + documento
_DOC_TERMS  = {"carta", "redactar", "solicitud", "documento", "escrib", "generar", "genera"}
_LEGAL_TERMS = {"ley", "leyes", "legal", "derecho", "derechos", "artículo", "norma", "normativa"}

# Respuestas afirmativas para confirmar generación de documento
_AFIRMATIVO = {"si", "sí", "dale", "ok", "okay", "claro", "yes", "hazlo",
               "bueno", "adelante", "genérala", "generala", "1"}

# Menú principal — 5 opciones consistentes en todo el flujo
MAIN_MENU_MAP = {
    "1": AgentIntent.LEGAL.value,
    "2": AgentIntent.ESTRATEGA.value,
    "3": AgentIntent.REDACTOR.value,
    "4": AgentIntent.OPORTUNIDADES.value,
    "5": AgentIntent.RED.value,
}

# Traducción del número al texto real de la intención (para que el nodo sepa qué quiere el usuario)
_MAIN_MENU_TEXT = {
    "1": "Quiero conocer mis derechos y las leyes que me protegen",
    "2": "Quiero saber qué acciones concretas puedo tomar en mi comunidad",
    "3": "Quiero redactar una carta o solicitud formal",
    "4": "Quiero ver oportunidades de participación en mi distrito",
    "5": "Quiero conectar con organizaciones juveniles en mi zona",
}

# Menú post-documento (3 opciones)
_POST_DOC_MAP = {
    "1": AgentIntent.ESTRATEGA.value,
    "2": AgentIntent.RED.value,
    "3": AgentIntent.GENERAL.value,
}

# Saludos cortos → mostrar menú
_SALUDOS = {"hola", "buenas", "buenos", "hey", "hi", "ola", "saludos"}
_MENU_TRIGGERS = {"ayudarme", "ayudarte", "qué puedes", "que puedes",
                  "opciones", "menú", "menu", "en qué más", "en que mas"}


def _is_compound_legal_doc(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _LEGAL_TERMS) and any(t in msg for t in _DOC_TERMS)


def _is_saludo(message: str) -> bool:
    msg = message.lower().strip()
    return len(msg.split()) <= 4 and any(s in msg for s in _SALUDOS)


def _wants_menu(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _MENU_TRIGGERS)


def make_classify_intent_node(llm_client: ILlmClient):
    async def classify_intent(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}

        # 1. Forzar onboarding hasta tener nombre Y distrito
        if not profile.get("name") or not profile.get("district"):
            return {"intent": AgentIntent.ONBOARDING.value}

        msg = state["user_message"].strip()

        # 2. Menú post-documento (awaiting_next_action)
        if profile.get("awaiting_next_action"):
            if msg in _POST_DOC_MAP:
                updated_profile = {**profile, "awaiting_next_action": False}
                return {"intent": _POST_DOC_MAP[msg], "user_profile": updated_profile}

        # 3. Confirmación de generación de documento
        if profile.get("awaiting_doc_confirmation"):
            if any(p in msg.lower() for p in _AFIRMATIVO):
                return {"intent": AgentIntent.REDACTOR.value, "doc_confirmed": True}

        # 4. Selección numerada del menú principal (1-5)
        # Se traduce el número a texto para que el nodo destino entienda la intención real
        if msg in MAIN_MENU_MAP:
            return {
                "intent": MAIN_MENU_MAP[msg],
                "user_message": _MAIN_MENU_TEXT[msg],
            }

        # 5. Saludo corto o solicitud de menú → mostrar menú principal
        if _is_saludo(msg) or _wants_menu(msg):
            return {"intent": AgentIntent.MENU.value}

        # 6. Clasificación por LLM — con contexto de los últimos 4 mensajes
        history_tail = state.get("conversation_history", [])[-4:]
        try:
            raw = await llm_client.generate_with_history(_SYSTEM_PROMPT, history_tail)
            intent = raw.strip().lower()
            if intent not in _VALID_INTENTS:
                intent = AgentIntent.GENERAL.value
        except Exception:
            intent = AgentIntent.GENERAL.value

        # 7. Intención compuesta legal + redactor
        if intent == AgentIntent.LEGAL.value and _is_compound_legal_doc(state["user_message"]):
            return {"intent": AgentIntent.LEGAL_REDACTOR.value}

        return {"intent": intent}

    return classify_intent
