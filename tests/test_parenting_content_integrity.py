"""Consistency tests for parenting education in both languages."""
from app.services.parenting_knowledge import TOPICS, format_topic
from app.services.language_preferences import EN_TOPICS, english_topic
from app.services.parenting_en import TOPICS_EN


def test_parenting_topic_ids_unique():
    keys = [topic.key for topic in TOPICS]
    assert len(keys) == len(set(keys))


def test_all_parenting_topics_have_coaching_and_evidence():
    for topic in TOPICS:
        assert topic.summary.strip()
        assert topic.coaching_question.strip()
        assert topic.evidence.strip()
        assert topic.references
        assert topic.tags
        assert len(format_topic(topic)) < 4096


def test_english_parenting_topics_cover_russian_index():
    assert {topic.key for topic in TOPICS} <= set(EN_TOPICS)
    for topic in TOPICS:
        assert len(english_topic(topic.key)) < 4096
    assert TOPICS_EN
    assert all(len(card) < 4096 for card in TOPICS_EN)


def test_social_learning_nuance_preserved():
    topic = next(t for t in TOPICS if t.key == "cognitive_safety")
    assert "ненормативной лексики" in topic.summary
    assert "интеллекта" in topic.summary
    assert "пассивный табачный дым" in topic.summary
