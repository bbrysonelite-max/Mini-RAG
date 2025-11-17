# pgvector Setup Guide

Complete guide for setting up PostgreSQL with pgvector for the Multi-Agent RAG Brain.

## Prerequisites

- PostgreSQL 12+ installed
- Python 3.9+
- Admin access to PostgreSQL

## Step 1: Install pgvector Extension

### macOS (Homebrew)

```bash
# Install PostgreSQL if not already installed
brew install postgresql@15

# Install pgvector
brew install pgvector

# Start PostgreSQL
brew services start postgresql@15
```

### Ubuntu/Debian

```bash
# Add PostgreSQL APT repository
sudo apt install postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

# Install PostgreSQL and pgvector
sudo apt install postgresql-15 postgresql-15-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
```

### Docker (Easiest for Development)

```bash
# Run PostgreSQL with pgvector pre-installed
docker run --name rag-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag_brain \
  -p 5432:5432 \
  -d pgvector/pgvector:pg15

# Check it's running
docker ps
```

## Step 2: Create Database and Enable Extension

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE rag_brain;

# Connect to the database
\c rag_brain

# Enable pgvector extension
CREATE EXTENSION vector;

# Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

# Exit
\q
```

## Step 3: Configure Connection String

Create or update your `.env` file:

```bash
# Database connection
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_brain

# API Keys (for embeddings)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Model overrides
MODEL_EMBEDDING=text-embedding-3-small
```

## Step 4: Install Python Dependencies

```bash
# Install psycopg3 with binary driver
pip install 'psycopg[binary]' psycopg-pool

# Or add to requirements.txt:
echo 'psycopg[binary]>=3.1.0' >> requirements.txt
echo 'psycopg-pool>=3.1.0' >> requirements.txt
pip install -r requirements.txt
```

## Step 5: Initialize Database Schema

```python
# Python script or interactive
import asyncio
from database import init_database

async def setup():
    db = await init_database(
        init_schema=True,
        schema_file="db_schema.sql"
    )
    print("Database initialized!")

asyncio.run(setup())
```

Or from command line:

```bash
# Using psql
psql -U postgres -d rag_brain -f db_schema.sql
```

## Step 6: Verify Setup

```bash
# Run pgvector tests
python test_pgvector.py
```

Expected output:
```
✓ DATABASE_URL configured
✓ Database connection established
✓ pgvector extension available
✓ Health check: healthy
```

## Common Issues & Solutions

### Issue: "could not load library pgvector.so"

**Solution**: pgvector extension not properly installed.

```bash
# macOS
brew reinstall pgvector

# Ubuntu/Debian
sudo apt install --reinstall postgresql-15-pgvector

# Restart PostgreSQL
brew services restart postgresql@15  # macOS
sudo systemctl restart postgresql     # Linux
```

### Issue: "connection refused"

**Solution**: PostgreSQL not running.

```bash
# Check status
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Start if needed
brew services start postgresql@15  # macOS
sudo systemctl start postgresql     # Linux
```

### Issue: "permission denied for database"

**Solution**: User needs proper permissions.

```sql
-- As postgres user
GRANT ALL PRIVILEGES ON DATABASE rag_brain TO your_user;
GRANT ALL ON SCHEMA public TO your_user;
```

### Issue: "peer authentication failed"

**Solution**: Update `pg_hba.conf` for password authentication.

```bash
# Find config file
psql -U postgres -c "SHOW hba_file"

# Edit (replace 'peer' with 'md5' or 'trust' for local)
# Example line:
# local   all             all                                     md5

# Restart PostgreSQL
brew services restart postgresql@15  # macOS
sudo systemctl restart postgresql     # Linux
```

## Performance Tuning

### Optimize for Vector Search

Edit `postgresql.conf`:

```conf
# Memory settings
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
maintenance_work_mem = 1GB

# Query planner
random_page_cost = 1.1            # For SSD storage

# HNSW index specific
hnsw.ef_construction = 128        # Build quality (higher = better, slower)
```

Restart PostgreSQL after changes.

### Index Optimization

```sql
-- Rebuild index for better performance after bulk inserts
REINDEX INDEX idx_chunk_embeddings_vector;

-- Or use the VectorStore method
-- await vector_store.rebuild_index()
```

## Monitoring

### Check Index Size

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname = 'idx_chunk_embeddings_vector';
```

### Query Performance

```sql
-- Enable timing
\timing on

-- Test vector search
SELECT COUNT(*) 
FROM chunk_embeddings 
WHERE embedding <=> '[0.1, 0.2, ...]'::vector < 0.5;
```

### Connection Pool Stats

```python
from database import get_database

db = get_database()
health = await db.health_check()
print(health['pool_stats'])
```

## Backup & Restore

### Backup Database

```bash
# Full backup
pg_dump -U postgres rag_brain > backup.sql

# Data only (for migration)
pg_dump -U postgres --data-only rag_brain > data.sql
```

### Restore Database

```bash
# Create new database
createdb -U postgres rag_brain_new

# Restore
psql -U postgres rag_brain_new < backup.sql
```

## Production Deployment

### Recommended Setup

- **PostgreSQL 15+** with pgvector
- **Connection pooling**: Built-in via psycopg-pool
- **Backup strategy**: Daily automated backups
- **Monitoring**: pg_stat_statements, pg_stat_activity
- **SSL**: Enable for remote connections

### Docker Compose Example

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: rag_brain
      POSTGRES_USER: rag_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db_schema.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

## Migration from In-Memory

If you have existing in-memory vectors:

```python
from rag_pipeline import RAGPipeline
from model_service_impl import ConcreteModelService
from vector_store import VectorStore
from database import init_database

async def migrate():
    # Initialize
    db = await init_database()
    model_service = ConcreteModelService()
    vector_store = VectorStore(db)
    
    # Create pipeline with pgvector
    pipeline = RAGPipeline(
        chunks_path="out/chunks.jsonl",
        model_service=model_service,
        vector_store=vector_store,
        use_pgvector=True
    )
    
    # Build index (this will insert into pgvector)
    stats = await pipeline.build_vector_index(batch_size=50)
    print(f"Migrated {stats['chunks_embedded']} embeddings to pgvector")

asyncio.run(migrate())
```

## Next Steps

After setup:

1. ✅ Test basic operations: `python test_pgvector.py`
2. ✅ Build vector index for your chunks
3. ✅ Test hybrid retrieval with real queries
4. ✅ Monitor performance and tune as needed
5. ✅ Set up automated backups

## Resources

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/)

