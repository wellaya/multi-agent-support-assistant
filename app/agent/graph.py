from typing import Callable, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.nodes import decide_action, run_draft, run_triage
from app.agent.schemas import TriageResult
from app.providers.base import LLMProvider
from app.rag.retriever import RetrievedChunk
from app.safety.input_guardrail import check_input
from app.safety.output_guardrail import check_output

BLOCKED_RESPONSE = (
    "This message was flagged by our safety system and will be reviewed by "
    "a human before any response is sent."
)


class AgentState(TypedDict, total=False):
    message: str
    triage: TriageResult
    chunks: list[RetrievedChunk]
    draft_response: str
    action: str
    input_flagged: bool
    input_flag_reasons: list[str]
    output_flagged: bool
    output_flag_reasons: list[str]


def build_agent_graph(
    provider: LLMProvider,
    retrieve_fn: Callable[[str], list[RetrievedChunk]],
):
    async def input_guardrail_node(state: AgentState) -> dict:
        result = check_input(state["message"])
        return {"input_flagged": result.flagged, "input_flag_reasons": result.reasons}

    async def blocked_node(state: AgentState) -> dict:
        return {
            "triage": TriageResult(
                category="other",
                sentiment="neutral",
                needs_escalation=True,
                reasoning="Blocked by input guardrail before triage.",
            ),
            "chunks": [],
            "draft_response": BLOCKED_RESPONSE,
            "action": "escalate",
            "output_flagged": False,
            "output_flag_reasons": [],
        }

    async def triage_node(state: AgentState) -> dict:
        return {"triage": await run_triage(provider, state["message"])}

    async def retrieve_node(state: AgentState) -> dict:
        return {"chunks": retrieve_fn(state["message"])}

    async def draft_node(state: AgentState) -> dict:
        draft = await run_draft(provider, state["message"], state["chunks"])
        return {"draft_response": draft}

    async def output_guardrail_node(state: AgentState) -> dict:
        result = check_output(state["draft_response"])
        return {"output_flagged": result.flagged, "output_flag_reasons": result.reasons}

    async def decide_node(state: AgentState) -> dict:
        action = decide_action(state["triage"], state["chunks"])
        if state.get("output_flagged"):
            action = "escalate"
        return {"action": action}

    graph = StateGraph(AgentState)
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node("triage", triage_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("draft", draft_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("decide", decide_node)

    graph.set_entry_point("input_guardrail")
    graph.add_conditional_edges(
        "input_guardrail",
        lambda state: "blocked" if state["input_flagged"] else "triage",
        {"blocked": "blocked", "triage": "triage"},
    )
    graph.add_edge("blocked", END)
    graph.add_edge("triage", "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "output_guardrail")
    graph.add_edge("output_guardrail", "decide")
    graph.add_edge("decide", END)

    return graph.compile()
