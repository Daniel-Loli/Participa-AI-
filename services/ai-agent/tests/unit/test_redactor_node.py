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
    }
    base.update(kwargs)
    return base


def make_llm(response: str = "Carta formal generada.") -> MagicMock:
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
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


class TestRedactorNode:
    async def test_mensaje_carta_perfil_completo_genera_documento(self, tmp_path):
        (tmp_path / "municipios.json").write_text(json.dumps(_MUNICIPIOS))
        mock_llm = make_llm("Estimado Alcalde, por medio del presente...")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(
            user_message="quiero redactar una carta de queja",
            user_profile={"name": "Ana García", "district": "Miraflores", "issue": "basura"},
        ))
        system_prompt = mock_llm.generate.call_args[0][0]
        assert "Ana García" in system_prompt
        assert "Miraflores" in system_prompt
        assert "basura" in system_prompt
        assert "Luis Molina" in system_prompt

    async def test_municipios_ausente_genera_sin_datos_oficial(self, tmp_path):
        mock_llm = make_llm("Documento generado.")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state(
            user_profile={"name": "Carlos", "district": "Lima"},
        ))
        system_prompt = mock_llm.generate.call_args[0][0]
        assert "Señor/a Alcalde/sa" in system_prompt
        assert result["response"] == "Documento generado."

    async def test_tipo_documento_guardado_en_tool_data(self, tmp_path):
        (tmp_path / "municipios.json").write_text("[]")
        node = make_redactor_node(make_llm(), data_dir=str(tmp_path))
        result = await node(make_state(user_message="quiero hacer una solicitud"))
        assert result["tool_data"]["tipo_documento"] == "solicitud"

    async def test_respuesta_guardada_en_response(self, tmp_path):
        (tmp_path / "municipios.json").write_text("[]")
        mock_llm = make_llm("Carta generada exitosamente.")
        node = make_redactor_node(mock_llm, data_dir=str(tmp_path))
        result = await node(make_state())
        assert result["response"] == "Carta generada exitosamente."
