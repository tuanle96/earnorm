"""MongoDB query implementation.

This module provides MongoDB-specific query implementation including:

1. Query Builder (MongoQueryBuilder)
   - Pipeline building
   - Stage generation
   - Result mapping
   - Error handling

2. Query Implementation (MongoQuery)
   - Query execution
   - Result processing
   - Type conversion
   - Connection management

3. Type Converter (MongoConverter)
   - BSON conversion
   - ObjectId handling
   - Date/time types
   - Decimal support

Examples:
    >>> from earnorm.base.database.query.backends.mongo import (
    ...     MongoQuery,
    ...     MongoQueryBuilder,
    ...     MongoConverter
    ... )
    >>> from earnorm.types import DatabaseModel

    >>> # Query example
    >>> query = MongoQuery(User)
    >>> query.filter(age__gt=18)
    >>> results = await query.execute()

    >>> # Builder example
    >>> builder = MongoQueryBuilder()
    >>> pipeline = builder.match(
    ...     {"age": {"$gt": 18}}
    ... ).sort(
    ...     {"created_at": -1}
    ... ).limit(10).build()

    >>> # Converter example
    >>> converter = MongoConverter()
    >>> mongo_filter = converter.convert(domain.to_list())
"""

from .builder import MongoQueryBuilder
from .converter import MongoConverter
from .operations import MongoAggregate, MongoJoin, MongoWindow
from .query import MongoQuery

__all__ = [
    # Query classes
    "MongoQuery",
    "MongoQueryBuilder",
    "MongoConverter",
    # Operations
    "MongoAggregate",
    "MongoJoin",
    "MongoWindow",
]
