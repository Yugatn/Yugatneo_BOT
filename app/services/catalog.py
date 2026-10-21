import json
from functools import lru_cache
from pathlib import Path
from app.core.models import Question

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "questions.ru.json"


@lru_cache(maxsize=1)
def load_questions() -> list[Question]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [Question.model_validate(item) for item in raw["questions"]]


def get_question(index: int) -> Question:
    questions = load_questions()
    if not questions:
        raise RuntimeError("Question catalog is empty")
    return questions[index % len(questions)]
