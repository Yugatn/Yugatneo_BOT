"""Staleness policy for the optional, non-critical Telegram /start response.

Telegram message.date is a UTC Unix timestamp. An update older than this
bounded replay window must not re-enter the experimental transport after a
24-hour deletion fence has expired. Missing/malformed timestamps fail closed
in the experimental branch only; emergency and deletion flows are untouched.
"""
from __future__ import annotations

import time

EXPERIMENTAL_START_MAX_AGE_SECONDS = 23 * 60 * 60
MAX_FUTURE_CLOCK_SKEW_SECONDS = 120


def is_fresh_experimental_start(message_date, *, now=None) -> bool:
    """Reject absent, future-dated or stale /start envelopes."""
    if type(message_date) is not int or message_date <= 0:
        return False
    current = int(time.time()) if now is None else now
    if type(current) is not int or current <= 0:
        return False
    age = current - message_date
    return (
        -MAX_FUTURE_CLOCK_SKEW_SECONDS <= age
        <= EXPERIMENTAL_START_MAX_AGE_SECONDS
    )
