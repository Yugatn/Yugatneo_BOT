"""Token-gated operator recovery entry point.

The token is supplied through a server-side environment variable, never
through a Telegram chat. Use host access controls as an additional boundary.
"""
import hmac
import os

from app.services.update_operations import release_quarantined


def authorized_release(db_path, update_id, token):
    expected = os.environ.get("YUGATNEO_OPERATOR_TOKEN", "")
    if not expected or len(expected) < 32:
        raise PermissionError("Operator token is not configured securely")
    if not isinstance(token, str) or not hmac.compare_digest(expected, token):
        raise PermissionError("Invalid operator credentials")
    return release_quarantined(db_path, update_id, operator_approved=True)
