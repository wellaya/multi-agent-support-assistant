from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.providers.claude_provider import ClaudeProvider

router = APIRouter()

_provider = ClaudeProvider()


def get_provider() -> LLMProvider:
    return _provider


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, provider: LLMProvider = Depends(get_provider)):
    reply = await provider.generate(
        messages=[{"role": "user", "content": request.message}]
    )
    return ChatResponse(response=reply)
