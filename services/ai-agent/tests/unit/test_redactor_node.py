import json
from unittest.mock import AsyncMock, MagicMock

from agents.redactor_node import make_redactor_node, _detect_doc_type


def make_state(**kwargs):
    base = {
        "session_id": "s1",
        "user_message": "quiero redactar una carta",
        "intent": "redactor",
        "user_profile": {},
        "rag_context": [],
        "tool_data": {},
        "response": "",
        "conversation_history": [],
        "doc_confirmed": False,
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Carta formal generada.") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    mock.generate_with_history = AsyncMock(return_value=response)
    return mock


_MUNICIPIOS = [
    {
        "distrito": "Miraflores",
        "funcionario": "Luis Molina",
        "cargo": "Alcalde",
        "municipio": "Municipalidad de Miraflores",
        "mesa_partes": "Av. Larco 400",
    }
]


class TestDetectDocType:
    def test_carta_por_defecto(self):
        assert _detect_doc_type("hola quiero hacer algo") == "carta"

    def test_detecta_carta(self):
        assert _detect_doc_type("necesito redactar una carta al alcalde") == "carta"

    def test_detecta_solicitud(self):
        assert _detect_doc_type("quiero hacer una solicitud de información") == "solicitud"

    def test_detecta_propuesta(self):
        assert _detect_doc_type("voy a presentar una propuesta de PP") == "propuesta"

    def test_detecta_presupuesto_participativo(self):
        assert _detect_doc_type("quiero postular al presupuesto participativo") == "propuesta"

    def test_detecta_inscripcion(self):
        assert _detect_doc_type("necesito una inscripción en la mesa") == "inscripcion"


class TestRedactorConfirmacion:
    """Sin doc_confirmed, el nodo pide confirmación y NO genera el documento."""

    async def test_sin_confirmacion_pide_confirmar_sin_llamar_llm(self, tmp_path):
        mock_llm = make_llm()
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="quiero redactar una carta de queja",
            user_profile={"name": "Ana", "district": "Miraflores"},
        ))
        mock_llm.generate_with_history.assert_not_called()
        assert "confirma" in result["response"].lower()
        assert result["user_profile"]["awaiting_doc_confirmation"] is True
        assert result["user_profile"]["pending_doc_type"] == "carta"
        assert "pdf_base64" not in result

    async def test_confirmacion_pendiente_guarda_tipo_solicitud(self, tmp_path):
        node = make_redactor_node(make_llm(), data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="quiero hacer una solicitud de información",
            user_profile={"name": "Ana", "district": "Lima"},
        ))
        assert result["user_profile"]["pending_doc_type"] == "solicitud"


class TestRedactorGeneracion:
    """Con doc_confirmed=True, el nodo genera el documento y el PDF."""

    async def test_mensaje_carta_perfil_completo_genera_documento(self, tmp_path):
        (tmp_path / "municipios.json").write_text(json.dumps(_MUNICIPIOS))
        mock_llm = make_llm("Estimado Alcalde, por medio del presente...")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="sí, genérala",
            doc_confirmed=True,
            user_profile={
                "name": "Ana García", "district": "Miraflores",
                "issue": "basura", "pending_doc_type": "carta",
            },
        ))
        system_prompt = mock_llm.generate_with_history.call_args[0][0]
        assert "Ana García" in system_prompt
        assert "Miraflores" in system_prompt
        assert "basura" in system_prompt
        assert "Luis Molina" in system_prompt
        assert result["pdf_base64"]
        assert result["pdf_filename"].endswith(".pdf")

    async def test_usa_tipo_pendiente_del_turno_anterior(self, tmp_path):
        # El mensaje de confirmación ("sí") no menciona el tipo — debe usar pending_doc_type
        (tmp_path / "municipios.json").write_text("[]")
        node = make_redactor_node(make_llm(), data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="sí",
            doc_confirmed=True,
            user_profile={"name": "Ana", "district": "Lima", "pending_doc_type": "solicitud"},
        ))
        assert result["tool_data"]["tipo_documento"] == "solicitud"
        assert result["user_profile"]["pending_doc_type"] is None

    async def test_municipios_ausente_genera_sin_datos_oficial(self, tmp_path):
        mock_llm = make_llm("Documento generado.")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(
            doc_confirmed=True,
            user_profile={"name": "Carlos", "district": "Lima"},
        ))
        system_prompt = mock_llm.generate_with_history.call_args[0][0]
        assert "Señor/a Alcalde/sa" in system_prompt
        assert "Documento generado." in result["response"]

    async def test_tipo_documento_guardado_en_tool_data(self, tmp_path):
        (tmp_path / "municipios.json").write_text("[]")
        node = make_redactor_node(make_llm(), data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="quiero hacer una solicitud",
            doc_confirmed=True,
        ))
        assert result["tool_data"]["tipo_documento"] == "solicitud"

    async def test_respuesta_incluye_menu_post_documento(self, tmp_path):
        (tmp_path / "municipios.json").write_text("[]")
        mock_llm = make_llm("Carta generada exitosamente.")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(doc_confirmed=True))
        assert "Carta generada exitosamente." in result["response"]
        assert result["user_profile"]["awaiting_next_action"] is True

    async def test_fecha_en_espanol_sin_locale(self, tmp_path):
        # La fecha del documento debe ir en español aunque el locale sea C
        (tmp_path / "municipios.json").write_text("[]")
        mock_llm = make_llm()
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        await node(make_state(doc_confirmed=True))
        system_prompt = mock_llm.generate_with_history.call_args[0][0]
        meses_en = ["January", "February", "March", "April", "May", "June", "July",
                    "August", "September", "October", "November", "December"]
        assert not any(m in system_prompt for m in meses_en)
