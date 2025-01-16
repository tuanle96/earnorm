"""Domain builder implementation."""

from typing import Any, List, Optional, Union

from earnorm.base.domain.operators import DomainOperator


class DomainBuilder:
    """Domain builder for constructing domain expressions.

    This class provides a fluent interface for building domain expressions:
    - Combining multiple conditions
    - Applying operators
    - Building complex queries

    Examples:
        >>> builder = DomainBuilder()
        >>> domain = (
        ...     builder
        ...     .field("age").greater_than(18)
        ...     .and_()
        ...     .field("active").equals(True)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize domain builder."""
        self._domain: List[Any] = []
        self._current_field: Optional[str] = None

    def field(self, name: str) -> "DomainBuilder":
        """Set current field.

        Args:
            name: Field name

        Returns:
            Self for chaining
        """
        self._current_field = name
        return self

    def equals(self, value: Any) -> "DomainBuilder":
        """Add equals condition.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, "=", value])
        self._current_field = None
        return self

    def not_equals(self, value: Any) -> "DomainBuilder":
        """Add not equals condition.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, "!=", value])
        self._current_field = None
        return self

    def greater_than(self, value: Union[int, float]) -> "DomainBuilder":
        """Add greater than condition.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, ">", value])
        self._current_field = None
        return self

    def less_than(self, value: Union[int, float]) -> "DomainBuilder":
        """Add less than condition.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, "<", value])
        self._current_field = None
        return self

    def in_(self, values: List[Any]) -> "DomainBuilder":
        """Add in condition.

        Args:
            values: List of values

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, "in", values])
        self._current_field = None
        return self

    def not_in(self, values: List[Any]) -> "DomainBuilder":
        """Add not in condition.

        Args:
            values: List of values

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is set
        """
        if not self._current_field:
            raise ValueError("No field set")

        self._domain.append([self._current_field, "not in", values])
        self._current_field = None
        return self

    def and_(self) -> "DomainBuilder":
        """Add AND operator.

        Returns:
            Self for chaining
        """
        self._domain.append(DomainOperator.AND)
        return self

    def or_(self) -> "DomainBuilder":
        """Add OR operator.

        Returns:
            Self for chaining
        """
        self._domain.append(DomainOperator.OR)
        return self

    def not_(self) -> "DomainBuilder":
        """Add NOT operator.

        Returns:
            Self for chaining
        """
        self._domain.append(DomainOperator.NOT)
        return self

    def build(self) -> List[Any]:
        """Build domain expression.

        Returns:
            Domain expression
        """
        return self._domain
