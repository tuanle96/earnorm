"""Query module.

This module provides query functionality for EarnORM.
It includes:
- Query builder with fluent interface
- Domain expressions and field references
- Operations (join, aggregate, window)
- Query caching
- Type safety with generics

Examples:
    >>> from earnorm.types import DatabaseModel
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    >>> class Post(DatabaseModel):
    ...     title: str
    ...     user_id: str
    >>> # Basic query
    >>> users = await User.query().filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> # Join query
    >>> users = await User.query().join(Post).on(User.id == Post.user_id)
    >>> # Aggregate query
    >>> stats = await User.query().aggregate().group_by(User.age).count()
    >>> # Window query
    >>> ranked = await User.query().window().over(partition_by=[User.age]).row_number()
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
