"""Base query interface.

This module provides the base Query class and QueryBuilder for all database-specific
implementations. It integrates with domain expressions for query building.

Examples:
    >>> # Using Query directly
    >>> query = MongoQuery[User](collection)
    >>> query.filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
    >>> query.sort("name", ascending=True)
    >>> query.limit(10)
    >>> query.offset(20)
    >>> results = query.execute()

    >>> # Using QueryBuilder
    >>> builder = QueryBuilder[User](collection)
    >>> results = (
    ...     builder
    ...     .where("age").greater_than(18)
    ...     .and_()
    ...     .where("status").equals("active")
    ...     .sort("name")
    ...     .limit(10)
    ...     .offset(20)
    ...     .all()
    ... )
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar

from earnorm.base.domain.expression import DomainExpression, Operator
from earnorm.types import DatabaseModel, JsonDict, ValueType

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class Query(Generic[ModelT], ABC):
    """Base class for all database queries.

    This class defines the interface that all database-specific queries must implement.
    It provides methods for filtering, sorting, limiting, and executing queries.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize query."""
        self._domain: Optional[DomainExpression[ValueType]] = None
        self._sort_fields: List[tuple[str, bool]] = []  # (field, ascending)
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def filter(self, domain: DomainExpression[ValueType]) -> "Query[ModelT]":
        """Add domain expression filter.

        Args:
            domain: Domain expression to filter by

        Returns:
            Self for chaining

        Raises:
            ValueError: If domain expression is invalid
        """
        domain.validate()
        self._domain = domain
        return self

    def sort(self, field: str, ascending: bool = True) -> "Query[ModelT]":
        """Add sort field.

        Args:
            field: Field to sort by
            ascending: Sort direction

        Returns:
            Self for chaining

        Raises:
            ValueError: If field name is empty
        """
        if not field:
            raise ValueError("Sort field name cannot be empty")
        self._sort_fields.append((field, ascending))
        return self

    def limit(self, limit: int) -> "Query[ModelT]":
        """Set result limit.

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining

        Raises:
            ValueError: If limit is negative
        """
        if limit < 0:
            raise ValueError("Limit cannot be negative")
        self._limit = limit
        return self

    def offset(self, offset: int) -> "Query[ModelT]":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining

        Raises:
            ValueError: If offset is negative
        """
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        self._offset = offset
        return self

    @abstractmethod
    def to_filter(self) -> JsonDict:
        """Convert domain expression to database filter.

        Returns:
            Database-specific filter format
        """
        pass

    @abstractmethod
    def to_sort(self) -> Any:
        """Convert sort fields to database sort.

        Returns:
            Database-specific sort format
        """
        pass

    @abstractmethod
    def execute(self) -> List[ModelT]:
        """Execute query and return results.

        Returns:
            Query results
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Count results without fetching them.

        Returns:
            Number of results
        """
        pass

    @abstractmethod
    def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        pass

    @abstractmethod
    def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        pass


class AsyncQuery(Query[ModelT], ABC):
    """Base class for all async database queries.

    This class defines the interface that all async database-specific queries must implement.
    It provides methods for filtering, sorting, limiting, and executing queries asynchronously.

    Args:
        ModelT: Type of model being queried
    """

    def execute(self) -> List[ModelT]:
        """Execute query and return results.

        Returns:
            Query results
        """
        raise NotImplementedError("Use execute_async() instead")

    def count(self) -> int:
        """Count results without fetching them.

        Returns:
            Number of results
        """
        raise NotImplementedError("Use count_async() instead")

    def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        raise NotImplementedError("Use exists_async() instead")

    def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        raise NotImplementedError("Use first_async() instead")

    @abstractmethod
    async def execute_async(self) -> List[ModelT]:
        """Execute query and return results asynchronously.

        Returns:
            Query results
        """
        pass

    @abstractmethod
    async def count_async(self) -> int:
        """Count results without fetching them asynchronously.

        Returns:
            Number of results
        """
        pass

    @abstractmethod
    async def exists_async(self) -> bool:
        """Check if any results exist asynchronously.

        Returns:
            True if results exist
        """
        pass

    @abstractmethod
    async def first_async(self) -> Optional[ModelT]:
        """Get first result or None asynchronously.

        Returns:
            First result or None
        """
        pass


class QueryBuilder(Generic[ModelT]):
    """Builder for database queries.

    This class provides a fluent interface for building and executing queries.
    It integrates with domain expressions and database-specific query implementations.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self, query: Query[ModelT]) -> None:
        """Initialize builder.

        Args:
            query: Database-specific query implementation
        """
        self._query = query
        self._current_field: Optional[str] = None

    def where(self, field: str) -> "QueryBuilder[ModelT]":
        """Start building field expression.

        Args:
            field: Field name

        Returns:
            Self for chaining

        Raises:
            ValueError: If field name is empty
        """
        if not field:
            raise ValueError("Field name cannot be empty")
        self._current_field = field
        return self

    def _create_expression(
        self, operator: Operator, value: Any
    ) -> DomainExpression[ValueType]:
        """Create domain expression from current field and value.

        Args:
            operator: Comparison operator
            value: Value to compare

        Returns:
            Domain expression

        Raises:
            ValueError: If no field is selected
        """
        if not self._current_field:
            raise ValueError("No field selected")
        return DomainExpression([(self._current_field, operator, value)])

    def equals(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field equals value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("=", value))
        return self

    def not_equals(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field not equals value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("!=", value))
        return self

    def greater_than(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field greater than value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression(">", value))
        return self

    def greater_than_or_equal(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field greater than or equal to value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression(">=", value))
        return self

    def less_than(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field less than value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("<", value))
        return self

    def less_than_or_equal(self, value: ValueType) -> "QueryBuilder[ModelT]":
        """Field less than or equal to value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("<=", value))
        return self

    def in_list(self, values: List[ValueType]) -> "QueryBuilder[ModelT]":
        """Field value in list.

        Args:
            values: List of values to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("in", values))
        return self

    def not_in_list(self, values: List[ValueType]) -> "QueryBuilder[ModelT]":
        """Field value not in list.

        Args:
            values: List of values to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._query.filter(self._create_expression("not in", values))
        return self

    def sort(self, field: str, ascending: bool = True) -> "QueryBuilder[ModelT]":
        """Add sort field.

        Args:
            field: Field to sort by
            ascending: Sort direction

        Returns:
            Self for chaining
        """
        self._query.sort(field, ascending)
        return self

    def limit(self, limit: int) -> "QueryBuilder[ModelT]":
        """Set result limit.

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining
        """
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "QueryBuilder[ModelT]":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self._query.offset(offset)
        return self

    def all(self) -> List[ModelT]:
        """Execute query and return all results.

        Returns:
            Query results
        """
        return self._query.execute()

    def count(self) -> int:
        """Count results without fetching them.

        Returns:
            Number of results
        """
        return self._query.count()

    def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        return self._query.exists()

    def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        return self._query.first()
