# Low-Level Design: Safety Guardrails, Audit Log, Approval Queue

Files: [`app/safety/models.py`](../../app/safety/models.py),
[`app/safety/input_guardrail.py`](../../app/safety/input_guardrail.py),
[`app/safety/output_guardrail.py`](../../app/safety/output_guardrail.py),
[`app/safety/store.py`](../../app/safety/store.py)

If "guardrail" / "HITL" / "prompt injection" are unfamiliar, read
[concepts.md](../concepts.md#guardrail) first.

## `GuardrailResult` — the shared shape

```python
@dataclass
class GuardrailResult:
    flagged: bool
    reasons: list[str]
```

Both guardrails return this. `reasons` isn't just for debugging — it's
persisted into the audit log's `flag_reasons` column, so *why* something
was flagged is recoverable later, not just *that* it was.

## Input guardrail — prompt-injection heuristic

`check_input(message) -> GuardrailResult`. A fixed list of regex patterns
matched case-insensitively against the whole message, e.g.:

```python
r"ignore (all|any|the)? ?(previous|prior|above) instructions"
r"you are now (in )?(dan|jailbreak|developer) mode"
r"reveal (your|the) (system prompt|instructions)"
```

Any match flags the message; `reasons` lists every pattern that matched
(usually just one, but injection attempts sometimes trip several at
once). Pure regex — no LLM call, near-zero latency, runs before anything
else in the agent graph. See
[agent-loop.md](agent-loop.md#the-conditional-edge--the-actual-payoff-of-using-langgraph)
for how this connects to the graph's conditional edge.

**Deliberately over-inclusive, not exhaustive**: this catches common,
somewhat literal injection phrasing. A determined attacker using
paraphrasing, encoding, or a different language would likely get through.
See [decisions-and-limitations.md](../decisions-and-limitations.md) for
what a production system would add on top.

## Output guardrail — PII + risky-policy-phrase heuristic

`check_output(draft_text) -> GuardrailResult`. Two independent checks,
combined:

1. **PII patterns** (regex): email addresses, US-style phone numbers,
   credit-card-shaped digit runs, SSN-shaped digit runs.
2. **Policy phrases** (plain substring match, case-insensitive): a short
   list of over-promising language a support bot shouldn't say
   unsupervised — `"100% guaranteed"`, `"we promise"`, `"no matter what"`,
   `"unlimited refund"`.

**Intentionally trigger-happy.** For example the email pattern will flag
a draft that legitimately says "contact support at help@company.com" —
that's a false positive, not a bug: the cost of a false positive here is
one extra human review; the cost of a false *negative* would be real PII
reaching a customer unsupervised. For a safety check specifically, biasing
toward over-flagging is the correct trade-off. See how this connects to
routing in [agent-loop.md](agent-loop.md#decide_action--the-routing-logic) —
an output-guardrail flag *always* forces `action = "escalate"`, even
overriding a triage classification that would otherwise auto-respond.

## `SafetyStore` — audit log + approval queue

One class, one SQLite connection, two tables. SQLite chosen deliberately
for a single-process, low-volume workload with zero setup — see
[high-level-design.md](../high-level-design.md#why-these-technology-choices).

### `audit_log` — append-only

| Column | Meaning |
| --- | --- |
| `id`, `created_at` | |
| `message` | the customer's original message |
| `category`, `sentiment` | from `TriageResult` |
| `action` | the final decided action |
| `input_flagged`, `output_flagged` | 0/1 |
| `flag_reasons` | JSON-encoded list, combining both guardrails' reasons |

Written once per `/support/request` call, unconditionally — `log_audit()`
is called before the approval-queue branch, so *every* request is
recoverable later regardless of outcome.

### `approval_queue` — mutable, one row per item needing human review

| Column | Meaning |
| --- | --- |
| `id`, `created_at` | |
| `message`, `draft_response`, `category`, `action` | what a human needs to see to decide |
| `status` | `pending` → `approved` \| `rejected` |
| `reviewer_note`, `decided_at` | set when a human calls `decide_approval()` |

Only enqueued when `action != "respond"` — see
`app/api/routes.py::support_request`. `list_pending_approvals()` filters
to `status = 'pending'`, so a decided item naturally drops off the list
without being deleted (it's still in the table, and still shows up via
`GET /audit` if you look at `audit_log` instead — note `audit_log` and
`approval_queue` are separate, independently-queryable records of
overlapping events, not the same row).

### Concurrency note

`sqlite3.connect(..., check_same_thread=False)` — required because
FastAPI can serve one `SafetyStore` singleton (via `lru_cache`, see
`app/api/routes.py::get_safety_store`) from multiple worker threads.
Fine at this project's scale; see
[decisions-and-limitations.md](../decisions-and-limitations.md) for where
this would need to change.

## Full request → audit → approval flow

See the sequence diagram in
[high-level-design.md](../high-level-design.md#request-lifecycle-post-supportrequest).
