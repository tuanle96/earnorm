"""Transaction management base classes.

This module provides base classes for transaction management.
It includes:
- Transaction interface
- Transaction manager
- Transaction context

Examples:
    ```python
    async with TransactionManager(pool) as tx:
        await tx.execute(query)
        await tx.commit()
    ```
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar, cast

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol

# Type variables for database and collection
DBType = TypeVar("DBType")
CollType = TypeVar("CollType")

# Type variables for query and result
QueryType = TypeVar("QueryType")
ResultType = TypeVar("ResultType")


class Transaction(ABC, Generic[DBType, CollType, QueryType, ResultType]):
    """Abstract transaction.

    This class defines the interface for database transactions.
    It provides methods for executing queries within a transaction.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)
        CollType: Collection type (e.g. AsyncIOMotorCollection)
        QueryType: Query type (e.g. MongoQuery)
        ResultType: Result type (e.g. Dict[str, Any])

    Examples:
        ```python
        async with backend.transaction() as tx:
            await tx.execute(query1)
            await tx.execute(query2)
        ```
    """

    def __init__(self, conn: ConnectionProtocol[DBType, CollType]) -> None:
        """Initialize transaction.

        Args:
            conn: Database connection from pool
        """
        self._conn = conn
        self._active = False

    @property
    def connection(self) -> ConnectionProtocol[DBType, CollType]:
        """Get current connection.

        Returns:
            Database connection
        """
        return self._conn

    @property
    def is_active(self) -> bool:
        """Check if transaction is active.

        Returns:
            True if transaction is active
        """
        return self._active

    @abstractmethod
    async def validate(self) -> None:
        """Validate transaction state.

        This method should check if:
        - Connection is valid
        - Transaction is active
        - Any other database-specific validation

        Raises:
            TransactionError: If validation fails
        """
        pass

    @abstractmethod
    async def execute(self, query: QueryType) -> ResultType:
        """Execute query in transaction.

        Args:
            query: Query to execute

        Returns:
            Query results

        Examples:
            ```python
            async with backend.transaction() as tx:
                result = await tx.execute(query)
            ```
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction.

        Examples:
            ```python
            async with backend.transaction() as tx:
                try:
                    await tx.execute(query)
                except:
                    await tx.rollback()
            ```
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction.

        Examples:
            ```python
            async with backend.transaction() as tx:
                await tx.execute(query)
                await tx.commit()
            ```
        """
        pass


class TransactionManager(ABC, Generic[DBType, CollType, QueryType, ResultType]):
    """Abstract transaction manager.

    This class provides interface for managing database transactions.
    It handles transaction lifecycle and resource management.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)
        CollType: Collection type (e.g. AsyncIOMotorCollection)
        QueryType: Query type (e.g. MongoQuery)
        ResultType: Result type (e.g. Dict[str, Any])

    Examples:
        ```python
        async with TransactionManager(pool) as tx:
            await tx.execute(query)
            await tx.commit()
        ```
    """

    def __init__(self, pool: PoolProtocol[DBType, CollType]) -> None:
        """Initialize transaction manager.

        Args:
            pool: Connection pool
        """
        self._pool = pool
        self._conn: Optional[ConnectionProtocol[DBType, CollType]] = None
        self._transaction: Optional[
            Transaction[DBType, CollType, QueryType, ResultType]
        ] = None

    @property
    def connection(self) -> Optional[ConnectionProtocol[DBType, CollType]]:
        """Get current connection.

        Returns:
            Database connection or None if not connected
        """
        return self._conn

    @property
    def transaction(
        self,
    ) -> Optional[Transaction[DBType, CollType, QueryType, ResultType]]:
        """Get current transaction.

        Returns:
            Transaction instance or None if not started
        """
        return self._transaction

    @abstractmethod
    async def _create_transaction(
        self, conn: ConnectionProtocol[DBType, CollType]
    ) -> Transaction[DBType, CollType, QueryType, ResultType]:
        """Create new transaction.

        Args:
            conn: Database connection

        Returns:
            New transaction instance
        """
        pass

    async def begin(self) -> Transaction[DBType, CollType, QueryType, ResultType]:
        """Begin new transaction.

        Returns:
            New transaction

        Raises:
            ValueError: If no connection available

        Examples:
            ```python
            tx = await manager.begin()
            ```
        """
        if not self._conn:
            conn = await self._pool.acquire()
            self._conn = cast(ConnectionProtocol[DBType, CollType], conn)

        if not self._conn:
            raise ValueError("No connection available")

        self._transaction = await self._create_transaction(self._conn)
        return self._transaction

    async def __aenter__(self) -> Transaction[DBType, CollType, QueryType, ResultType]:
        """Enter transaction context.

        Returns:
            Transaction context

        Examples:
            ```python
            async with TransactionManager(pool) as tx:
                await tx.execute(query)
            ```
        """
        return await self.begin()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit transaction context.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred

        Examples:
            ```python
            async with TransactionManager(pool) as tx:
                await tx.execute(query)
            # Transaction is automatically committed or rolled back
            ```
        """
        try:
            if self._transaction:
                if exc_type:
                    # Error occurred, rollback
                    await self._transaction.rollback()
                else:
                    # No error, commit
                    await self._transaction.commit()
                self._transaction = None

            if self._conn:
                await self._pool.release(self._conn)
                self._conn = None
        except Exception:  # Ignore cleanup errors
            pass
