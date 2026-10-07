# Setup

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js only if packaging or developing the JavaScript SDK

## Install and run

From the project root:

```sh
uv sync
uv run streamlit run app.py
```

The workspace UI is at `http://localhost:8501`. In another terminal, start the API:

```sh
uv run secretary-api
```

The API is at `http://localhost:8000`; interactive API documentation is at `/docs`. Health can be checked at `/health`.

## Configuration

Configuration is read from environment variables and an optional `.env` file in the project root. Do not commit secrets. SQLite is used by default at `./secretary.db`; PostgreSQL URLs are also supported. For real data, set `SEED_DEMO_DATA=false` to disable synthetic fixture records.

| Variable | Purpose |
| --- | --- |
| `API_AUTH_TOKEN` | Shared bearer token for administrative API routes; set a long random value. |
| `DATABASE_URL` | SQLAlchemy URL; defaults to `sqlite:///./secretary.db`. |
| `COMPANY_WORKSPACE_ID`, `COMPANY_WORKSPACE_NAME` | Workspace identity and display name. |
| `APP_USER_ID`, `APP_USER_NAME` | Operator identity recorded for audit events. |
| `SEED_DEMO_DATA` | Seed labeled synthetic events; defaults to `true`. |
| `LLM_API_KEY` | Enables assistant answers through an OpenAI-compatible chat completions API. |
| `LLM_BASE_URL`, `LLM_MODEL` | LLM endpoint base and model; defaults target OpenAI-compatible settings. |
| `SLACK_BOT_TOKEN` | Slack token used by explicit sync requests. Restrict channel IDs in each sync request. |
| `GITHUB_TOKEN`, `GITHUB_REPOSITORIES` | GitHub token and comma-separated `owner/repo` allowlist. |
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_IDS` | Verification, signature validation, and allowed WhatsApp Business phone number IDs. |
| `PUBLIC_BASE_URL` | Public callback base URL for webhook configuration. |
| `ALERT_WEBHOOK_URL`, `ALERT_THRESHOLD` | Optional occurrence threshold notification target and threshold. |
| `MONITOR_ALLOWED_ORIGINS` | Comma-separated origins for monitoring browser clients; defaults to `*`. |

Slack and GitHub sync are initiated through authenticated API requests; a scheduler is not included. The WhatsApp integration supports Business Cloud API, not personal WhatsApp accounts. Provider credentials are not included in this repository.

## Monitoring SDKs

Create a project through the authenticated `POST /monitor/projects` route or the UI. The returned project key is shown once; store it in the monitored application's secret configuration. Send events to `POST /monitor/events` with the `X-Project-Key` header. The JavaScript SDK is in `sdks/javascript`; the Python client is `sdks/python/secretary_monitor.py`. OTLP JSON traces are also accepted at `/monitor/otlp/v1/traces`.

## Deployment notes

Use HTTPS and a production database with backups and retention controls. The Streamlit interface is a trusted single-workspace admin surface; `API_AUTH_TOKEN` does not provide user identity, per-user authorization, or tenant isolation. The MVP creates database tables at startup and does not include production migrations. Do not expose it publicly without adding appropriate authentication, authorization, rate limiting, migration, backup, and monitoring controls. Monitoring events can contain stack traces and payload data; redact secrets and personal data before sending them.
