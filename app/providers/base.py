from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider-agnostic interface for chat-style LLM calls.

    Implementations (Claude, Azure OpenAI, OpenAI, Gemini, ...) plug in here
    so the rest of the app never depends on a specific vendor SDK.
    """

    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> str:
        """Send chat messages to the LLM and return the text response.

        messages: list of {"role": "user"|"assistant", "content": str}
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        """Send chat messages to the LLM and return a dict matching `schema`
        (a JSON Schema object), using the provider's structured-output /
        tool-use mechanism instead of free-text parsing.
        """
        raise NotImplementedError
