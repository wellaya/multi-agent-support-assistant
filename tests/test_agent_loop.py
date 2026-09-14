import pytest

from app.agent.graph import build_agent_graph
from app.agent.loop import handle_request
from app.agent.schemas import TriageResult
from app.providers.base import LLMProvider
from app.rag.retriever import RetrievedChunk


class FakeProvider(LLMProvider):
    """Deterministic provider: triage/draft behavior is picked from the
    incoming message so each test can drive a specific decide_action branch
    without a real API key or network call."""

    async def generate(self, messages: list[dict], **kwargs) -> str:
        return "Here is a drafted reply based on the knowledge base."

    async def generate_structured(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        prompt = messages[0]["content"]
        if "angry" in prompt.lower():
            return {
                "category": "billing",
                "sentiment": "angry",
                "needs_escalation": True,
                "reasoning": "Customer is angry about a charge.",
            }
        if "favorite color" in prompt.lower():
            return {
                "category": "other",
                "sentiment": "neutral",
                "needs_escalation": False,
                "reasoning": "Off-topic question, not in the knowledge base.",
            }
        return {
            "category": "password_reset",
            "sentiment": "neutral",
            "needs_escalation": False,
            "reasoning": "Customer wants to reset their password.",
        }


def _password_chunks() -> list[RetrievedChunk]:
    return [RetrievedChunk(text="Click 'Forgot password?'...", source="password_reset.md", score=0.9)]


@pytest.mark.asyncio
async def test_respond_when_in_scope_and_calm():
    graph = build_agent_graph(FakeProvider(), retrieve_fn=lambda q: _password_chunks())
    result = await handle_request("I forgot my password, how do I reset it?", graph)

    assert result.action == "respond"
    assert result.triage.category == "password_reset"
    assert result.draft_response


@pytest.mark.asyncio
async def test_escalate_when_customer_is_angry():
    graph = build_agent_graph(FakeProvider(), retrieve_fn=lambda q: [])
    result = await handle_request("I am so angry about this billing charge!", graph)

    assert result.action == "escalate"
    assert result.triage.needs_escalation is True


@pytest.mark.asyncio
async def test_ticket_when_out_of_scope():
    graph = build_agent_graph(FakeProvider(), retrieve_fn=lambda q: [])
    result = await handle_request("What's your favorite color?", graph)

    assert result.action == "ticket"
    assert result.triage.category == "other"


@pytest.mark.asyncio
async def test_ticket_when_no_chunks_retrieved():
    graph = build_agent_graph(FakeProvider(), retrieve_fn=lambda q: [])
    result = await handle_request("How do I reset my password?", graph)

    assert result.action == "ticket"
    assert result.triage.category == "password_reset"


def test_triage_result_is_typed():
    triage = TriageResult(
        category="refund",
        sentiment="frustrated",
        needs_escalation=False,
        reasoning="Wants a refund.",
    )
    assert triage.category == "refund"
