# Setting Up a Shared Database for Multiple Machines

This guide helps you set up a PostgreSQL database that both machines can access, so all ingested documents, workspaces, and assets sync automatically.

## Option 1: Docker Compose on One Machine (Easiest for Local)

**Best for:** Two machines on the same local network

### Setup Steps:

**On Machine A (Database Host):**

1. **Start Docker Compose:**
   ```bash
   docker-compose up -d db
   ```

2. **Expose PostgreSQL to network:**
   - Docker Compose already exposes port `5432` to localhost
   - To allow network access, edit `docker-compose.yml`:
     ```yaml
     ports:
       - "0.0.0.0:5432:5432"  # Allow connections from network
     ```
   - Or use: `docker-compose up -d db` (already configured)

3. **Find Machine A's IP address:**
   ```bash
   # macOS/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Or:
   hostname -I | awk '{print $1}'
   ```
   Example: `192.168.1.100`

4. **Update .env on Machine A:**
   ```bash
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_brain
   ```

**On Machine B (Client):**

1. **Update .env:**
   ```bash
   # Replace 192.168.1.100 with Machine A's IP
   DATABASE_URL=postgresql://postgres:postgres@192.168.1.100:5432/rag_brain
   ```

2. **Test connection:**
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

**Initialize schema (run once, on either machine):**
```bash
psql $DATABASE_URL < db_schema.sql
```

### Security Note:
For production, change the default password (`postgres`) and use a firewall to restrict access.

---

## Option 2: Cloud Database (Best for Remote Access)

**Best for:** Machines in different locations, or production use

### Option 2A: Railway (Free Tier Available)

1. **Sign up:** https://railway.app
2. **Create new project** → **Add PostgreSQL**
3. **Copy connection string** from Railway dashboard
4. **On both machines, update .env:**
   ```bash
   DATABASE_URL=postgresql://postgres:password@hostname.railway.app:5432/railway
   ```
5. **Initialize schema:**
   ```bash
   psql $DATABASE_URL < db_schema.sql
   ```

### Option 2B: Supabase (Free Tier Available)

1. **Sign up:** https://supabase.com
2. **Create new project**
3. **Go to Settings → Database**
4. **Copy connection string** (use "Connection pooling" for better performance)
5. **On both machines, update .env:**
   ```bash
   DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
   ```
6. **Enable pgvector extension** (Supabase has it pre-installed):
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
7. **Initialize schema:**
   ```bash
   psql $DATABASE_URL < db_schema.sql
   ```

### Option 2C: Render (Free Tier Available)

1. **Sign up:** https://render.com
2. **Create new PostgreSQL database**
3. **Copy connection string** from dashboard
4. **On both machines, update .env:**
   ```bash
   DATABASE_URL=postgresql://user:password@hostname.onrender.com:5432/dbname
   ```
5. **Initialize schema:**
   ```bash
   psql $DATABASE_URL < db_schema.sql
   ```

---

## Option 3: Local PostgreSQL Server

**Best for:** One machine always on, both machines on same network

### Setup Steps:

**On Machine A (Database Server):**

1. **Install PostgreSQL:**
   ```bash
   # macOS:
   brew install postgresql@15
   brew services start postgresql@15
   
   # Ubuntu/Debian:
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create database:**
   ```bash
   createdb rag_brain
   ```

3. **Enable pgvector extension:**
   ```bash
   psql rag_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

4. **Configure PostgreSQL for network access:**
   ```bash
   # Edit postgresql.conf (usually /usr/local/var/postgres/postgresql.conf or /etc/postgresql/15/main/postgresql.conf)
   # Find and set:
   listen_addresses = '*'  # or '0.0.0.0'
   ```

5. **Configure pg_hba.conf** (usually `/usr/local/var/postgres/pg_hba.conf` or `/etc/postgresql/15/main/pg_hba.conf`):
   ```
   # Add line for your network (replace with your network range):
   host    all             all             192.168.1.0/24          md5
   ```

6. **Set password for postgres user:**
   ```bash
   psql postgres -c "ALTER USER postgres PASSWORD 'your-secure-password';"
   ```

7. **Restart PostgreSQL:**
   ```bash
   # macOS:
   brew services restart postgresql@15
   
   # Linux:
   sudo systemctl restart postgresql
   ```

**On Machine B (Client):**

1. **Update .env:**
   ```bash
   DATABASE_URL=postgresql://postgres:your-secure-password@192.168.1.100:5432/rag_brain
   ```

2. **Initialize schema:**
   ```bash
   psql $DATABASE_URL < db_schema.sql
   ```

---

## Verification Steps

After setting up, verify on both machines:

1. **Test connection:**
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

2. **Check pgvector extension:**
   ```bash
   psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
   ```

3. **Verify schema:**
   ```bash
   psql $DATABASE_URL -c "\dt"  # List tables
   ```

4. **Test data sync:**
   - On Machine A: Create a workspace and ingest a document
   - On Machine B: Check if workspace and document appear
   - Both should see the same data!

---

## Troubleshooting

### Connection Refused
- Check firewall settings on database host
- Verify PostgreSQL is listening on the correct port: `netstat -an | grep 5432`
- Check `pg_hba.conf` allows connections from your IP

### Authentication Failed
- Verify username/password in `DATABASE_URL`
- Check `pg_hba.conf` authentication method (md5 vs trust)

### Extension Not Found (pgvector)
- For cloud databases: Most have pgvector pre-installed
- For local: Install pgvector: `CREATE EXTENSION vector;`

### Can't Connect from Remote Machine
- Ensure PostgreSQL is bound to `0.0.0.0` not just `localhost`
- Check firewall allows port 5432
- Verify network connectivity: `ping <database-host-ip>`

---

## Quick Reference

**Current setup (Docker Compose):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_brain
```

**Shared database (same network):**
```bash
DATABASE_URL=postgresql://postgres:postgres@<machine-a-ip>:5432/rag_brain
```

**Cloud database:**
```bash
DATABASE_URL=postgresql://user:password@hostname:5432/dbname
```

**Initialize schema:**
```bash
psql $DATABASE_URL < db_schema.sql
```


