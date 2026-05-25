from __future__ import annotations


class AiAgentError(Exception):
    """Base para todos los errores del servicio ai-agent."""


# --- LLM ---

class LlmTimeoutError(AiAgentError):
    """OpenAI LLM no respondió dentro del timeout configurado (30s)."""


class LlmApiError(AiAgentError):
    """Error HTTP de la API de OpenAI LLM."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# --- STT ---

class SttTimeoutError(AiAgentError):
    """OpenAI Whisper no respondió dentro del timeout configurado (20s)."""


class SttInvalidAudioError(AiAgentError):
    """El audio enviado a Whisper es inválido o no puede transcribirse."""


# --- TTS ---

class TtsApiError(AiAgentError):
    """Error al sintetizar audio con OpenAI TTS."""


# --- RAG ---

class RagTimeoutError(AiAgentError):
    """Qdrant no respondió dentro del timeout configurado (5s)."""


# --- Sesión ---

class SessionStoreError(AiAgentError):
    """Error al leer o escribir en Redis. Se maneja de forma degradada."""


# --- Orquestador / Use case ---

class SttTranscriptionError(AiAgentError):
    """Fallo irrecuperable en la transcripción STT. Se propaga al router → 422."""


class OrchestratorError(AiAgentError):
    """Fallo irrecuperable en el grafo LangGraph. Se propaga al router → 500."""
