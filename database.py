"""
Database connection and utilities for PostgreSQL with pgvector.

Handles:
- Database connection pooling
- Schema initialization
- Connection management
- Query helpers
"""

import os
import logging
import re
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Check for psycopg availability
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    PSYCOPG_AVAILABLE = True
except ImportError:
    logger.warning("psycopg3 not installed. Run: pip install psycopg[binary] psycopg-pool")
    PSYCOPG_AVAILABLE = False


class Database:
    """
    Database connection manager with connection pooling.
    
    Uses psycopg3 with async support and connection pooling.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            connection_string: PostgreSQL connection string
                Format: postgresql://user:password@host:port/database
                If not provided, reads from DATABASE_URL environment variable
        """
        if not PSYCOPG_AVAILABLE:
            raise RuntimeError("psycopg3 not installed")
        
        self.connection_string = connection_string or os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/rag_brain'
        )
        self.pool: Optional[AsyncConnectionPool] = None
    
    async def initialize(self, min_size: int = 2, max_size: int = 10) -> None:
        """
        Initialize connection pool.
        
        Args:
            min_size: Minimum number of connections in pool
            max_size: Maximum number of connections in pool
        """
        if self.pool:
            logger.warning("Pool already initialized")
            return
        
        try:
            self.pool = AsyncConnectionPool(
                self.connection_string,
                min_size=min_size,
                max_size=max_size,
                open=False
            )
            await self.pool.open()
            logger.info(f"Database pool initialized (min={min_size}, max={max_size})")
            
            # Test connection
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT version()")
                    version = await cur.fetchone()
                    logger.info(f"Connected to PostgreSQL: {version[0][:50]}...")
        
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
            self.pool = None
    
    @asynccontextmanager
    async def connection(self):
        """
        Get a connection from the pool (context manager).
        
        Usage:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT ...")
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        
        async with self.pool.connection() as conn:
            yield conn
    
    def _normalize_params(self, params: Optional[Any]) -> Optional[Any]:
        """Ensure query parameters are in a psycopg-friendly format."""
        if params is None:
            return None
        if isinstance(params, dict):
            return params
        if isinstance(params, (list, tuple)):
            return tuple(params)
        return (params,)

    def _convert_placeholders(self, query: str) -> str:
        """Convert $n style placeholders to %s for psycopg compatibility."""
        if not query or "$" not in query:
            return query
        return re.sub(r"\$(\d+)", "%s", query)

    async def execute(
        self,
        query: str,
        params: Optional[Any] = None,
        fetch: bool = False
    ) -> Optional[List[Any]]:
        """
        Execute a query.
        
        Args:
            query: SQL query
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            List of results if fetch=True, None otherwise
        """
        async with self.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(self._convert_placeholders(query), self._normalize_params(params))
                if fetch:
                    return await cur.fetchall()
                await conn.commit()
                return None
    
    async def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ) -> None:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
        """
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(self._convert_placeholders(query), [self._normalize_params(p) for p in params_list])
                await conn.commit()
    
    async def fetch_one(
        self,
        query: str,
        params: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Dictionary row or None
        """
        async with self.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(self._convert_placeholders(query), self._normalize_params(params))
                return await cur.fetchone()
    
    async def fetch_all(
        self,
        query: str,
        params: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of dictionary rows
        """
        async with self.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(self._convert_placeholders(query), self._normalize_params(params))
                return await cur.fetchall()
    
    async def init_schema(self, schema_file: str = "db_schema.sql") -> None:
        """
        Initialize database schema from SQL file.
        
        Args:
            schema_file: Path to schema SQL file
        """
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        logger.info("Initializing database schema...")
        
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(schema_sql)
                await conn.commit()
        
        logger.info("Database schema initialized successfully")
    
    async def check_pgvector(self) -> bool:
        """
        Check if pgvector extension is installed.
        
        Returns:
            True if pgvector is available
        """
        try:
            result = await self.fetch_one(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') as exists"
            )
            return result['exists'] if result else False
        except Exception as e:
            logger.error(f"Failed to check pgvector: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database connection.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Test basic query
            await self.execute("SELECT 1", fetch=True)
            
            # Check pgvector
            has_pgvector = await self.check_pgvector()
            
            # Get pool stats
            pool_stats = {}
            if self.pool:
                pool_stats = {
                    'size': self.pool.get_stats().get('pool_size', 0),
                    'available': self.pool.get_stats().get('pool_available', 0)
                }
            
            return {
                'status': 'healthy',
                'pgvector_available': has_pgvector,
                'pool_stats': pool_stats
            }
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global database instance
_global_db: Optional[Database] = None


def get_database(connection_string: Optional[str] = None) -> Database:
    """
    Get the global database instance.
    
    Args:
        connection_string: Optional connection string (only used on first call)
        
    Returns:
        Database instance
    """
    global _global_db
    if _global_db is None:
        _global_db = Database(connection_string)
    return _global_db


async def init_database(
    connection_string: Optional[str] = None,
    init_schema: bool = False,
    schema_file: str = "db_schema.sql"
) -> Database:
    """
    Initialize the global database instance.
    
    Args:
        connection_string: Optional connection string
        init_schema: Whether to initialize schema
        schema_file: Path to schema file
        
    Returns:
        Initialized Database instance
    """
    db = get_database(connection_string)
    
    if not db.pool:
        await db.initialize()
    
    if init_schema:
        await db.init_schema(schema_file)
    
    return db


