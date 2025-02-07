"""Base module for EarnORM.

This module provides core functionality for EarnORM framework, including:

1. Model System
   - Model definition and management
   - Field types and validation
   - CRUD operations
   - Query building and execution
   - Event handling and lifecycle hooks

2. Database System
   - Database adapters
   - Transaction management
   - Query building
   - Connection pooling
   - Result mapping

3. Environment System
   - Application state management
   - Service registry
   - Dependency injection
   - Configuration management
   - Resource cleanup

Examples:
    >>> from earnorm.base import BaseModel, Transaction
    >>> from earnorm.fields import StringField, IntegerField

    >>> # Define model
    >>> class User(BaseModel):
    ...     _name = 'data.user'
    ...     name = StringField(required=True)
    ...     age = IntegerField()

    >>> # Use transaction
    >>> async with Transaction() as txn:
    ...     user = await User.with_env(txn).create({
    ...         "name": "John",
    ...         "age": 30
    ...     })

Features:
    1. Model Layer:
       - Async/await support
       - Field validation
       - Type checking
       - Event system
       - Cache management

    2. Database Layer:
       - Multiple backends
       - ACID transactions
       - Query optimization
       - Connection pooling
       - Error handling

    3. Environment Layer:
       - Service registry
       - DI container
       - Config management
       - Resource cleanup
       - Logging support

See Also:
    - earnorm.fields: Field definitions
    - earnorm.database: Database adapters
    - earnorm.env: Environment management
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

__all__ = [
    # Base model
    "BaseModel",
    # Transaction classes
    "Transaction",
    "TransactionError",
    "TransactionManager",
    # MongoDB specific
    "MongoTransaction",
    "MongoTransactionError",
    "MongoTransactionManager",
]
