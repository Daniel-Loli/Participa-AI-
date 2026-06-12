import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.errors import OrchestratorError, SttTranscriptionError
from src.application.use_cases.process_message import ProcessMessageUseCase
from src.domain.entities.message import Message
from src.domain.entities.user_profile import UserProfile
from src.domain.value_objects.message_type import MessageType


def make_text_message(**kwargs):
    base = {
        "from_hash": "abc123",
        "type": MessageType.TEXT,
        "session_id": "session-1",
        "timestamp": 1700000000,
        "text_content": "¿qué leyes me protegen?",
    }
    base.update(kwargs)
    return Message(**base)


def make_audio_message(**kwargs):
    base = {
        "from_hash": "abc123",
        "type": MessageType.AUDIO,
        "session_id": "session-1",
        "timestamp": 1700000000,
        "audio_base64": base64.b64encode(b"fake-audio").decode(),
        "audio_mime_type": "audio/ogg",
    }
    base.update(kwargs)
    return Message(**base)


def make_orchestrator(response_text="Respuesta del agente.", session_id="session-1"):
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value={
        "session_id": session_id,
        "user_message": "texto",
        "intent": "legal",
        "user_profile": {"name": "Ana", "district": "Lima"},
        "rag_context": [],
        "tool_data": {},
        "response": response_text,
        "conversation_history": [],
    })
    return mock


def make_stt(transcript="texto transcrito"):
    mock = MagicMock()
    mock.transcribe = AsyncMock(return_value=transcript)
    return mock


def make_tts(audio_bytes=b"fake-mp3"):
    mock = MagicMock()
    mock.synthesize = AsyncMock(return_value=audio_bytes)
    return mock


def make_session_store(profile=None):
    mock = MagicMock()
    mock.get_profile = AsyncMock(return_value=profile)
    mock.save_profile = AsyncMock()
    return mock


def make_lt_store(profile=None):
    mock = MagicMock()
    mock.get_profile = AsyncMock(return_value=profile)
    mock.save_profile = AsyncMock()
    return mock


def make_use_case(stt=None, tts=None, session_store=None, lt_store=None, orchestrator=None):
    return ProcessMessageUseCase(
        stt_client=stt or make_stt(),
        tts_client=tts or make_tts(),
        session_store=session_store or make_session_store(),
        lt_store=lt_store or make_lt_store(),
        orchestrator=orchestrator or make_orchestrator(),
    )


class TestProcessMessageUseCase:
    async def test_mensaje_texto_no_llama_stt(self):
        mock_stt = make_stt()
        use_case = make_use_case(stt=mock_stt)
        await use_case.execute(make_text_message())
        mock_stt.transcribe.assert_not_called()

    async def test_mensaje_texto_retorna_respuesta_texto(self):
        use_case = make_use_case(orchestrator=make_orchestrator("Hola!"))
        result = await use_case.execute(make_text_message())
        assert result.response_type == "text"
        assert result.response_text == "Hola!"

    async def test_mensaje_texto_no_llama_tts(self):
        mock_tts = make_tts()
        use_case = make_use_case(tts=mock_tts)
        await use_case.execute(make_text_message())
        mock_tts.synthesize.assert_not_called()

    async def test_mensaje_audio_llama_stt_primero(self):
        mock_stt = make_stt("texto transcrito")
        mock_orch = make_orchestrator()
        use_case = make_use_case(stt=mock_stt, orchestrator=mock_orch)
        await use_case.execute(make_audio_message())
        mock_stt.transcribe.assert_called_once()

    async def test_mensaje_audio_pasa_transcript_al_grafo(self):
        mock_stt = make_stt("mi consulta transcrita")
        mock_orch = make_orchestrator()
        use_case = make_use_case(stt=mock_stt, orchestrator=mock_orch)
        await use_case.execute(make_audio_message())
        call_args = mock_orch.ainvoke.call_args
        state_arg = call_args[0][0]
        assert state_arg["user_message"] == "mi consulta transcrita"

    async def test_mensaje_audio_llama_tts_con_respuesta_del_grafo(self):
        mock_tts = make_tts(b"mp3-bytes")
        mock_orch = make_orchestrator("Respuesta para TTS.")
        use_case = make_use_case(tts=mock_tts, orchestrator=mock_orch)
        await use_case.execute(make_audio_message())
        mock_tts.synthesize.assert_called_once_with("Respuesta para TTS.")

    async def test_mensaje_audio_retorna_audio_base64(self):
        mp3_bytes = b"fake-mp3-audio"
        mock_tts = make_tts(mp3_bytes)
        use_case = make_use_case(tts=mock_tts, orchestrator=make_orchestrator("resp"))
        result = await use_case.execute(make_audio_message())
        assert result.response_type == "audio"
        assert result.response_audio_base64 == base64.b64encode(mp3_bytes).decode()

    async def test_stt_falla_propaga_stt_transcription_error(self):
        mock_stt = make_stt()
        mock_stt.transcribe = AsyncMock(side_effect=Exception("Whisper falló"))
        use_case = make_use_case(stt=mock_stt)
        with pytest.raises(SttTranscriptionError):
            await use_case.execute(make_audio_message())

    async def test_tts_falla_fallback_a_texto_sin_excepcion(self):
        mock_tts = make_tts()
        mock_tts.synthesize = AsyncMock(side_effect=Exception("TTS no disponible"))
        use_case = make_use_case(tts=mock_tts, orchestrator=make_orchestrator("Respuesta."))
        result = await use_case.execute(make_audio_message())
        assert result.response_type == "text"
        assert result.response_text == "Respuesta."

    async def test_redis_falla_ejecuta_con_perfil_vacio(self):
        mock_store = make_session_store()
        mock_store.get_profile = AsyncMock(side_effect=Exception("Redis no disponible"))
        mock_orch = make_orchestrator()
        use_case = make_use_case(session_store=mock_store, orchestrator=mock_orch)
        result = await use_case.execute(make_text_message())
        call_args = mock_orch.ainvoke.call_args
        state_arg = call_args[0][0]
        assert state_arg["user_profile"] == {}
        assert result is not None

    async def test_orquestador_falla_lanza_orchestrator_error(self):
        mock_orch = make_orchestrator()
        mock_orch.ainvoke = AsyncMock(side_effect=Exception("LangGraph falló"))
        use_case = make_use_case(orchestrator=mock_orch)
        with pytest.raises(OrchestratorError):
            await use_case.execute(make_text_message())

    async def test_grafo_invocado_con_thread_id_correcto(self):
        mock_orch = make_orchestrator(session_id="mi-sesion")
        use_case = make_use_case(orchestrator=mock_orch)
        await use_case.execute(make_text_message(session_id="mi-sesion"))
        _, kwargs = mock_orch.ainvoke.call_args
        assert kwargs["config"]["configurable"]["thread_id"] == "mi-sesion"

    async def test_perfil_guardado_tras_invocar_grafo(self):
        mock_store = make_session_store()
        use_case = make_use_case(session_store=mock_store)
        await use_case.execute(make_text_message())
        mock_store.save_profile.assert_called_once()

    async def test_perfil_de_redis_se_pasa_al_grafo(self):
        profile = UserProfile(user_id="session-1", name="Carlos", district="Miraflores")
        mock_store = make_session_store(profile=profile)
        mock_orch = make_orchestrator()
        use_case = make_use_case(session_store=mock_store, orchestrator=mock_orch)
        await use_case.execute(make_text_message())
        call_args = mock_orch.ainvoke.call_args
        state_arg = call_args[0][0]
        assert state_arg["user_profile"]["name"] == "Carlos"
        assert state_arg["user_profile"]["district"] == "Miraflores"

    async def test_perfil_vacio_no_llama_save(self):
        mock_orch = MagicMock()
        mock_orch.ainvoke = AsyncMock(return_value={
            "session_id": "s1",
            "user_message": "hola",
            "intent": "general",
            "user_profile": {},
            "rag_context": [],
            "tool_data": {},
            "response": "Hola!",
            "conversation_history": [],
        })
        mock_store = make_session_store()
        use_case = make_use_case(session_store=mock_store, orchestrator=mock_orch)
        await use_case.execute(make_text_message())
        mock_store.save_profile.assert_not_called()
