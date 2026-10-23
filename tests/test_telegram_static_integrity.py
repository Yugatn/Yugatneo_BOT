"""Static regression checks for Telegram MVP wiring.

These tests deliberately do not contact Telegram or external AI providers.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_telegram_polling_parses():
    ast.parse((ROOT / "app" / "telegram_polling.py").read_text(encoding="utf-8"))


def test_telegram_routes_and_language_storage():
    source = (ROOT / "app" / "telegram_polling.py").read_text(encoding="utf-8")
    for command in (
        "/start", "/language", "/lang_ru", "/lang_en",
        "/parenting", "/parenting_all", "/parenting_en",
        "/career", "/report", "/age", "/delete_my_data",
    ):
        assert command in source, command
    assert "from app.services.language_preferences import" in source
    assert "CREATE TABLE IF NOT EXISTS user_locale" not in source
    assert 'if text in {"/lang_ru", "/lang_en"}:' in source
    assert source.count('if text in {"/lang_ru", "/lang_en"}:') == 1


def test_knowledge_sources_parse():
    for path in (
        "app/services/parenting_knowledge.py",
        "app/services/parenting_index.py",
        "app/services/parenting_en.py",
        "app/services/language_preferences.py",
    ):
        ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
