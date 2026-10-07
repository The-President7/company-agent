# AI behavior

The assistant answers questions from source events already stored in the active workspace. It does not directly search Slack, GitHub, or other providers while answering. Provider synchronization determines which records are available.

```mermaid
flowchart TD
    Q[Operator question] --> Scope[Restrict to active workspace and time window]
    Scope --> Retrieve[Rank stored source events by text match]
    Retrieve --> Limit[Select up to 12 evidence candidates]
    Limit -->|No API key| Error[Return configuration error]
    Limit --> Prompt[Send question and bounded evidence to configured LLM]
    Prompt --> Model[OpenAI-compatible chat completions endpoint]
    Model --> Answer[Answer with [n] evidence markers]
    Answer --> Display[Show answer alongside source records and links]
```

## Evidence and limits

- Retrieval is scoped to the configured workspace and requested date range, then ranks stored records using simple token matching.
- The model receives up to 12 matching records, with each record's content truncated before prompt construction.
- The system instruction asks the model to rely only on supplied evidence, cite factual statements with evidence markers, and state when evidence is insufficient. Source text is explicitly treated as untrusted data.
- Answers cover matching stored records only. Missing permissions, failed syncs, incomplete history, or sparse records can make coverage incomplete.
- Demo records are synthetic and labeled in the UI. Confirm conclusions against linked provider records before relying on demo-backed answers.

The current integration uses an OpenAI-compatible `/chat/completions` endpoint configured by `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. Treat prompts and responses under the selected provider's data-handling terms. Do not send sensitive information unless the organization has approved that processing. Reports remain drafts until an operator reviews them; the model does not approve or publish reports autonomously.
