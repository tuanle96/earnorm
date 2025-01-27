"""Query interfaces package.

This package provides interfaces for all query operations.
"""

from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.base.database.query.interfaces.query import QueryProtocol

__all__ = [
    "QueryProtocol",
    "OperationProtocol",
    "AggregateProtocol",
    "JoinProtocol",
    "WindowProtocol",
]
