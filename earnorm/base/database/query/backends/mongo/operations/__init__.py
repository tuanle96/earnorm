"""MongoDB operations package.

This package provides MongoDB-specific implementations for query operations:

1. Aggregate Operations (MongoAggregate)
   - Group by fields
   - Aggregation functions
   - Having clauses
   - Pipeline stages

2. Join Operations (MongoJoin)
   - $lookup stages
   - Multiple joins
   - Join conditions
   - Field selection

3. Window Operations (MongoWindow)
   - Ranking functions
   - Frame specifications
   - Partitioning
   - Custom functions

Examples:
    >>> from earnorm.base.database.query.backends.mongo.operations import (
    ...     MongoAggregate,
    ...     MongoJoin,
    ...     MongoWindow
    ... )

    >>> # Aggregate example
    >>> agg = MongoAggregate(Order)
    >>> stats = await agg.group_by(
    ...     "status"
    ... ).count("total").execute()

    >>> # Join example
    >>> join = MongoJoin(User)
    >>> results = await join.join(
    ...     Post
    ... ).on(
    ...     User.id == Post.user_id
    ... ).execute()

    >>> # Window example
    >>> window = MongoWindow(Employee)
    >>> results = await window.over(
    ...     partition_by=["department"]
    ... ).row_number("rank").execute()
"""

from earnorm.base.database.query.backends.mongo.operations.aggregate import (
    MongoAggregate,
)
from earnorm.base.database.query.backends.mongo.operations.join import MongoJoin
from earnorm.base.database.query.backends.mongo.operations.window import MongoWindow

__all__ = [
    # Aggregate operations
    "MongoAggregate",
    # Join operations
    "MongoJoin",
    # Window operations
    "MongoWindow",
]
