# Multi-Agent Support Assistant

[![CI](https://github.com/wellaya/multi-agent-support-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/wellaya/multi-agent-support-assistant/actions/workflows/ci.yml)

An agentic email/chat support assistant: it classifies a customer message,
retrieves grounded answers from a knowledge base, drafts a cited reply, and
decides whether to respond automatically, escalate to a human, or open a
ticket — with safety guardrails and an audit trail along the way.

Built with FastAPI, LangGraph, Qdrant, and the Claude API behind a
provider-agnostic interface.

For the full architecture, design decisions, and a guided walkthrough of
the code, see **[docs/](docs/README.md)**.

## Prerequisites

- Python 3.11+
- Docker Desktop (for the Qdrant vector database)
- An Anthropic API key with credits — [console.anthropic.com](https://console.anthropic.com)

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env         # then fill in ANTHROPIC_API_KEY
```

## Run

```bash
docker compose up -d              # starts Qdrant on localhost:6333
python scripts/ingest_kb.py       # loads data/kb/*.md into Qdrant (run once, or after editing the KB)
uvicorn app.main:app --reload     # starts the API on localhost:8000
```

Open `http://127.0.0.1:8000/docs` for an interactive Swagger UI, or see
[docs/low-level-design/api-reference.md](docs/low-level-design/api-reference.md)
for every endpoint with example requests (including PowerShell-safe ones).

Main endpoint: `POST /support/request` — `{"message": "..."}` runs the full
triage → retrieve → draft → decide pipeline and returns the classification,
action, and a cited draft reply.

## Test

```bash
pytest              # 23 tests, fully offline — no API key or Docker needed
pytest -m eval       # 27 additional live-eval cases against the real Claude
                     # API + Qdrant — costs API credits, run manually (see
                     # docs/eval-and-testing.md)
```

## Project layout

```
app/          FastAPI app: providers, RAG, agent graph, safety layer, routes
data/kb/      Mock knowledge base (source markdown, committed)
eval/         Eval harness and cases (live-API quality checks)
tests/        Offline test suite (mocked provider, in-memory Qdrant)
docs/         Full architecture and design documentation
```
