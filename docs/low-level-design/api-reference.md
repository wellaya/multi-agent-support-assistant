# Low-Level Design: API Reference

File: [`app/api/routes.py`](../../app/api/routes.py)

All endpoints are also browsable interactively at `http://127.0.0.1:8000/docs`
(FastAPI's auto-generated Swagger UI) once the app is running — that's
the fastest way to try these without writing any client code.

**PowerShell note**: `curl.exe -d '{"key": "value"}'` corrupts JSON bodies
in Windows PowerShell 5.1 (it mangles embedded double quotes when passing
arguments to native executables). Use `Invoke-RestMethod` instead, as
shown below. Plain `curl` in bash/Git Bash/macOS/Linux works fine as-is.

## Dependency wiring (how every endpoint gets its collaborators)

Every route takes its dependencies (`LLMProvider`, `Embedder`,
`QdrantVectorStore`, the agent graph, `SafetyStore`) via FastAPI's
`Depends(...)`, backed by module-level getter functions in `routes.py`:

| Getter | Cached? | Returns |
| --- | --- | --- |
| `get_provider()` | singleton at import time | the one `ClaudeProvider` |
| `get_embedder()` | `@lru_cache` | one `Embedder` (loads the model once) |
| `get_vector_store()` | `@lru_cache` | one `QdrantVectorStore` pointed at `settings.qdrant_url` |
| `get_agent_graph()` | `@lru_cache` | one compiled LangGraph, wired to the provider + a `retrieve_fn` closure |
| `get_safety_store()` | `@lru_cache` | one `SafetyStore` pointed at `settings.safety_db_path` |

This is what lets tests swap in fakes with one line
(`app.dependency_overrides[get_provider] = lambda: FakeProvider()`)
without touching any route function — see
[eval-and-testing.md](../eval-and-testing.md).

---

## `GET /health`

Liveness check.

```bash
curl.exe http://127.0.0.1:8000/health
```
```json
{"status": "ok"}
```

---

## `POST /chat`

Plain single-turn chat — no RAG, no agent loop, just `LLMProvider.generate()`.

**Request**: `{"message": string}`
**Response**: `{"response": string}`

```powershell
$body = @{ message = "Say hi in 5 words." } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/chat -Method Post -Body $body -ContentType "application/json"
```

---

## `POST /rag/query`

Retrieval only — no LLM call, no agent loop. Useful for inspecting what
the RAG pipeline would ground a draft with, independent of triage/drafting.

**Request**: `{"query": string, "top_k"?: int = 3}`
**Response**: `{"results": [{"text": string, "source": string, "score": float}, ...]}`

```powershell
$body = @{ query = "how do I get a refund"; top_k = 2 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/rag/query -Method Post -Body $body -ContentType "application/json"
```

---

## `POST /support/request`

**The main endpoint.** Runs the full agent loop (input guardrail → triage
→ retrieve → draft → output guardrail → decide), logs an audit row, and
enqueues an approval-queue row if the action isn't `"respond"`. See
[agent-loop.md](agent-loop.md) and
[safety-guardrails.md](safety-guardrails.md) for what happens inside.

**Request**: `{"message": string}`

**Response**:
```json
{
  "category": "password_reset",
  "sentiment": "neutral",
  "needs_escalation": false,
  "action": "respond",
  "draft_response": "...cited reply text (password_reset.md)...",
  "sources": ["password_reset.md"],
  "needs_approval": false
}
```

`action` is one of `"respond"` / `"escalate"` / `"ticket"`.
`needs_approval` is `true` whenever `action != "respond"` — that's exactly
when a row was also written to the approval queue.

```powershell
$body = @{ message = "I forgot my password, how do I reset it?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/support/request -Method Post -Body $body -ContentType "application/json"
```

---

## `GET /approvals`

Lists every **pending** approval-queue item (already-decided items drop
off this list, but remain queryable via the database directly if needed).

**Response**: `{"results": [{"id", "created_at", "message", "draft_response", "category", "action", "status", "reviewer_note", "decided_at"}, ...]}`

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/approvals
```

---

## `POST /approvals/{approval_id}/decide`

A human reviewer approves or rejects one pending item.

**Request**: `{"approved": bool, "note"?: string}`
**Response**: the updated approval row (`status` becomes `"approved"` or
`"rejected"`, `reviewer_note` and `decided_at` are set).
**404** if `approval_id` doesn't exist.

```powershell
$body = @{ approved = $true; note = "looks good" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/approvals/1/decide -Method Post -Body $body -ContentType "application/json"
```

---

## `GET /audit?limit=50`

Every logged decision, newest first, regardless of outcome — see
[safety-guardrails.md](safety-guardrails.md#audit_log--append-only).

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/audit?limit=10"
```
