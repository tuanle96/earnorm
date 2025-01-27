"""Transaction module.

This module provides transaction functionality for EarnORM.
It includes:
- Transaction context manager
- ACID properties
- Error handling
- Transaction logging

Examples:
    >>> # Basic transaction
    >>> async with User.transaction() as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
    >>> # Rollback on error
    >>> async with User.transaction() as tx:
    ...     try:
    ...         user = User(name="John", age=25)
    ...         await tx.insert(user)
    ...         await tx.commit()
    ...     except Exception as e:
    ...         await tx.rollback()
    ...         logger.error("Transaction failed: %s", str(e))
    >>> # Multiple operations
    >>> async with User.transaction() as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     user.age = 26
    ...     await tx.update(user)
    ...     await tx.commit()
"""

import logging
from typing import TypeVar

from earnorm.types import DatabaseModel

from .backends.mongo import (
    MongoTransaction,
    MongoTransactionError,
    MongoTransactionManager,
)
from .base import Transaction, TransactionError, TransactionManager

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=DatabaseModel)

__all__ = [
    # Base classes
    "Transaction",
    "TransactionError",
    "TransactionManager",
    # MongoDB implementations
    "MongoTransaction",
    "MongoTransactionError",
    "MongoTransactionManager",
]
