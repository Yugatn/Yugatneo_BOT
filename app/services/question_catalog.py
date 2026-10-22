"""Offline-first, validated question bank for the Telegram coach.

GitHub JSON is the canonical published snapshot. Google Sheets may be used
as an editorial staging source but never for live per-message retrieval.
No user answers are written to this question catalogue.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "data" / "questions.ru.json"
EXTENDED_CATALOG = DEFAULT_CATALOG.with_name("questions.extended.ru.json")


@dataclass(frozen=True)
class CatalogQuestion:
    id: str
    category: str
    subcategory: str
    text: str
    purpose: str
    risk_level: str
    tags: tuple[str, ...]


class QuestionCatalog:
    def __init__(self, path: Path = DEFAULT_CATALOG):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        additional = []
        if Path(path).resolve() == DEFAULT_CATALOG.resolve() and EXTENDED_CATALOG.exists():
            extension = json.loads(EXTENDED_CATALOG.read_text(encoding="utf-8"))
            additional = extension.get("questions", [])
            if extension.get("count") != len(additional):
                raise ValueError("Extended catalog count does not match question rows")
        if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
            raise ValueError("Invalid question catalog")
        questions: list[CatalogQuestion] = []
        seen: set[str] = set()
        for raw in data["questions"] + additional:
            if not isinstance(raw, dict):
                raise ValueError("Invalid question row")
            qid = raw.get("id")
            category = raw.get("category")
            phrase = raw.get("text")
            if not all(isinstance(x, str) and x.strip() for x in (qid, category, phrase)):
                raise ValueError("Question needs id, category and text")
            if qid in seen:
                raise ValueError(f"Duplicate question ID: {qid}")
            seen.add(qid)
            tags = raw.get("tags") or []
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                raise ValueError(f"Invalid tags: {qid}")
            questions.append(CatalogQuestion(
                id=qid, category=category,
                subcategory=str(raw.get("subcategory", "")),
                text=phrase, purpose=str(raw.get("purpose", "")),
                risk_level=str(raw.get("risk_level", "standard")),
                tags=tuple(tags),
            ))
        if data.get("count") != len(data["questions"]):
            raise ValueError("Catalog count does not match question rows")
        self.version = str(data.get("version", "unknown"))
        self.questions = tuple(questions)

    def categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(q.category for q in self.questions))

    def select(self, category: str, *, seen_ids: set[str] | None = None,
               allow_sensitive: bool = False) -> CatalogQuestion | None:
        prior = seen_ids or set()
        for q in self.questions:
            if q.category != category or q.id in prior:
                continue
            if not allow_sensitive and q.risk_level not in {"standard"}:
                continue
            return q
        return None

    def by_id(self, question_id: str) -> CatalogQuestion | None:
        return next((q for q in self.questions if q.id == question_id), None)
