"""Run the eval suite against the REAL Claude API + real Qdrant-backed
retrieval and write a markdown report to eval/results.md.

Prerequisites: Docker/Qdrant running with the KB ingested (see
scripts/ingest_kb.py), and a real ANTHROPIC_API_KEY in .env.

Usage: python eval/run_eval.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.routes import get_agent_graph
from eval.cases import CASES
from eval.harness import run_all

RESULTS_PATH = Path(__file__).resolve().parent / "results.md"


async def main() -> None:
    graph = get_agent_graph()
    results = await run_all(CASES, graph)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    lines = [f"{'PASS' if r.passed else 'FAIL'}  {r.case_id:<20} {r.checks}" for r in results]
    print("\n".join(lines))
    print(f"\n{passed}/{total} passed ({passed / total:.0%})")

    _write_report(results, passed, total)
    print(f"\nWrote {RESULTS_PATH}")


def _write_report(results, passed: int, total: int) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = "\n".join(
        f"| {r.case_id} | {'✅' if r.passed else '❌'} | {r.actual_category} | "
        f"{r.actual_action} | {r.checks} |"
        for r in results
    )
    report = f"""# Eval Results

Generated {generated_at} — **{passed}/{total} passed ({passed / total:.0%})**

| Case | Result | Category | Action | Checks |
| --- | --- | --- | --- | --- |
{rows}
"""
    RESULTS_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
