"""Generate machine-readable offline quality summaries without user data."""
from __future__ import annotations

import json

from app.services.release_gate import release_gate, run_scenarios


def quality_report() -> dict[str, object]:
    gate = release_gate()
    return {
        "schema_version": "1",
        "suite": "offline_safety_regression",
        "total": gate["total"],
        "passed": gate["passed"],
        "failed": gate["failed"],
        "ready_for_controlled_review": gate["ready_for_controlled_review"],
        "scenarios": [
            {"name": item.name, "passed": item.passed, "detail": item.detail}
            for item in run_scenarios()
        ],
        "limitations": [
            "Does not validate clinical correctness or real-world effectiveness",
            "Does not cover all prompt injections or crisis expressions",
            "Passing does not authorize public deployment",
        ],
    }


def main() -> None:
    print(json.dumps(quality_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
