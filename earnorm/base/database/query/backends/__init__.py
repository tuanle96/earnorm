"""Database-specific query implementations.

This module provides query implementations for different database backends.
Currently supports:
- MongoDB
"""

from earnorm.base.database.query.backends.mongo import MongoQuery, MongoQueryBuilder

__all__ = ["MongoQuery", "MongoQueryBuilder"]
