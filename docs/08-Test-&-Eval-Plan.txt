# Test & Eval Plan — Multi-Agent RAG Brain

## 1. Objectives

- Make sure the RAG pipeline actually works (not just “seems to work”).
- Catch regressions when:
  - changing models
  - changing chunking / retrieval parameters
  - adding new connectors.
- Keep quality measurable, not just based on vibes.

---

## 2. Test Levels

### 2.1 Unit Tests

Focus: small pieces of logic.

Examples:

- **Chunking**
  - Given sample text, expected number of chunks and boundaries.
- **Tagging**
  - Given source metadata, correct tags are attached to chunks.
- **Hashing / Dedupe**
  - Same content → same hash; duplicates are skipped.
- **TTL / Freshness**
  - Given TTL config and timestamps, chunk is correctly classified as fresh/stale.

### 2.2 Integration Tests

Focus: end-to-end over a small path.

Examples:

- **Ingest PDF**
  - Upload a PDF.
  - Chunks are created in Postgres.
  - BM25 and vector searches return content from that PDF.
- **Ingest YouTube**
  - Given a YouTube URL, transcript is fetched → normalized → chunked → searchable.
- **Basic Query**
  - For a test project, queries return relevant content with at least one citation.

### 2.3 End-to-End (E2E) Tests

Focus: real user flows.

1. **First Brain Flow**
   - Create a project via wizard.
   - Add a sample PDF or YouTube.
   - Wait for project status to become `ready`.
   - Ask a question and receive a sensible answer with citations.

2. **Blueprint Generation Flow**
   - Create a project with a Blueprint Agent.
   - Trigger Blueprint generation.
   - Artifact is stored as version 1.
   - Regenerate Blueprint → version 2 is created.

3. **Guardrail Flow**
   - Query before any data is ingested:
     - System explains that no data exists yet and suggests adding sources.
   - Ask a question unrelated to ingested data:
     - System abstains or clearly indicates lack of relevant info.

---

## 3. Eval Plan (RAG-Specific)

### 3.1 Per-Project Eval Sets

- Each project can define 10–20 **EvalQuestions**.
- For each question:
  - `question` text
  - optional `expectedAnswerSummary`
  - optional `expectedSourceChunkIds` (gold chunks).

Eval sets are created and refined by the owner over time.

### 3.2 Metrics

For each eval run:

- **Retrieval**
  - `ret@k` (k = 5, 10):
    - Fraction of questions where at least one expected chunk appears in the top-k retrieved.
- **Answer Quality** (optional, via LLM judge)
  - Score 0–100 on:
    - relevance
    - correctness
    - groundedness
    - clarity.
- **Citations**
  - Citation rate:
    - Fraction of answers with at least one citation.
  - Citation correctness:
    - Fraction of citations that refer to actually retrieved chunks.

### 3.3 Promotion Rules

Before applying major changes (for a given project):

- Change types:
  - New model or model profile mapping.
  - New retrieval parameters (topK, etc.).
  - New index version (big ingestion changes).

**Rule:**

- Run eval for at least one representative project.
- Compare with previous baseline:
  - No key metric should degrade more than an agreed threshold (e.g. 5–10%) unless explicitly accepted.

### 3.4 Automation

- Provide a CLI command or API endpoint to:
  - Trigger eval for a project.
  - Store results in `EvalRun`.
- Later, this can be wired into CI/CD, but v1 can be manual:
  - “Click Run Eval” in the UI, or run a script.

---

## 4. Logging & Debugging

For debugging bad answers or failures:

- Log, at minimum:
  - `projectId`
  - `agentId` (if any)
  - user query
  - top retrieved `chunkIds`
  - model used (`modelId`, `profile`)
  - latency (retrieval + generation)
  - any errors.

When an answer seems wrong:

- Check:
  - Was the right project used?
  - Were relevant chunks retrieved?
  - Did the model ignore important context?
  - Were citations correct?

This information feeds back into:

- Better chunking / tagging
- Prompt tuning for agents
- Possibly changing model profiles/providers.

---

## 5. Scope for v1

For v1, the goal is **not** a heavyweight test framework, but:

- A small but real set of eval questions per project.
- A repeatable eval run process.
- Basic metrics and logs to tell:
  - “Is this getting better or worse after I change something?”

Future versions can add:

- Automatic dashboards
- CI integration
- More advanced LLM-judge based evaluations.
