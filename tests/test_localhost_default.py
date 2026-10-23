from app.core.config import Settings


def test_service_listens_only_on_loopback_by_default(monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    assert Settings(_env_file=None).host == "127.0.0.1"


def test_external_bind_requires_explicit_configuration(monkeypatch):
    monkeypatch.setenv("HOST", "0.0.0.0")
    assert Settings(_env_file=None).host == "0.0.0.0"
