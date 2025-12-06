#!/usr/bin/env python3
"""
Run database migrations using Alembic.

This script handles database schema migrations for the Mini-RAG application.
"""

import os
import sys
import logging
from alembic import command
from alembic.config import Config

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations(direction: str = "upgrade", revision: str = "head"):
    """
    Run database migrations.
    
    Args:
        direction: "upgrade" or "downgrade"
        revision: Target revision (default "head" for latest)
    """
    # Get database URL from environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set, using default: postgresql://postgres:postgres@localhost:5432/rag_brain")
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        os.environ["DATABASE_URL"] = db_url
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    try:
        if direction == "upgrade":
            logger.info(f"Upgrading database to {revision}")
            command.upgrade(alembic_cfg, revision)
            logger.info("Database upgrade completed successfully")
        elif direction == "downgrade":
            logger.info(f"Downgrading database to {revision}")
            command.downgrade(alembic_cfg, revision)
            logger.info("Database downgrade completed successfully")
        else:
            raise ValueError(f"Invalid direction: {direction}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


def check_current_revision():
    """Check the current database revision."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        os.environ["DATABASE_URL"] = db_url
    
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    try:
        command.current(alembic_cfg)
    except Exception as e:
        logger.error(f"Failed to check current revision: {e}")
        sys.exit(1)


def create_migration(message: str):
    """Create a new migration file."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        os.environ["DATABASE_URL"] = db_url
    
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    try:
        logger.info(f"Creating migration: {message}")
        command.revision(alembic_cfg, message=message, autogenerate=False)
        logger.info("Migration file created successfully")
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "command",
        choices=["upgrade", "downgrade", "current", "create"],
        help="Migration command to run"
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="Target revision (default: head)"
    )
    parser.add_argument(
        "--message",
        help="Migration message (for create command)"
    )
    
    args = parser.parse_args()
    
    if args.command == "upgrade":
        run_migrations("upgrade", args.revision)
    elif args.command == "downgrade":
        run_migrations("downgrade", args.revision)
    elif args.command == "current":
        check_current_revision()
    elif args.command == "create":
        if not args.message:
            logger.error("--message required for create command")
            sys.exit(1)
        create_migration(args.message)


if __name__ == "__main__":
    main()



