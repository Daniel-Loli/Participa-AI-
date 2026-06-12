import pytest
from src.domain.value_objects.message_type import MessageType
from src.domain.value_objects.agent_intent import AgentIntent
from src.domain.value_objects.rag_collection import RagCollection


# --- MessageType ---

class TestMessageType:
    def test_text_value(self):
        assert MessageType("text") == MessageType.TEXT

    def test_audio_value(self):
        assert MessageType("audio") == MessageType.AUDIO

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MessageType("imagen")

    def test_values_are_strings(self):
        for member in MessageType:
            assert isinstance(member.value, str)

    def test_str_enum_is_string(self):
        # str, Enum hace que el miembro mismo sea un str
        assert isinstance(MessageType.TEXT, str)
        assert MessageType.TEXT == "text"


# --- AgentIntent ---

class TestAgentIntent:
    def test_all_valid_values(self):
        valid = ["onboarding", "menu", "legal", "legal_redactor", "estratega",
                 "oportunidades", "red", "redactor", "general"]
        for v in valid:
            assert AgentIntent(v).value == v

    def test_legal_value(self):
        assert AgentIntent("legal") == AgentIntent.LEGAL

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AgentIntent("invalido")

    def test_nine_members(self):
        assert len(AgentIntent) == 9

    def test_values_are_strings(self):
        for member in AgentIntent:
            assert isinstance(member.value, str)

    def test_str_enum_is_string(self):
        assert isinstance(AgentIntent.LEGAL, str)
        assert AgentIntent.LEGAL == "legal"


# --- RagCollection ---

class TestRagCollection:
    def test_all_valid_values(self):
        valid = ["legal", "ods", "procedimientos", "casos_exito"]
        for v in valid:
            assert RagCollection(v).value == v

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            RagCollection("otro")

    def test_four_members(self):
        assert len(RagCollection) == 4

    def test_values_are_strings(self):
        for member in RagCollection:
            assert isinstance(member.value, str)

    def test_str_enum_is_string(self):
        assert isinstance(RagCollection.LEGAL, str)
        assert RagCollection.LEGAL == "legal"


# --- Verificación de no-imports externos ---

def test_no_external_imports_in_value_objects():
    """Verifica que los módulos del dominio solo usan la librería estándar."""
    import importlib, sys
    mods = [
        "src.domain.value_objects.message_type",
        "src.domain.value_objects.agent_intent",
        "src.domain.value_objects.rag_collection",
    ]
    stdlib_prefix = ("enum", "builtins", "_")
    for mod_name in mods:
        mod = importlib.import_module(mod_name)
        for name, obj in vars(mod).items():
            if isinstance(obj, type(pytest)):  # es un módulo importado
                assert obj.__name__.startswith(stdlib_prefix), (
                    f"{mod_name} importa módulo externo: {obj.__name__}"
                )
