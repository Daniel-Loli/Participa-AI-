from unittest.mock import AsyncMock, MagicMock

from agents.classify_intent import make_classify_intent_node


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "hola",
        "intent": None,
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "general") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    mock.generate_with_history = AsyncMock(return_value=response)
    return mock


# Perfil completo (nombre + distrito + etapa activa) — estado post-onboarding
_FULL_PROFILE = {"name": "Ana", "district": "Lima", "conversation_stage": "ACTIVE"}


class TestClassifyIntentNode:
    async def test_perfil_vacio_retorna_onboarding_sin_llamar_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={}))
        assert result["intent"] == "onboarding"
        mock_llm.generate_with_history.assert_not_called()

    async def test_perfil_sin_nombre_retorna_onboarding_sin_llamar_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"district": "Lima"}))
        assert result["intent"] == "onboarding"
        mock_llm.generate_with_history.assert_not_called()

    async def test_perfil_sin_distrito_retorna_onboarding(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_profile={"name": "Ana"}))
        assert result["intent"] == "onboarding"

    async def test_sin_issue_y_stage_onboarding_sigue_en_onboarding(self):
        # El "3" del menú de problemáticas NO debe capturarlo el menú principal
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="3",
            user_profile={"name": "Ana", "district": "Lima", "conversation_stage": "ONBOARDING"},
        ))
        assert result["intent"] == "onboarding"

    async def test_con_stage_active_sin_issue_clasifica_normal(self):
        # Usuario recurrente (perfil LT): stage ACTIVE sin issue → flujo normal
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="3",
            user_profile={"name": "Ana", "district": "Lima", "conversation_stage": "ACTIVE"},
        ))
        assert result["intent"] == "redactor"

    async def test_llm_responde_legal_retorna_legal(self):
        mock_llm = make_llm("legal")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="¿qué leyes me protegen?",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "legal"

    async def test_llm_responde_texto_invalido_fallback_general(self):
        mock_llm = make_llm("no sé")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="cuéntame algo",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "general"

    async def test_llm_responde_con_mayusculas_y_espacios_se_normaliza(self):
        mock_llm = make_llm("  LEGAL  ")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="¿qué normas existen?",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "legal"

    async def test_llm_responde_redactor_retorna_redactor(self):
        mock_llm = make_llm("redactor")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="ayúdame a preparar un escrito",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "redactor"

    async def test_excepcion_en_llm_fallback_general(self):
        mock_llm = MagicMock()
        mock_llm.generate_with_history = AsyncMock(side_effect=Exception("LLM error"))
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="cuéntame de los ODS",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "general"


class TestSaludoYMenu:
    async def test_saludo_corto_retorna_menu_sin_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_message="hola", user_profile=dict(_FULL_PROFILE)))
        assert result["intent"] == "menu"
        mock_llm.generate_with_history.assert_not_called()

    async def test_palabra_con_saludo_embebido_no_es_saludo(self):
        # "mi hijo sufre" contiene "hi" como substring pero no es saludo
        mock_llm = make_llm("general")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="mi hijo sufre",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "general"

    async def test_numero_menu_principal_traduce_a_texto(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_message="3", user_profile=dict(_FULL_PROFILE)))
        assert result["intent"] == "redactor"
        assert "redactar" in result["user_message"]


class TestConfirmacionDocumento:
    def _profile(self, **extra):
        return {**_FULL_PROFILE, "awaiting_doc_confirmation": True, **extra}

    async def test_afirmativo_redirige_a_redactor_confirmado(self):
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="sí, dale", user_profile=self._profile()))
        assert result["intent"] == "redactor"
        assert result["doc_confirmed"] is True

    async def test_palabra_con_si_embebido_no_confirma(self):
        # "sesión" contiene "si" como substring — no debe confirmar el documento
        node = make_classify_intent_node(make_llm("oportunidades"))
        result = await node(make_state(
            user_message="¿cuándo es la sesión municipal?",
            user_profile=self._profile(),
        ))
        assert result["intent"] != "redactor"
        assert result["user_profile"]["awaiting_doc_confirmation"] is False

    async def test_negativa_limpia_flag_y_muestra_menu(self):
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="no", user_profile=self._profile()))
        assert result["intent"] == "menu"
        assert result["user_profile"]["awaiting_doc_confirmation"] is False

    async def test_opcion_2_del_confirm_no_va_a_estratega(self):
        # "2" durante confirmación significa "No" — no debe mapear al menú principal
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="2", user_profile=self._profile()))
        assert result["intent"] == "menu"
        assert result["user_profile"]["awaiting_doc_confirmation"] is False


class TestMenuPostDocumento:
    def _profile(self):
        return {**_FULL_PROFILE, "awaiting_next_action": True}

    async def test_opcion_1_va_a_estratega_con_texto_traducido(self):
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="1", user_profile=self._profile()))
        assert result["intent"] == "estratega"
        assert "mesa de partes" in result["user_message"]
        assert result["user_profile"]["awaiting_next_action"] is False

    async def test_texto_libre_limpia_flag_y_clasifica_normal(self):
        node = make_classify_intent_node(make_llm("legal"))
        result = await node(make_state(
            user_message="¿qué dice la ley sobre el presupuesto?",
            user_profile=self._profile(),
        ))
        assert result["intent"] == "legal"
        assert result["user_profile"]["awaiting_next_action"] is False


class TestContinuacionAfirmativa:
    """Un "sí" suelto tras una oferta del bot debe volver al nodo anterior,
    no al clasificador LLM (que tiende a resetear al menú)."""

    def _profile(self, last_intent="estratega"):
        return {**_FULL_PROFILE, "last_intent": last_intent}

    async def test_si_suelto_vuelve_al_nodo_anterior_sin_llm(self):
        mock_llm = make_llm()
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_message="Si", user_profile=self._profile()))
        assert result["intent"] == "estratega"
        mock_llm.generate_with_history.assert_not_called()

    async def test_a_ver_continua_con_el_nodo_anterior(self):
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="A ver", user_profile=self._profile("general")))
        assert result["intent"] == "general"

    async def test_dale_continua_con_red(self):
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="dale", user_profile=self._profile("red")))
        assert result["intent"] == "red"

    async def test_si_sin_last_intent_clasifica_con_llm(self):
        mock_llm = make_llm("general")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(user_message="sí", user_profile=dict(_FULL_PROFILE)))
        assert result["intent"] == "general"
        mock_llm.generate_with_history.assert_called_once()

    async def test_numero_de_menu_gana_sobre_continuacion(self):
        # "1" como mensaje suelto es selección de menú, no un "sí"
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(user_message="1", user_profile=self._profile()))
        assert result["intent"] == "legal"

    async def test_mensaje_largo_con_si_no_es_continuacion(self):
        # "sí, pero cuéntame sobre las leyes de presupuesto" tiene contenido propio → LLM
        mock_llm = make_llm("legal")
        node = make_classify_intent_node(mock_llm)
        result = await node(make_state(
            user_message="sí, pero mejor cuéntame sobre las leyes de presupuesto",
            user_profile=self._profile(),
        ))
        assert result["intent"] == "legal"
        mock_llm.generate_with_history.assert_called_once()

    async def test_confirmacion_de_documento_tiene_prioridad(self):
        # awaiting_doc_confirmation gana sobre la continuación genérica
        node = make_classify_intent_node(make_llm())
        result = await node(make_state(
            user_message="sí",
            user_profile={**self._profile(), "awaiting_doc_confirmation": True},
        ))
        assert result["intent"] == "redactor"
        assert result["doc_confirmed"] is True


class TestIntencionCompuesta:
    async def test_ley_mas_carta_activa_legal_redactor(self):
        node = make_classify_intent_node(make_llm("legal"))
        result = await node(make_state(
            user_message="¿qué ley me protege? quiero redactar una carta",
            user_profile=dict(_FULL_PROFILE),
        ))
        assert result["intent"] == "legal_redactor"
