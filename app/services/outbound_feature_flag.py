"""Explicit opt-in switch for experimental outbound delivery.

The switch is intentionally disabled by default. Enabling it alone does not
change the production Telegram transport; integration requires review.
"""
import os


def outbound_guard_requested(env=None):
    """Opt in only for isolated non-production environments."""
    values = os.environ if env is None else env
    enabled = values.get("YUGATNEO_EXPERIMENTAL_OUTBOUND", "").strip().lower() == "true"
    environment = values.get("APP_ENV", "development").strip().lower()
    return enabled and environment in {"development", "test", "staging"}
