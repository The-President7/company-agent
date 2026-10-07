# Architecture

Secretary has two application surfaces over shared Python services and a relational database. The Streamlit UI is intended for a trusted workspace operator. The FastAPI service exposes administrative, assistant, connector, webhook, and monitoring endpoints.

```mermaid
flowchart LR
    Operator[Workspace operator] --> UI[Streamlit UI<br/>app.py]
    Product[Monitored application] --> JS[JavaScript SDK]
    Product --> Py[Python SDK]
    UI --> Core[Shared services<br/>services.py]
    UI --> API[FastAPI<br/>api.py]
    JS -->|Project key| API
    Py -->|Project key| API
    Provider[Slack / GitHub / WhatsApp] -->|Scoped sync or webhook| API
    API --> Core
    Core --> DB[(SQLite or PostgreSQL)]
    API --> DB
    API -->|Evidence prompt| LLM[OpenAI-compatible chat API]
```

## Main data paths

### Company activity and reports

```mermaid
sequenceDiagram
    participant P as Provider
    participant A as FastAPI
    participant D as Database
    participant U as Streamlit UI
    participant L as LLM API
    P->>A: Scoped sync request or WhatsApp webhook
    A->>D: Store source events and connector state
    U->>D: Search workspace events
    U->>L: Question plus bounded evidence records
    L-->>U: Answer with evidence markers
    U->>D: Save audit event / report draft
    U-->>U: Operator reviews report and evidence
```

### Application monitoring

```mermaid
flowchart TD
    E[Error or transaction] --> SDK[Python or JavaScript SDK]
    SDK -->|X-Project-Key| Ingest[POST /monitor/events]
    Ingest --> Validate[Validate project key and event]
    Validate --> Group[Fingerprint and group error]
    Group --> Store[(Monitor event and issue tables)]
    Store --> Dashboard[Workspace monitoring view]
```

The `api.py` process creates tables at startup for this MVP. Slack and GitHub synchronization is request driven; no scheduler or background worker is included. WhatsApp Business Cloud API events are accepted by the configured webhook. `sdks/` contains independent client packages and is kept separate from the root Python service modules.
