from app.services.telegram_text import split_telegram_text


def test_long_report_is_not_truncated():
    report = ("Interests: game development\n" * 400) + "FINAL USER GOAL"
    parts = split_telegram_text(report)
    assert len(parts) > 1
    assert all(len(part) <= 4000 for part in parts)
    assert "".join(parts) == report
    assert parts[-1].endswith("FINAL USER GOAL")


def test_short_text_and_paragraphs():
    assert split_telegram_text("hello") == ["hello"]
    assert split_telegram_text("one\n" + "two" * 5, limit=5) == ["one\n", "twotw", "otwot", "wotwo"]


def test_empty_and_invalid_limit():
    import pytest
    assert split_telegram_text("") == [""]
    with pytest.raises(ValueError):
        split_telegram_text("hello", limit=0)
