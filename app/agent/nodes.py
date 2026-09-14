from app.agent.schemas import TriageResult
from app.providers.base import LLMProvider
from app.rag.retriever import RetrievedChunk

TRIAGE_PROMPT = """You are a support ticket triage assistant for a SaaS product.
Classify the customer's message using the submit_triage tool.

Customer message:
{message}
"""

DRAFT_SYSTEM_PROMPT = """You are a customer support agent. Answer the customer's \
message using ONLY the knowledge base excerpts below. Cite the source of any fact \
you use by its filename in parentheses, e.g. (password_reset.md). If the excerpts \
don't cover the question, say clearly that you're not sure and that a human will \
follow up. Keep the reply concise and friendly.

Knowledge base excerpts:
{context}

Customer message:
{message}
"""


async def run_triage(provider: LLMProvider, message: str) -> TriageResult:
    result = await provider.generate_structured(
        messages=[{"role": "user", "content": TRIAGE_PROMPT.format(message=message)}],
        schema=TriageResult.model_json_schema(),
        tool_name="submit_triage",
    )
    return TriageResult(**result)


async def run_draft(provider: LLMProvider, message: str, chunks: list[RetrievedChunk]) -> str:
    context = (
        "\n\n".join(f"[{chunk.source}]\n{chunk.text}" for chunk in chunks)
        or "(no relevant knowledge base articles found)"
    )
    prompt = DRAFT_SYSTEM_PROMPT.format(context=context, message=message)
    return await provider.generate(messages=[{"role": "user", "content": prompt}])


def decide_action(triage: TriageResult, chunks: list[RetrievedChunk]) -> str:
    if triage.needs_escalation:
        return "escalate"
    if triage.category == "other" or not chunks:
        return "ticket"
    return "respond"
