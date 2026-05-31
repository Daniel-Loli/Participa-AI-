from __future__ import annotations

import base64
import dataclasses
import logging
from datetime import date

from langchain_core.messages import HumanMessage

from agents.wa_format import clean as wa_clean
from src.application.errors import OrchestratorError, SttTranscriptionError
from src.domain.entities.agent_response import AgentResponse
from src.domain.entities.long_term_profile import LongTermProfile
from src.domain.entities.message import Message
from src.domain.entities.user_profile import UserProfile
from src.domain.ports.i_long_term_profile_store import ILongTermProfileStore
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
        lt_store: ILongTermProfileStore,
        orchestrator,
    ) -> None:
        self._stt = stt_client
        self._tts = tts_client
        self._session_store = session_store
        self._lt_store = lt_store
        self._orchestrator = orchestrator

    async def execute(self, message: Message) -> AgentResponse:
        text = await self._transcribe_if_audio(message)

        # Capa 2: perfil de sesión (corto plazo, 24 h)
        profile_dict = await self._load_profile(message.session_id)

        # Capa 3: perfil de largo plazo (30 días); pre-poblamos la sesión si hay datos
        lt_profile = await self._load_lt_profile(message.session_id)
        profile_dict = self._merge_lt_into_session(profile_dict, lt_profile)
        lt_summary = lt_profile.last_session_summary if lt_profile else None

        initial_state = {
            "session_id": message.session_id,
            "user_message": text,
            "intent": None,
            "user_profile": profile_dict,
            "rag_context": [],
            "tool_data": {},
            "response": "",
            "conversation_history": [HumanMessage(content=text)],
            "pdf_base64": None,
            "pdf_filename": None,
            "doc_confirmed": False,
            "lt_summary": lt_summary,
        }

        try:
            final_state = await self._orchestrator.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": message.session_id}},
            )
        except Exception as exc:
            raise OrchestratorError(str(exc)) from exc

        final_profile = final_state.get("user_profile", {})
        await self._save_profile(message.session_id, final_profile)
        await self._update_lt_profile(
            message.session_id,
            final_profile,
            lt_profile,
            generated_doc=bool(final_state.get("pdf_base64")),
        )

        response_text = wa_clean(final_state.get("response", ""))
        pdf_base64 = final_state.get("pdf_base64")
        pdf_filename = final_state.get("pdf_filename")
        return await self._build_response(message, response_text, pdf_base64, pdf_filename)

    # ── Capa 3 helpers ────────────────────────────────────────────────────────

    async def _load_lt_profile(self, user_id: str) -> LongTermProfile | None:
        try:
            return await self._lt_store.get_profile(user_id)
        except Exception as exc:
            logger.warning("Error cargando LT profile para '%s': %s", user_id, exc)
            return None

    def _merge_lt_into_session(self, profile_dict: dict, lt: LongTermProfile | None) -> dict:
        """Si el perfil de sesión está vacío, rellena con datos del perfil LT."""
        if lt is None:
            return profile_dict
        merged = dict(profile_dict)
        if not merged.get("name") and lt.name:
            merged["name"] = lt.name
        if not merged.get("district") and lt.district:
            merged["district"] = lt.district
        if not merged.get("issue") and lt.issues_worked:
            merged["issue"] = lt.issues_worked[-1]
        # Si ya tiene nombre y distrito, ya completó el onboarding anteriormente
        if merged.get("name") and merged.get("district"):
            merged.setdefault("conversation_stage", "ACTIVE")
        return merged

    async def _update_lt_profile(
        self,
        user_id: str,
        profile_dict: dict,
        existing: LongTermProfile | None,
        generated_doc: bool = False,
    ) -> None:
        try:
            today = date.today().isoformat()
            if existing is None:
                lt = LongTermProfile(
                    user_id=user_id,
                    name=profile_dict.get("name"),
                    district=profile_dict.get("district"),
                    first_seen=today,
                    last_seen=today,
                    sessions_count=1,
                )
            else:
                lt = existing
                if profile_dict.get("name"):
                    lt.name = profile_dict["name"]
                if profile_dict.get("district"):
                    lt.district = profile_dict["district"]
                # Contar como nueva sesión si el último contacto fue otro día
                if lt.last_seen != today:
                    lt.sessions_count += 1
                lt.last_seen = today

            # Acumular problemática si es nueva
            issue = profile_dict.get("issue")
            if issue and issue not in lt.issues_worked:
                lt.issues_worked.append(issue)

            if generated_doc:
                lt.documents_generated += 1

            # Resumen estructurado (sin LLM) que se inyecta en la próxima sesión
            if lt.name and lt.district:
                issue_str = lt.issues_worked[-1] if lt.issues_worked else "participación ciudadana"
                lt.last_session_summary = (
                    f"Sesión anterior ({today}): {lt.name} de {lt.district} "
                    f"trabajó el tema de {issue_str}."
                )

            await self._lt_store.save_profile(lt)
        except Exception as exc:
            logger.warning("Error actualizando LT profile para '%s': %s", user_id, exc)

    # ── Capa 2 helpers ────────────────────────────────────────────────────────

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
                awaiting_doc_confirmation=bool(profile_dict.get("awaiting_doc_confirmation", False)),
                awaiting_next_action=bool(profile_dict.get("awaiting_next_action", False)),
            )
            await self._session_store.save_profile(profile)
        except Exception as exc:
            logger.warning("Error guardando perfil para sesión '%s': %s", session_id, exc)

    # ── Build response ────────────────────────────────────────────────────────

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

    async def _build_response(
        self,
        message: Message,
        response_text: str,
        pdf_base64: str | None = None,
        pdf_filename: str | None = None,
    ) -> AgentResponse:
        if pdf_base64:
            return AgentResponse(
                response_type="document",
                response_text=response_text,
                response_pdf_base64=pdf_base64,
                response_pdf_filename=pdf_filename,
            )
        if message.is_text():
            return AgentResponse(response_type="text", response_text=response_text)
        try:
            audio_bytes = await self._tts.synthesize(response_text)
            audio_b64 = base64.b64encode(audio_bytes).decode()
            return AgentResponse(response_type="audio", response_audio_base64=audio_b64)
        except Exception as exc:
            logger.warning("TTS falló, usando fallback a texto: %s", exc)
            return AgentResponse(response_type="text", response_text=response_text)
