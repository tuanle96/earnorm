"""Query operation interfaces package.

This package provides interfaces for all query operations:

1. Base Operations (OperationProtocol)
   - Operation execution
   - Result processing
   - Configuration validation

2. Aggregate Operations (AggregateProtocol)
   - Group by operations
   - Aggregation functions
   - Having clauses

3. Join Operations (JoinProtocol)
   - Multiple join types
   - Join conditions
   - Field selection

4. Window Operations (WindowProtocol)
   - Window functions
   - Frame specifications
   - Partitioning

Examples:
    >>> from earnorm.base.database.query.interfaces.operations import (
    ...     OperationProtocol,
    ...     AggregateProtocol,
    ...     JoinProtocol,
    ...     WindowProtocol
    ... )
    >>> from earnorm.types import DatabaseModel

    >>> # Base operation
    >>> class CustomOperation(OperationProtocol[ModelT]):
    ...     async def execute(self) -> List[ModelT]:
    ...         pass

    >>> # Aggregate operation
    >>> class CustomAggregate(AggregateProtocol[ModelT]):
    ...     def group_by(self, *fields: str) -> Self:
    ...         pass

    >>> # Join operation
    >>> class CustomJoin(JoinProtocol[ModelT, JoinT]):
    ...     def join(self, model: Type[JoinT]) -> Self:
    ...         pass

    >>> # Window operation
    >>> class CustomWindow(WindowProtocol[ModelT]):
    ...     def over(self, partition_by: List[str]) -> Self:
    ...         pass
"""

from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol

__all__ = [
    # Base protocol
    "OperationProtocol",
    # Operation protocols
    "AggregateProtocol",
    "JoinProtocol",
    "WindowProtocol",
]
