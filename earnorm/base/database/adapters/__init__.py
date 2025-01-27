"""Database adapters module.

This module provides database adapters for EarnORM.
It includes:
- Database adapter interface
- Connection pooling
- CRUD operations
- Error handling
- Operation logging

Examples:
    >>> from earnorm.types import DatabaseModel
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    >>> # Basic operations
    >>> adapter = MongoAdapter(uri="mongodb://localhost:27017", database="test")
    >>> await adapter.init()
    >>> # Insert
    >>> user = User(name="John", age=25)
    >>> await adapter.insert(user)
    >>> # Update
    >>> user.age = 26
    >>> await adapter.update(user)
    >>> # Delete
    >>> await adapter.delete(user)
    >>> # Query
    >>> users = await adapter.query(User).filter({"age": {"$gt": 18}}).all()
    >>> # Transaction
    >>> async with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
"""

import logging

from .mongo import MongoAdapter

logger = logging.getLogger(__name__)

__all__ = [
    # MongoDB adapter
    "MongoAdapter",
]
