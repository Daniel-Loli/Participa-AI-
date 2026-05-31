from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import Literal

from src.application.errors import OrchestratorError, SttTranscriptionError
from src.application.use_cases.delete_session import DeleteSessionUseCase
from src.application.use_cases.process_message import ProcessMessageUseCase
from src.domain.entities.message import Message
from src.domain.value_objects.message_type import MessageType

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRequest(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    type: Literal["text", "audio"]
    session_id: str
    timestamp: int
    message: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None

    @model_validator(mode="after")
    def check_content_present(self) -> "AgentRequest":
        if self.type == "text" and self.message is None:
            raise ValueError("El campo 'message' es requerido para mensajes de tipo 'text'")
        if self.type == "audio" and self.audio_base64 is None:
            raise ValueError("El campo 'audio_base64' es requerido para mensajes de tipo 'audio'")
        return self


class AgentResponseDTO(BaseModel):
    response_type: str
    response_text: str | None = None
    response_audio_base64: str | None = None
    response_pdf_base64: str | None = None
    response_pdf_filename: str | None = None


def get_process_message_use_case() -> ProcessMessageUseCase:
    raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")


def get_delete_session_use_case() -> DeleteSessionUseCase:
    raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")


@router.post("/agent", response_model=AgentResponseDTO)
async def process_message(
    body: AgentRequest,
    use_case: ProcessMessageUseCase = Depends(get_process_message_use_case),
) -> AgentResponseDTO:
    domain_message = Message(
        from_hash=body.from_,
        type=MessageType(body.type),
        session_id=body.session_id,
        timestamp=body.timestamp,
        text_content=body.message,
        audio_base64=body.audio_base64,
        audio_mime_type=body.audio_mime_type,
    )
    try:
        agent_response = await use_case.execute(domain_message)
    except SttTranscriptionError:
        raise HTTPException(
            status_code=422,
            detail="No pudimos entender el audio. Por favor intenta de nuevo.",
        )
    except OrchestratorError:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servicio. Por favor intenta más tarde.",
        )

    return AgentResponseDTO(
        response_type=agent_response.response_type,
        response_text=agent_response.response_text,
        response_audio_base64=agent_response.response_audio_base64,
        response_pdf_base64=agent_response.response_pdf_base64,
        response_pdf_filename=agent_response.response_pdf_filename,
    )


@router.delete("/session/{session_id}", status_code=200)
async def delete_session(
    session_id: str,
    use_case: DeleteSessionUseCase = Depends(get_delete_session_use_case),
) -> dict:
    await use_case.execute(session_id)
    return {"deleted": True}


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "ai-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
