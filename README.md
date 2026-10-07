# Secretary Platform

Secretary combines a source-aware company operations assistant with application error and performance monitoring. Python application modules live at the project root. The Streamlit workspace and FastAPI service share the same database and core services; JavaScript and Python monitoring SDKs live under `sdks/`.

Start with [setup](docs/setup.md). See [architecture](docs/architecture.md) for system components and workflows, and [AI](docs/ai.md) for evidence retrieval and model behavior.

## Project layout

```text
.
├── api.py, app.py, config.py, db.py, models.py, services.py
├── docs/                 # Architecture, setup, and AI documentation
├── sdks/                 # JavaScript and Python monitoring clients
├── pyproject.toml
└── uv.lock
```

The service is an MVP: the UI is a trusted single-workspace admin surface, and `API_AUTH_TOKEN` is a shared secret rather than user identity or multi-tenant authentication. Review the security and operational limits in [setup](docs/setup.md) before deployment.
