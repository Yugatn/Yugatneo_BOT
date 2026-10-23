"""Regression checks for polling failure isolation and privacy."""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "telegram_polling.py").read_text(encoding="utf-8")


def test_polling_handler_isolation():
    tree = ast.parse(SOURCE)
    main = next(n for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
    loops = [n for n in ast.walk(main)
             if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
             and n.iter.id == "updates"]
    assert len(loops) == 1
    loop = loops[0]
    tries = [node for node in loop.body if isinstance(node, ast.Try)]
    assert len(tries) == 1
    block = tries[0]
    assert block.handlers, "Individual update errors must be isolated"
    assert not block.finalbody, "Failed updates must not be acknowledged in finally"
    assert any(isinstance(n, ast.Break) for n in ast.walk(block)), "Stop after failure"


def test_polling_does_not_log_private_payload():
    assert 'log.error("Telegram update failed; awaiting safe retry (redacted)")' in SOURCE
    assert "log.exception(str(update))" not in SOURCE
