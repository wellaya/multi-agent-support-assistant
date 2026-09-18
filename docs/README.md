# Documentation

Full design and implementation documentation for the Multi-Agent Support
Assistant. Written to be readable end-to-end by someone new to agentic
AI/RAG systems, and useful as a reference later (including to the
project's own author, revisiting this in six months).

**Start here if you're new to these concepts:**
1. [concepts.md](concepts.md) — RAG, embeddings, vector DBs, tool use,
   LangGraph, guardrails, HITL — explained from first principles before
   you see how this project uses them.

**Then the design, top-down:**

2. [high-level-design.md](high-level-design.md) — what the system does,
   the architecture diagram, the request lifecycle, and why the major
   technology choices were made.
3. **Low-level design** — one subsystem per file:
   - [low-level-design/provider-layer.md](low-level-design/provider-layer.md) — the LLM abstraction
   - [low-level-design/rag-pipeline.md](low-level-design/rag-pipeline.md) — chunking, embeddings, Qdrant
   - [low-level-design/agent-loop.md](low-level-design/agent-loop.md) — the LangGraph state machine
   - [low-level-design/safety-guardrails.md](low-level-design/safety-guardrails.md) — guardrails, audit log, approval queue
   - [low-level-design/api-reference.md](low-level-design/api-reference.md) — every HTTP endpoint, with examples
4. [eval-and-testing.md](eval-and-testing.md) — how correctness and model
   quality are both verified, and how to run each kind of check.

**Reference, when you need to change or extend something:**

5. [extending.md](extending.md) — practical how-tos: add an LLM provider,
   a KB article, an agent node, a guardrail rule.
6. [decisions-and-limitations.md](decisions-and-limitations.md) — why the
   project is built this way instead of the alternatives, and what it
   deliberately doesn't do yet.

## Map of the code

```
app/
├── main.py              FastAPI app entrypoint
├── config.py             Settings (env vars)
├── providers/             LLM abstraction (see provider-layer.md)
│   ├── base.py             LLMProvider interface
│   └── claude_provider.py  Claude implementation
├── rag/                    Retrieval (see rag-pipeline.md)
│   ├── chunking.py, embeddings.py, vector_store.py, ingest.py, retriever.py
├── agent/                  The LangGraph agent loop (see agent-loop.md)
│   ├── schemas.py, nodes.py, graph.py, loop.py
├── safety/                 Guardrails + audit/approval store (see safety-guardrails.md)
│   ├── models.py, input_guardrail.py, output_guardrail.py, store.py
└── api/
    └── routes.py            All HTTP endpoints (see api-reference.md)

data/kb/      Mock knowledge base articles (input to the RAG pipeline)
eval/         Eval harness: cases.py, harness.py, run_eval.py, results.md
tests/        Offline test suite (one file per subsystem above)
```
