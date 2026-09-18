# Eval Harness & Test Suite

Two different kinds of correctness are checked here, deliberately kept
separate — see [concepts.md](concepts.md#eval-evaluation-harness) for why
unit tests alone aren't enough for an LLM-backed system.

| | Tests in `tests/` | Eval in `eval/` |
| --- | --- | --- |
| Question answered | Does the *code* behave correctly given a fixed response? | Does the *real model* actually classify/answer well? |
| LLM calls | None — a `FakeProvider` returns scripted responses | Real Claude API calls |
| Cost | Free | Costs API credits |
| Speed | Seconds | ~1-3 minutes for the full suite |
| Runs in CI? | Yes, every push | No — manual only |
| Command | `pytest` | `pytest -m eval` or `python eval/run_eval.py` |

## The offline test suite (`tests/`) — 23 tests

| File | Covers |
| --- | --- |
| `test_chat_endpoint.py` | `/health`, `/chat` via `TestClient` + a `FakeProvider` override |
| `test_rag_retrieval.py` | Real embedding model + in-memory Qdrant — checks retrieval *ranking quality* is real, not mocked |
| `test_agent_loop.py` | The full LangGraph, with a `FakeProvider` whose `generate`/`generate_structured` branch on keywords in the prompt to deterministically drive each `decide_action` outcome (`respond`/`escalate`/`ticket`), plus the input-guardrail short-circuit (asserted via a call-counter on the fake provider — `generate_calls == 0`) and the output-guardrail override |
| `test_guardrails.py` | `check_input`/`check_output` directly — pure regex, no dependencies at all |
| `test_safety_store.py` | `SafetyStore(":memory:")` — audit log + approval queue CRUD |

**Why a `FakeProvider` and not a mocking library**: `LLMProvider` is a
small ABC, so a hand-written fake subclass is simpler and more readable
than `unittest.mock` patching — see any `FakeProvider` class in the test
files above. It's also swapped in via FastAPI's own dependency-override
mechanism (`app.dependency_overrides[get_provider] = lambda: FakeProvider()`),
not monkeypatching, so it exercises the exact same code path as
production.

**Why `pytest.ini` matters**: it registers a custom `eval` marker and sets
`addopts = -m "not eval"`, so a plain `pytest` (what CI and this whole
project's habits use) *automatically* skips the costly eval suite without
anyone needing to remember a flag. See [`pytest.ini`](../pytest.ini).

## The eval suite (`eval/`) — 27 cases

| File | Role |
| --- | --- |
| `cases.py` | `EvalCase` dataclass + the 27 `CASES` (see breakdown below) |
| `harness.py` | `run_case()`/`run_all()` — calls the real `handle_request()` and grades the result against each case's expected fields |
| `run_eval.py` | CLI: builds the real graph via `app.api.routes.get_agent_graph()` (same wiring the running app uses), runs every case, prints a table, writes `results.md` |
| `tests/test_eval.py` | Thin `@pytest.mark.eval` pytest wrapper around the same harness, so the same cases can also be run/filtered with normal pytest tooling |
| `results.md` | The output of the last `run_eval.py` run — committed so it's visible without re-running |

### Case breakdown (27 total)

| Category | Count | Checks |
| --- | --- | --- |
| In-scope, calm (one per KB topic × 3-4 phrasings) | 16 | `category`, `action == "respond"`, draft contains a `(*.md)` citation |
| Angry/frustrated | 3 | `action == "escalate"` |
| Off-topic | 3 | `category == "other"`, `action == "ticket"` |
| Prompt-injection phrasing | 5 | `action == "escalate"`, `input_flagged == True` — **free**, since these never reach the LLM |

**Prerequisites to run**: Docker/Qdrant up with the KB ingested (`docker
compose up -d` + `python scripts/ingest_kb.py`), and a real
`ANTHROPIC_API_KEY` in `.env` — same as running the app itself.

```bash
python eval/run_eval.py
# or, via pytest:
pytest -m eval -v
```

### Reading `EvalCase`/`EvalResult`

```python
@dataclass
class EvalCase:
    id: str
    message: str
    expected_category: str | None = None
    expected_action: str | None = None
    expected_input_flagged: bool | None = None
    expect_citation: bool = False
```
Any `expected_*` field left `None` (or `expect_citation=False`) is simply
not checked for that case — e.g. the angry/off-topic cases don't assert
on `expect_citation` since the draft's exact wording there is less
important than the routing decision. Grading in `harness.run_case()`
builds a `checks: dict[str, bool]` and passes only if every check that
*was* run is `True`.

### A real example of the eval suite catching a bad assumption, not a bug

The case `password_reset_4` ("I no longer have access to my old email,
can you still help me reset my password?") was originally written
expecting `action == "respond"`. The live run disagreed — Claude
escalated it. Looking at the KB article, that's *correct*: `password_reset.md`
explicitly says losing access to your account email requires manual
identity verification by a human. The eval case's expectation was wrong,
not the model's behavior — it was corrected to `expected_action="escalate"`.
This is the actual value of running a live eval suite instead of writing
fixed expected outputs and calling it done: it surfaces exactly this kind
of mismatch between an assumption and the real, considered model behavior.

## Continuous Integration

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every
push/PR: checkout → set up Python 3.13 (with pip caching) → cache the
sentence-transformers model directory (`~/.cache/huggingface/hub`, so it
isn't re-downloaded every run) → `pip install -r requirements.txt` →
`pytest -v`. No secrets, no Docker service, no cost — this only ever runs
the 23 offline tests, per the `pytest.ini` default exclusion above.
