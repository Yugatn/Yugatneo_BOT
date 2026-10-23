from app.services.language_preferences import (
    EN_TOPICS, english_topic, get_language, set_language,
)
from app.services.parenting_knowledge import TOPICS


def test_language_default_and_switch(tmp_path):
    path = tmp_path / "bot.sqlite3"
    assert get_language(path, "user1") == "ru"
    set_language(path, "user1", "en")
    assert get_language(path, "user1") == "en"
    assert get_language(path, "user2") == "ru"
    set_language(path, "user1", "ru")
    assert get_language(path, "user1") == "ru"


def test_english_parenting_coverage():
    assert {topic.key for topic in TOPICS} <= set(EN_TOPICS)
    for topic in TOPICS:
        assert english_topic(topic.key).startswith("📘 ")


def test_invalid_language_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        set_language(tmp_path / "bot.sqlite3", "user", "xx")
