"""Repeatable offline acceptance exercise with synthetic data only.

Run: python -m app.services.offline_acceptance
No Telegram credentials, server, or external requests are required.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cryptography.fernet import Fernet

from app.services.backup_restore import create_verified_backup, verify_restore_roundtrip
from app.services.guided_report_storage import read_report, save_report
from app.services.offline_telegram_simulator import FakeTelegramTransport
from app.services.outbound_delivery import deliver_user_reserved
from app.services.outbound_delivery import reserve_user_delivery
from app.services.personal_data import delete_telegram_user_records
from app.services.report_readiness import count_unreadable_reports


async def _transport_exercise(db_path):
    simulator = FakeTelegramTransport()
    async def send_ok():
        await simulator.send_message("offline-ok")
    assert await deliver_user_reserved(db_path, "synthetic-user", "offline-ok", send_ok)
    assert not await deliver_user_reserved(db_path, "synthetic-user", "offline-ok", send_ok)
    assert simulator.calls["offline-ok"] == 1

    uncertain = FakeTelegramTransport(fail_after_accept=True)
    async def send_uncertain():
        await uncertain.send_message("offline-unknown")
    try:
        await deliver_user_reserved(
            db_path, "synthetic-user", "offline-unknown", send_uncertain
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("Expected synthetic lost acknowledgement")
    assert not await deliver_user_reserved(
        db_path, "synthetic-user", "offline-unknown", send_uncertain
    )
    assert uncertain.calls["offline-unknown"] == 1
    return {"normal_send": "passed", "uncertain_send": "passed"}


def run_offline_acceptance():
    """Return only synthetic test statuses; never return key or report content."""
    with TemporaryDirectory(prefix="yugatneo-offline-") as directory:
        base = Path(directory)
        database = base / "source.sqlite"
        backup = base / "backup.sqlite"
        restored = base / "restored.sqlite"
        key = Fernet.generate_key().decode("ascii")
        with patch.dict(os.environ, {"YUGATNEO_DATA_ENCRYPTION_KEY": key}):
            save_report(database, "synthetic-user", "Synthetic test summary")
            assert create_verified_backup(database, backup).verified
            assert verify_restore_roundtrip(backup, restored).verified
            assert read_report(restored, "synthetic-user") == "Synthetic test summary"
            assert count_unreadable_reports(restored) == {
                "checked": 1, "unreadable": 0
            }
            transport = asyncio.run(_transport_exercise(database))
            deleted = delete_telegram_user_records(database, "synthetic-user")
            assert deleted["guided_reflection_reports"] == 1
            assert deleted["user_outbound_delivery"] == 2
            assert read_report(database, "synthetic-user") is None
            assert reserve_user_delivery(
                database, "synthetic-user", "late-after-deletion"
            ) is False
            assert reserve_user_delivery(
                database, "other-synthetic-user", "new-user-event"
            ) is True
        return {
            "offline_only": True,
            "backup_restore": "passed",
            "encrypted_report_readable": "passed",
            "user_data_deletion": "passed",
            "post_deletion_delivery_blocked": "passed",
            **transport,
        }


if __name__ == "__main__":
    print(json.dumps(run_offline_acceptance(), sort_keys=True))
