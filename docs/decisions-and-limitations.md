# Decisions & Limitations

The "why" behind choices that would otherwise just look arbitrary, and a
candid list of what this project deliberately doesn't do — useful both
for anyone evaluating this as a portfolio piece and for future-you
deciding what to build next.

## Key decisions and their rationale

| Decision | Rationale | Trade-off accepted |
| --- | --- | --- |
| LangGraph over a hand-rolled async function | Wanted an explicit, inspectable graph structure once a real branch existed (Stage 4's guardrail short-circuit) rather than `if`-statements accumulating inside one function | Extra dependency and a small amount of conceptual overhead for what is, structurally, still a mostly-linear pipeline |
| Regex/heuristic guardrails, not an LLM-based classifier | Free, instant (~85ms), deterministic, easy to unit test exhaustively | Narrower coverage than a model-based classifier — see *Guardrail coverage* below |
| SQLite for the safety store | Zero ops overhead for a single-process, low-volume audit log/queue | Not safe for multi-process/multi-instance deployment as-is — see *Storage* below |
| Qdrant over Chroma | Matches the project's Docker-first workflow; same client class works in-memory for tests and against a real server for the app, with zero test-only code | Requires Docker running locally for anything beyond the offline test suite |
| sentence-transformers (local) over a hosted embeddings API | No extra API key, no per-embedding cost, works offline after first download | Slightly lower quality than a state-of-the-art hosted embedding model; ~90MB one-time download |
| Approval queue is *after-the-fact*, not a blocking interrupt | Simpler to build and reason about; still gives a human full visibility and veto power on anything not auto-sent | A `"respond"` action is sent (conceptually — see *No real delivery channel*) without a human ever seeing it first; there's no interrupt gate before that specific path |
| No paid hosting/deployment | Portfolio project, no operating budget, deployment was already "optional" in the original plan | The system only runs where you run it; nothing is continuously live to point a recruiter at |

## Known limitations

### Guardrail coverage

The input guardrail matches a fixed list of fairly literal English
injection phrasings. It will not catch: paraphrased attacks, attacks
encoded (base64, unusual unicode, etc.), attacks in other languages, or
multi-turn attacks that build up context across several messages (this
system only ever sees one message at a time — there's no conversation
history). A production system would likely add a model-based
classifier as a second layer, and/or a dedicated prompt-injection
detection service, rather than relying on regex alone.

### Output guardrail is heuristic, not exhaustive

Same shape of limitation as above — the PII patterns cover the common
cases (email, US-style phone, card-shaped digit runs, SSN-shaped digit
runs) but aren't a complete PII detector (no address detection, no names,
no non-US ID formats, etc.). The policy-phrase list is a handful of
illustrative examples, not a real legal/compliance-reviewed policy.

### `sources` field isn't cross-checked against the draft's actual citations

See [rag-pipeline.md](low-level-design/rag-pipeline.md#known-limitation-top_k-sourcing-is-coarse) —
`sources` lists every retrieved chunk's filename, not only the ones the
model actually cited in the drafted text.

### No conversation memory / multi-turn context

Every `/support/request` call is independent — there's no session or
thread concept, so a follow-up message doesn't know what was said before.
A real assistant handling an ongoing email thread or chat session would
need to carry conversation history into the triage/draft prompts.

### No real delivery channel

`"respond"` means "the system decided this is safe enough to not require
human review" — it does not actually email or message the customer
anywhere. There's no SMTP/chat-platform integration; wiring one up would
be the natural next step to make this more than a decision-making
backend.

### SQLite concurrency

`SafetyStore` uses one SQLite connection with `check_same_thread=False`,
fine for FastAPI's default threaded execution of sync-looking work at
this project's scale, but not something you'd run multiple app instances
against concurrently without moving to a real database server (Postgres,
etc.) with proper connection pooling.

### No authentication

Every endpoint, including the approval-decision and audit-log endpoints,
is open with no auth. Fine for local/demo use; a production deployment
would need at minimum an API key or session auth in front of
`/approvals`, `/audit`, and probably `/support/request` itself.

### Chunking is word-count-based, not token-based

`chunking.py` splits on whitespace-delimited words, not the model's
actual tokenizer — close enough for this project's short KB articles, but
imprecise for controlling exact prompt-token budgets at scale.

### Eval suite size and scope

27 cases is enough to catch obvious regressions and was chosen to fit
CLAUDE.md's ~20-30 case target, not because it's exhaustive. It doesn't
cover: multi-language input, extremely long messages, or adversarial
inputs designed to evade the *specific* regex patterns currently in
place (as opposed to generic/obvious injection phrasing).

## Natural next steps (not built, listed for completeness)

- A blocking HITL interrupt before `"respond"` sends anything (LangGraph
  supports this natively — see [extending.md](extending.md#add-a-new-agent-node))
- A real email/chat delivery integration
- Conversation/session memory
- A model-based (not just regex) guardrail layer, run alongside the
  heuristics rather than instead of them
- Moving `SafetyStore` to a real database if this ever needed multi-instance deployment
- Basic auth in front of the review/audit endpoints
