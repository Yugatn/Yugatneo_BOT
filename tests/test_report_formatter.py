from app.services.report_formatter import build_report


def test_empty_report_bilingual():
    assert "No saved" in build_report("en", [], None, None, [])
    assert "нет сохранённых" in build_report("ru", [], None, None, [])


def test_report_preserves_user_data_without_diagnosis():
    report = build_report(
        "en", [("Creativity", 7), ("Health", 5)],
        ("Game development", "Drawing", "Prototype"),
        ("Health", "Walk"), [("Creativity", "Sketch", "2026-10-23")]
    )
    assert "6.0/10" in report
    assert "Game development" in report
    assert "Prototype" in report
    assert "diagnosis" in report
    assert "Sketch" in report


def test_report_russian():
    report = build_report("ru", [("Творчество", 8)], None, None, [])
    assert "Творчество: 8/10" in report
    assert "психологический диагноз" in report
