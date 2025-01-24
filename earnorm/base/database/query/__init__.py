"""Query module.

This module provides query functionality for different database backends.
It includes base classes and implementations for MongoDB, MySQL and PostgreSQL.
"""

from earnorm.base.database.query.backends.mongo.builder import MongoQueryBuilder
from earnorm.base.database.query.backends.mongo.executor import MongoQueryExecutor
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.base import Query, QueryBuilder, QueryExecutor

__all__ = [
    # Base classes
    "Query",
    "QueryBuilder",
    "QueryExecutor",
    # MongoDB implementations
    "MongoQuery",
    "MongoQueryBuilder",
    "MongoQueryExecutor",
]
