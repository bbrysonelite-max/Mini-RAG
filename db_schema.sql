-- Database Schema for Multi-Agent RAG Brain
-- PostgreSQL with pgvector extension (optional)

-- Enable pgvector extension (will be handled by database.py init_schema if available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    username VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255), -- bcrypt hashed password for username/password auth
    auth_method VARCHAR(50) NOT NULL DEFAULT 'oauth', -- 'oauth' or 'password'
    role VARCHAR(50) NOT NULL DEFAULT 'reader', -- owner, admin, editor, reader
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT users_email_or_username CHECK (email IS NOT NULL OR username IS NOT NULL)
);

-- API Keys table (hashed storage)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    key_prefix VARCHAR(12) NOT NULL,
    hashed_key VARCHAR(128) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY['read'],
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (key_prefix, hashed_key)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

-- Organizations (tenants)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free', -- free, pro, enterprise
    quotas JSONB DEFAULT '{"users": 5, "workspaces": 3, "chunks": 50000}',
    metadata JSONB DEFAULT '{}',
    billing_status VARCHAR(50) NOT NULL DEFAULT 'trialing', -- trialing, active, past_due, canceled
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    billing_metadata JSONB DEFAULT '{}',
    billing_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspace quota settings
CREATE TABLE IF NOT EXISTS workspace_quota_settings (
    workspace_id UUID PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    chunk_limit BIGINT NOT NULL DEFAULT 500000,
    request_limit_per_day BIGINT NOT NULL DEFAULT 10000,
    request_limit_per_minute INTEGER NOT NULL DEFAULT 120,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspace usage counters (per day)
CREATE TABLE IF NOT EXISTS workspace_usage_counters (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    bucket_date DATE NOT NULL,
    chunk_count BIGINT NOT NULL DEFAULT 0,
    request_count BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (workspace_id, bucket_date)
);

CREATE INDEX IF NOT EXISTS idx_workspace_usage_date ON workspace_usage_counters(bucket_date);

-- Organization billing events (webhook audit)
CREATE TABLE IF NOT EXISTS organization_billing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(event_id)
);

CREATE INDEX IF NOT EXISTS idx_org_billing_events_org ON organization_billing_events(organization_id);

-- User <-> Organization membership
CREATE TABLE IF NOT EXISTS user_organizations (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, billing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, organization_id)
);

-- Workspaces (per-organization)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    quota JSONB DEFAULT '{"chunks": 20000, "sources": 2000}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (organization_id, slug)
);

-- Workspace membership
CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'editor', -- owner, admin, editor, viewer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Projects (workspaces default project records)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    namespace VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'not_ready',
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
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    uri TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    hash VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_ingested_at TIMESTAMP WITH TIME ZONE
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title VARCHAR(500),
    version INTEGER NOT NULL DEFAULT 1,
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks table (core retrieval unit)
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    start_offset INTEGER,
    end_offset INTEGER,
    tags TEXT[] DEFAULT '{}', -- Array of tags: project:slug, source_type:youtube, etc.
    ttl_expires_at TIMESTAMP WITH TIME ZONE,
    index_version INTEGER NOT NULL DEFAULT 1,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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

-- Organizations
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_plan ON organizations(plan);
CREATE INDEX IF NOT EXISTS idx_organizations_billing_status ON organizations(billing_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_organizations_stripe_customer ON organizations(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- User organizations
CREATE INDEX IF NOT EXISTS idx_user_org_user ON user_organizations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_org_org ON user_organizations(organization_id);

-- Workspaces
CREATE INDEX IF NOT EXISTS idx_workspaces_org_id ON workspaces(organization_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);

-- Workspace members
CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id ON workspace_members(user_id);

-- Projects
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_workspace_id ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_namespace ON projects(namespace);

-- Sources
CREATE INDEX IF NOT EXISTS idx_sources_project_id ON sources(project_id);
CREATE INDEX IF NOT EXISTS idx_sources_workspace_id ON sources(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(hash);

-- Documents
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_workspace_id ON documents(workspace_id);

-- Chunks
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_project_id ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_organization_id ON chunks(organization_id);
CREATE INDEX IF NOT EXISTS idx_chunks_workspace_id ON chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tags ON chunks USING GIN(tags);
-- Full-text search index (commented out - using functional index in queries instead)
-- CREATE INDEX IF NOT EXISTS idx_chunks_text_search ON chunks USING GIN(text_search_vector);

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

-- Workspace settings (Phase I: Second Brain)
CREATE TABLE IF NOT EXISTS workspace_settings (
    workspace_id UUID PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    default_engine VARCHAR(100) NOT NULL DEFAULT 'auto',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Assets table (Phase I: Second Brain)
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- prompt, workflow, page, sequence, decision, expert_instructions, customer_avatar, document
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- History table (Phase I: Second Brain)
CREATE TABLE IF NOT EXISTS history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    command VARCHAR(100) NOT NULL,
    input_snippet TEXT,
    output_snippet TEXT,
    full_input TEXT,
    full_output TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Phase I tables
CREATE INDEX IF NOT EXISTS idx_assets_workspace_id ON assets(workspace_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_history_workspace_id ON history(workspace_id);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_command ON history(command);


