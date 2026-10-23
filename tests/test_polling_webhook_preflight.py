"""Guard against running long polling while a Telegram webhook is active."""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "telegram_polling.py").read_text(encoding="utf-8")


def test_polling_checks_webhook_before_getupdates():
    tree = ast.parse(SOURCE)
    main = next(node for node in ast.walk(tree)
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "main")
    body = ast.get_source_segment(SOURCE, main)
    assert body is not None
    assert '"getWebhookInfo"' in body
    assert body.index('"getWebhookInfo"') < body.index('"getUpdates"')
    assert 'if webhook.get("url"):' in body
    assert "raise SystemExit(" in body
    assert '"deleteWebhook"' not in body


def test_polling_never_logs_bot_token():
    assert 'log.info("Polling started for @%s.' in SOURCE
    assert "log.info(token)" not in SOURCE
