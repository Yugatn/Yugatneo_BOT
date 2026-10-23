"""Offline Telegram API simulator for repeatable transport acceptance tests.

No network requests, tokens, or user data are required.
"""
from __future__ import annotations

from collections import defaultdict


class FakeTelegramTransport:
    def __init__(self, fail_after_accept=False, fail_before_accept=False):
        self.fail_after_accept = fail_after_accept
        self.fail_before_accept = fail_before_accept
        self.messages = []
        self.calls = defaultdict(int)

    async def send_message(self, event_key, text="test"):
        self.calls[event_key] += 1
        if self.fail_before_accept:
            raise ConnectionError("simulated failure before remote acceptance")
        self.messages.append((event_key, text))
        if self.fail_after_accept:
            raise TimeoutError("simulated lost acknowledgement")
        return {"ok": True, "message_id": len(self.messages)}
