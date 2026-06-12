from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

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

# Respuestas afirmativas para confirmar generación de documento (comparación por palabra completa)
_AFIRMATIVO = {"si", "sí", "dale", "ok", "okay", "claro", "yes", "hazlo",
               "bueno", "adelante", "genérala", "generala", "1"}

# Respuestas negativas a la confirmación de documento
_NEGATIVO = {"no", "2", "nop", "todavía", "todavia", "aún", "aun", "espera", "cancelar", "cancela"}

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

# Menú post-documento (3 opciones) — también se traduce a texto real
# La opción 3 ("consultar otro tema") vuelve al menú principal
_POST_DOC_MAP = {
    "1": AgentIntent.ESTRATEGA.value,
    "2": AgentIntent.RED.value,
    "3": AgentIntent.MENU.value,
}

_POST_DOC_TEXT = {
    "1": "¿Cómo presento mi documento en la mesa de partes de la municipalidad?",
    "2": "Quiero ver organizaciones juveniles de apoyo en mi distrito",
    "3": "Quiero consultar otro tema de participación ciudadana",
}

# Saludos cortos → mostrar menú (comparación por palabra completa, no substring)
_SALUDOS = {"hola", "buenas", "buenos", "hey", "hi", "ola", "saludos"}
_MENU_TRIGGERS = {"ayudarme", "ayudarte", "qué puedes", "que puedes",
                  "opciones", "menú", "menu", "en qué más", "en que mas"}


def _tokens(message: str) -> set[str]:
    """Extrae palabras normalizadas del mensaje (sin signos de puntuación)."""
    return set(re.findall(r"[a-záéíóúüñ0-9]+", message.lower()))


def _is_compound_legal_doc(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _LEGAL_TERMS) and any(t in msg for t in _DOC_TERMS)


def _is_saludo(message: str) -> bool:
    words = _tokens(message)
    return len(message.split()) <= 4 and bool(words & _SALUDOS)


def _wants_menu(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _MENU_TRIGGERS)


def _is_afirmativo(message: str) -> bool:
    return bool(_tokens(message) & _AFIRMATIVO)


def _is_negativo(message: str) -> bool:
    return bool(_tokens(message) & _NEGATIVO)


def _rewrite_last_human_message(state: AgentState, new_text: str) -> list:
    """Reemplaza el contenido del último HumanMessage del historial.

    Cuando el usuario escribe un número de menú ("1"), el historial guarda "1";
    al traducirlo a texto real también actualizamos el historial para que los
    nodos y el LLM vean la intención real y no un número suelto.
    """
    history = state.get("conversation_history") or []
    if history and isinstance(history[-1], HumanMessage) and history[-1].id:
        return [HumanMessage(content=new_text, id=history[-1].id)]
    return []


def make_classify_intent_node(llm_client: ILlmClient):
    async def classify_intent(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}

        # 1. Forzar onboarding hasta tener nombre Y distrito
        if not profile.get("name") or not profile.get("district"):
            return {"intent": AgentIntent.ONBOARDING.value}

        # 1b. Onboarding aún activo (falta la problemática): el siguiente mensaje
        # responde al menú de problemáticas — sin esto, "3" lo capturaría el menú principal
        if not profile.get("issue") and profile.get("conversation_stage") != "ACTIVE":
            return {"intent": AgentIntent.ONBOARDING.value}

        msg = state["user_message"].strip()

        # 2. Menú post-documento (awaiting_next_action)
        if profile.get("awaiting_next_action"):
            updated_profile = {**profile, "awaiting_next_action": False}
            if msg in _POST_DOC_MAP:
                translated = _POST_DOC_TEXT[msg]
                return {
                    "intent": _POST_DOC_MAP[msg],
                    "user_message": translated,
                    "user_profile": updated_profile,
                    "conversation_history": _rewrite_last_human_message(state, translated),
                }
            # Escribió otra cosa: limpiar el flag y seguir con la clasificación normal
            profile = updated_profile

        # 3. Confirmación de generación de documento
        if profile.get("awaiting_doc_confirmation"):
            if _is_afirmativo(msg):
                return {
                    "intent": AgentIntent.REDACTOR.value,
                    "doc_confirmed": True,
                    "user_profile": profile,
                }
            # Negativa explícita o cualquier otro mensaje: limpiar el flag.
            # Una negativa pura ("no", "2") vuelve al menú; otro texto se clasifica normal.
            profile = {**profile, "awaiting_doc_confirmation": False, "pending_doc_type": None}
            if _is_negativo(msg) and len(msg.split()) <= 6:
                return {"intent": AgentIntent.MENU.value, "user_profile": profile}

        # 4. Selección numerada del menú principal (1-5)
        # Se traduce el número a texto para que el nodo destino entienda la intención real
        if msg in MAIN_MENU_MAP:
            translated = _MAIN_MENU_TEXT[msg]
            return {
                "intent": MAIN_MENU_MAP[msg],
                "user_message": translated,
                "user_profile": profile,
                "conversation_history": _rewrite_last_human_message(state, translated),
            }

        # 5. Saludo corto o solicitud de menú → mostrar menú principal
        if _is_saludo(msg) or _wants_menu(msg):
            return {"intent": AgentIntent.MENU.value, "user_profile": profile}

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
            return {"intent": AgentIntent.LEGAL_REDACTOR.value, "user_profile": profile}

        return {"intent": intent, "user_profile": profile}

    return classify_intent
