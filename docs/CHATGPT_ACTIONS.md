# ChatGPT Action / private API integration

This repository can expose a small, owner-scoped REST API that a **custom GPT Action** can call. This is not an automatically installable ChatGPT plugin: the API must be deployed at a public HTTPS URL, and an Action must be configured in the ChatGPT GPT editor using `openapi/chatgpt-actions.yaml`.

## What it can do

- Check API status.
- Read the Wheel of Balance and score history.
- Add a life sphere and record a subjective score from 0 to 10.
- Create/list personal goals and change goal status.
- Send a reflection prompt to the bot's configured dialogue engine.

## Security requirements

1. Set a long random `CHAT_CONTROL_API_KEY` in the deployment environment. Never commit it or send it in ordinary chat.
2. In the GPT Action authentication settings, use API-key authentication via a custom header named `X-API-Key`.
3. Use HTTPS only. Do not expose the API key in a browser or client-side mobile app.
4. Treat this as a private single-owner API. Do not give the key to other users. If multi-user access is added later, implement per-user identity, authorization, and data isolation first.
5. Avoid storing sensitive health or therapy notes. Wheel scores are self-reports, not diagnoses.
6. The current storage is SQLite and intended for a small prototype. Production deployment needs persistent storage and backups.

## Local setup

Add this to your local `.env` file (do not paste the value into GitHub):

```dotenv
CHAT_CONTROL_API_KEY=replace-with-a-long-random-secret
```

Generate a key on macOS with:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Then start the API as described in the root README. Test locally at `http://127.0.0.1:8000/docs` while `APP_ENV=development`. The GPT Action cannot reach localhost; deployment with HTTPS is required before connecting it.

## Example calls

```bash
curl -H "X-API-Key: $CHAT_CONTROL_API_KEY" http://127.0.0.1:8000/api/v1/status
curl -H "X-API-Key: $CHAT_CONTROL_API_KEY" http://127.0.0.1:8000/api/v1/wheel
curl -X POST -H "X-API-Key: $CHAT_CONTROL_API_KEY" -H "Content-Type: application/json" \
  -d '{"sphere":"Творчество","score":7,"note":"Хочу выделять время регулярно"}' \
  http://127.0.0.1:8000/api/v1/wheel/scores
```

## Known limitations

- This initial API does not implement calendar synchronization, audio storage, video-stream analysis, or payment processing.
- The current dialogue engine may be a mock provider unless an actual LLM provider is configured.
- The Action can call this API only after a deployment URL is substituted into the OpenAPI file and the GPT Action is configured.
