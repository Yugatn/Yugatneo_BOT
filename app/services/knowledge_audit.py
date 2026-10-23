"""Deterministic checks for source-backed psychoeducation outputs.

This checks provenance and conservative boundaries, not clinical correctness.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.knowledge_index import lookup


@dataclass(frozen=True)
class AuditResult:
    passed: bool
    issues: tuple[str, ...]
    sources_checked: int


def audit_knowledge(topic: str, *, locale: str = "ru", age: int | None = None,
                    include_author_hypotheses: bool = False) -> AuditResult:
    records = lookup(topic, locale=locale, age=age,
                     include_author_hypotheses=include_author_hypotheses)
    issues: list[str] = []
    for entry in records:
        if not entry["text"].strip():
            issues.append(f"{entry['id']}: missing text")
        if not entry["source"].strip():
            issues.append(f"{entry['id']}: missing source")
        url = urlparse(entry["source_url"])
        if url.scheme != "https" or not url.netloc:
            issues.append(f"{entry['id']}: invalid source URL")
        if entry["evidence"] not in {"guideline", "research", "theory", "author_hypothesis"}:
            issues.append(f"{entry['id']}: invalid evidence label")
        if entry["evidence"] == "author_hypothesis" and not include_author_hypotheses:
            issues.append(f"{entry['id']}: unexpected author hypothesis")
    return AuditResult(not issues, tuple(issues), len(records))
