#!/usr/bin/env python3
"""
Load db_schema.sql into Railway Postgres.
Run once to initialize the database.
"""
import psycopg

# Railway Postgres connection string (public URL)
DATABASE_URL = "postgresql://postgres:qjaFsNuEEoPqzncehfUbzVfFMPNGGQpV@trolley.proxy.rlwy.net:32671/railway"

# Read schema file
with open("db_schema.sql", "r") as f:
    schema_sql = f.read()

# Connect and execute
print("Connecting to Railway Postgres...")
conn = psycopg.connect(DATABASE_URL)
cur = conn.cursor()

print("Loading schema...")
cur.execute(schema_sql)
conn.commit()

print("✅ Schema loaded successfully")
cur.close()
conn.close()

