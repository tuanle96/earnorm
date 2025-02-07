"""Operation implementations.

This module provides concrete implementations of database operations:

1. Base Operation
   - Operation chaining
   - Result processing
   - Pipeline building

2. Aggregate Operations
   - Group by fields
   - Aggregation functions
   - Having clauses

3. Join Operations
   - Multiple join types
   - Join conditions
   - Field selection

4. Window Operations
   - Ranking functions
   - Frame specifications
   - Partitioning

Examples:
    >>> from earnorm.base.database.query.core.operations import (
    ...     Operation,
    ...     AggregateOperation,
    ...     JoinOperation,
    ...     WindowOperation
    ... )
    >>> from earnorm.types import DatabaseModel

    >>> # Base operation
    >>> op = Operation(User)
    >>> op.add_processor(lambda x: x.upper())
    >>> results = await op.execute()

    >>> # Aggregate operation
    >>> agg = AggregateOperation(Order)
    >>> stats = await agg.group_by(
    ...     "status"
    ... ).count(
    ...     "total"
    ... ).execute()

    >>> # Join operation
    >>> join = JoinOperation(User)
    >>> results = await join.join(
    ...     Post
    ... ).on(
    ...     User.id == Post.user_id
    ... ).execute()

    >>> # Window operation
    >>> window = WindowOperation(Employee)
    >>> results = await window.over(
    ...     partition_by=["department"]
    ... ).row_number(
    ...     "rank"
    ... ).execute()
"""

from .aggregate import BaseAggregate
from .base import BaseOperation, Operation
from .join import BaseJoin
from .window import BaseWindow

__all__ = [
    # Base classes
    "BaseOperation",
    "Operation",
    # Aggregate operations
    "BaseAggregate",
    # Join operations
    "BaseJoin",
    # Window operations
    "BaseWindow",
]
