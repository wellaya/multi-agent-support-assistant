from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agent.graph import build_agent_graph
from app.agent.loop import handle_request
from app.config import settings
from app.providers.base import LLMProvider
from app.providers.claude_provider import ClaudeProvider
from app.rag.embeddings import Embedder
from app.rag.retriever import retrieve
from app.rag.vector_store import QdrantVectorStore
from app.safety.store import SafetyStore

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


@lru_cache
def get_agent_graph():
    embedder = get_embedder()
    store = get_vector_store()

    def retrieve_fn(query: str):
        return retrieve(query, store=store, embedder=embedder, top_k=3)

    return build_agent_graph(get_provider(), retrieve_fn)


@lru_cache
def get_safety_store() -> SafetyStore:
    return SafetyStore(db_path=settings.safety_db_path)


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


class SupportRequest(BaseModel):
    message: str


class SupportResponse(BaseModel):
    category: str
    sentiment: str
    needs_escalation: bool
    action: str
    draft_response: str
    sources: list[str]
    needs_approval: bool


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    note: str | None = None


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


@router.post("/support/request", response_model=SupportResponse)
async def support_request(
    request: SupportRequest,
    graph=Depends(get_agent_graph),
    safety_store: SafetyStore = Depends(get_safety_store),
):
    result = await handle_request(request.message, graph)
    needs_approval = result.action != "respond"

    safety_store.log_audit(
        message=request.message,
        category=result.triage.category,
        sentiment=result.triage.sentiment,
        action=result.action,
        input_flagged=result.input_flagged,
        output_flagged=result.output_flagged,
        flag_reasons=result.input_flag_reasons + result.output_flag_reasons,
    )
    if needs_approval:
        safety_store.enqueue_approval(
            message=request.message,
            draft_response=result.draft_response,
            category=result.triage.category,
            action=result.action,
        )

    return SupportResponse(
        category=result.triage.category,
        sentiment=result.triage.sentiment,
        needs_escalation=result.triage.needs_escalation,
        action=result.action,
        draft_response=result.draft_response,
        sources=sorted({chunk.source for chunk in result.chunks}),
        needs_approval=needs_approval,
    )


@router.get("/approvals")
async def list_approvals(safety_store: SafetyStore = Depends(get_safety_store)):
    return {"results": safety_store.list_pending_approvals()}


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: int,
    request: ApprovalDecisionRequest,
    safety_store: SafetyStore = Depends(get_safety_store),
):
    decided = safety_store.decide_approval(approval_id, request.approved, request.note)
    if decided is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return decided


@router.get("/audit")
async def list_audit(limit: int = 50, safety_store: SafetyStore = Depends(get_safety_store)):
    return {"results": safety_store.list_audit(limit=limit)}
