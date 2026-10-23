"""Privacy and input boundary regression tests for Telegram polling."""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "telegram_polling.py").read_text(encoding="utf-8")


def test_telegram_handler_has_private_chat_boundary():
    tree = ast.parse(SOURCE)
    handler = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_message")
    first = ast.get_source_segment(SOURCE, handler.body[0])
    assert first is not None
    assert 'chat.get("type") != "private"' in SOURCE
    assert 'user.get("is_bot")' in SOURCE


def test_telegram_handler_bounds_input_before_classification():
    assert 'if len(raw_text) > 4000:' in SOURCE
    assert SOURCE.index('if len(raw_text) > 4000:') < SOURCE.index('classify_crisis_message(text)')


def test_telegram_never_publishes_articles_from_chat():
    assert 'publish_public_article(' not in SOURCE
    assert 'TELEGRAPH_ACCESS_TOKEN' not in SOURCE
    assert 'report[:4000]' not in SOURCE
