# Low-Level Design: Provider Layer

Files: [`app/providers/base.py`](../../app/providers/base.py),
[`app/providers/claude_provider.py`](../../app/providers/claude_provider.py),
[`app/config.py`](../../app/config.py)

## Why this layer exists

Every other module in the codebase (the agent loop, `/chat`) depends only
on the `LLMProvider` interface — never on the `anthropic` package
directly. That's the entire point: it's the seam where Azure OpenAI,
OpenAI, or Gemini can be plugged in later by writing one new class, with
zero changes anywhere else. See [concepts.md](../concepts.md#provider-abstraction)
if this pattern (program to an interface, not an implementation) is new
to you.

## The interface

```python
class LLMProvider(ABC):
    async def generate(self, messages: list[dict], **kwargs) -> str: ...
    async def generate_structured(self, messages: list[dict], schema: dict, **kwargs) -> dict: ...
```

Two methods, both intentionally minimal:

- **`generate`** — free-text chat completion. `messages` is the standard
  `[{"role": "user"|"assistant", "content": str}]` shape most chat APIs
  share, so implementing this for a new vendor is usually a thin
  translation layer. Used for the draft-writing step and the plain
  `/chat` endpoint.
- **`generate_structured`** — takes a JSON Schema (`schema`) and returns a
  `dict` guaranteed to match it. Used for triage classification, where a
  reliable typed result matters more than natural-sounding prose.

Neither method leaks any vendor-specific concept (Claude's "tools",
OpenAI's "functions", etc.) into the interface itself — that translation
is each implementation's job.

## `ClaudeProvider.generate_structured` — how it actually gets structure

Claude has no separate "structured output" API distinct from tool use, so
`generate_structured` is implemented as **forced tool use**: it defines
exactly one tool whose `input_schema` *is* the caller's JSON Schema, then
sets `tool_choice={"type": "tool", "name": tool_name}` — which forces
Claude to respond by calling that tool rather than replying in free text.
The response's `tool_use` content block's `.input` is already a dict
matching the schema, so there's no text-parsing step at all.

```python
tools=[{"name": tool_name, "description": "...", "input_schema": schema}]
tool_choice={"type": "tool", "name": tool_name}
```

Caller side ([`app/agent/nodes.py`](../../app/agent/nodes.py)), the schema
comes straight from the Pydantic model that will hold the result — one
source of truth, no hand-maintained JSON Schema:

```python
result = await provider.generate_structured(
    messages=[...],
    schema=TriageResult.model_json_schema(),
    tool_name="submit_triage",
)
return TriageResult(**result)
```

## Configuration

`app/config.py` defines a Pydantic `Settings` object (loaded from `.env`
via `pydantic-settings`) holding every provider- and infra-level setting
the app needs, including `anthropic_api_key` and `anthropic_model`. A
module-level `settings = Settings()` singleton is imported wherever
config is needed. See [.env.example](../../.env.example) for the full
list of variables.

## How the singleton is wired

`app/api/routes.py` creates one `_provider = ClaudeProvider()` at import
time and exposes it through a `get_provider()` function used as a FastAPI
`Depends(...)`. Routes never construct a provider themselves — this is
what lets tests override `get_provider` with a fake implementation
(`app.dependency_overrides[get_provider] = lambda: FakeProvider()`)
without touching route code at all. See
[eval-and-testing.md](../eval-and-testing.md) for how the offline test
suite uses this.

## Adding a new provider

See [extending.md](../extending.md#add-a-new-llm-provider) for the
step-by-step guide.
