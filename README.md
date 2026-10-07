# Secretary Platform

Secretary combines a source-aware company operations assistant with project-based application error and performance monitoring. The repository includes a Streamlit workspace UI and a FastAPI service.

## Run locally

Requires Python 3.11+ and `uv`.

```sh
uv sync
uv run streamlit run company_agent/app.py
```

The UI runs at `http://localhost:8501`. Start the API separately with `uv run secretary-api`; API docs are at `http://localhost:8000/docs`. For production, put both behind HTTPS and configure `API_AUTH_TOKEN` with a long random secret. Administrative API routes require `Authorization: Bearer <API_AUTH_TOKEN>`.

SQLite is used by default. Set `SEED_DEMO_DATA=false` when connecting a real database. PostgreSQL URLs use psycopg 3.

## Configure the LLM and providers

Copy `.env.example` to `.env` and configure:

- `LLM_API_KEY`, optional `LLM_BASE_URL`, and `LLM_MODEL` for an OpenAI-compatible chat completions API.
- `SLACK_BOT_TOKEN` with read access to the opted-in conversations. Call `POST /connectors/slack/sync` using the admin bearer token and `X-Channel-Ids: C123,C456` to sync only those channels.
- `GITHUB_TOKEN` and `GITHUB_REPOSITORIES=owner/repo,...` to sync only the listed repositories through `POST /connectors/github/sync`.
- `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, and authorized number IDs in `WHATSAPP_PHONE_NUMBER_IDS` for a WhatsApp Business Cloud API webhook at `/webhooks/whatsapp`. Personal WhatsApp accounts are not supported.
- `ALERT_WEBHOOK_URL` and `ALERT_THRESHOLD` for an occurrence-threshold webhook notification.

No provider credentials are included. Slack and GitHub sync runs when requested; a scheduler or worker is not included yet. WhatsApp messages arrive through the configured webhook. Use provider-issued credentials and limit source scopes to data the organization is authorized to process.

## App monitoring

Create a project in the UI or `POST /monitor/projects` (authenticated). The project key is returned once. Keep it in the monitored app's environment, not source control. Send events to `POST /monitor/events` with `X-Project-Key`; error events with matching fingerprints are grouped into issues, and transaction events retain duration data.

Install the local JavaScript client from `sdks/javascript` or import `SecretaryMonitor` from `sdks/python/secretary_monitor.py`. The JavaScript client can capture uncaught browser errors and unhandled rejections. Python and JavaScript clients support manual exception and transaction capture. OTLP JSON traces are accepted at `/monitor/otlp/v1/traces` with the same project key.

The first release stores stack traces and event payload fields in the configured database. Set retention and access policies appropriate for your data before production use; redact secrets and personal data before sending events.

## Reports and security limits

Reports remain reviewable drafts and can be downloaded as PDFs from the UI or `GET /reports/{id}.pdf`. PDFs include the period, report content, coverage note, and evidence links.

The Streamlit interface currently runs as a trusted single-workspace admin surface configured by environment variables. `API_AUTH_TOKEN` is a shared administrative secret, not user identity or multi-tenant authentication. Do not expose the UI or API to the public internet without adding user authentication, authorization, rate limits, production migrations, backups, and monitoring. Database tables are created on startup for this MVP.
