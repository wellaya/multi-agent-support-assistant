import re
from dataclasses import dataclass, field

from app.agent.loop import handle_request
from eval.cases import EvalCase

CITATION_PATTERN = re.compile(r"\([\w_-]+\.md\)")


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    actual_category: str = ""
    actual_action: str = ""
    actual_input_flagged: bool = False
    draft_response: str = ""


async def run_case(case: EvalCase, graph) -> EvalResult:
    result = await handle_request(case.message, graph)
    checks: dict[str, bool] = {}

    if case.expected_category is not None:
        checks["category"] = result.triage.category == case.expected_category
    if case.expected_action is not None:
        checks["action"] = result.action == case.expected_action
    if case.expected_input_flagged is not None:
        checks["input_flagged"] = result.input_flagged == case.expected_input_flagged
    if case.expect_citation:
        checks["citation"] = bool(CITATION_PATTERN.search(result.draft_response))

    return EvalResult(
        case_id=case.id,
        passed=all(checks.values()) if checks else False,
        checks=checks,
        actual_category=result.triage.category,
        actual_action=result.action,
        actual_input_flagged=result.input_flagged,
        draft_response=result.draft_response,
    )


async def run_all(cases: list[EvalCase], graph) -> list[EvalResult]:
    return [await run_case(case, graph) for case in cases]
