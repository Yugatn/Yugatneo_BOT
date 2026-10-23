# Security baseline for Telegram polling

Implemented: simple arithmetic challenge for new Telegram user IDs, SQLite-backed verification, 3 attempts, 10-minute challenge lifetime, and a 20-message-per-minute limit per user. Safety/crisis messages and data deletion bypass the challenge.

**Limitations:** arithmetic questions are not robust bot detection. Telegram user IDs can be created at scale. SQLite throttling is local to a single deployment. This is not protection against distributed denial of service, account takeover, malicious dependencies, prompt injection, model cost exhaustion or Telegram token leakage.

Before public launch:
1. Run tests and verify real bot flow, including /start, challenge answer, /delete_my_data, and crisis support.
2. Add a global budget and per-user quotas for OpenAI/Telegraph calls, plus caching and an administrator-only article publication path.
3. Configure deployment firewall, resource caps, service health checks, minimal privileges and secret rotation.
4. Limit inbound text size, log safely without recording private conversation content, and handle API errors with bounded retries.
5. Add optional accessible alternative to arithmetic for users with cognitive, numerical or language difficulties; do not treat failed challenges as proof of abuse.
6. Avoid sending arbitrary user messages as instructions to the model; keep retrieved articles and user content separate from trusted system rules.
7. In a multi-instance deployment use a shared rate-limit store (e.g. Redis), not separate SQLite counters.
8. Review dependency updates, secret scanning, branch protection and deployment configuration.

Security features committed to GitHub have **not** been verified in a running production bot.
