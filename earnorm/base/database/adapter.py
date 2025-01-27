"""Database adapter interface.

This module provides the base adapter interface for database operations.
It provides methods for querying, inserting, updating, and deleting data asynchronously.

Examples:
    >>> adapter = MongoAdapter(client)
    >>> # Basic query
    >>> users = await adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> # Join query
    >>> users = await adapter.query(User).join(Post).on(User.id == Post.user_id)
    >>> # Aggregate query
    >>> stats = await adapter.query(User).aggregate().group_by(User.age).count()
    >>> # Window query
    >>> ranked = await adapter.query(User).window().over(partition_by=[User.age]).row_number()
    >>> # Transaction
    >>> async with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar

from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol as AggregateQuery,
)
from earnorm.base.database.query.interfaces.operations.join import (
    JoinProtocol as JoinQuery,
)
from earnorm.base.database.transaction.base import TransactionManager
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class DatabaseAdapter(Generic[ModelT], ABC):
    """Base class for all database adapters.

    This class defines the interface that all database-specific adapters must implement.
    It provides methods for querying, inserting, updating, and deleting data asynchronously.

    Args:
        ModelT: Type of model being queried
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize the adapter.

        This method should be called before using the adapter.
        It should initialize any resources needed by the adapter.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the adapter.

        This method should be called when the adapter is no longer needed.
        It should clean up any resources used by the adapter.
        """
        pass

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get a connection from the adapter.

        Returns:
            Any: A connection object that can be used to interact with the database.
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
    async def query(self, model_type: Type[ModelT]) -> BaseQuery[ModelT]:
        """Create query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Query builder instance
        """
        pass

    @abstractmethod
    async def get_aggregate_query(
        self, model_type: Type[ModelT]
    ) -> AggregateQuery[ModelT]:
        """Create aggregate query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Aggregate query builder instance
        """
        pass

    @abstractmethod
    async def get_join_query(self, model_type: Type[ModelT]) -> JoinQuery[ModelT, Any]:
        """Create join query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Join query builder instance
        """
        pass

    @abstractmethod
    async def get_group_query(self, model_type: Type[ModelT]) -> AggregateQuery[ModelT]:
        """Create group query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Group query builder instance
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
    async def insert_one(self, table_name: str, values: Dict[str, Any]) -> Any:
        """Insert one document into table.

        Args:
            table_name: Table name
            values: Document values

        Returns:
            Document ID
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

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Get backend type.

        Returns:
            Backend type (e.g. 'mongodb', 'postgresql', etc.)
        """
        pass

    @abstractmethod
    async def update_many_by_filter(
        self, table_name: str, domain_filter: Dict[str, Any], values: Dict[str, Any]
    ) -> int:
        """Update multiple documents in table by filter.

        Args:
            table_name: Table name
            filter: Filter to match documents
            values: Values to update

        Returns:
            Number of documents updated
        """
        pass

    @abstractmethod
    async def delete_many_by_filter(
        self, table_name: str, domain_filter: Dict[str, Any]
    ) -> int:
        """Delete multiple documents in table by filter.

        Args:
            table_name: Table name
            filter: Filter to match documents

        Returns:
            Number of documents deleted
        """
        pass
