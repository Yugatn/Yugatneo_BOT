# Telegram-native content delivery policy

**Current decision:** All educational and personal content is delivered within Telegram. Telegraph publishing is disabled in the bot routing.

- /articles lists available parenting and development topics as Telegram commands.
- /article creativity displays the existing educational topic inside Telegram.
- /parenting creativity remains available.
- /report stays in the private chat; long messages are split into chunks without truncation.
- No external publishing token is required for core operation.

The experimental Telegraph publisher module is retained in the repository for possible future offline/editorial use, but it is not invoked from Telegram commands. Never publish personal reports, user messages or assessment answers to public pages.

Before production release, run the full test suite, verify long-message delivery and add bounded retries for Telegram API failures. Telegram availability remains an external dependency; no software can guarantee zero failures.
