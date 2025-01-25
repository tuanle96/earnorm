"""Query module.

This module provides query functionality for different database backends.
It includes base classes and implementations for MongoDB, MySQL and PostgreSQL.
"""

from .backends.mongo.builder import MongoQueryBuilder
from .backends.mongo.query import MongoQuery
from .base.query import Query, QueryBuilder

__all__ = [
    # Base classes
    "Query",
    "QueryBuilder",
    # MongoDB implementations
    "MongoQuery",
    "MongoQueryBuilder",
]
