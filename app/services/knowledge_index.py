"""Small versioned, inspectable knowledge index for psychoeducation.

Source references are bibliographic pointers, not a claim that every
interpretation is clinically validated. Never label hypotheses as facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Evidence = Literal["guideline", "research", "theory", "author_hypothesis"]


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    topic: str
    ru: str
    en: str
    evidence: Evidence
    source: str
    source_url: str
    reviewed: str
    min_age: int = 0


KNOWLEDGE_VERSION = "2026.10.1"
ENTRIES = (
    KnowledgeEntry(
        "learning_social", "parenting",
        "Дети могут усваивать модели поведения, наблюдая за значимыми взрослыми; "
        "наблюдение не означает неизбежного копирования каждого поступка.",
        "Children can learn patterns by observing significant adults; "
        "observation does not mean they inevitably copy every action.",
        "theory", "Bandura, Social Learning Theory (1977)",
        "https://www.worldcat.org/title/social-learning-theory/oclc/2631093",
        "2026-10-23",
    ),
    KnowledgeEntry(
        "scaffolding", "parenting",
        "Поддержка взрослого при выполнении посильной задачи может помочь ребёнку "
        "осваивать новые действия; сложность и помощь следует подбирать индивидуально.",
        "Adult support with an achievable task can help children learn new skills; "
        "the task and support should be adapted to the child.",
        "theory", "Vygotsky, Mind in Society (1978)",
        "https://www.worldcat.org/title/mind-in-society/oclc/3513653",
        "2026-10-23",
    ),
    KnowledgeEntry(
        "violence_prevention", "parenting",
        "Безопасная, поддерживающая среда и ненасильственные способы воспитания "
        "относятся к мерам профилактики насилия над детьми.",
        "Safe, supportive environments and nonviolent parenting practices "
        "are among approaches to preventing violence against children.",
        "guideline", "WHO, INSPIRE: Seven Strategies for Ending Violence Against Children (2016)",
        "https://www.who.int/publications/i/item/9789241565356",
        "2026-10-23",
    ),
    KnowledgeEntry(
        "author_philosophy", "philosophy",
        "Амбивалентный солипсизм — авторская философская концепция, "
        "а не установленная нейронаучная теория.",
        "Ambivalent solipsism is an author's philosophical concept, "
        "not an established neuroscientific theory.",
        "author_hypothesis", "Author's concept: Ambivalent Solipsism",
        "https://yugatn.github.io/ambivalent-solipsism/",
        "2026-10-23", min_age=18,
    ),
)


def lookup(topic: str, *, locale: str = "ru", age: int | None = None,
           include_author_hypotheses: bool = False) -> list[dict[str, str]]:
    if locale not in {"ru", "en"}:
        raise ValueError("Unsupported locale")
    result = []
    for item in ENTRIES:
        if item.topic != topic:
            continue
        if item.evidence == "author_hypothesis" and not include_author_hypotheses:
            continue
        # Unknown age is treated conservatively, not as adult.
        if item.min_age and (age is None or age < item.min_age):
            continue
        result.append({
            "id": item.id,
            "text": item.ru if locale == "ru" else item.en,
            "evidence": item.evidence,
            "source": item.source,
            "source_url": item.source_url,
            "reviewed": item.reviewed,
        })
    return result
