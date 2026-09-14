from typing import Callable, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.nodes import decide_action, run_draft, run_triage
from app.agent.schemas import TriageResult
from app.providers.base import LLMProvider
from app.rag.retriever import RetrievedChunk


class AgentState(TypedDict, total=False):
    message: str
    triage: TriageResult
    chunks: list[RetrievedChunk]
    draft_response: str
    action: str


def build_agent_graph(
    provider: LLMProvider,
    retrieve_fn: Callable[[str], list[RetrievedChunk]],
):
    async def triage_node(state: AgentState) -> dict:
        return {"triage": await run_triage(provider, state["message"])}

    async def retrieve_node(state: AgentState) -> dict:
        return {"chunks": retrieve_fn(state["message"])}

    async def draft_node(state: AgentState) -> dict:
        draft = await run_draft(provider, state["message"], state["chunks"])
        return {"draft_response": draft}

    async def decide_node(state: AgentState) -> dict:
        return {"action": decide_action(state["triage"], state["chunks"])}

    graph = StateGraph(AgentState)
    graph.add_node("triage", triage_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("draft", draft_node)
    graph.add_node("decide", decide_node)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "decide")
    graph.add_edge("decide", END)

    return graph.compile()
