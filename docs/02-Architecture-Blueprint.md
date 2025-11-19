# Architecture Blueprint — Multi-Agent RAG Brain

## 1. Overview

This project is a **multi-agent RAG brain** designed:

- **Like** a multi-tenant SaaS (multiple projects, agents, users).
- **Deployed** initially as a **single-user** app (Brent as owner).

It ingests content (files, YouTube, URLs), normalizes and chunks it, indexes it (BM25 + vectors), retrieves relevant chunks, and uses a **Model Flex Layer** (cheap / balanced / premium) to generate structured artifacts:

- Blueprints
- PDRs
- Workflows
- Build plans

---

## 2. Main Components

### 2.1 Frontend (Web UI)

- SPA (React/Next-style).
- Key screens:
  - **Project Wizard** – create/set up a “Brain”.
  - **Sources** – upload files, add YouTube/URLs, view ingestion status.
  - **Ask / Chat** – ask questions, run agents, view citations.
  - **Artifacts Library** – list + view versions of Blueprints, PDRs, etc.
  - **Admin** – manage agents, model profiles, eval runs.

### 2.2 Backend API

- Stateless HTTP/JSON API.
- Endpoints for:
  - Projects, Sources, Agents, Artifacts
  - Ingestion triggers
  - Queries (RAG)
  - Eval runs
- Orchestrates calls to:
  - Ingestion workers
  - RAG pipeline
  - Model Flex Layer

### 2.3 Ingestion Service

- Queue-driven workers.
- Responsibilities:
  - Download raw content (files, YouTube transcripts, web pages).
  - Normalize to internal `Document` format.
  - Chunk documents into `Chunk`s with metadata.
  - Call `ModelService.embed` to create embeddings.
  - Write chunks + metadata to Postgres and vector store.
- Detects changes via content hash and updates `indexVersion` when needed.

### 2.4 RAG / Retrieval Service

- Implements the RAG pipeline:
  1. Hybrid retrieval:
     - BM25/FTS from Postgres.
     - Vector similarity from pgvector.
  2. Optional re-ranking via reranker model.
  3. Filters by:
     - project/namespace
     - tags (source_type, confidentiality, etc.).
  4. Returns top-N chunks to the Generation layer.

### 2.5 Model Flex Layer

- Single abstraction around all models.
- Profiles:
  - `cheap` – low-cost tasks (summaries, tagging).
  - `balanced` – general Q&A.
  - `premium` – high-quality artifacts (Blueprints, PDRs).
- Providers:
  - e.g. OpenAI, Anthropic, gateway, local/OpenLLM.
- Methods:
  - `generate`, `embed`, `rerank`.
- All LLM usage goes through this layer (no direct SDK calls in business logic).

### 2.6 Eval & Test Service

- Stores per-project eval questions and expected behavior.
- Runs:
  - Retrieval tests (ret@k, etc.).
  - Answer quality checks (optional LLM judge).
- Used before promoting new model configs or index versions.

### 2.7 Metrics & Observability

- Logs structured events:
  - Ingest jobs, query requests, model calls, errors.
- Basic metrics:
  - Latency p50/p95
  - Error rates
  - Token usage / cost estimates
- Health endpoint summarizing system status.

---

## 3. Data Stores

### 3.1 Postgres (primary DB)

Stores:

- **User**
- **Project**
- **Source**
- **Document**
- **Chunk** (metadata + text)
- **Agent**
- **Artifact**
- **EvalQuestion**
- **EvalRun**
- **IndexVersion**

Also holds BM25/FTS index (using Postgres full-text search).

### 3.2 Vector Store

- v1 default: **pgvector inside Postgres**.
- Future: can swap to Pinecone/Qdrant with the same `Chunk.id` + metadata.
- Treated as **rebuildable index**, not the source of truth.

### 3.3 Object Storage

- For raw files, transcripts, and exported artifacts.
- Local deployment: can be S3-compatible like MinIO.

---

## 4. Core Flows

### 4.1 Project Setup Wizard

1. User creates a project (Brain).
2. Chooses a template/playbook (optional).
3. Adds sources (files / YouTube / URLs).
4. Chooses or creates agents (Blueprint, PDR, Workflow).
5. Adds 5–10 eval questions.
6. System kicks off ingestion; project status moves:
   - `not_ready → ingesting → ready`.

### 4.2 Ingestion Flow

1. `Source` created with status `pending`.
2. Worker picks up source:
   - Downloads content.
   - Creates `Document` record.
   - Chunks into `Chunk`s with tags (project, source_type, etc.).
   - Embeds chunks via `ModelService.embed`.
   - Inserts into vector index.
3. Marks `Source` as `ingested`.
4. If many changes, increments project `indexVersion` and maybe sets status `needs_refresh`.

### 4.3 Query & Artifact Generation Flow

1. User opens a project and:
   - Asks a question, or
   - Triggers “Generate Blueprint / PDR / Workflow / Build Plan”.
2. Backend:
   - Validates project is `ready`.
   - Calls RAG service:
     - Hybrid retrieval + optional rerank.
   - Builds messages:
     - system: agent persona + instructions (cite or abstain).
     - user: query + desired output format.
   - Calls `ModelService.generate` with appropriate profile.
3. Response:
   - Returned to user with citations.
   - Optionally saved as an `Artifact` with a new version pointing to the source chunks.

### 4.4 Eval Flow

1. User selects project and runs eval.
2. Service:
   - Iterates over `EvalQuestion`s.
   - Runs RAG pipeline for each.
   - Measures retrieval + answer metrics.
3. Results stored in `EvalRun` and displayed in UI.

---

## 5. Security & Roles

- Initial deployment: single user (owner).
- Data model supports roles for future multi-user mode:
  - `owner`, `admin`, `editor`, `reader`.
- Access controlled by:
  - `projectId`
  - user role.
- Secrets (API keys) stored in environment variables, not in code or DB.

---

## 6. Deployment (v1)

- Target: simple **Docker Compose** setup:

  - `frontend` (web UI)
  - `backend` (API + RAG)
  - `worker` (ingestion jobs)
  - `postgres` (with pgvector)
  - `minio` or similar (optional object storage)

- All services are stateless except Postgres and storage.
- This layout later maps cleanly to:
  - Single VPS
  - Or Kubernetes with autoscaling.

---

## 7. Design Principles

- **Design like SaaS, run like single-user app** for v1.
- **Model Flex Layer** for all LLM calls (cheap/balanced/premium).
- **Postgres as source of truth**, vector index as rebuildable.
- **Explicit agents and artifacts**, not generic chat.
- **Eval before big changes** (model, index, prompts) to avoid regressions.
