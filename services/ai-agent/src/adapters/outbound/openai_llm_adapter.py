from __future__ import annotations

import openai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.adapters.outbound.errors import LlmApiError, LlmTimeoutError
from src.domain.ports.i_llm_client import ILlmClient


class OpenAILlmAdapter(ILlmClient):
    """Implementa ILlmClient usando OpenAI gpt-4o-mini vía LangChain."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = ChatOpenAI(
            model=model,
            temperature=0.3,
            timeout=30,
            api_key=api_key,
        )

    async def generate(self, system_prompt: str, user_message: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        try:
            response = await self._client.ainvoke(messages)
            return str(response.content)
        except openai.APITimeoutError as exc:
            raise LlmTimeoutError("LLM no respondió en 30s") from exc
        except openai.APIStatusError as exc:
            raise LlmApiError(str(exc), status_code=exc.status_code) from exc
        except openai.APIError as exc:
            raise LlmApiError(str(exc)) from exc

    async def generate_with_history(self, system_prompt: str, messages: list) -> str:
        all_messages = [SystemMessage(content=system_prompt)] + list(messages)
        try:
            response = await self._client.ainvoke(all_messages)
            return str(response.content)
        except openai.APITimeoutError as exc:
            raise LlmTimeoutError("LLM no respondió en 30s") from exc
        except openai.APIStatusError as exc:
            raise LlmApiError(str(exc), status_code=exc.status_code) from exc
        except openai.APIError as exc:
            raise LlmApiError(str(exc)) from exc
