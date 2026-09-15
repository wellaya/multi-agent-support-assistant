from dataclasses import dataclass

from app.agent.schemas import TriageResult
from app.rag.retriever import RetrievedChunk


@dataclass
class AgentResult:
    triage: TriageResult
    chunks: list[RetrievedChunk]
    draft_response: str
    action: str
    input_flagged: bool
    input_flag_reasons: list[str]
    output_flagged: bool
    output_flag_reasons: list[str]


async def handle_request(message: str, graph) -> AgentResult:
    state = await graph.ainvoke({"message": message})
    return AgentResult(
        triage=state["triage"],
        chunks=state.get("chunks", []),
        draft_response=state["draft_response"],
        action=state["action"],
        input_flagged=state.get("input_flagged", False),
        input_flag_reasons=state.get("input_flag_reasons", []),
        output_flagged=state.get("output_flagged", False),
        output_flag_reasons=state.get("output_flag_reasons", []),
    )
