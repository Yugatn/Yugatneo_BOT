from types import SimpleNamespace
from app.services import security


def test_rate_limit_and_one_time_human_code(tmp_path, monkeypatch):
    db = tmp_path / "security.sqlite3"
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite:///{db}"))

    assert security.allow_request("test-ip", limit=2, window_seconds=60)
    assert security.allow_request("test-ip", limit=2, window_seconds=60)
    assert not security.allow_request("test-ip", limit=2, window_seconds=60)

    subject = "telegram:12345"
    code = security.issue_human_code(subject, ttl_seconds=60)
    assert not security.is_human_verified(subject)
    assert security.consume_human_code(subject, code)
    assert security.is_human_verified(subject)
    assert not security.consume_human_code(subject, code)
    assert not security.consume_human_code("telegram:someone-else", code)
