"""Core query implementation.

This module provides base implementation for database queries.
All database-specific query implementations should inherit from this class.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> query = BaseQuery[User]()
    >>> query.where(User.age > 18).order_by(User.name)
    >>> query.join(Post).on(User.id == Post.user_id)
    >>> query.group_by(User.age).having(User.age > 20)
    >>> query.window().over(partition_by=[User.age]).row_number()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from earnorm.base.database.query.interfaces.domain import DomainExpression, DomainItem
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.base.database.query.interfaces.query import QueryProtocol
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class BaseQuery(Generic[ModelT], QueryProtocol[ModelT], ABC):
    """Base class for database queries.

    This class provides common functionality for all database queries.
    Database-specific query implementations should inherit from this class.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self, model: Type[ModelT]) -> None:
        """Initialize query.

        Args:
            model: Model class being queried
        """
        self._model = model
        self._domain: Optional[Union[List[DomainItem], DomainExpression]] = None
        self._fields: Optional[List[str]] = None
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None
        self._order_by: List[str] = []
        self._joins: List[JoinProtocol[ModelT, Any]] = []
        self._aggregates: List[AggregateProtocol[ModelT]] = []
        self._windows: List[WindowProtocol[ModelT]] = []

    def select(self, *fields: str) -> "BaseQuery[ModelT]":
        """Select fields to return.

        Args:
            fields: Fields to select

        Returns:
            Self for chaining
        """
        self._fields = list(fields)
        return self

    def where(
        self, domain: Union[List[DomainItem], DomainExpression]
    ) -> "BaseQuery[ModelT]":
        """Add where conditions.

        Args:
            domain: Where conditions in domain expression format

        Returns:
            Self for chaining
        """
        self._domain = domain
        return self

    def offset(self, offset: int) -> "BaseQuery[ModelT]":
        """Set offset.

        Args:
            offset: Number of records to skip

        Returns:
            Self for chaining
        """
        self._offset = offset
        return self

    def limit(self, limit: int) -> "BaseQuery[ModelT]":
        """Set limit.

        Args:
            limit: Maximum number of records to return

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def order_by(self, *fields: str) -> "BaseQuery[ModelT]":
        """Set order by fields.

        Args:
            fields: Fields to order by

        Returns:
            Self for chaining
        """
        self._order_by.extend(fields)
        return self

    @abstractmethod
    def join(
        self,
        model: Union[str, Type[JoinT]],
        on: Optional[Dict[str, Any]] = None,
        join_type: str = "inner",
    ) -> JoinProtocol[ModelT, JoinT]:
        """Create join operation.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Join operation
        """
        ...

    @abstractmethod
    def aggregate(self) -> AggregateProtocol[ModelT]:
        """Create aggregate operation.

        Returns:
            Aggregate operation
        """
        ...

    @abstractmethod
    def window(self) -> WindowProtocol[ModelT]:
        """Create window operation.

        Returns:
            Window operation
        """
        ...

    def validate(self) -> None:
        """Validate query configuration.

        Raises:
            ValueError: If query configuration is invalid
        """
        for join in self._joins:
            join.validate()
        for aggregate in self._aggregates:
            aggregate.validate()
        for window in self._windows:
            window.validate()

    @property
    def model(self) -> Type[ModelT]:
        """Get model class.

        Returns:
            Model class
        """
        return self._model

    @property
    def domain(self) -> Optional[Union[List[DomainItem], DomainExpression]]:
        """Get where conditions.

        Returns:
            Where conditions
        """
        return self._domain

    @property
    def fields(self) -> Optional[List[str]]:
        """Get selected fields.

        Returns:
            Selected fields
        """
        return self._fields

    @property
    def offset_value(self) -> Optional[int]:
        """Get offset.

        Returns:
            Offset value
        """
        return self._offset

    @property
    def limit_value(self) -> Optional[int]:
        """Get limit.

        Returns:
            Limit value
        """
        return self._limit

    @property
    def order_by_fields(self) -> List[str]:
        """Get order by fields.

        Returns:
            Order by fields
        """
        return self._order_by

    @property
    def joins(self) -> List[JoinProtocol[ModelT, Any]]:
        """Get join operations.

        Returns:
            List of join operations
        """
        return self._joins

    @property
    def aggregates(self) -> List[AggregateProtocol[ModelT]]:
        """Get aggregate operations.

        Returns:
            List of aggregate operations
        """
        return self._aggregates

    @property
    def windows(self) -> List[WindowProtocol[ModelT]]:
        """Get window operations.

        Returns:
            List of window operations
        """
        return self._windows
