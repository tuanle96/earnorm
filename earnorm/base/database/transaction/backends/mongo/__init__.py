"""MongoDB transaction implementation.

This module provides MongoDB-specific transaction implementation.

Examples:
    >>> with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     tx.insert(user)
    ...     tx.update(user)
    ...     tx.delete(user)
    ...     tx.commit()
"""

from .transaction import (
    MongoTransaction,
    MongoTransactionError,
    MongoTransactionManager,
)

__all__ = ["MongoTransaction", "MongoTransactionError", "MongoTransactionManager"]
