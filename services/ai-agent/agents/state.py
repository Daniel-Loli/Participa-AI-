from __future__ import annotations

from typing import Annotated, TypedDict

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    session_id: str
    user_message: str
    intent: str | None                          # valor de AgentIntent
    user_profile: dict                          # UserProfile serializado como dict
    rag_context: list[str]                      # chunks recuperados de Qdrant
    tool_data: dict                             # datos de JSONs locales (calendar, directorio…)
    response: str                               # respuesta generada por el nodo activo
    conversation_history: Annotated[list, add_messages]  # historial acumulativo
    pdf_base64: NotRequired[str | None]         # PDF generado por redactor_node (base64)
    pdf_filename: NotRequired[str | None]       # nombre del archivo PDF
    doc_confirmed: NotRequired[bool]            # usuario confirmó generación del documento
    lt_summary: NotRequired[str | None]         # resumen de la sesión anterior (memoria LT)
