#!/usr/bin/env python3
"""
Create an admin user with username and password.
Usage: python scripts/create_admin_user.py
"""
import os
import sys
import getpass
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed. Run: pip install bcrypt")
    sys.exit(1)

from database import init_database

async def create_admin_user():
    """Create an admin user with username and password."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL='postgresql://user:pass@host:port/db'")
        sys.exit(1)
    
    print("=" * 60)
    print("Create Admin User")
    print("=" * 60)
    print()
    
    # Get username
    username = input("Enter username: ").strip()
    if not username:
        print("ERROR: Username cannot be empty")
        sys.exit(1)
    
    # Check if username already exists
    db = await init_database(db_url, init_schema=False)
    existing = await db.fetch_one(
        "SELECT id, username, role FROM users WHERE username = $1",
        (username,)
    )
    
    if existing:
        print(f"\n⚠️  User '{username}' already exists!")
        response = input("Do you want to update their password? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
        
        user_id = existing['id']
        # Update password
        password = getpass.getpass("Enter new password: ")
        if not password:
            print("ERROR: Password cannot be empty")
            sys.exit(1)
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
        
        await db.execute(
            """
            UPDATE users 
            SET password_hash = $1, 
                auth_method = 'password',
                role = 'admin',
                updated_at = NOW()
            WHERE id = $2
            """,
            (password_hash, user_id)
        )
        
        print(f"\n✅ Password updated for user '{username}'")
        print(f"   User ID: {user_id}")
        print(f"   Role: admin")
        return
    
    # Get password
    password = getpass.getpass("Enter password: ")
    if not password:
        print("ERROR: Password cannot be empty")
        sys.exit(1)
    
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)
    
    # Password requirements
    if len(password) < 12:
        print("⚠️  WARNING: Password should be at least 12 characters long")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    
    # Get name
    name = input("Enter full name (optional): ").strip()
    if not name:
        name = username
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
    
    # Create user
    try:
        user = await db.fetch_one(
            """
            INSERT INTO users (username, name, password_hash, auth_method, role)
            VALUES ($1, $2, $3, 'password', 'admin')
            RETURNING id, username, name, role, created_at
            """,
            (username, name, password_hash)
        )
        
        print("\n✅ Admin user created successfully!")
        print(f"   Username: {user['username']}")
        print(f"   Name: {user['name']}")
        print(f"   User ID: {user['id']}")
        print(f"   Role: {user['role']}")
        print(f"   Created: {user['created_at']}")
        print()
        print("You can now login at: /auth/login")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to create user: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_admin_user())


