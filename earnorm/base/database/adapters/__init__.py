"""Database adapter implementations.

This module provides concrete implementations of the DatabaseAdapter interface
for different database backends.

Currently supported databases:
- MongoDB (MongoAdapter)

Examples:
    >>> from earnorm.base.database.adapters import MongoAdapter

    >>> # Create and initialize adapter
    >>> adapter = MongoAdapter(
    ...     uri="mongodb://localhost:27017",
    ...     database="mydb"
    ... )
    >>> await adapter.init()

    >>> # Basic query
    >>> users = await adapter.query(User).filter(
    ...     age__gt=18,
    ...     status="active"
    ... ).all()

    >>> # Aggregate query
    >>> stats = await adapter.query(User, "aggregate")\\
    ...     .group_by("status")\\
    ...     .count("total")\\
    ...     .execute()

    >>> # Close when done
    >>> await adapter.close()
"""

import logging

from .mongo import MongoAdapter

logger = logging.getLogger(__name__)

__all__ = [
    # MongoDB adapter
    "MongoAdapter",
]
