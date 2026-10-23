"""SQLite index for curated parenting knowledge; no user data stored here."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.services.parenting_knowledge import TOPICS, ParentingTopic

SCHEMA = """
CREATE TABLE IF NOT EXISTS parenting_knowledge (
  key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  ages TEXT NOT NULL,
  summary TEXT NOT NULL,
  coaching_question TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  evidence TEXT NOT NULL,
  references_json TEXT NOT NULL,
  locale TEXT NOT NULL DEFAULT 'ru',
  region TEXT NOT NULL DEFAULT 'global',
  reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_parenting_locale_region
  ON parenting_knowledge(locale, region);
"""


def init_index(path: str | Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            """INSERT INTO parenting_knowledge
               (key, title, ages, summary, coaching_question, tags_json,
                evidence, references_json, locale, region)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ru', 'global')
               ON CONFLICT(key) DO UPDATE SET
                 title=excluded.title, ages=excluded.ages, summary=excluded.summary,
                 coaching_question=excluded.coaching_question,
                 tags_json=excluded.tags_json, evidence=excluded.evidence,
                 references_json=excluded.references_json""",
            [(t.key, t.title, t.ages, t.summary, t.coaching_question,
              json.dumps(t.tags, ensure_ascii=False), t.evidence,
              json.dumps(t.references, ensure_ascii=False)) for t in TOPICS],
        )


def search_index(path: str | Path, query: str, limit: int = 5) -> tuple[ParentingTopic, ...]:
    """Parameterized substring lookup, capped for short Telegram responses."""
    needle = query.strip().casefold()
    if not needle:
        return ()
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """SELECT key, title, ages, summary, coaching_question, tags_json,
                      evidence, references_json
               FROM parenting_knowledge
               WHERE locale='ru' AND
                 (instr(lower(key), ?) > 0 OR instr(lower(title), ?) > 0
                  OR instr(lower(tags_json), ?) > 0)
               ORDER BY CASE WHEN lower(key)=? THEN 0 ELSE 1 END, key
               LIMIT ?""",
            (needle, needle, needle, needle, max(1, min(limit, 10))),
        ).fetchall()
    return tuple(
        ParentingTopic(row[0], row[1], row[2], row[3], row[4],
                       tuple(json.loads(row[5])), row[6], tuple(json.loads(row[7])))
        for row in rows
    )
