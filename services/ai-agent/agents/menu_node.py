from __future__ import annotations

from agents.state import AgentState

MAIN_MENU = (
    "1. ⚖️ Conocer mis derechos y leyes\n"
    "2. 🗺️ Ver qué acciones puedo tomar\n"
    "3. ✍️ Redactar una carta o solicitud\n"
    "4. 📅 Ver oportunidades en mi distrito\n"
    "5. 🤝 Conectar con organizaciones juveniles"
)


def make_menu_node():
    async def menu(state: AgentState) -> dict:
        profile = state.get("user_profile") or {}
        name = profile.get("name", "")
        lt_summary = state.get("lt_summary")

        # Saludo y resumen de la sesión anterior solo en el primer mensaje de una sesión
        # nueva — a mitad de conversación re-saludar y citar "Sesión anterior: hoy" confunde
        if state.get("is_new_session"):
            saludo = f"¡Hola de nuevo, {name}! 👋" if name else "¡Hola! 👋"
            contexto = f"\n\n_{lt_summary}_" if lt_summary else ""
            response = f"{saludo}{contexto}\n\n¿En qué te puedo ayudar hoy?\n\n{MAIN_MENU}"
        else:
            response = f"¿En qué te puedo ayudar?\n\n{MAIN_MENU}"

        return {
            "response": response,
            "skip_tone": True,
        }

    return menu
