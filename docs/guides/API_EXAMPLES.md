# Mini-RAG API Examples

Practical examples for integrating with the Mini-RAG API using curl, Python, and JavaScript.

---

## Authentication

All examples assume you have either:
1. **JWT Cookie** (from browser OAuth login)
2. **API Key** (from `scripts/manage_api_keys.py`)

### Getting an API Key
```bash
# SSH into your server or run locally
python scripts/manage_api_keys.py create \
  --user <your-user-uuid> \
  --scope read --scope write

# Copy the printed key (shown only once)
export MINI_RAG_API_KEY="mrag_..."
```

---

## Query Endpoints

### Ask a Question

#### curl
```bash
curl -X POST "https://yourdomain.com/api/v1/ask" \
  -H "X-API-Key: $MINI_RAG_API_KEY" \
  -F "query=What is the main topic of the uploaded documents?" \
  -F "k=5"
```

#### Python (requests)
```python
import requests

response = requests.post(
    "https://yourdomain.com/api/v1/ask",
    headers={"X-API-Key": "mrag_..."},
    data={
        "query": "What is the main topic of the uploaded documents?",
        "k": 5
    }
)

data = response.json()
print("Answer:", data["answer"])
print("Score:", data["score"])
print("Chunks:", len(data.get("chunks", [])))
```

#### Python (SDK)
```python
from clients.sdk import MiniRAGClient

client = MiniRAGClient(
    base_url="https://yourdomain.com",
    api_key="mrag_..."
)

result = client.ask(query="What is RAG?", k=5)
print(result["answer"])
```

#### JavaScript (fetch)
```javascript
const response = await fetch("https://yourdomain.com/api/v1/ask", {
  method: "POST",
  headers: {
    "X-API-Key": "mrag_..."
  },
  body: new FormData([
    ["query", "What is RAG?"],
    ["k", "5"]
  ])
});

const data = await response.json();
console.log("Answer:", data.answer);
```

---

## Source Management

### List Sources

#### curl
```bash
curl -X GET "https://yourdomain.com/api/v1/sources" \
  -H "X-API-Key: $MINI_RAG_API_KEY"
```

#### Python
```python
response = requests.get(
    "https://yourdomain.com/api/v1/sources",
    headers={"X-API-Key": "mrag_..."}
)

sources = response.json()["sources"]
for source in sources:
    print(f"{source['id']}: {source['path']} ({source['chunks']} chunks)")
```

### Get Source Chunks

#### curl
```bash
SOURCE_ID="your-source-id"
curl -X GET "https://yourdomain.com/api/v1/sources/$SOURCE_ID/chunks" \
  -H "X-API-Key: $MINI_RAG_API_KEY"
```

#### Python
```python
source_id = "your-source-id"
response = requests.get(
    f"https://yourdomain.com/api/v1/sources/{source_id}/chunks",
    headers={"X-API-Key": "mrag_..."}
)

chunks = response.json()["chunks"]
print(f"Found {len(chunks)} chunks")
```

### Delete a Source

#### curl
```bash
curl -X DELETE "https://yourdomain.com/api/v1/sources/$SOURCE_ID" \
  -H "X-API-Key: $MINI_RAG_API_KEY"
```

#### Python
```python
response = requests.delete(
    f"https://yourdomain.com/api/v1/sources/{source_id}",
    headers={"X-API-Key": "mrag_..."}
)

print(f"Deleted. Remaining chunks: {response.json()['kept']}")
```

---

## Ingestion

### Upload Files

#### curl
```bash
curl -X POST "https://yourdomain.com/api/v1/ingest/files" \
  -H "X-API-Key: $MINI_RAG_API_KEY" \
  -F "files=@document.pdf" \
  -F "files=@notes.md" \
  -F "language=en"
```

#### Python (multiple files)
```python
files = [
    ("files", open("document.pdf", "rb")),
    ("files", open("notes.md", "rb"))
]

response = requests.post(
    "https://yourdomain.com/api/v1/ingest/files",
    headers={"X-API-Key": "mrag_..."},
    files=files,
    data={"language": "en"}
)

print("Ingested:", response.json()["message"])
```

#### Python (SDK)
```python
result = client.ingest_files(
    files=["/path/to/doc.pdf", "/path/to/notes.md"],
    language="en"
)
print(result)
```

### Ingest URLs (YouTube)

#### curl
```bash
curl -X POST "https://yourdomain.com/api/v1/ingest/urls" \
  -H "X-API-Key: $MINI_RAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ],
    "language": "en"
  }'
```

#### Python
```python
response = requests.post(
    "https://yourdomain.com/api/v1/ingest/urls",
    headers={
        "X-API-Key": "mrag_...",
        "Content-Type": "application/json"
    },
    json={
        "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        "language": "en"
    }
)

print(response.json())
```

---

## Admin Operations

### List Workspaces

#### curl
```bash
curl -X GET "https://yourdomain.com/api/v1/admin/workspaces" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Python
```python
# Requires API key with 'admin' scope
response = requests.get(
    "https://yourdomain.com/api/v1/admin/workspaces",
    headers={"X-API-Key": "mrag_admin_key"}
)

workspaces = response.json()["workspaces"]
for ws in workspaces:
    print(f"{ws['name']}: {ws['billing_status']}")
```

### Get Billing Status

#### curl
```bash
curl -X GET "https://yourdomain.com/api/v1/admin/billing" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Python
```python
response = requests.get(
    "https://yourdomain.com/api/v1/admin/billing",
    headers={"X-API-Key": "mrag_admin_key"}
)

orgs = response.json()["organizations"]
for org in orgs:
    print(f"{org['name']}: {org['billing_status']}")
```

### Update Billing Status (Override)

#### curl
```bash
ORG_ID="your-org-uuid"
curl -X PATCH "https://yourdomain.com/api/v1/admin/billing/$ORG_ID" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "billing_status": "active",
    "plan": "enterprise"
  }'
```

#### Python
```python
org_id = "your-org-uuid"
response = requests.patch(
    f"https://yourdomain.com/api/v1/admin/billing/{org_id}",
    headers={
        "X-API-Key": "mrag_admin_key",
        "Content-Type": "application/json"
    },
    json={
        "billing_status": "active",
        "plan": "enterprise"
    }
)

print("Updated:", response.json())
```

---

## Billing (Stripe)

### Create Checkout Session

#### curl
```bash
curl -X POST "https://yourdomain.com/api/v1/billing/checkout" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1234567890",
    "success_url": "https://yourdomain.com/success",
    "cancel_url": "https://yourdomain.com/cancel"
  }'
```

#### Python
```python
response = requests.post(
    "https://yourdomain.com/api/v1/billing/checkout",
    headers={
        "X-API-Key": "mrag_admin_key",
        "Content-Type": "application/json"
    },
    json={
        "price_id": "price_1234567890",
        "success_url": "https://yourdomain.com/success",
        "cancel_url": "https://yourdomain.com/cancel"
    }
)

checkout_url = response.json()["url"]
print(f"Redirect user to: {checkout_url}")
```

### Create Portal Session

#### curl
```bash
curl -X POST "https://yourdomain.com/api/v1/billing/portal" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "return_url": "https://yourdomain.com/app"
  }'
```

#### Python
```python
response = requests.post(
    "https://yourdomain.com/api/v1/billing/portal",
    headers={
        "X-API-Key": "mrag_admin_key",
        "Content-Type": "application/json"
    },
    json={
        "return_url": "https://yourdomain.com/app"
    }
)

portal_url = response.json()["url"]
print(f"Billing portal: {portal_url}")
```

---

## Error Handling

### Handle Quota Exceeded (429)
```python
response = requests.post(
    "https://yourdomain.com/api/v1/ask",
    headers={"X-API-Key": "mrag_..."},
    data={"query": "test", "k": 5}
)

if response.status_code == 429:
    error = response.json()
    print(f"Quota exceeded: {error['detail']}")
    # Wait and retry, or upgrade plan
elif response.status_code == 402:
    print("Billing issue - subscription required")
    # Redirect to checkout
else:
    data = response.json()
    print(data["answer"])
```

### Handle Billing Block (402)
```python
if response.status_code == 402:
    # Create checkout session
    checkout_resp = requests.post(
        "https://yourdomain.com/api/v1/billing/checkout",
        headers={"X-API-Key": admin_key},
        json={
            "price_id": "price_...",
            "success_url": "https://yourdomain.com/success",
            "cancel_url": "https://yourdomain.com/cancel"
        }
    )
    checkout_url = checkout_resp.json()["url"]
    print(f"Subscribe here: {checkout_url}")
```

---

## Batch Operations

### Batch Ask (Multiple Queries)
```python
queries = [
    "What is RAG?",
    "How does embedding work?",
    "What are the key benefits?"
]

results = []
for query in queries:
    response = requests.post(
        "https://yourdomain.com/api/v1/ask",
        headers={"X-API-Key": "mrag_..."},
        data={"query": query, "k": 3}
    )
    results.append(response.json()["answer"])

for i, answer in enumerate(results):
    print(f"Q{i+1}: {queries[i]}")
    print(f"A{i+1}: {answer}\n")
```

### Bulk Ingestion
```python
import os
import glob

files_to_upload = glob.glob("/path/to/docs/*.pdf")

for file_path in files_to_upload:
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://yourdomain.com/api/v1/ingest/files",
            headers={"X-API-Key": "mrag_..."},
            files={"files": f},
            data={"language": "en"}
        )
        print(f"Uploaded {file_path}: {response.status_code}")
```

---

## Complete Integration Example

```python
import requests
import time

class MiniRAGClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-API-Key": api_key}
    
    def ask(self, query, k=5, retry_on_quota=True):
        """Ask a question with automatic quota retry"""
        response = requests.post(
            f"{self.base_url}/api/v1/ask",
            headers=self.headers,
            data={"query": query, "k": k}
        )
        
        if response.status_code == 429 and retry_on_quota:
            print("Quota exceeded, waiting 60s...")
            time.sleep(60)
            return self.ask(query, k, retry_on_quota=False)
        
        response.raise_for_status()
        return response.json()
    
    def ingest_file(self, file_path, language="en"):
        """Upload and ingest a single file"""
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/v1/ingest/files",
                headers=self.headers,
                files={"files": f},
                data={"language": language}
            )
        
        response.raise_for_status()
        return response.json()
    
    def list_sources(self):
        """Get all ingested sources"""
        response = requests.get(
            f"{self.base_url}/api/v1/sources",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["sources"]

# Usage
client = MiniRAGClient(
    base_url="https://yourdomain.com",
    api_key="mrag_..."
)

# Ingest documents
client.ingest_file("/path/to/doc.pdf")

# Query
result = client.ask("What is this document about?")
print(result["answer"])

# List sources
sources = client.list_sources()
print(f"Total sources: {len(sources)}")
```

---

**See Also:**
- `clients/sdk.py` - Official Python SDK
- `docs/postman/mini-rag.postman_collection.json` - Postman collection
- `docs/guides/BILLING_AND_API.md` - Billing integration details

