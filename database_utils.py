"""
Database utilities for transaction management and retry logic.

Provides decorators and utilities for robust database operations.
"""

import asyncio
import logging
import functools
from typing import Any, Callable, TypeVar, Optional, Dict
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Type variables for generic decorators
F = TypeVar('F', bound=Callable[..., Any])


class DatabaseTransactionError(Exception):
    """Custom exception for transaction failures."""
    pass


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    max_delay: float = 5.0,
    retry_exceptions: tuple = (ConnectionError, TimeoutError)
):
    """
    Decorator for retrying database operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay on each retry
        max_delay: Maximum delay between retries
        retry_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                except Exception as e:
                    # Non-retryable exception, re-raise immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            # All attempts failed, raise the last exception
            if last_exception:
                raise DatabaseTransactionError(
                    f"Failed after {max_attempts} attempts: {last_exception}"
                ) from last_exception
        
        return wrapper
    return decorator


@asynccontextmanager
async def database_transaction(db, savepoint: bool = False):
    """
    Context manager for database transactions with automatic rollback on error.
    
    Args:
        db: Database instance
        savepoint: Whether to use a savepoint instead of full transaction
        
    Usage:
        async with database_transaction(db) as conn:
            # Perform database operations
            await conn.execute(...)
    """
    conn = None
    try:
        async with db.connection() as conn:
            if savepoint:
                # Use savepoint for nested transactions
                await conn.execute("SAVEPOINT sp1")
                try:
                    yield conn
                    await conn.execute("RELEASE SAVEPOINT sp1")
                except Exception:
                    await conn.execute("ROLLBACK TO SAVEPOINT sp1")
                    raise
            else:
                # Full transaction
                await conn.execute("BEGIN")
                try:
                    yield conn
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        raise


async def batch_insert_with_transaction(
    db,
    table: str,
    records: list,
    columns: list,
    batch_size: int = 100,
    on_conflict: Optional[str] = None
) -> Dict[str, Any]:
    """
    Insert multiple records in batches within a transaction.
    
    Args:
        db: Database instance
        table: Table name
        records: List of records to insert
        columns: Column names
        batch_size: Number of records per batch
        on_conflict: Optional ON CONFLICT clause
        
    Returns:
        Dictionary with insertion results
    """
    if not records:
        return {"inserted": 0, "batches": 0}
    
    inserted = 0
    batches = 0
    errors = []
    
    # Build query
    placeholders = ", ".join(["%s"] * len(columns))
    column_list = ", ".join(columns)
    query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
    
    if on_conflict:
        query += f" {on_conflict}"
    
    try:
        async with database_transaction(db) as conn:
            # Process in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                batches += 1
                
                try:
                    # Convert records to tuples for insertion
                    values = []
                    for record in batch:
                        if isinstance(record, dict):
                            values.append(tuple(record.get(col) for col in columns))
                        else:
                            values.append(record)
                    
                    # Execute batch insert
                    async with conn.cursor() as cur:
                        await cur.executemany(query, values)
                        inserted += len(batch)
                        
                except Exception as e:
                    errors.append(f"Batch {batches}: {e}")
                    logger.error(f"Failed to insert batch {batches}: {e}")
                    # Continue with other batches in transaction
            
            if errors and inserted == 0:
                # All batches failed, rollback will happen
                raise DatabaseTransactionError(f"All batches failed: {errors}")
    
    except Exception as e:
        logger.error(f"Batch insert transaction failed: {e}")
        return {
            "inserted": inserted,
            "batches": batches,
            "errors": errors,
            "transaction_error": str(e)
        }
    
    logger.info(f"Successfully inserted {inserted} records in {batches} batches")
    return {
        "inserted": inserted,
        "batches": batches,
        "errors": errors
    }


@with_retry(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))
async def execute_with_retry(db, query: str, params: Optional[tuple] = None) -> Any:
    """
    Execute a query with automatic retry on connection errors.
    
    Args:
        db: Database instance
        query: SQL query
        params: Query parameters
        
    Returns:
        Query result
    """
    return await db.execute(query, params, fetch=True)


@with_retry(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))
async def fetch_with_retry(db, query: str, params: Optional[tuple] = None) -> list:
    """
    Fetch results with automatic retry on connection errors.
    
    Args:
        db: Database instance
        query: SQL query
        params: Query parameters
        
    Returns:
        List of results
    """
    return await db.fetch_all(query, params)


async def ensure_connection(db) -> bool:
    """
    Ensure database connection is alive and reconnect if needed.
    
    Args:
        db: Database instance
        
    Returns:
        True if connection is healthy
    """
    try:
        # Try a simple query
        await db.execute("SELECT 1", fetch=True)
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        
        # Try to reconnect
        try:
            if db.pool:
                await db.pool.close()
            await db.initialize()
            logger.info("Database reconnected successfully")
            return True
        except Exception as reconnect_error:
            logger.error(f"Failed to reconnect to database: {reconnect_error}")
            return False


class ConnectionPool:
    """Enhanced connection pool with health checks and auto-recovery."""
    
    def __init__(self, db, check_interval: int = 30):
        """
        Initialize connection pool monitor.
        
        Args:
            db: Database instance
            check_interval: Seconds between health checks
        """
        self.db = db
        self.check_interval = check_interval
        self._health_check_task = None
    
    async def start_health_checks(self):
        """Start background health check task."""
        if self._health_check_task:
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Connection pool health checks started")
    
    async def stop_health_checks(self):
        """Stop background health check task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Connection pool health checks stopped")
    
    async def _health_check_loop(self):
        """Background task to check connection health."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check pool health
                if self.db.pool:
                    stats = self.db.pool.get_stats()
                    pool_size = stats.get('pool_size', 0)
                    pool_available = stats.get('pool_available', 0)
                    
                    # Log pool status
                    logger.debug(f"Pool status: {pool_available}/{pool_size} available")
                    
                    # Check if pool is exhausted
                    if pool_available == 0 and pool_size > 0:
                        logger.warning("Connection pool exhausted")
                    
                    # Perform health check
                    healthy = await ensure_connection(self.db)
                    if not healthy:
                        logger.error("Database health check failed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")


# Optimized query patterns
BULK_INSERT_CHUNK_QUERY = """
    INSERT INTO chunks (
        id, organization_id, workspace_id, document_id, 
        project_id, text, position, start_offset, end_offset
    ) VALUES %s
    ON CONFLICT (id) DO UPDATE SET
        text = EXCLUDED.text,
        position = EXCLUDED.position,
        start_offset = EXCLUDED.start_offset,
        end_offset = EXCLUDED.end_offset
"""

BULK_DELETE_CHUNKS_QUERY = """
    DELETE FROM chunks 
    WHERE id = ANY(%s::uuid[])
    RETURNING id
"""
