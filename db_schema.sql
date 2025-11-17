-- Database Schema for Multi-Agent RAG Brain
-- PostgreSQL with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'reader', -- owner, admin, editor, reader
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects (Brains) table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    namespace VARCHAR(255) NOT NULL UNIQUE, -- e.g., bbryson/ai-brain/prod
    status VARCHAR(50) NOT NULL DEFAULT 'not_ready', -- not_ready, ingesting, ready, needs_refresh
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index versions table
CREATE TABLE IF NOT EXISTS index_versions (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'
);

-- Sources table
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- youtube, file, url
    uri TEXT NOT NULL, -- URL, path, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, ingesting, ingested, failed
    hash VARCHAR(64), -- content hash for dedupe / change detection
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_ingested_at TIMESTAMP WITH TIME ZONE
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title VARCHAR(500),
    version INTEGER NOT NULL DEFAULT 1,
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks table (core retrieval unit)
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    start_offset INTEGER,
    end_offset INTEGER,
    tags TEXT[] DEFAULT '{}', -- Array of tags: project:slug, source_type:youtube, etc.
    ttl_expires_at TIMESTAMP WITH TIME ZONE,
    index_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Full-text search
    text_search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
);

-- Vector embeddings table (using pgvector)
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI text-embedding-3-small/large dimension
    model_id VARCHAR(100) NOT NULL, -- e.g., 'text-embedding-3-small'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_profile VARCHAR(50) NOT NULL, -- cheap, balanced, premium
    prompt_template TEXT,
    output_types TEXT[] DEFAULT '{}', -- blueprint, pdr, workflow, build_plan
    tools_allowed TEXT[] DEFAULT '{}',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Artifacts table
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id),
    type VARCHAR(50) NOT NULL, -- blueprint, pdr, workflow, build_plan, other
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    source_chunk_ids UUID[] DEFAULT '{}', -- For traceability
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'
);

-- Eval questions table
CREATE TABLE IF NOT EXISTS eval_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    expected_answer_summary TEXT,
    expected_source_chunk_ids UUID[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Eval runs table
CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    config JSONB NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance

-- Projects
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_namespace ON projects(namespace);

-- Sources
CREATE INDEX IF NOT EXISTS idx_sources_project_id ON sources(project_id);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(hash);

-- Documents
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);

-- Chunks
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_project_id ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tags ON chunks USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_chunks_text_search ON chunks USING GIN(text_search_vector);

-- Vector similarity search index (HNSW for fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_vector 
    ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);

-- Agents
CREATE INDEX IF NOT EXISTS idx_agents_project_id ON agents(project_id);

-- Artifacts
CREATE INDEX IF NOT EXISTS idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_agent_id ON artifacts(agent_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);

-- Eval questions
CREATE INDEX IF NOT EXISTS idx_eval_questions_project_id ON eval_questions(project_id);

-- Eval runs
CREATE INDEX IF NOT EXISTS idx_eval_runs_project_id ON eval_runs(project_id);

-- Helper function for vector similarity search
CREATE OR REPLACE FUNCTION search_chunks_by_embedding(
    query_embedding vector(1536),
    search_project_id UUID,
    similarity_threshold FLOAT DEFAULT 0.3,
    max_results INT DEFAULT 40
)
RETURNS TABLE (
    chunk_id UUID,
    chunk_text TEXT,
    chunk_tags TEXT[],
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.text,
        c.tags,
        1 - (ce.embedding <=> query_embedding) AS similarity
    FROM chunk_embeddings ce
    JOIN chunks c ON ce.chunk_id = c.id
    WHERE c.project_id = search_project_id
        AND 1 - (ce.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Helper function for full-text search
CREATE OR REPLACE FUNCTION search_chunks_by_text(
    query_text TEXT,
    search_project_id UUID,
    max_results INT DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    chunk_text TEXT,
    chunk_tags TEXT[],
    rank FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.text,
        c.tags,
        ts_rank(c.text_search_vector, plainto_tsquery('english', query_text)) AS rank
    FROM chunks c
    WHERE c.project_id = search_project_id
        AND c.text_search_vector @@ plainto_tsquery('english', query_text)
    ORDER BY rank DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;


