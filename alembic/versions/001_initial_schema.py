"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('email', sa.String(255), unique=True),
        sa.Column('username', sa.String(255), unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('auth_method', sa.String(50), nullable=False, server_default='oauth'),
        sa.Column('role', sa.String(50), nullable=False, server_default='reader'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('email IS NOT NULL OR username IS NOT NULL', name='users_email_or_username')
    )
    
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='free'),
        sa.Column('quotas', postgresql.JSONB, server_default=sa.text("'{\"users\": 5, \"workspaces\": 3, \"chunks\": 50000}'::jsonb")),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('billing_status', sa.String(50), nullable=False, server_default='trialing'),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('stripe_subscription_id', sa.String(255)),
        sa.Column('trial_ends_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('subscription_expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('billing_metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('billing_updated_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    
    # Create indexes for organizations
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])
    op.create_index('idx_organizations_plan', 'organizations', ['plan'])
    op.create_index('idx_organizations_billing_status', 'organizations', ['billing_status'])
    op.create_index('idx_organizations_stripe_customer', 'organizations', ['stripe_customer_id'], unique=True, postgresql_where=sa.text('stripe_customer_id IS NOT NULL'))
    
    # User organizations
    op.create_table(
        'user_organizations',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'organization_id')
    )
    
    # Workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('quota', postgresql.JSONB, server_default=sa.text("'{\"chunks\": 20000, \"sources\": 2000}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'slug')
    )
    
    # API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True)),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('hashed_key', sa.String(128), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.Text), server_default=sa.text("ARRAY['read']")),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('key_prefix', 'hashed_key')
    )
    
    # Projects
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('namespace', sa.String(255), nullable=False, unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='not_ready'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Sources
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('uri', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('hash', sa.String(64)),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('last_ingested_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    
    # Documents
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    
    # Chunks
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.Column('start_offset', sa.Integer),
        sa.Column('end_offset', sa.Integer),
        sa.Column('tags', postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'")),
        sa.Column('ttl_expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('index_version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    
    # Create indexes for chunks
    op.create_index('idx_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('idx_chunks_project_id', 'chunks', ['project_id'])
    op.create_index('idx_chunks_organization_id', 'chunks', ['organization_id'])
    op.create_index('idx_chunks_workspace_id', 'chunks', ['workspace_id'])
    op.create_index('idx_chunks_tags', 'chunks', ['tags'], postgresql_using='gin')
    
    # Chunk embeddings (requires pgvector)
    op.execute("""
        CREATE TABLE IF NOT EXISTS chunk_embeddings (
            chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
            embedding vector(1536),
            model_id VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create HNSW index for vector search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_vector 
        ON chunk_embeddings USING hnsw (embedding vector_cosine_ops)
    """)
    
    # Additional tables for workspace management
    op.create_table(
        'workspace_members',
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='editor'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'user_id')
    )
    
    # Workspace quota settings
    op.create_table(
        'workspace_quota_settings',
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('chunk_limit', sa.BigInteger, nullable=False, server_default='500000'),
        sa.Column('request_limit_per_day', sa.BigInteger, nullable=False, server_default='10000'),
        sa.Column('request_limit_per_minute', sa.Integer, nullable=False, server_default='120'),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    
    # Assets table (Second Brain Phase I)
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    
    # History table (Second Brain Phase I)
    op.create_table(
        'history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('command', sa.String(100), nullable=False),
        sa.Column('input_snippet', sa.Text),
        sa.Column('output_snippet', sa.Text),
        sa.Column('full_input', sa.Text),
        sa.Column('full_output', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    
    # Drop tables in reverse order of creation
    op.drop_table('history')
    op.drop_table('assets')
    op.drop_table('workspace_quota_settings')
    op.drop_table('workspace_members')
    
    # Drop chunk_embeddings with special handling for vector type
    op.execute("DROP TABLE IF EXISTS chunk_embeddings")
    
    # Drop chunks and related indexes
    op.drop_index('idx_chunks_tags')
    op.drop_index('idx_chunks_workspace_id')
    op.drop_index('idx_chunks_organization_id')
    op.drop_index('idx_chunks_project_id')
    op.drop_index('idx_chunks_document_id')
    op.drop_table('chunks')
    
    op.drop_table('documents')
    op.drop_table('sources')
    op.drop_table('projects')
    op.drop_table('api_keys')
    op.drop_table('workspaces')
    op.drop_table('user_organizations')
    
    # Drop organizations with indexes
    op.drop_index('idx_organizations_stripe_customer')
    op.drop_index('idx_organizations_billing_status')
    op.drop_index('idx_organizations_plan')
    op.drop_index('idx_organizations_slug')
    op.drop_table('organizations')
    
    op.drop_table('users')
    
    # Note: We don't drop the pgvector extension as it might be used by other applications


