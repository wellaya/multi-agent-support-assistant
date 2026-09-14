from dataclasses import dataclass

from app.agent.schemas import TriageResult
from app.rag.retriever import RetrievedChunk


@dataclass
class AgentResult:
    triage: TriageResult
    chunks: list[RetrievedChunk]
    draft_response: str
    action: str


async def handle_request(message: str, graph) -> AgentResult:
    state = await graph.ainvoke({"message": message})
    return AgentResult(
        triage=state["triage"],
        chunks=state["chunks"],
        draft_response=state["draft_response"],
        action=state["action"],
    )
