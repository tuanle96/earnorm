"""Query building and execution system.

This module provides a flexible and type-safe query building system for EarnORM.
It supports three main types of queries:

1. Basic Queries
   - Filtering with operators
   - Sorting and pagination
   - Field selection
   - Result limiting

2. Aggregate Queries
   - Group by operations
   - Aggregation functions (count, sum, avg)
   - Having clauses
   - Pipeline stages

3. Join Queries
   - Inner/outer joins
   - Multiple join conditions
   - Join-specific field selection
   - Cross-database joins

Examples:
    >>> from earnorm.base.database.query import Query
    >>> from earnorm.types import DatabaseModel

    >>> # Basic query
    >>> users = await Query(User).filter(
    ...     age__gt=18,
    ...     status="active"
    ... ).order_by("-created_at").all()

    >>> # Complex filter with domain builder
    >>> from earnorm.base.database.query import DomainBuilder
    >>> users = await Query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .or_()
    ...     .field("role").in_(["admin", "moderator"])
    ...     .build()
    ... ).all()

    >>> # Aggregate query
    >>> stats = await Query(Order, "aggregate")\\
    ...     .group_by("status", "category")\\
    ...     .count("total_orders")\\
    ...     .sum("amount", "total_amount")\\
    ...     .avg("amount", "avg_amount")\\
    ...     .having(total_orders__gt=10)\\
    ...     .execute()

    >>> # Join query
    >>> results = await Query(User, "join")\\
    ...     .join(Post)\\
    ...     .on(User.id == Post.user_id)\\
    ...     .select("name", "posts.title")\\
    ...     .execute()
"""

from .core.query import BaseQuery
from .interfaces.domain import DomainExpression, DomainLeaf, DomainNode, DomainOperator
from .interfaces.field import Field
from .interfaces.operations.aggregate import AggregateProtocol
from .interfaces.operations.base import OperationProtocol
from .interfaces.operations.join import JoinProtocol
from .interfaces.operations.window import WindowProtocol
from .interfaces.query import QueryProtocol

__all__ = [
    # Base classes
    "BaseQuery",
    # Interfaces
    "QueryProtocol",
    "OperationProtocol",
    "AggregateProtocol",
    "JoinProtocol",
    "WindowProtocol",
    # Domain expressions
    "DomainExpression",
    "DomainLeaf",
    "DomainNode",
    "DomainOperator",
    # Field references
    "Field",
]
