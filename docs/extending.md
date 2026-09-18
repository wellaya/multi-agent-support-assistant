# Extending the Project

Practical, step-by-step guides for the changes you're most likely to want
to make later.

## Add a new LLM provider

The whole point of [the provider abstraction](low-level-design/provider-layer.md)
is that this is a self-contained change.

1. Create `app/providers/<vendor>_provider.py` with a class implementing
   both `LLMProvider` methods:
   ```python
   class AzureOpenAIProvider(LLMProvider):
       async def generate(self, messages, **kwargs) -> str: ...
       async def generate_structured(self, messages, schema, **kwargs) -> dict: ...
   ```
   - `generate` just needs to translate `messages` into that vendor's
     chat-completion call and return the text.
   - `generate_structured` needs to translate the JSON Schema into
     whatever that vendor calls structured output (OpenAI: `tools` +
     `tool_choice` work almost identically to Claude's; Gemini: function
     calling with a forced function).
2. Add any new settings it needs (API key, endpoint, deployment name) to
   `app/config.py`'s `Settings` class, and to `.env.example`.
3. Swap the instantiation in `app/api/routes.py`:
   ```python
   _provider = AzureOpenAIProvider()   # was: ClaudeProvider()
   ```
   Nothing else changes — not the agent graph, not the RAG code, not any
   route function.
4. Run `pytest` — the 23 offline tests never touch a real provider, so
   they should still pass unchanged; they're your regression check that
   nothing outside the provider layer assumed anything Claude-specific.

## Add a new knowledge-base article

1. Add a new `.md` file to `data/kb/`.
2. Re-run ingestion: `python scripts/ingest_kb.py` (this recreates the
   Qdrant collection from scratch each time — see
   [rag-pipeline.md](low-level-design/rag-pipeline.md#ingestion--ingestpy) —
   so it picks up new and edited files alike).
3. If the new topic should be its own triage category, add it to the
   `Literal[...]` in `app/agent/schemas.py::TriageResult.category` — right
   now it's a closed set matching the 5 mock KB topics plus `"other"`.
4. Consider adding a couple of eval cases for it in `eval/cases.py` (see
   [eval-and-testing.md](eval-and-testing.md)).

## Add a new agent node

Say you want a genuine HITL **interrupt** — pause before auto-sending a
`"respond"` action, not just queueing `"escalate"`/`"ticket"` outcomes
after the fact (today's HITL queue is *after* the decision, not blocking
it).

1. In `app/agent/graph.py`, add a new node function inside
   `build_agent_graph` (it can close over `provider`/`retrieve_fn` the
   same way existing nodes do, or over new dependencies you pass into the
   factory function).
2. Add it with `graph.add_node("your_node", your_node_fn)`.
3. Wire it in with `graph.add_edge(...)` (straight line) or
   `graph.add_conditional_edges(...)` (branch on state — see the
   `input_guardrail → blocked/triage` branch in
   [agent-loop.md](low-level-design/agent-loop.md) for a worked example).
4. If the node needs new state, add the field to `AgentState` (remember
   it's `total=False` — not every path through the graph needs to set
   every field).
5. LangGraph natively supports pausing a graph mid-execution for external
   input (an "interrupt") and resuming it later — that's the mechanism
   you'd reach for for a true pre-send approval gate. Consult LangGraph's
   own docs for the current API, since this project doesn't use that
   feature yet (see [decisions-and-limitations.md](decisions-and-limitations.md)).
6. Add a test in `tests/test_agent_loop.py` following the existing
   pattern: build the graph with a `FakeProvider`, assert on the
   resulting `AgentResult`.

## Add a new guardrail rule

**Input guardrail** (`app/safety/input_guardrail.py`): add a new regex
string to `INJECTION_PATTERNS`. Keep patterns lowercase-oriented (the
message is lowercased before matching) and prefer matching a specific
phrase pattern over a single common word, to limit false positives.

**Output guardrail** (`app/safety/output_guardrail.py`): either add a new
entry to `PII_PATTERNS` (a regex) or `POLICY_PHRASES` (a plain substring,
case-insensitive). Remember: false positives here are the *safe* failure
mode (they just route to human review), so when in doubt, add the
pattern.

Either way, add a test case to `tests/test_guardrails.py` (a message that
should flag, and — just as important — one nearby message that shouldn't,
to catch overly broad patterns) and consider adding a live eval case in
`eval/cases.py` if it's a new *kind* of attack, not just a new phrasing of
an existing one.

## Add a new API endpoint

Follow the existing pattern in `app/api/routes.py`:
1. Define request/response Pydantic models.
2. Add a route function taking any dependencies via `Depends(get_*)` —
   reuse an existing getter if one already provides what you need, or add
   a new `@lru_cache`-decorated getter following the existing style if
   not.
3. Document it in [low-level-design/api-reference.md](low-level-design/api-reference.md).
