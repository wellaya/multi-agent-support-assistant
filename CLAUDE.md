# Project: Multi-Agent Support Assistant (Email + Chat)

## Goal

Build a portfolio project demonstrating agentic AI + AI safety skills for
AI Engineer / AI Safety roles in the Australian market. Mirrors real use
cases like email automation and customer-facing chatbots.

## Constraints

- No Azure subscription currently — build cloud-agnostic / open-source first.
- Have Claude.ai/API access (Pro subscription) — use Claude API as primary LLM provider.
- Design provider-agnostic (LLMProvider abstract interface) so Azure OpenAI /
  OpenAI / Gemini can be added later with minimal changes.

## Tech stack

- Backend: Python, FastAPI (async)
- Orchestration: LangGraph (or custom agent loop)
- LLM: Claude API (tool use, structured outputs, streaming) via abstraction layer
- RAG: ChromaDB or Qdrant (local/Docker), sentence-transformers or Claude embeddings
- Safety layer: input guardrail (prompt injection heuristic), output guardrail
  (PII/policy check before send), human-in-the-loop approval queue, structured
  decision/audit logging
- Eval: promptfoo or pytest-based eval harness (~20-30 test cases)
- DevOps: Docker, GitHub Actions CI/CD, optional deploy to Fly.io/Railway/Render

## Build order (stages)

1. Skeleton + provider abstraction (FastAPI + ClaudeProvider, one working call)
2. RAG layer (vector DB + mock KB ingestion + retrieval with citations)
3. Agent loop (triage → retrieve → draft → decide: respond/escalate/ticket)
4. Safety & guardrails (input/output checks, HITL approval, audit logging)
5. Eval harness + CI/CD (GitHub Actions running eval suite)
6. README polish (architecture diagram, safety considerations, eval results)

## Currently on: Stage 1
