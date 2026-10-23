"""Fail-closed, source-bounded answer delivery.

Offline deterministic rendering avoids invented citations. AI output must pass
separate review before it can be displayed; quality checks alone are insufficient.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.answer_quality import Evaluation, evaluate_answer
from app.services.knowledge_index import lookup


@dataclass(frozen=True)
class Delivery:
    text: str
    delivered: bool
    findings: tuple[str, ...] = ()


def safe_fallback(locale: str = "ru") -> str:
    if locale == "en":
        return ("I cannot verify this answer against the available sources. "
                "Please choose a source-backed topic or consult a qualified professional "
                "for an individual health concern.")
    return ("Не удалось проверить ответ по доступным источникам. "
            "Можно выбрать тему из проверяемой библиотеки; "
            "по индивидуальному вопросу здоровья обратитесь к профильному специалисту.")


def source_bounded_answer(topic: str, *, locale: str = "ru",
                          age: int | None = None) -> Delivery:
    """Only deliver text taken verbatim from indexed entries, with citations."""
    if locale not in {"ru", "en"}:
        return Delivery(safe_fallback("ru"), False, ("unsupported_locale",))
    records = lookup(topic, locale=locale, age=age)
    if not records:
        return Delivery(safe_fallback(locale), False, ("no_sources",))
    lines = []
    for entry in records:
        lines.append(
            f"• {entry['text']}\n"
            f"  [{entry['evidence']}] {entry['source']}\n"
            f"  {entry['source_url']}"
        )
    text = "\n\n".join(lines)
    result = evaluate_answer(
        text, topic=topic, locale=locale, age=age,
        cited_ids=tuple(entry["id"] for entry in records),
    )
    if not result.approved:
        return Delivery(safe_fallback(locale), False, result.findings)
    return Delivery(text, True)


def review_external_draft(draft: str, *, topic: str, locale: str = "ru",
                          age: int | None = None,
                          cited_ids: tuple[str, ...] = ()) -> Delivery:
    """Never auto-publish an unreviewed external model draft.

    Structural evaluation is recorded for later human review. Even a passing
    draft stays blocked until a separately designed verification workflow exists.
    """
    result = evaluate_answer(
        draft, topic=topic, locale=locale, age=age, cited_ids=cited_ids,
    )
    return Delivery(safe_fallback(locale), False,
                    ("human_review_required",) + result.findings)
