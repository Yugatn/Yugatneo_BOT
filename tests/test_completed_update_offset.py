from pathlib import Path


def test_completed_update_advances_polling_offset():
    source = Path("app/telegram_polling.py").read_text()
    assert "if job and job[0] == 'done':" in source
    assert "offset = update_id + 1" in source
    assert "continue" in source
