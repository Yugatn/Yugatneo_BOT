# Channel adapters

Each adapter translates the platform-specific webhook payload into `IncomingMessage`, calls application services, and translates `OutgoingMessage` into the platform's reply format.

- Telegram: Bot API webhook or long polling for local tests.
- Instagram: Meta Messenger API for Instagram professional accounts, webhook verification/signature checks, and required permissions.
- WhatsApp: WhatsApp Business Platform Cloud API, webhook verification/signature checks, template/window policy.
- MAX: separate adapter only after access to the official developer API is confirmed.

Adapters must not implement subscription or safety policy independently; those belong to shared services. Verify webhook signatures, deduplicate platform event IDs, and never log access tokens or full sensitive message bodies.
