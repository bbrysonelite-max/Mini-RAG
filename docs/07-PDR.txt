# Product Definition Review (PDR) — Multi-Agent RAG Brain

## 1. Goal

Deliver a single-user deployed, multi-project, multi-agent RAG product that:

- Ingests files, YouTube, and URLs.
- Generates structured artifacts:
  - Blueprints
  - PDRs
  - Workflows
  - Build Plans
- Uses a **Model Flex Layer** (`cheap`, `balanced`, `premium`) so models can change over time.
- Is designed like a multi-tenant SaaS but deployed initially for a single owner (Brent).

---

## 2. Functional Requirements (FR)

### FR1 — Projects (Brains)

- Create, update, delete projects.
- Each project has:
  - `name`, `description`, `namespace`, `status`.
- Wizard for first-time setup:
  - Name & goal
  - Template/playbook (optional)
  - Sources
  - Agents
  - Eval questions
- Project statuses:
  - `not_ready`
  - `ingesting`
  - `ready`
  - `needs_refresh`

### FR2 — Sources & Ingestion

- Supported sources (v1):
  - File uploads: `pdf`, `docx`, `md`, `txt`
  - YouTube URLs → transcripts
  - Web URLs → basic HTML-to-text extraction
- For each source:
  - Track status: `pending`, `ingesting`, `ingested`, `failed`
  - Store metadata (title, URL, file name, etc.)
- Ingestion behavior:
  - Normalize to `Document`
  - Chunk into `Chunk`s
  - Call `ModelService.embed` for embeddings
  - Write to Postgres + vector store
- Dedupe by content hash:
  - Same content is not ingested twice.

### FR3 — Chunking & Indexing

- Chunking rules:
  - ~700–1000 tokens with ~100–150 token overlap.
  - Semantic boundaries when possible.
- Store:
  - `Chunk` metadata and text in Postgres.
  - Embeddings in vector store keyed by `chunk.id`.
- Maintain `indexVersion` per project.

### FR4 — Retrieval (RAG)

- Hybrid retrieval:
  - BM25/FTS over `Chunk.text`.
  - Vector similarity via pgvector.
- Merge and dedupe candidates.
- Optional reranker via `ModelService.rerank`.
- Apply filters:
  - project/namespace
  - `source_type`
  - `confidentiality`
- Truncate to a limited number of chunks for context.

### FR5 — Agents & Personas

- Define Agents per project:
  - `name`, `description`, `modelProfile` (`cheap`, `balanced`, `premium`)
  - `promptTemplate`
  - `outputTypes` (Blueprint, PDR, Workflow, Build Plan)
- Agents use RAG pipeline + their persona to generate artifacts or answer questions.

### FR6 — Artifacts (Blueprints, PDRs, etc.)

- Agents can generate artifacts:
  - Blueprint
  - PDR
  - Workflow
  - Build Plan
- Artifacts are:
  - Stored as Markdown
  - Versioned per project/agent
  - Linked to `sourceChunkIds` for traceability
- User can:
  - View artifacts
  - Download (Markdown/PDF)
  - Regenerate (creating a new version)

### FR7 — Query & Ask UI

- User can:
  - Select a project
  - Optionally select an Agent
  - Type a question or choose “Generate Blueprint/PDR/Workflow/Build Plan”
- UI shows:
  - Answer
  - Citations (sources/chunks)
  - Optional “show work” view of retrieved chunks.

### FR8 — Eval & Testing

- Each project can store:
  - 10–20 `EvalQuestion`s (Q&A-style).
- Eval run:
  - Executes RAG pipeline for each question.
  - Captures metrics (retrieval & answer quality).
- Eval results stored as `EvalRun` records.

### FR9 — Admin & Config

- Simple Owner/Admin UI to:
  - Configure which models map to `cheap`, `balanced`, `premium`.
  - Adjust basic parameters (topK, max chunks, etc.).
  - View recent logs / basic metrics.

---

## 3. Non-Functional Requirements (NFR)

### NFR1 — Performance

- p95 latency:
  - < 6 seconds for typical queries using RAG.
- Ingestion:
  - Can process small sources (PDF, YouTube) in a reasonable time for a solo user (no hard SLA, but should feel responsive).

### NFR2 — Reliability

- Single-user deployment:
  - System should be stable on a modest server or desktop machine.
- Index rebuild:
  - It must be possible to rebuild the vector index from Postgres if needed.

### NFR3 — Security & Secrets

- API keys (OpenAI, Anthropic, gateway, etc.) stored only in:
  - Environment variables
  - Or a secure config, not hard-coded.
- Data access:
  - All queries filtered by `projectId` and (future) user role.

### NFR4 — Extensibility

- Clear boundaries for:
  - Ingestion connectors (YouTube/file/URL)
  - RAG pipeline
  - Model Flex Layer
- Easy to add:
  - New connectors
  - New models/providers
  - New artifact types (e.g., “Email Sequence Generator”) later.

### NFR5 — Maintainability

- No code outside `ModelService` calls providers directly.
- Domain model (`Project`, `Source`, `Document`, `Chunk`, `Agent`, `Artifact`) kept consistent between:
  - DB schema
  - RAG pipeline
  - API
  - Docs

---

## 4. KPIs

- Retrieval quality:
  - `ret@10 ≥ 0.70` on project eval sets.
- Answer quality:
  - `citation rate ≥ 0.95` (most answers have at least one citation).
  - LLM-judged quality score ≥ 70/100 on eval questions (optional).
- Usability:
  - A new user (owner) can:
    - create a project
    - ingest at least one source
    - generate a Blueprint
    - **without reading docs**, in under ~10 minutes.

---

## 5. Acceptance Criteria (v1)

The product is considered **v1-complete** when:

1. **Project Flow**
   - Owner can:
     - Create a project via wizard.
     - Add at least one source (file or YouTube).
     - Wait for ingestion to complete (`ready` state).

2. **RAG Flow**
   - For a project with at least one good source:
     - User can ask a question.
     - System returns a relevant answer with citations.
     - System can abstain clearly when data is missing.

3. **Artifact Generation**
   - At least one Agent (e.g., “Blueprint Architect”) can:
     - Generate a Blueprint artifact.
     - Store it as version 1.
     - Regenerate to create version 2.

4. **Eval**
   - Owner can:
     - Define an eval set (EvalQuestions) for a project.
     - Run eval to produce metrics.
     - View eval summary (retrieval/answer metrics).

5. **Model Flex Layer**
   - At least:
     - one `cheap` model
     - one `balanced` model
     - one `premium` model
   - Agents can switch between profiles without code changes (config-only).

6. **Docs**
   - The repo contains at least:
     - Architecture Blueprint
     - Domain Model & Metadata
     - Model Flex Layer Spec
     - RAG Pipeline Spec
     - This PDR
