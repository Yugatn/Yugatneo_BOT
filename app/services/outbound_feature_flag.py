"""Explicit opt-in switch for experimental outbound delivery.

The switch is intentionally disabled by default. Enabling it alone does not
change the production Telegram transport; integration requires review.
"""
import os


def outbound_guard_requested(env=None):
    values = os.environ if env is None else env
    return values.get("YUGATNEO_EXPERIMENTAL_OUTBOUND", "").strip().lower() == "true"
