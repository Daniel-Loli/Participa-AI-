from __future__ import annotations

from langchain_core.messages import AIMessage

from agents.state import AgentState
from src.domain.ports.i_llm_client import ILlmClient

_SYSTEM_PROMPT = """Eres el revisor de tono de Participa AI, un chatbot de participación ciudadana para jóvenes peruanos (15-29 años).

TAREA: Ajusta el tono de la respuesta sin cambiar su contenido ni información.

REGLAS:
- Usa siempre "tú" (nunca "usted")
- Lenguaje claro y directo, sin tecnicismos innecesarios
- Si el usuario expresa frustración, miedo o urgencia → abre con una línea empática corta antes de la información
- Si la consulta es sobre leyes, trámites o documentos → tono profesional y serio, máximo 1 emoji, sin exclamaciones vacías
- Si es saludo, menú o pregunta general → tono cálido y motivador, 1-2 emojis relevantes
- Si el usuario logró algo o da un paso concreto → celebra en una frase y motiva a continuar
- Si el mensaje tiene urgencia o gravedad → responde con calma y autoridad, sin dramatizar
- Nunca uses frases vacías como "¡Claro que sí!", "¡Por supuesto!", "¡Genial!" sin contexto real
- Mantén la misma estructura, longitud y toda la información de la respuesta original
- Máximo 3 emojis en toda la respuesta

CONTEXTO:
- Tipo de consulta: {intent}
- Mensaje del usuario: {user_message}

RESPUESTA A REVISAR:
{response}

Devuelve SOLO la respuesta con el tono ajustado, sin explicaciones."""


def make_tone_review_node(llm_client: ILlmClient):
    async def tone_review(state: AgentState) -> dict:
        response = state.get("response", "")

        if not response.strip():
            return {}

        # Para documentos PDF: no revisar tono pero sí guardar en historial
        if state.get("pdf_base64"):
            return {"conversation_history": [AIMessage(content=response)]}

        intent = state.get("intent") or "general"
        user_message = (state.get("user_message") or "")[:300]

        prompt = _SYSTEM_PROMPT.format(
            intent=intent,
            user_message=user_message,
            response=response,
        )

        try:
            revised = await llm_client.generate(prompt, "")
            revised = revised.strip()
            if revised:
                return {
                    "response": revised,
                    "conversation_history": [AIMessage(content=revised)],
                }
        except Exception:
            pass

        # Fallback: guardar la respuesta original sin revisión
        return {"conversation_history": [AIMessage(content=response)]}

    return tone_review
