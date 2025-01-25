"""Asynchronous database adapter interface.

This module provides the base adapter interface for asynchronous database operations.
It provides methods for querying, inserting, updating, and deleting data asynchronously.

Examples:
    >>> adapter = AsyncMongoAdapter(client)
    >>> users = await adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> async with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, Type, TypeVar

from earnorm.base.database.query.base.query import Query
from earnorm.base.database.transaction.base import TransactionManager
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class AsyncDatabaseAdapter(Generic[ModelT], ABC):
    """Base class for all asynchronous database adapters.

    This class defines the interface that all database-specific adapters must implement.
    It provides methods for querying, inserting, updating, and deleting data asynchronously.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize adapter."""
        self._connection: Optional[Any] = None

    @abstractmethod
    async def init(self) -> None:
        """Initialize adapter.

        This method should be called before using the adapter.
        It should initialize any resources needed by the adapter.

        Raises:
            ConnectionError: If initialization fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close adapter.

        This method should be called when the adapter is no longer needed.
        It should clean up any resources used by the adapter.
        """
        pass

    @abstractmethod
    def get_connection(self) -> Any:
        """Get database connection.

        Returns:
            Database connection
        """
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to database.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from database."""
        pass

    @abstractmethod
    async def query(self, model_type: Type[ModelT]) -> Query[ModelT]:
        """Create query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Query builder
        """
        pass

    @abstractmethod
    async def transaction(self, model_type: Type[ModelT]) -> TransactionManager[ModelT]:
        """Create new transaction.

        Args:
            model_type: Type of model to use in transaction

        Returns:
            Transaction context manager
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
