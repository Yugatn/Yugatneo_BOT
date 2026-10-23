"""User-selected interface language and curated English parenting summaries.

Do not present untranslated Russian content as English. Expand this catalog
before advertising full bilingual coverage.
"""
import sqlite3

EN_TOPICS = {
    "infancy": ("Infancy and the transition around age one", "Children develop mobility, communication and autonomy at different rates. Offer safe opportunities to explore."),
    "toddler": ("Autonomy around age three", "Young children increasingly seek independence. Offer age-appropriate choices and calm, consistent boundaries."),
    "school": ("Starting school", "School transitions can change routines and expectations. Provide support and avoid rigid developmental deadlines."),
    "adolescence": ("Adolescence", "Listen respectfully, discuss boundaries and allow age-appropriate autonomy."),
    "conflict": ("Conflict between adults", "Frequent hostile, unresolved conflict can undermine children's emotional security. Model respectful disagreement and repair."),
    "screens": ("Family digital habits", "Children learn from adults' habits. Protect responsive interactions without claiming that every use of a phone nearby is harmful."),
    "creativity": ("Creativity and making things together", "You do not need to be an expert. Learn, draw, build and safely repair things together without humiliation or pressure."),
    "family_safety": ("Safety and respect at home", "Violence and coercion are unacceptable regardless of gender. If someone is unsafe, seek trusted local human support."),
    "cognitive_safety": ("Cognitive safety and adult example", "Avoid exposing children to tobacco smoke, do not normalize underage alcohol use, and model respectful language. Children may repeat profanity without understanding context."),
}


def ensure_language_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_language ("
        "telegram_user_id TEXT PRIMARY KEY, language TEXT NOT NULL "
        "CHECK(language IN ('ru', 'en')))"
    )


def get_language(path, user_id: str) -> str:
    with sqlite3.connect(path) as conn:
        ensure_language_table(conn)
        row = conn.execute(
            "SELECT language FROM user_language WHERE telegram_user_id=?",
            (user_id,),
        ).fetchone()
    return row[0] if row else "ru"


def set_language(path, user_id: str, language: str) -> None:
    if language not in {"ru", "en"}:
        raise ValueError("Unsupported language")
    with sqlite3.connect(path) as conn:
        ensure_language_table(conn)
        conn.execute(
            "INSERT INTO user_language(telegram_user_id, language) VALUES (?, ?) "
            "ON CONFLICT(telegram_user_id) DO UPDATE SET language=excluded.language",
            (user_id, language),
        )


def english_topic(key: str) -> str:
    title, summary = EN_TOPICS[key]
    return f"📘 {title}\\n\\n{summary}\\n\\nEducational information, not a diagnosis."
