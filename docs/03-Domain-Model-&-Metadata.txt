# Domain Model & Metadata

## 1. Core Entities

### 1.1 User

Represents a person who can log in and use the system.

- `id: string`
- `email: string`
- `name: string`
- `role: 'owner' | 'admin' | 'editor' | 'reader'`
- `createdAt: Date`
- `updatedAt: Date`

### 1.2 Project (Brain)

Represents a long-lived context (e.g., "Webinar Brain", "Business OS Brain").

- `id: string`
- `ownerId: string` (User)
- `name: string`
- `description?: string`
- `namespace: string` (e.g., `bbryson/ai-brain/prod`)
- `status: 'not_ready' | 'ingesting' | 'ready' | 'needs_refresh'`
- `createdAt: Date`
- `updatedAt: Date`

### 1.3 Source

Logical source of content (YouTube, file, URL).

- `id: string`
- `projectId: string`
- `type: 'youtube' | 'file' | 'url'`
- `uri: string` (URL, path, etc.)
- `status: 'pending' | 'ingesting' | 'ingested' | 'failed'`
- `hash?: string` (content hash for dedupe / change detection)
- `metadata: jsonb`
  - e.g., `title`, `channel`, `uploadedAt`, `fileName`, etc.
- `createdAt: Date`
- `updatedAt: Date`
- `lastIngestedAt?: Date`

### 1.4 Document

Normalized representation of a source.

- `id: string`
- `sourceId: string`
- `title: string`
- `version: number`
- `language?: string`
- `metadata: jsonb`
- `createdAt: Date`

### 1.5 Chunk

Small, retrievable unit in the index.

- `id: string`
- `documentId: string`
- `projectId: string`
- `text: string`
- `position: number` (for ordering)
- `startOffset?: number`
- `endOffset?: number`
- `tags: string[]`
  - Example tags:
    - `project:{projectSlug}`
    - `source_type:youtube|pdf|url`
    - `confidentiality:public|internal|restricted`
    - `language:en`
    - `agent_hint:blueprint|pdr|workflow`
- `ttlExpiresAt?: Date`
- `indexVersion: number`
- `createdAt: Date`

> Embeddings are stored in the vector store, keyed by chunk `id`.  
> Chunk row in Postgres contains metadata and text.

### 1.6 Agent

An AI persona with a specific purpose.

- `id: string`
- `projectId: string`
- `name: string` (e.g., "Blueprint Architect")
- `description: string`
- `modelProfile: 'cheap' | 'balanced' | 'premium'`
- `promptTemplate: string` (system prompt)
- `outputTypes: ('blueprint' | 'pdr' | 'workflow' | 'build_plan')[]`
- `toolsAllowed: string[]`
- `config: jsonb`
  - e.g., temperature, max tokens, retrieval settings
- `createdAt: Date`
- `updatedAt: Date`

### 1.7 Artifact

Generated result (Blueprint, PDR, etc.).

- `id: string`
- `projectId: string`
- `agentId: string`
- `type: 'blueprint' | 'pdr' | 'workflow' | 'build_plan' | 'other'`
- `title: string`
- `content: string` (Markdown)
- `version: number`
- `sourceChunkIds: string[]` (for traceability)
- `createdAt: Date`
- `createdByUserId?: string`
- `metadata: jsonb`

### 1.8 EvalQuestion

Per-project test question.

- `id: string`
- `projectId: string`
- `question: string`
- `expectedAnswerSummary?: string`
- `expectedSourceChunkIds?: string[]`
- `tags: string[]` (e.g., `retrieval_only`, `generation_full`)
- `createdAt: Date`

### 1.9 EvalRun

Record of a batch of evals.

- `id: string`
- `projectId: string`
- `config: jsonb` (model, indexVersion, parameters)
- `metrics: jsonb`
- `createdAt: Date`

### 1.10 IndexVersion

Tracks index state for a project.

- `id: number`
- `projectId: string`
- `description?: string`
- `createdAt: Date`
- `createdByUserId?: string`
- `metadata: jsonb`

---

## 2. Metadata & Tagging Conventions

Each chunk should have a consistent set of tags so retrieval and filtering stay predictable.

### 2.1 Required Tags

- `project:{slug}`
  - Identifies which project/brain this chunk belongs to.
- `source_type:{youtube|pdf|url|docx|md|txt}`
  - Where the chunk came from.
- `language:{en|es|...}`
  - Language of the chunk.
- `confidentiality:{public|internal|restricted}`
  - Sensitivity level.

### 2.2 Optional Tags

- `agent_hint:{blueprint|pdr|workflow|build_plan}`
  - Hints which agent(s) might care about this chunk.
- `topic:{freeform}`
  - Optional high-level topic labels (e.g., `topic:webinar`, `topic:pricing`).

### 2.3 Usage

- Retrieval can filter chunks by:
  - `project` namespace
  - `source_type` (e.g., only YouTube)
  - `confidentiality` (based on user role)
  - `agent_hint` (optional biasing of results)
- Tags should be:
  - lowercase
  - use `key:value` style when possible
  - kept small and meaningful (not sentence-length).

