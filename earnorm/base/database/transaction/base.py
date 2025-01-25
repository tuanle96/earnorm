"""Base transaction interface.

This module provides the base interface for database transactions.

Examples:
    >>> with adapter.transaction() as tx:
    ...     user = User(name="John", age=25)
    ...     tx.insert(user)
    ...     tx.update(user)
    ...     tx.delete(user)
    ...     tx.commit()
"""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Generic, List, Optional, Type, TypeVar

from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class TransactionError(Exception):
    """Base class for transaction errors."""

    pass


class Transaction(ABC, Generic[ModelT]):
    """Base class for database transactions.

    This class defines the interface that all database transactions must implement.
    It provides methods for inserting, updating, and deleting models.
    """

    @abstractmethod
    def __enter__(self) -> "Transaction[ModelT]":
        """Enter transaction context.

        Returns:
            Transaction instance
        """
        pass

    @abstractmethod
    def __exit__(
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
    def insert(self, model: ModelT) -> ModelT:
        """Insert model into database.

        Args:
            model: Model to insert

        Returns:
            Inserted model with ID
        """
        pass

    @abstractmethod
    def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs
        """
        pass

    @abstractmethod
    def update(self, model: ModelT) -> ModelT:
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
    def update_many(self, models: List[ModelT]) -> List[ModelT]:
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
    def delete(self, model: ModelT) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            ValueError: If model has no ID
        """
        pass

    @abstractmethod
    def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
        """
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction.

        Raises:
            TransactionError: If transaction cannot be committed
        """
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction.

        Raises:
            TransactionError: If transaction cannot be rolled back
        """
        pass


class TransactionManager(AbstractContextManager[Transaction[ModelT]]):
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

    def __enter__(self) -> Transaction[ModelT]:
        """Enter transaction context.

        Returns:
            Transaction instance
        """
        self._transaction = self._begin_transaction()
        return self._transaction

    def __exit__(
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
                self._transaction.rollback()
        else:
            if self._transaction is not None:
                self._transaction.commit()

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
    def _begin_transaction(self) -> Transaction[ModelT]:
        """Begin new transaction.

        Returns:
            Transaction instance

        Raises:
            TransactionError: If transaction cannot be started
            ValueError: If model type is not set
        """
        raise NotImplementedError
