"""Fail-closed recovery planning, without executing changes.

A plan is a proposal, never an instruction to launch or overwrite software.
"""
from pathlib import Path


def plan_recovery(findings, registry):
    by_id = {item["id"]: item for item in registry["agents"]}
    actions = []
    for finding in findings:
        if finding["status"] == "verified":
            continue
        agent = by_id.get(finding["id"])
        if agent is None:
            actions.append({"id": finding["id"], "action": "manual_investigation", "reason": "unknown_agent"})
            continue
        actions.append({
            "id": finding["id"],
            "action": "request_human_review",
            "reason": finding["status"],
            "expected_sha256": agent["sha256"],
            "candidate_path": str(Path(agent["path"])),
            "auto_execute": False,
        })
    return {"status": "review_required" if actions else "healthy", "proposals": actions}
