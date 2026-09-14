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

    async def generate_structured(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        tool_name = kwargs.pop("tool_name", "submit_structured_output")
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=kwargs.pop("max_tokens", 1024),
            messages=messages,
            tools=[
                {
                    "name": tool_name,
                    "description": "Submit the extracted structured output.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            **kwargs,
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise ValueError("Claude response did not contain a tool_use block")
