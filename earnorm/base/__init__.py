"""Base module for EarnORM.

This module provides core functionality:
- Model definition and management
- Field types and validation
- Query building and execution
- Record management and operations
- Event handling and lifecycle hooks
"""

from earnorm.base.database import (
    MongoTransaction,
    MongoTransactionError,
    MongoTransactionManager,
    Transaction,
    TransactionError,
    TransactionManager,
)

from .model import BaseModel
from .registry import DatabaseRegistry

__all__ = [
    "BaseModel",
    "DatabaseRegistry",
    "Transaction",
    "TransactionError",
    "TransactionManager",
    "MongoTransaction",
    "MongoTransactionError",
    "MongoTransactionManager",
]
