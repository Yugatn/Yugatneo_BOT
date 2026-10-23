import json

from app.services.quality_report import quality_report


def test_report_is_machine_readable_and_contains_no_raw_messages():
    report = quality_report()
    assert report["total"] >= 12
    assert report["passed"] == report["total"]
    assert len(report["scenarios"]) == report["total"]
    serialized = json.dumps(report, ensure_ascii=False)
    assert "telegram_user_id" not in serialized
    assert "chat_id" not in serialized
    assert "Passing does not authorize public deployment" in report["limitations"]
