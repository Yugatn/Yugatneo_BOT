"""Read-only preflight for the local closed-beta environment.

Never print secret values or contact external providers.
"""
import os
from pathlib import Path

from app.services.beta_readiness import beta_readiness
from app.services.key_validation import encryption_key_is_valid


def environment_preflight(db_path, *, environ=None):
    env = os.environ if environ is None else environ
    db = Path(db_path)
    checks = {
        "telegram_token_configured": bool(env.get("TELEGRAM_BOT_TOKEN")),
        "data_encryption_key_configured": encryption_key_is_valid(env.get("YUGATNEO_DATA_ENCRYPTION_KEY")),
        "operator_token_configured": len(env.get("YUGATNEO_OPERATOR_TOKEN", "")) >= 32,
        "database_parent_exists": db.parent.is_dir(),
        "database_parent_writable": os.access(db.parent, os.W_OK),
    }
    review = beta_readiness()
    return {
        "checks": checks,
        "environment_checks_passed": all(checks.values()),
        "external_reviews_pending": review["external_reviews_pending"],
        "approved_for_closed_beta": False,
        "approved_for_public_release": False,
    }
