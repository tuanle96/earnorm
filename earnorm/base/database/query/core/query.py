"""Core query implementation.

This module provides the core query building functionality for EarnORM.
It implements the base query class that all other query types inherit from.

The query builder uses a fluent interface pattern to construct database queries
in a type-safe and intuitive way. It supports:

- Filtering with comparison operators
- Field selection and projection
- Sorting and ordering
- Pagination with limit/offset
- Result caching
- Type hints and validation
- Custom result processors

Examples:
    >>> from earnorm.base.database.query import Query
    >>> from earnorm.types import DatabaseModel

    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...     status: str

    >>> # Basic filtering
    >>> users = await Query(User).filter(
    ...     age__gt=18,
    ...     status="active"
    ... ).all()

    >>> # Field selection
    >>> users = await Query(User).select(
    ...     "name", "age"
    ... ).all()

    >>> # Sorting
    >>> users = await Query(User).order_by(
    ...     "-age", "name"
    ... ).all()

    >>> # Pagination
    >>> users = await Query(User).limit(10).offset(20).all()

    >>> # Complex filtering with domain builder
    >>> from earnorm.base.database.query import DomainBuilder
    >>> users = await Query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .or_()
    ...     .field("role").in_(["admin", "moderator"])
    ...     .build()
    ... ).all()

    >>> # Custom result processor
    >>> def process_user(user):
    ...     user["full_name"] = f"{user['first_name']} {user['last_name']}"
    ...     return user
    ...
    >>> users = await Query(User).add_processor(process_user).all()
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
    """Base query builder implementation.

    This class provides the core functionality for building and executing database queries.
    It implements common query operations like filtering, sorting, and pagination.

    The query builder uses method chaining to construct queries in a fluent interface style.
    Each method returns self to allow for method chaining.

    Args:
        model_type: The model class to query

    Attributes:
        _model_type: The model class being queried
        _filters: List of filter conditions
        _order_by: List of sort fields
        _limit: Maximum number of results
        _offset: Number of results to skip
        _selected_fields: List of fields to return
        _processors: List of result processor functions

    Examples:
        >>> # Create query builder
        >>> query = BaseQuery(User)

        >>> # Add filters
        >>> query.filter(age__gt=18, status="active")

        >>> # Add sorting
        >>> query.order_by("-created_at", "name")

        >>> # Set pagination
        >>> query.limit(10).offset(20)

        >>> # Select fields
        >>> query.select("id", "name", "email")

        >>> # Execute query
        >>> results = await query.all()
    """

    def __init__(self, model_type: Type[ModelT]) -> None:
        """Initialize query builder.

        Args:
            model_type: The model class to query
        """
        self._model = model_type
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

    @abstractmethod
    async def to_raw_data(self) -> List[Dict[str, Any]]:
        """Get raw data from query result.

        This method executes the query and returns raw data instead of model instances.
        Useful when you only need the raw data without model instantiation.

        Returns:
            List[Dict[str, Any]]: List of raw data dictionaries

        Example:
            >>> query = User.search([("age", ">", 18)])
            >>> raw_data = await query.to_raw_data()
            >>> print(raw_data)
            [{"_id": "...", "name": "John", "age": 25}, ...]
        """
        pass

    @abstractmethod
    async def execute(self) -> List[ModelT]:
        """Execute query and return model instances.

        This method executes the query and returns model instances.

        Returns:
            List[ModelT]: List of model instances

        Example:
            >>> query = User.search([("age", ">", 18)])
            >>> users = await query.execute()
            >>> print(users[0].name)
            "John"
        """
        pass

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

    def reset(self) -> "BaseQuery[ModelT]":
        """Reset query."""
        self._domain = None
        self._fields = None
        self._offset = None
        self._limit = None
        self._order_by = []
        self._joins = []
        self._aggregates = []
        self._windows = []
        return self
