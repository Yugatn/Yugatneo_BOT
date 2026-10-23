# Development audit — Telegram MVP (October 2026)

## Implemented in repository
- Telegram polling bot, wheel of life, scores, history and action tracking.
- Question catalog, reflection and introductory CBT / ACT / DBT / coaching / gestalt options.
- Career interest and skill reflection, personal text report.
- Age-band preference (self-declared; **not** age verification).
- Parenting education: developmental transitions, family conflict, creativity, family violence prevention, digital habits and cognitive safety.
- SQLite parenting topic index and regression tests committed (not yet executed in production).
- RU/EN language preference commands `/language`, `/lang_ru`, `/lang_en`.
- Initial English parenting library: `/parenting_en`, `/parenting_en_1` through `/parenting_en_5`.

## Important gaps / not yet verified
1. English localization is **partial**: the main keyboard, wheel, coaching flows and most bot replies are still Russian. Language preference currently selects only the entry-point message and the separate English parenting library. It is not a complete bilingual UI.
2. The parenting index is seeded on topic search, not globally migrated at startup. Its source references are editorial pointers, not validated URLs. No live external scientific fact checking.
3. No production Telegram bot execution, OpenAI integration end-to-end, CI verification, or real deployment has been confirmed.
4. Age controls are self-declared; server-side gating for all sensitive questions and actual consent verification remain incomplete.
5. Reports are Telegram text, not PDF or downloadable files.
6. The scientific-claims table, immutable review workflow and multilingual indexed records are specified but not implemented.
7. No dedicated evidence-reviewed assessment instrument for career guidance has been integrated.
8. The speech-modeling / profanity social-context nuance was discussed; a dedicated revised educational entry and tests are still to be added.
9. Several code paths require a full syntax, data-schema, deletion and privacy regression audit. Do not treat a GitHub commit as proof of functioning production code.

## Recommended order
1. Run `python -m compileall app` and `pytest`; repair failures.
2. Verify `/start`, `/language`, `/parenting_en`, `/parenting`, `/report`, `/delete_my_data` in a staging Telegram bot.
3. Build a single locale-aware message catalog for every user-facing string and locale-specific keyboards.
4. Add source URL, reviewed date and evidence level to knowledge records; peer-review the educational content.
5. Add strict server-side eligibility checks for sensitive scenarios and consent flows.
6. Add verified OpenAI provider integration and bounded retrieval of reviewed facts.
7. Add PDF export and separate-app API only after a stable Telegram MVP.

Progress percentages from previous messages are **informal estimates**, not objective test coverage or deployment readiness.
