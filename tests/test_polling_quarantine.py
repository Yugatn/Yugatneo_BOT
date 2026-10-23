"""Ensure quarantined updates halt polling without confirming Telegram offset."""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "telegram_polling.py").read_text()


def test_polling_quarantine_requires_operator():
    tree = ast.parse(SOURCE)
    main = next(n for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
    names = {n.id for n in ast.walk(main) if isinstance(n, ast.Name)}
    assert "quarantine_if_exhausted" in names
    assert "update_job_status" in names
    assert any(isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
               and isinstance(n.exc.func, ast.Name)
               and n.exc.func.id == "SystemExit" for n in ast.walk(main))
    assert "offset = update_id + 1" in SOURCE
    assert "Telegram update quarantined; operator review required" in SOURCE
