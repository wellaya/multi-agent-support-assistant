# Multi-Agent Support Assistant

Portfolio project: an agentic email/chat support assistant with a
provider-agnostic LLM layer, RAG, and safety guardrails. See
[CLAUDE.md](CLAUDE.md) for the full design and build plan.

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
