"""Database module.

This module provides database functionality for EarnORM, including:
1. Database adapters
2. Query building
3. Transaction management

The module is organized into several submodules:

- adapters/: Database-specific adapter implementations
- query/: Query building and execution
- transaction/: Transaction management

Examples:
    >>> from earnorm.base.database import DatabaseAdapter
    >>> from earnorm.base.database.adapters import MongoAdapter

    >>> # Create and initialize adapter
    >>> adapter = MongoAdapter(uri="mongodb://localhost:27017")
    >>> await adapter.init()

    >>> # Basic query
    >>> users = await adapter.query(User).filter(
    ...     age__gt=18,
    ...     status="active"
    ... ).all()

    >>> # Transaction
    >>> async with adapter.transaction() as txn:
    ...     user = await txn.create(User, {"name": "John"})
    ...     order = await txn.create(Order, {"user_id": user.id})
"""

from .transaction import (
    MongoTransaction,
    MongoTransactionError,
    MongoTransactionManager,
    Transaction,
    TransactionError,
    TransactionManager,
)

__all__ = [
    "MongoTransaction",
    "MongoTransactionError",
    "MongoTransactionManager",
    "Transaction",
    "TransactionError",
    "TransactionManager",
]
