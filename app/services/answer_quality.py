"""Conservative deterministic pre-release checks for generated psychoeducation.

These checks are defense-in-depth heuristics, not proof of clinical safety.
Unreviewed text is never promoted to an authoritative recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from app.services.knowledge_index import lookup


@dataclass(frozen=True)
class Evaluation:
    approved: bool
    findings: tuple[str, ...]


_DIAGNOSES = (
    re.compile(r"\b(?:у\s+вас|у\s+тебя|вам\s+поставлен)\s+(?:диагноз\s+)?"
               r"(?:депрессия|биполярное\s+расстройство|шизофрения|сдвг)\b", re.I),
    re.compile(r"\byou\s+(?:have|definitely\s+have)\s+"
               r"(?:depression|bipolar\s+disorder|schizophrenia|adhd)\b", re.I),
)
_CERTAINTY = (
    "научно доказано, что амбивалентный солипсизм",
    "science proves ambivalent solipsism",
)
_UNSAFE_AUTHORITY = (
    "гарантированно вылечит", "guaranteed cure",
)


def evaluate_answer(text: str, *, topic: str, age: int | None = None,
                    locale: str = "ru", cited_ids: tuple[str, ...] = (),
                    include_author_hypotheses: bool = False) -> Evaluation:
    findings: list[str] = []
    if not text.strip():
        findings.append("empty_answer")
    if len(text) > 6000:
        findings.append("overlong_answer")
    if any(pattern.search(text) for pattern in _DIAGNOSES):
        findings.append("unsupported_diagnosis")
    lowered = text.casefold()
    if any(phrase in lowered for phrase in _CERTAINTY):
        findings.append("hypothesis_as_science")
    if any(phrase in lowered for phrase in _UNSAFE_AUTHORITY):
        findings.append("unsupported_treatment_guarantee")
    if locale not in ("ru", "en"):
        findings.append("unsupported_locale")
        return Evaluation(False, tuple(findings))
    allowed = {
        entry["id"]: entry for entry in lookup(
            topic, locale=locale, age=age,
            include_author_hypotheses=include_author_hypotheses
        )
    }
    if not cited_ids:
        findings.append("missing_citations")
    for cited_id in cited_ids:
        if cited_id not in allowed:
            findings.append(f"unavailable_citation:{cited_id}")
        elif not allowed[cited_id]["source_url"].startswith("https://"):
            findings.append(f"invalid_citation:{cited_id}")
    if len(set(cited_ids)) != len(cited_ids):
        findings.append("duplicate_citations")
    return Evaluation(not findings, tuple(findings))
