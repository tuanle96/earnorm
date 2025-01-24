"""Transaction management package.

This package provides transaction management for different databases.
It includes base classes and implementations for:
- MongoDB
- PostgreSQL
- MySQL

Examples:
    ```python
    # MongoDB
    async with MongoTransactionManager(pool) as tx:
        await tx.execute(query)
        await tx.commit()

    # PostgreSQL
    async with PostgresTransactionManager(pool) as tx:
        await tx.execute(query)
        await tx.commit()

    # MySQL
    async with MySQLTransactionManager(pool) as tx:
        await tx.execute(query)
        await tx.commit()
    ```
"""

from earnorm.base.database.transaction.base import Transaction, TransactionManager
from earnorm.base.database.transaction.mongo import (
    MongoTransaction,
    MongoTransactionCommitError,
    MongoTransactionError,
    MongoTransactionManager,
    MongoTransactionRollbackError,
)

__all__ = [
    # Base classes
    "Transaction",
    "TransactionManager",
    # MongoDB
    "MongoTransaction",
    "MongoTransactionError",
    "MongoTransactionManager",
    "MongoTransactionCommitError",
    "MongoTransactionRollbackError",
]
