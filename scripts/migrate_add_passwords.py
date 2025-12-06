#!/usr/bin/env python3
"""
Migration script to add username, password_hash, and auth_method columns to users table.
Run this once to update existing databases.
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database

async def migrate():
    """Add password authentication columns to users table."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("=" * 60)
    print("Database Migration: Add Password Authentication")
    print("=" * 60)
    print()
    
    db = await init_database(db_url, init_schema=False)
    
    try:
        # Check if columns already exist
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('username', 'password_hash', 'auth_method')
        """
        existing = await db.fetch_all(check_query)
        existing_cols = {row['column_name'] for row in existing}
        
        if 'username' in existing_cols and 'password_hash' in existing_cols and 'auth_method' in existing_cols:
            print("✅ Migration already applied - columns exist")
            return
        
        print("Applying migration...")
        
        # Add columns one by one
        if 'username' not in existing_cols:
            print("  Adding username column...")
            await db.execute("ALTER TABLE users ADD COLUMN username VARCHAR(255) UNIQUE")
        
        if 'password_hash' not in existing_cols:
            print("  Adding password_hash column...")
            await db.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
        
        if 'auth_method' not in existing_cols:
            print("  Adding auth_method column...")
            await db.execute("ALTER TABLE users ADD COLUMN auth_method VARCHAR(50) NOT NULL DEFAULT 'oauth'")
        
        # Update existing users to have auth_method = 'oauth'
        print("  Updating existing users...")
        await db.execute("UPDATE users SET auth_method = 'oauth' WHERE auth_method IS NULL")
        
        # Add constraint (if not exists)
        try:
            await db.execute("""
                ALTER TABLE users 
                ADD CONSTRAINT users_email_or_username 
                CHECK (email IS NOT NULL OR username IS NOT NULL)
            """)
            print("  Added constraint: users_email_or_username")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                print("  Constraint already exists")
            else:
                raise
        
        print()
        print("✅ Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Create admin user: python scripts/create_admin_user.py")
        print("  2. Test login: POST /auth/login with username and password")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())





