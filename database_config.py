"""
Database configuration for optimized connection pooling.

This module provides optimized database configuration settings for production use.
"""

import os
from typing import Dict, Any

def get_pool_config(environment: str = "production") -> Dict[str, Any]:
    """
    Get optimized connection pool configuration based on environment.
    
    Args:
        environment: Environment name (development, staging, production)
        
    Returns:
        Dictionary with pool configuration settings
    """
    
    # Base configuration
    base_config = {
        # Connection pool settings
        "min_size": 5,           # Minimum connections in pool
        "max_size": 20,          # Maximum connections in pool
        "max_overflow": 10,      # Maximum overflow connections
        "max_idle": 300,         # Max idle time (seconds) before connection is closed
        "max_lifetime": 3600,    # Max lifetime (seconds) of a connection
        
        # Retry settings
        "connect_timeout": 10,   # Connection timeout in seconds
        "command_timeout": 30,   # Command timeout in seconds
        "retry_on_failure": True,
        "max_retries": 3,
        
        # Performance settings
        "prepared_statements": True,
        "jit": "on",
        "statement_cache_size": 100,
        
        # Health check settings
        "health_check_interval": 30,  # Seconds between health checks
        "health_check_timeout": 5,    # Timeout for health checks
    }
    
    # Environment-specific overrides
    if environment == "development":
        return {
            **base_config,
            "min_size": 2,
            "max_size": 5,
            "max_overflow": 2,
            "health_check_interval": 60,
        }
    elif environment == "staging":
        return {
            **base_config,
            "min_size": 3,
            "max_size": 10,
            "max_overflow": 5,
        }
    elif environment == "production":
        return {
            **base_config,
            "min_size": int(os.getenv("DB_POOL_MIN", 5)),
            "max_size": int(os.getenv("DB_POOL_MAX", 20)),
            "max_overflow": int(os.getenv("DB_POOL_OVERFLOW", 10)),
            "max_idle": int(os.getenv("DB_POOL_MAX_IDLE", 300)),
            "max_lifetime": int(os.getenv("DB_POOL_MAX_LIFETIME", 3600)),
        }
    else:
        return base_config


def get_connection_string_with_params(base_url: str, environment: str = "production") -> str:
    """
    Enhance connection string with optimized parameters.
    
    Args:
        base_url: Base PostgreSQL connection URL
        environment: Environment name
        
    Returns:
        Enhanced connection string with parameters
    """
    # Parse base URL to add parameters
    if "?" in base_url:
        separator = "&"
    else:
        separator = "?"
    
    # Add connection parameters for better performance
    params = []
    
    # Connection pooling parameters
    params.append("pool_size=20")
    params.append("max_overflow=10")
    
    # Performance parameters
    params.append("statement_cache_size=100")
    params.append("prepared_statement_cache_size=100")
    
    # Timeout parameters
    params.append("connect_timeout=10")
    params.append("command_timeout=30")
    
    # SSL parameters (for production)
    if environment == "production":
        params.append("sslmode=require")
    else:
        params.append("sslmode=prefer")
    
    # Application name for monitoring
    app_name = os.getenv("APP_NAME", "mini-rag")
    params.append(f"application_name={app_name}")
    
    return base_url + separator + "&".join(params)


def calculate_optimal_pool_size() -> Dict[str, int]:
    """
    Calculate optimal pool size based on system resources.
    
    Returns:
        Dictionary with recommended pool sizes
    """
    import multiprocessing
    
    # Get CPU count
    cpu_count = multiprocessing.cpu_count()
    
    # Formula for optimal pool size:
    # Pool Size = (Number of CPU Cores * 2) + Number of Disk Spindles
    # For SSDs, we use CPU cores * 2 as a baseline
    
    recommended_min = max(2, cpu_count)
    recommended_max = max(4, cpu_count * 2)
    recommended_overflow = max(2, cpu_count // 2)
    
    return {
        "min_size": recommended_min,
        "max_size": recommended_max,
        "max_overflow": recommended_overflow,
        "cpu_count": cpu_count,
    }


class PoolMonitor:
    """Monitor and log connection pool statistics."""
    
    def __init__(self, pool, logger):
        """
        Initialize pool monitor.
        
        Args:
            pool: Connection pool instance
            logger: Logger instance
        """
        self.pool = pool
        self.logger = logger
        self._last_stats = {}
    
    def log_stats(self):
        """Log current pool statistics."""
        if not self.pool:
            return
        
        try:
            stats = self.pool.get_stats()
            
            # Calculate metrics
            pool_size = stats.get('pool_size', 0)
            pool_available = stats.get('pool_available', 0)
            pool_in_use = pool_size - pool_available
            usage_percent = (pool_in_use / pool_size * 100) if pool_size > 0 else 0
            
            # Log if there are significant changes
            if (
                stats != self._last_stats or
                usage_percent > 80 or
                pool_available == 0
            ):
                self.logger.info(
                    f"Pool Stats: {pool_in_use}/{pool_size} in use ({usage_percent:.1f}%), "
                    f"{pool_available} available"
                )
                
                # Warn if pool is exhausted or nearly exhausted
                if pool_available == 0:
                    self.logger.warning("Connection pool exhausted!")
                elif usage_percent > 90:
                    self.logger.warning(f"Connection pool usage high: {usage_percent:.1f}%")
            
            self._last_stats = stats.copy()
        except Exception as e:
            self.logger.error(f"Failed to get pool stats: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics for monitoring."""
        if not self.pool:
            return {}
        
        try:
            stats = self.pool.get_stats()
            pool_size = stats.get('pool_size', 0)
            pool_available = stats.get('pool_available', 0)
            pool_in_use = pool_size - pool_available
            
            return {
                "pool_size": pool_size,
                "pool_available": pool_available,
                "pool_in_use": pool_in_use,
                "pool_usage_percent": (pool_in_use / pool_size * 100) if pool_size > 0 else 0,
                "pool_exhausted": pool_available == 0,
            }
        except Exception:
            return {}


# Connection string templates for different cloud providers
CLOUD_TEMPLATES = {
    "railway": {
        "pattern": "postgresql://{user}:{password}@{host}:{port}/{database}",
        "defaults": {
            "sslmode": "require",
            "pool_size": "20",
            "statement_cache_size": "100",
        }
    },
    "supabase": {
        "pattern": "postgresql://{user}:{password}@{host}:{port}/{database}",
        "defaults": {
            "sslmode": "require",
            "pool_mode": "transaction",
            "pgbouncer": "true",
        }
    },
    "render": {
        "pattern": "postgresql://{user}:{password}@{host}/{database}",
        "defaults": {
            "sslmode": "require",
            "pool_size": "20",
        }
    },
    "aws_rds": {
        "pattern": "postgresql://{user}:{password}@{host}:{port}/{database}",
        "defaults": {
            "sslmode": "require",
            "sslrootcert": "rds-ca-2019-root.pem",
        }
    },
    "gcp_cloud_sql": {
        "pattern": "postgresql://{user}:{password}@/{database}?host=/cloudsql/{instance}",
        "defaults": {
            "sslmode": "disable",  # Uses Unix socket
        }
    },
    "azure": {
        "pattern": "postgresql://{user}@{server}:{password}@{host}:{port}/{database}",
        "defaults": {
            "sslmode": "require",
            "sslcert": "BaltimoreCyberTrustRoot.crt.pem",
        }
    }
}


