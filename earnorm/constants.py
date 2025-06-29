"""Constants for EarnORM.

This module contains all constants used across EarnORM.
"""


# Backend types
class BackendType:
    """Database backend types."""

    MONGODB = "mongodb"
    """MongoDB backend type."""

    POSTGRESQL = "postgresql"  # For future use
    """PostgreSQL backend type."""

    MYSQL = "mysql"  # For future use
    """MySQL backend type."""

    SQLITE = "sqlite"  # For future use
    """SQLite backend type."""


# Field mapping by backend
FIELD_MAPPING = {BackendType.MONGODB: {"id": "_id"}}
"""Field name mapping for different backends."""

__all__ = ["FIELD_MAPPING", "BackendType"]
