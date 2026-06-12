from agents.menu_node import make_menu_node, MAIN_MENU


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "hola",
        "intent": "menu",
        "user_profile": {"name": "Ana", "district": "Lima"},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


class TestMenuNode:
    async def test_sesion_nueva_saluda_y_muestra_resumen_anterior(self):
        node = make_menu_node()
        result = await node(make_state(
            is_new_session=True,
            lt_summary="Sesión anterior (2026-06-05): Ana de Lima trabajó seguridad.",
        ))
        assert "¡Hola de nuevo, Ana!" in result["response"]
        assert "Sesión anterior (2026-06-05)" in result["response"]
        assert MAIN_MENU in result["response"]

    async def test_mitad_de_conversacion_no_saluda_ni_muestra_resumen(self):
        # Mostrar "Sesión anterior (hoy)" a mitad de conversación confunde al usuario
        node = make_menu_node()
        result = await node(make_state(
            is_new_session=False,
            lt_summary="Sesión anterior (2026-06-12): Ana de Lima trabajó seguridad.",
        ))
        assert "Hola" not in result["response"]
        assert "Sesión anterior" not in result["response"]
        assert MAIN_MENU in result["response"]

    async def test_menu_es_plantilla_sin_revision_de_tono(self):
        node = make_menu_node()
        result = await node(make_state(is_new_session=True))
        assert result["skip_tone"] is True
