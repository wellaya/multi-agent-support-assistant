from anthropic import AsyncAnthropic

from app.config import settings
from app.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
        self._model = model or settings.anthropic_model

    async def generate(self, messages: list[dict], **kwargs) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=kwargs.pop("max_tokens", 1024),
            messages=messages,
            **kwargs,
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )
