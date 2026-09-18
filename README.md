# Multi-Agent Support Assistant

[![CI](https://github.com/wellaya/multi-agent-support-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/wellaya/multi-agent-support-assistant/actions/workflows/ci.yml)

Portfolio project: an agentic email/chat support assistant with a
provider-agnostic LLM layer, RAG, and safety guardrails.

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # then fill in ANTHROPIC_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload
```

- `GET /health` — liveness check
- `POST /chat` — `{"message": "..."}` -> `{"response": "..."}`

## Test

```bash
pytest
```
