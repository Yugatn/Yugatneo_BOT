"""Regression checks for polling failure isolation and privacy."""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "telegram_polling.py").read_text(encoding="utf-8")


def test_polling_handler_isolation():
    tree = ast.parse(SOURCE)
    main = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
    loops = [n for n in ast.walk(main) if isinstance(n, ast.For) and
             isinstance(n.iter, ast.Name) and n.iter.id == "updates"]
    assert len(loops) == 1
    loop = loops[0]
    assert len(loop.body) == 1 and isinstance(loop.body[0], ast.Try)
    assert loop.body[0].finalbody, "offset must advance even when an update fails"
    assert any(isinstance(n, ast.ExceptHandler) for n in loop.body[0].handlers)


def test_polling_does_not_log_private_payload():
    assert 'log.exception("Telegram update processing failed; update skipped")' in SOURCE
    assert "log.exception(str(update))" not in SOURCE
