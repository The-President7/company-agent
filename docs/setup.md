# Setup

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js only if packaging or developing the JavaScript SDK

## Install, configure, and run

Run these commands from the project root. Install dependencies and create your private environment file:

```sh
uv sync
cp -n .env.example .env
```

The `-n` option leaves an existing `.env` untouched.

Open `.env` in a text editor and set at least these values:

```dotenv
API_AUTH_TOKEN=paste-a-long-random-value-here
LLM_API_KEY=paste-your-AgentRouter-key-here
```

Generate a strong admin token with `openssl rand -hex 32`, then paste its output as `API_AUTH_TOKEN`. Get an API key from your AgentRouter account and paste it as `LLM_API_KEY`. The example file already sets AgentRouter's OpenAI-compatible URL and the default model; choose a different `LLM_MODEL` if that model is not enabled for your account. Keep `.env` private and never commit it. The repository ignores `.env` in Git.

`API_AUTH_TOKEN` protects administrative API routes. `LLM_API_KEY` enables AI answers. You can leave provider variables blank until you configure those integrations. The example uses local SQLite and labeled demo records so the UI can run without a database or connector setup. Before connecting real data, set `SEED_DEMO_DATA=false` and configure your production `DATABASE_URL`.

Start the UI:

```sh
uv run streamlit run app.py
```

Open `http://localhost:8501`. In another terminal, start the API:

```sh
uv run secretary-api
```

The API is at `http://localhost:8000`; interactive API documentation is at `/docs`. Health can be checked at `/health`.

## Configuration

The repository's [`.env.example`](../.env.example) lists every supported setting with development defaults. Configuration is read from environment variables and the `.env` file in the project root. SQLite is used by default at `./secretary.db`; PostgreSQL URLs are also supported. For real data, set `SEED_DEMO_DATA=false` to disable synthetic fixture records.

| Variable | Purpose |
| --- | --- |
| `API_AUTH_TOKEN` | Shared bearer token for administrative API routes; set a long random value. |
| `API_RATE_LIMIT_REQUESTS`, `API_RATE_LIMIT_WINDOW_SECONDS` | Per-client API request limit; defaults to 120 requests per 60 seconds. |
| `LLM_RATE_LIMIT_REQUESTS`, `LLM_RATE_LIMIT_WINDOW_SECONDS` | Workspace-wide LLM call limit; defaults to 20 calls per 60 seconds across the API and Streamlit UI. |
| `DATABASE_URL` | SQLAlchemy URL; defaults to `sqlite:///./secretary.db`. |
| `COMPANY_WORKSPACE_ID`, `COMPANY_WORKSPACE_NAME` | Workspace identity and display name. |
| `APP_USER_ID`, `APP_USER_NAME` | Operator identity recorded for audit events. |
| `SEED_DEMO_DATA` | Seed labeled synthetic events; defaults to `true`. |
| `LLM_API_KEY` | AgentRouter API key; enables assistant answers through its OpenAI-compatible chat completions API. |
| `LLM_BASE_URL`, `LLM_MODEL` | OpenAI-compatible endpoint and AgentRouter model ID. Defaults are `https://co.agentrouter.org/v1` and `gpt-5.5`. |
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

Use HTTPS and a production database with backups and retention controls. The Streamlit interface is a trusted single-workspace admin surface; `API_AUTH_TOKEN` does not provide user identity, per-user authorization, or tenant isolation. The MVP creates database tables at startup and does not include production migrations. Rate limits are fixed-window and held in process memory: API requests are counted by direct client address, while LLM calls share a workspace-wide quota. Limits reset on restart and are not coordinated across multiple workers or replicas. For multi-worker or multi-replica deployments, use a shared rate-limit store such as Redis and configure trusted proxy handling at the edge. Monitoring events can contain stack traces and payload data; redact secrets and personal data before sending them.
