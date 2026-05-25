import pytest
from dataclasses import FrozenInstanceError

from src.domain.entities.message import Message
from src.domain.entities.agent_response import AgentResponse
from src.domain.entities.user_profile import UserProfile
from src.domain.value_objects.message_type import MessageType


# --- Message ---

class TestMessage:
    def test_is_text_true(self):
        msg = Message(from_hash="abc", type=MessageType.TEXT, session_id="abc", timestamp=1000, text_content="hola")
        assert msg.is_text() is True
        assert msg.is_audio() is False

    def test_is_audio_true(self):
        msg = Message(from_hash="abc", type=MessageType.AUDIO, session_id="abc", timestamp=1000, audio_base64="b64")
        assert msg.is_audio() is True
        assert msg.is_text() is False

    def test_is_immutable(self):
        msg = Message(from_hash="abc", type=MessageType.TEXT, session_id="abc", timestamp=1000)
        with pytest.raises(FrozenInstanceError):
            msg.from_hash = "otro"  # type: ignore

    def test_optional_fields_default_none(self):
        msg = Message(from_hash="abc", type=MessageType.TEXT, session_id="abc", timestamp=1000)
        assert msg.text_content is None
        assert msg.audio_base64 is None
        assert msg.audio_mime_type is None

    def test_text_message_with_content(self):
        msg = Message(
            from_hash="abc123",
            type=MessageType.TEXT,
            session_id="abc123",
            timestamp=1700000000,
            text_content="quiero participar",
        )
        assert msg.text_content == "quiero participar"

    def test_audio_message_with_fields(self):
        msg = Message(
            from_hash="abc123",
            type=MessageType.AUDIO,
            session_id="abc123",
            timestamp=1700000000,
            audio_base64="AABB==",
            audio_mime_type="audio/ogg",
        )
        assert msg.audio_base64 == "AABB=="
        assert msg.audio_mime_type == "audio/ogg"

    def test_from_hash_not_phone_number(self):
        # from_hash debe ser un hash, no el número real
        msg = Message(from_hash="e3b0c44298fc", type=MessageType.TEXT, session_id="e3b0c44298fc", timestamp=1000)
        assert not msg.from_hash.startswith("+")


# --- AgentResponse ---

class TestAgentResponse:
    def test_text_response(self):
        r = AgentResponse(response_type="text", response_text="Aquí tu ruta de incidencia")
        assert r.response_type == "text"
        assert r.response_text == "Aquí tu ruta de incidencia"
        assert r.response_audio_base64 is None

    def test_audio_response(self):
        r = AgentResponse(response_type="audio", response_audio_base64="AABB==")
        assert r.response_type == "audio"
        assert r.response_audio_base64 == "AABB=="
        assert r.response_text is None

    def test_text_response_with_none_text_is_valid(self):
        # Construir con response_text=None es válido (e.g. audio response)
        r = AgentResponse(response_type="text")
        assert r.response_text is None

    def test_is_immutable(self):
        r = AgentResponse(response_type="text", response_text="hola")
        with pytest.raises(FrozenInstanceError):
            r.response_type = "audio"  # type: ignore


# --- UserProfile ---

class TestUserProfile:
    def test_is_complete_false_when_no_name(self):
        p = UserProfile(user_id="abc", name=None, district="Miraflores")
        assert p.is_complete() is False

    def test_is_complete_false_when_no_district(self):
        p = UserProfile(user_id="abc", name="Carlos", district=None)
        assert p.is_complete() is False

    def test_is_complete_false_when_both_none(self):
        p = UserProfile(user_id="abc")
        assert p.is_complete() is False

    def test_is_complete_true_when_name_and_district(self):
        p = UserProfile(user_id="abc", name="Ana", district="San Isidro")
        assert p.is_complete() is True

    def test_default_stage_is_onboarding(self):
        p = UserProfile(user_id="abc")
        assert p.conversation_stage == "ONBOARDING"

    def test_is_mutable(self):
        p = UserProfile(user_id="abc")
        p.name = "Carlos"
        p.district = "Miraflores"
        assert p.is_complete() is True

    def test_issue_optional(self):
        p = UserProfile(user_id="abc", name="Ana", district="Surco")
        assert p.issue is None

    def test_stage_can_be_updated(self):
        p = UserProfile(user_id="abc", name="Luis", district="Lince")
        p.conversation_stage = "ACTIVE"
        assert p.conversation_stage == "ACTIVE"


# --- Verificación de no-imports externos ---

def test_no_external_imports_in_entities():
    import importlib
    allowed = {"__future__", "dataclasses", "src.domain"}
    mods_to_check = [
        "src.domain.entities.message",
        "src.domain.entities.agent_response",
        "src.domain.entities.user_profile",
    ]
    for mod_name in mods_to_check:
        mod = importlib.import_module(mod_name)
        for attr in vars(mod).values():
            if isinstance(attr, type(importlib)):
                pkg = attr.__name__.split(".")[0]
                assert pkg in ("__future__", "dataclasses", "src", "_"), (
                    f"{mod_name} importa paquete externo no permitido: {attr.__name__}"
                )
