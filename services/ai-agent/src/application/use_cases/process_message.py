from __future__ import annotations

import base64
import dataclasses
import logging

from langchain_core.messages import HumanMessage

from agents.wa_format import clean as wa_clean
from src.application.errors import OrchestratorError, SttTranscriptionError
from src.domain.entities.agent_response import AgentResponse
from src.domain.entities.message import Message
from src.domain.entities.user_profile import UserProfile
from src.domain.ports.i_session_store import ISessionStore
from src.domain.ports.i_stt_client import ISttClient
from src.domain.ports.i_tts_client import ITtsClient

logger = logging.getLogger(__name__)


class ProcessMessageUseCase:
    def __init__(
        self,
        stt_client: ISttClient,
        tts_client: ITtsClient,
        session_store: ISessionStore,
        orchestrator,
    ) -> None:
        self._stt = stt_client
        self._tts = tts_client
        self._session_store = session_store
        self._orchestrator = orchestrator

    async def execute(self, message: Message) -> AgentResponse:
        text = await self._transcribe_if_audio(message)

        profile_dict = await self._load_profile(message.session_id)

        initial_state = {
            "session_id": message.session_id,
            "user_message": text,
            "intent": None,
            "user_profile": profile_dict,
            "rag_context": [],
            "tool_data": {},
            "response": "",
            "conversation_history": [HumanMessage(content=text)],
        }

        try:
            final_state = await self._orchestrator.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": message.session_id}},
            )
        except Exception as exc:
            raise OrchestratorError(str(exc)) from exc

        await self._save_profile(message.session_id, final_state.get("user_profile", {}))

        response_text = wa_clean(final_state.get("response", ""))
        return await self._build_response(message, response_text)

    async def _transcribe_if_audio(self, message: Message) -> str:
        if message.is_text():
            return message.text_content or ""
        try:
            return await self._stt.transcribe(
                message.audio_base64 or "",
                message.audio_mime_type or "audio/ogg",
            )
        except Exception as exc:
            raise SttTranscriptionError(f"Error en transcripción STT: {exc}") from exc

    async def _load_profile(self, session_id: str) -> dict:
        try:
            profile = await self._session_store.get_profile(session_id)
            if profile is None:
                return {}
            return dataclasses.asdict(profile)
        except Exception as exc:
            logger.warning("Error cargando perfil para sesión '%s': %s", session_id, exc)
            return {}

    async def _save_profile(self, session_id: str, profile_dict: dict) -> None:
        if not profile_dict:
            return
        try:
            profile = UserProfile(
                user_id=session_id,
                name=profile_dict.get("name"),
                district=profile_dict.get("district"),
                issue=profile_dict.get("issue"),
                conversation_stage=profile_dict.get("conversation_stage", "ONBOARDING"),
            )
            await self._session_store.save_profile(profile)
        except Exception as exc:
            logger.warning("Error guardando perfil para sesión '%s': %s", session_id, exc)

    async def _build_response(self, message: Message, response_text: str) -> AgentResponse:
        if message.is_text():
            return AgentResponse(response_type="text", response_text=response_text)
        try:
            audio_bytes = await self._tts.synthesize(response_text)
            audio_b64 = base64.b64encode(audio_bytes).decode()
            return AgentResponse(response_type="audio", response_audio_base64=audio_b64)
        except Exception as exc:
            logger.warning("TTS falló, usando fallback a texto: %s", exc)
            return AgentResponse(response_type="text", response_text=response_text)
