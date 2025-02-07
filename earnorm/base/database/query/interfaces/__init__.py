"""Query interfaces package.

This package provides interfaces for the query system:

1. Query Protocol (QueryProtocol)
   - Query building
   - Query execution
   - Result processing

2. Operation Protocols
   - Base operations (OperationProtocol)
   - Aggregate operations (AggregateProtocol)
   - Join operations (JoinProtocol)
   - Window operations (WindowProtocol)

3. Domain Expressions
   - Expression building
   - Operator support
   - Type safety

4. Field References
   - Field operations
   - Type hints
   - Validation

Examples:
    >>> from earnorm.base.database.query.interfaces import (
    ...     QueryProtocol,
    ...     OperationProtocol,
    ...     AggregateProtocol,
    ...     JoinProtocol,
    ...     WindowProtocol
    ... )
    >>> from earnorm.types import DatabaseModel

    >>> # Query protocol
    >>> class CustomQuery(QueryProtocol[ModelT]):
    ...     async def execute(self) -> List[ModelT]:
    ...         pass
    ...     def filter(self, **conditions) -> Self:
    ...         pass

    >>> # Operation protocol
    >>> class CustomOperation(OperationProtocol[ModelT]):
    ...     async def execute(self) -> List[ModelT]:
    ...         pass

    >>> # Domain expressions
    >>> from earnorm.base.database.query.interfaces import DomainExpression
    >>> expr = DomainExpression([("age", ">", 18), "&", ("status", "=", "active")])
    >>> expr.validate()

    >>> # Field references
    >>> from earnorm.base.database.query.interfaces import Field
    >>> class User(DatabaseModel):
    ...     name = Field[str]()
    ...     age = Field[int]()
"""

from earnorm.base.database.query.interfaces.domain import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
    DomainOperator,
)
from earnorm.base.database.query.interfaces.field import Field
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.base.database.query.interfaces.query import QueryProtocol

__all__ = [
    # Query protocol
    "QueryProtocol",
    # Operation protocols
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
