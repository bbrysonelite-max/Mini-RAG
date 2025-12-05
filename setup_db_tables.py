#!/usr/bin/env python3
"""
Setup database tables for workspace functionality.
Run this to create all required tables.
"""
import os
import sys
import asyncio

async def setup_tables():
    """Create all required database tables."""
    # Import after we know the environment is set
    from database import init_database, Database
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set!")
        print("Set it first: export DATABASE_URL='postgresql://...'")
        sys.exit(1)
    
    print(f"✓ DATABASE_URL is set")
    print(f"✓ Connecting to database...")
    
    try:
        # Initialize database connection
        db = await init_database()
        print(f"✓ Connected to database")
        
        # Read schema file
        schema_path = "db_schema.sql"
        if not os.path.exists(schema_path):
            print(f"❌ Schema file not found: {schema_path}")
            sys.exit(1)
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print(f"✓ Read schema file ({len(schema_sql)} bytes)")
        print(f"✓ Creating tables...")
        
        # Split by statement and execute
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        for i, stmt in enumerate(statements, 1):
            if stmt.strip():
                try:
                    await db.execute(stmt)
                    # Only print table creation statements
                    if 'CREATE TABLE' in stmt:
                        table_name = stmt.split('CREATE TABLE')[1].split('(')[0].strip().split()[0]
                        print(f"  ✓ Created table: {table_name}")
                except Exception as e:
                    # Ignore "already exists" errors
                    if 'already exists' not in str(e):
                        print(f"  ⚠️  Statement {i}: {str(e)[:100]}")
        
        print(f"\n✓ Database setup complete!")
        
        # Verify key tables exist
        print(f"\n✓ Verifying tables...")
        required_tables = [
            'users',
            'organizations', 
            'workspaces',
            'workspace_members',
            'workspace_settings',
            'user_organizations'
        ]
        
        for table in required_tables:
            count = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
            print(f"  ✓ {table}: {count['cnt']} rows")
        
        print(f"\n🎉 All done! You can now create workspaces.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(setup_tables())


