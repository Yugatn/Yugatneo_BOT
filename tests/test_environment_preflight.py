from app.services.environment_preflight import environment_preflight
from cryptography.fernet import Fernet


def test_preflight_checks_presence_without_leaking_values(tmp_path):
    env = {
        "TELEGRAM_BOT_TOKEN": "placeholder",
        "YUGATNEO_DATA_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "YUGATNEO_OPERATOR_TOKEN": "x" * 40,
    }
    result = environment_preflight(tmp_path / "bot.sqlite", environ=env)
    assert result["environment_checks_passed"]
    assert not result["approved_for_closed_beta"]
    assert "placeholder" not in str(result)


def test_preflight_missing_configuration(tmp_path):
    result = environment_preflight(tmp_path / "bot.sqlite", environ={})
    assert not result["environment_checks_passed"]
    assert not result["checks"]["telegram_token_configured"]


def test_preflight_rejects_malformed_encryption_key(tmp_path):
    result = environment_preflight(tmp_path / "bot.sqlite", environ={
        "TELEGRAM_BOT_TOKEN": "configured",
        "YUGATNEO_DATA_ENCRYPTION_KEY": "not-a-valid-fernet-key",
        "YUGATNEO_OPERATOR_TOKEN": "x" * 40,
    })
    assert not result["checks"]["data_encryption_key_configured"]
    assert not result["environment_checks_passed"]
