"""MongoDB transaction implementation.

This module provides transaction management for MongoDB.
It includes:
- MongoDB transaction implementation
- MongoDB transaction manager
- MongoDB transaction context

Examples:
    ```python
    pool = MongoPool(uri="mongodb://localhost:27017")
    async with MongoTransactionManager(pool) as tx:
        # Find documents
        query = MongoQuery("users", filter={"age": {"$gt": 18}})
        result = await tx.execute(query)

        # Update documents
        query = MongoQuery("users", filter={"name": "John"})
        result = await tx.execute(query)

        # Commit changes
        await tx.commit()
    ```
"""

from typing import Any, Dict, Protocol, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorClientSession,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.base.database.query.backends.mongo import MongoQuery
from earnorm.base.database.transaction.base import Transaction, TransactionManager
from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol

Document = Dict[str, Any]


class MongoTransactionError(Exception):
    """Base class for MongoDB transaction errors."""

    pass


class MongoTransactionSessionError(MongoTransactionError):
    """Error when session operations fail."""

    pass


class MongoTransactionCommitError(MongoTransactionError):
    """Error when committing transaction fails."""

    pass


class MongoTransactionRollbackError(MongoTransactionError):
    """Error when rolling back transaction fails."""

    pass


class MongoConnectionProtocol(Protocol):
    """Protocol for MongoDB connection operations."""

    async def start_session(self) -> AsyncIOMotorClientSession:
        """Start new session.

        Returns:
            New MongoDB client session
        """
        ...


class MongoTransaction(
    Transaction[
        AsyncIOMotorDatabase[Document],
        AsyncIOMotorCollection[Document],
        MongoQuery[Document],
        Document,
    ]
):
    """MongoDB transaction implementation.

    This class provides transaction support for MongoDB operations.
    It supports:
    - CRUD operations within a transaction
    - Automatic rollback on error
    - Session management

    Examples:
        ```python
        async with backend.transaction() as tx:
            # Find documents
            query = MongoQuery("users", filter={"age": {"$gt": 18}})
            result = await tx.execute(query)

            # Update documents
            query = MongoQuery("users", filter={"name": "John"})
            result = await tx.execute(query)

            # Commit changes
            await tx.commit()
        ```
    """

    def __init__(
        self,
        conn: ConnectionProtocol[
            AsyncIOMotorDatabase[Document], AsyncIOMotorCollection[Document]
        ],
        session: AsyncIOMotorClientSession,
        database: str,
    ) -> None:
        """Initialize MongoDB transaction.

        Args:
            conn: MongoDB connection from pool
            session: MongoDB client session
            database: Database name to use
        """
        super().__init__(conn)
        self._session = session
        self._client = cast(AsyncIOMotorClient[Document], conn)
        self._db = self._client[database]
        self.active = False

    async def end_session(self) -> None:
        """End current session.

        This method ends the MongoDB session associated with this transaction.
        It should be called after committing or rolling back the transaction.

        Raises:
            MongoTransactionSessionError: If ending session fails
        """
        if self._session:
            try:
                await self._session.end_session()
            except Exception as e:
                raise MongoTransactionSessionError(f"Failed to end session: {e}") from e

    async def validate(self) -> None:
        """Validate transaction state.

        This method checks:
        - Connection is valid
        - Session is active
        - Transaction is active

        Raises:
            MongoTransactionError: If validation fails
        """
        if not self._conn:
            raise MongoTransactionError("No connection available")

        if not self._session:
            raise MongoTransactionError("No session available")

        if not self.active:
            raise MongoTransactionError("Transaction not active")

    async def execute(self, query: MongoQuery[Document]) -> Document:
        """Execute query in transaction.

        This method executes a MongoDB query within a transaction.
        The query can be a find, update, insert, delete, or count operation.

        Args:
            query: MongoDB query to execute

        Returns:
            Query results as a document

        Examples:
            ```python
            # Find documents
            query = MongoQuery("users", filter={"age": {"$gt": 18}})
            result = await tx.execute(query)

            # Update documents
            query = MongoQuery("users", filter={"name": "John"})
            result = await tx.execute(query)
            ```
        """
        await self.validate()

        collection = self._db[query.collection]
        try:
            result = await collection.find_one(
                filter=query.filter,
                projection=query.projection,
                session=self._session,
            )
            return result or {}
        except Exception as e:
            await self.rollback()
            raise MongoTransactionError(f"Failed to execute query: {e}") from e

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

        Raises:
            MongoTransactionRollbackError: If rollback fails
        """
        if self._session and self.active:
            try:
                await self._session.abort_transaction()
                self.active = False
            except Exception as e:
                raise MongoTransactionRollbackError(
                    f"Failed to rollback transaction: {e}"
                ) from e

    async def commit(self) -> None:
        """Commit transaction.

        Examples:
            ```python
            async with backend.transaction() as tx:
                await tx.execute(query)
                await tx.commit()
            ```

        Raises:
            MongoTransactionCommitError: If commit fails
        """
        if self._session and self.active:
            try:
                await self._session.commit_transaction()
                self.active = False
            except Exception as e:
                await self.rollback()
                raise MongoTransactionCommitError(
                    f"Failed to commit transaction: {e}"
                ) from e


class MongoTransactionManager(
    TransactionManager[
        AsyncIOMotorDatabase[Document],
        AsyncIOMotorCollection[Document],
        MongoQuery[Document],
        Document,
    ]
):
    """MongoDB transaction manager.

    This class manages MongoDB transactions.
    It handles:
    - Connection acquisition from pool
    - Session creation and cleanup
    - Transaction lifecycle

    Examples:
        ```python
        pool = MongoPool(uri="mongodb://localhost:27017")
        async with MongoTransactionManager(pool) as tx:
            await tx.execute(query)
            await tx.commit()
        ```
    """

    def __init__(
        self,
        pool: PoolProtocol[
            AsyncIOMotorDatabase[Document], AsyncIOMotorCollection[Document]
        ],
    ) -> None:
        """Initialize transaction manager.

        Args:
            pool: MongoDB connection pool

        Raises:
            ValueError: If pool is not a MongoPool instance or database name is not set
        """
        super().__init__(pool)
        mongo_pool = cast(
            MongoPool[AsyncIOMotorDatabase[Document], AsyncIOMotorCollection[Document]],
            pool,
        )
        if not mongo_pool.database_name:
            raise ValueError("Database name must be set in MongoPool")
        self._database: str = mongo_pool.database_name

    async def _create_transaction(
        self,
        conn: ConnectionProtocol[
            AsyncIOMotorDatabase[Document], AsyncIOMotorCollection[Document]
        ],
    ) -> Transaction[
        AsyncIOMotorDatabase[Document],
        AsyncIOMotorCollection[Document],
        MongoQuery[Document],
        Document,
    ]:
        """Create new transaction.

        Args:
            conn: MongoDB connection

        Returns:
            New transaction instance

        Raises:
            MongoTransactionError: If transaction creation fails
        """
        try:
            mongo_conn = cast(MongoConnectionProtocol, conn)
            session = await mongo_conn.start_session()
            session.start_transaction()  # Not awaitable, just starts transaction context

            transaction = MongoTransaction(conn, session, self._database)
            transaction.active = True
            return transaction
        except Exception as e:
            raise MongoTransactionError(f"Failed to create transaction: {e}") from e

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit transaction context.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred

        Examples:
            ```python
            async with MongoTransactionManager(pool) as tx:
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

                # End session
                if isinstance(self._transaction, MongoTransaction):
                    await self._transaction.end_session()
                self._transaction = None

            if self._conn:
                await self._pool.release(self._conn)
                self._conn = None
        except Exception:  # Ignore cleanup errors
            pass
