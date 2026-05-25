from __future__ import annotations


class AiAgentError(Exception):
    """Base para todos los errores de la capa de aplicación."""


class SttTranscriptionError(AiAgentError):
    """Fallo irrecuperable en la transcripción STT. Se propaga al router → 422."""


class OrchestratorError(AiAgentError):
    """Fallo irrecuperable en el grafo LangGraph. Se propaga al router → 500."""
