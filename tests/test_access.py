from types import SimpleNamespace
from app.services import access_store, monetization


def test_catalog_access_remains_free_after_seven_questions(tmp_path, monkeypatch):
    db = tmp_path / "access.sqlite3"
    monkeypatch.setattr(
        access_store,
        "get_settings",
        lambda: SimpleNamespace(database_url=f"sqlite:///{db}"),
    )

    decisions = [
        access_store.claim_question("telegram", "user-1", free_limit=7)
        for _ in range(12)
    ]
    assert all(decision["allowed"] for decision in decisions)
    assert decisions[6]["unlimited_free_access"] is True
    assert decisions[7]["reason"] == "free_access"
    assert decisions[-1]["question_index"] == 11


def test_tribute_buttons_are_off_by_default(monkeypatch):
    monkeypatch.setattr(
        monetization,
        "get_settings",
        lambda: SimpleNamespace(
            tribute_enabled=False,
            tribute_support_url="https://example.invalid/support",
            tribute_paid_product_url=None,
        ),
    )
    assert monetization.support_buttons() == []
    assert monetization.support_notice() == ""


def test_tribute_support_is_optional_and_does_not_gate_access(monkeypatch):
    monkeypatch.setattr(
        monetization,
        "get_settings",
        lambda: SimpleNamespace(
            tribute_enabled=True,
            tribute_support_url="https://example.invalid/support",
            tribute_paid_product_url=None,
        ),
    )
    buttons = monetization.support_buttons()
    assert len(buttons) == 1
    assert buttons[0]["url"] == "https://example.invalid/support"
    assert "Доступ к Yugatneo BOT бесплатный" in monetization.support_notice()
