# Telegraph articles in Yugatneo BOT

## Available commands
- /articles — list public educational topics.
- /article creativity — publish an educational article about creative learning and return a Telegraph link.
- /parenting creativity — read the same topic privately in the chat.
- /report — personal report, **never** automatically sent to Telegraph.

## Configuration
Create a Telegraph account/access token using the official Telegraph API createAccount method and store its access_token only in the server environment variable TELEGRAPH_ACCESS_TOKEN. Do not commit it to GitHub or expose it in Telegram. No additional pip dependency is required: the existing httpx client is used.

If the token is missing or the API fails, the bot directs users back to the in-chat article. Telegraph articles are public to anyone who has the link; deleting a Telegram message does not unpublish the article.

## Publication rules
- Only allowlisted educational content from the repository can be published.
- Never publish chat transcripts, scores, psychological reflections, names, identifiers or other personal information.
- Initial Russian educational cards are labelled preliminary because source references still need editorial verification.
- English publication is held back pending editorial review; English content remains accessible in Telegram.
- In production, prefer an administrator-only editorial workflow, reviewed content flags and reuse of published URLs to avoid duplicates.
- Add rate limiting and publication cache before opening /article to a large audience.
- Telegraph is not a secure document vault, user account system or personal-report storage.

## Status
Implementation and mock tests are committed; no live Telegraph publication or production Telegram deployment has been verified.
