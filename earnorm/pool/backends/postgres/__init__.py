"""PostgreSQL pool package.

This package provides PostgreSQL connection pool implementation.
"""

from earnorm.pool.backends.postgres.pool import PostgresPool

__all__ = ["PostgresPool"]
