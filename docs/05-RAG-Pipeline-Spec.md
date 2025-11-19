# RAG Pipeline Spec

## 1. Goals

- Use **hybrid retrieval** (BM25 + vector).
- Always prefer **cite-first** answers.
- **Abstain** when the data isn’t there (no hallucinations on unknowns).
- Produce **structured outputs** for:
  - Blueprints
  - PDRs
  - Workflows
  - Build Plans

---

## 2. Chunking

### 2.1 General Rules

- Target chunk size: **~700–1000 tokens**.
- Overlap between chunks: **~100–150 tokens** for context.
- Chunk at **semantic boundaries** when possible:
  - Headings
  - Paragraphs
  - Speaker turns (for transcripts)

### 2.2 Document Types

**PDF / DOCX / MD / TXT**

- Parse into sections/headings.
- Each section becomes one or more chunks.
- Merge small sections together until reaching target size.

**YouTube Transcript**

- Use time-coded segments.
- Group consecutive segments until reaching target size.
- Preserve:
  - Timestamps
  - Speaker (if available)

**Resulting Chunk fields:**

- `text`
- `position`
- `startOffset` / `endOffset` (optional)
- `tags` (project, source_type, etc.)
- `documentId`, `projectId`, `indexVersion`

---

## 3. Indexing

For each `Chunk`:

1. Insert metadata + text into **Postgres**.
2. Call `ModelService.embed` with chunk text to get an embedding.
3. Upsert embedding into **vector store** keyed by `chunk.id`.
4. Ensure metadata (tags, project, etc.) is also stored as vector metadata.

**BM25 / FTS**

- Use Postgres full-text search indexed on:
  - `Chunk.text`
  - Optional important metadata fields.

**Key rule:**

- **Postgres is the source of truth** (chunks + metadata).
- Vector index is **rebuildable** from Postgres.

---

## 4. Retrieval

### 4.1 Inputs

- `projectId`
- `userQuery`
- Optional filters:
  - `source_type`
  - `confidentiality`
  - `agent_hint`
  - date range (optional future feature)

### 4.2 Steps

1. **Candidate Retrieval**
   - BM25: get `topK_bm25` chunks.
   - Vector similarity: get `topK_vector` chunks.
2. **Merge & Dedupe**
   - Combine BM25 + vector results.
   - Remove duplicates based on `chunk.id`.
3. **Optional Re-ranking**
   - If reranker is configured:
     - Pass `query` + candidate list to `ModelService.rerank`.
     - Use returned scores to sort descending.
4. **Filter & Truncate**
   - Apply filters:
     - `projectId` / namespace
     - `confidentiality` (user role)
     - `source_type` (if requested)
   - Truncate to `maxChunksForContext` (e.g., 10–20 chunks) based on:
     - rerank score
     - token budget

### 4.3 Default Parameters (v1)

These values can live in config:

- `topK_bm25 = 20`
- `topK_vector = 40`
- `maxChunksForContext = 15`  
- `useReranker = false` (can be enabled later)

---

## 5. Generation

### 5.1 Building the Prompt

For each query or artifact generation request:

1. Look up the **Agent**:
   - persona/system prompt
   - `modelProfile` (`cheap`, `balanced`, `premium`)
   - output type (Blueprint, PDR, etc.)
2. Build messages:

   - `system`:
     - Agent persona.
     - Instructions:
       - Use only provided context.
       - Cite sources.
       - Abstain if context is insufficient.
   - `user`:
     - User’s question or “Generate a Blueprint/PDR/Workflow based on this brain.”
   - **Optional**: include a short “context summary” message if needed.

3. For artifacts (Blueprint, PDR, etc.), request a **structured Markdown format**:
   - e.g., for Blueprint:
     - `# Overview`
     - `## Goals`
     - `## Architecture`
     - `## Features`
     - `## Risks`
     - `## Next Steps`

### 5.2 Calling the Model

Call:

- `ModelService.generate` with:
  - `modelProfile` from the Agent (`cheap`, `balanced`, `premium`)
  - `messages` built above
  - `maxTokens` sized to output type
  - `temperature` low for structured artifacts (e.g., 0.2–0.4)

The retrieved chunks are **not** sent verbatim in this spec (implementation detail), but typically:

- The top-N chunks are included in the prompt as a context section, e.g.:

  > “Here is the relevant context from the project: … [chunks] … Use only this information to answer.”

---

## 6. Citation Policy

Every answer that uses project data must:

1. Include **citations** referencing chunks/sources.
   - Example formats:
     - `[source: {title}, page {p}]`
     - `[source: {videoTitle}, t=12:34]`
     - Or chunk-based: `[chunk: {chunkId}]`
2. Use only information supported by the context when citing.
3. If insufficient context:
   - Clearly say:  
     - “I don’t see enough information in this brain to answer that yet.”
   - Optionally suggest:
     - “You may want to ingest X/Y/Z documents.”

Post-processing (optional, but ideal):

- Verify that all citations in the answer refer to `chunk.id`s that were actually retrieved.

---

## 7. Abstention Behavior

The system should **abstain** rather than hallucinate when:

- No chunks are retrieved above a relevance threshold.
- Retrieved chunks do not seem related to the query (low overall score).
- The question is clearly outside the domain of the project.

Abstention response example:

> “I don’t see content in this project that directly answers that question yet. Try ingesting more relevant documents (e.g., your pricing sheets, webinar transcripts, or SOPs) and run this again.”

---

## 8. Logging & Metrics

For each query, log:

- `projectId`
- `agentId` (if applicable)
- `userQuery`
- retrieved `chunkIds`
- model used (`modelId`, `profile`)
- latency:
  - retrieval time
  - generation time
- token usage (if available)
- any errors

These logs are used for:

- Debugging bad answers.
- Evaluations (see Test & Eval Plan).
- Cost estimation and performance tuning.

---

## 9. Eval Hooks

The RAG pipeline must support being run in **eval mode**, where:

- Instead of answering a live user, it:
  - Runs a stored `EvalQuestion`.
  - Captures:
    - retrieved chunks
    - answer (optional)
    - metrics (ret@k, etc.).
- Results are written to an `EvalRun` record for later analysis.

This keeps the RAG behavior testable and safe to evolve over time.
