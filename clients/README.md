# Mini-RAG Python SDK

Lightweight helper around the `/api/v1` surface area for programmatic callers.

## Quick Start

```python
from clients.sdk import MiniRAGClient

client = MiniRAGClient(
    base_url="https://mini-rag.example.com",
    api_key="rk_live_your_api_key",  # generated via scripts/manage_api_keys.py
)

# Ask a question (returns JSON: answer, citations, metadata)
response = client.ask("Summarize onboarding process.", k=5)
print(response["answer"])

# Ingest a document from disk
from pathlib import Path
client.ingest_files([Path("handbook.pdf")])

# List sources visible to the API key
sources = client.list_sources()
print([s["source_id"] for s in sources["sources"]])

client.close()
```

### Scopes & Headers

- The client injects `X-API-Key` automatically; scopes must include `read` for `ask`, `write` for ingest, and `admin` for billing/admin routes.
- Alternate auth headers (`Authorization: ApiKey <token>`) are not required when using the SDK.

### Timeouts & Errors

- Requests default to a 30-second timeout; pass `timeout=<seconds>` to the constructor to override.
- Non-2xx responses raise `MiniRAGError` with the status code and server payload.

