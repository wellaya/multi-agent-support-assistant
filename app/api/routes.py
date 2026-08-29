from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.providers.base import LLMProvider
from app.providers.claude_provider import ClaudeProvider
from app.rag.embeddings import Embedder
from app.rag.retriever import retrieve
from app.rag.vector_store import QdrantVectorStore

router = APIRouter()

_provider = ClaudeProvider()


def get_provider() -> LLMProvider:
    return _provider


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        collection_name=settings.qdrant_collection, url=settings.qdrant_url
    )


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class RagQueryRequest(BaseModel):
    query: str
    top_k: int = 3


class RagResult(BaseModel):
    text: str
    source: str
    score: float


class RagQueryResponse(BaseModel):
    results: list[RagResult]


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, provider: LLMProvider = Depends(get_provider)):
    reply = await provider.generate(
        messages=[{"role": "user", "content": request.message}]
    )
    return ChatResponse(response=reply)


@router.post("/rag/query", response_model=RagQueryResponse)
async def rag_query(
    request: RagQueryRequest,
    embedder: Embedder = Depends(get_embedder),
    store: QdrantVectorStore = Depends(get_vector_store),
):
    chunks = retrieve(request.query, store=store, embedder=embedder, top_k=request.top_k)
    return RagQueryResponse(
        results=[RagResult(text=c.text, source=c.source, score=c.score) for c in chunks]
    )
