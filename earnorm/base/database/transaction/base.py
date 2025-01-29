"""Base transaction implementation."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    AsyncContextManager,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

if TYPE_CHECKING:
    from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound="DatabaseModel")


class TransactionError(Exception):
    """Base class for transaction errors."""

    pass


class Transaction(ABC, Generic[ModelT]):
    """Base class for database transactions.

    This class defines the interface that all database transactions must implement.
    It provides methods for inserting, updating, and deleting models.
    """

    @abstractmethod
    async def __aenter__(self) -> "Transaction[ModelT]":
        """Enter transaction context.

        Returns:
            Transaction instance
        """
        pass

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit transaction context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        pass

    @abstractmethod
    async def insert(self, model: ModelT) -> ModelT:
        """Insert model into database.

        Args:
            model: Model to insert

        Returns:
            Inserted model with ID
        """
        pass

    @abstractmethod
    async def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs
        """
        pass

    @abstractmethod
    async def update(self, model: ModelT) -> ModelT:
        """Update model in database.

        Args:
            model: Model to update

        Returns:
            Updated model

        Raises:
            ValueError: If model has no ID
        """
        pass

    @abstractmethod
    async def update_many(self, models: List[ModelT]) -> List[ModelT]:
        """Update multiple models in database.

        Args:
            models: Models to update

        Returns:
            Updated models

        Raises:
            ValueError: If any model has no ID
        """
        pass

    @abstractmethod
    async def delete(self, model: ModelT) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            ValueError: If model has no ID
        """
        pass

    @abstractmethod
    async def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction.

        Raises:
            TransactionError: If transaction cannot be committed
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction.

        Raises:
            TransactionError: If transaction cannot be rolled back
        """
        pass


class TransactionManager(AsyncContextManager[Transaction[ModelT]]):
    """Context manager for database transactions.

    This class provides a context manager interface for managing transactions.
    It ensures that transactions are properly committed or rolled back.

    Examples:
        >>> with adapter.transaction() as tx:
        ...     user = User(name="John", age=25)
        ...     tx.insert(user)
        ...     tx.update(user)
        ...     tx.delete(user)
        ...     tx.commit()
    """

    def __init__(self) -> None:
        """Initialize transaction manager."""
        self._transaction: Optional[Transaction[ModelT]] = None

    async def __aenter__(self) -> Transaction[ModelT]:
        """Enter transaction context.

        Returns:
            Transaction instance
        """
        self._transaction = await self._begin_transaction()
        return self._transaction

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit transaction context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_type is not None:
            if self._transaction is not None:
                await self._transaction.rollback()
        else:
            if self._transaction is not None:
                await self._transaction.commit()

    @abstractmethod
    def set_model_type(self, model_type: Type[ModelT]) -> None:
        """Set model type for transaction.

        This method must be called before starting a transaction.
        It sets the type of model that will be used in the transaction.

        Args:
            model_type: Type of model to use in transaction
        """
        pass

    @abstractmethod
    async def _begin_transaction(self) -> Transaction[ModelT]:
        """Begin new transaction.

        Returns:
            Transaction instance

        Raises:
            TransactionError: If transaction cannot be started
            ValueError: If model type is not set
        """
        raise NotImplementedError
