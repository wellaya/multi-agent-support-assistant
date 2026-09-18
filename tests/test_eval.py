"""Eval suite against the REAL Claude API + real Qdrant-backed retrieval.

Excluded from default `pytest` runs (see pytest.ini). Costs API credits.
Prerequisites: Docker/Qdrant running with the KB ingested, and a real
ANTHROPIC_API_KEY in .env. Run explicitly with:

    pytest -m eval -v
"""

import pytest

from app.api.routes import get_agent_graph
from eval.cases import CASES
from eval.harness import run_case

pytestmark = pytest.mark.eval


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
async def test_eval_case(case):
    graph = get_agent_graph()
    result = await run_case(case, graph)

    assert result.passed, (
        f"case={case.id} checks={result.checks} "
        f"actual_category={result.actual_category} actual_action={result.actual_action} "
        f"draft={result.draft_response!r}"
    )
