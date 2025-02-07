"""Database-specific query implementations.

This module provides query implementations for different database backends.
Currently supports:
- MongoDB (query building, aggregation pipeline, joins, window functions)

Examples:
    >>> from earnorm.base.database.query.backends import MongoQuery
    >>> from earnorm.types import DatabaseModel

    >>> # Create MongoDB query
    >>> query = MongoQuery(User)
    >>> query.filter(age__gt=18)
    >>> results = await query.execute()

    >>> # Use query builder
    >>> from earnorm.base.database.query.backends import MongoQueryBuilder
    >>> builder = MongoQueryBuilder()
    >>> pipeline = builder.match(
    ...     {"age": {"$gt": 18}}
    ... ).sort(
    ...     {"created_at": -1}
    ... ).limit(10).build()

    >>> # Use converter
    >>> from earnorm.base.database.query.backends.mongo import MongoConverter
    >>> converter = MongoConverter()
    >>> mongo_filter = converter.convert(domain.to_list())

    >>> # Use operations
    >>> from earnorm.base.database.query.backends.mongo.operations import (
    ...     MongoAggregate,
    ...     MongoJoin,
    ...     MongoWindow
    ... )
    >>> # Aggregate
    >>> agg = MongoAggregate(Order)
    >>> stats = await agg.group_by("status").count("total").execute()
    >>> # Join
    >>> join = MongoJoin(User)
    >>> results = await join.join(Post).on(User.id == Post.user_id).execute()
    >>> # Window
    >>> window = MongoWindow(Employee)
    >>> results = await window.over(
    ...     partition_by=["department"]
    ... ).row_number("rank").execute()
"""

from earnorm.base.database.query.backends.mongo import (
    MongoConverter,
    MongoQuery,
    MongoQueryBuilder,
)
from earnorm.base.database.query.backends.mongo.operations import (
    MongoAggregate,
    MongoJoin,
    MongoWindow,
)

__all__ = [
    # MongoDB query
    "MongoQuery",
    "MongoQueryBuilder",
    "MongoConverter",
    # MongoDB operations
    "MongoAggregate",
    "MongoJoin",
    "MongoWindow",
]
