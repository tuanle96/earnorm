"""Field reference interface.

This module defines interfaces for type-safe field references.
Field references are used to build type-safe query conditions.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> # Using field references
    >>> User.name == "John"  # Returns a condition
    >>> User.age > 18  # Returns a condition
    >>> User.name.desc()  # Returns a sort specification
"""

from typing import Any, Generic, TypeVar

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)
T = TypeVar("T")


class Field(Generic[ModelT, T]):
    """Field reference.

    This class represents a reference to a model field.
    It provides methods for building type-safe conditions.

    Args:
        model_type: Type of model containing the field
        name: Field name
    """

    def __init__(self, model_type: type[ModelT], name: str) -> None:
        """Initialize field reference.

        Args:
            model_type: Type of model containing the field
            name: Field name
        """
        self.model_type = model_type
        self.name = name

    def __eq__(self, other: Any) -> bool:
        """Equal condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": "=", "value": other})

    def __ne__(self, other: Any) -> bool:
        """Not equal condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": "!=", "value": other})

    def __gt__(self, other: Any) -> bool:
        """Greater than condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": ">", "value": other})

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": ">=", "value": other})

    def __lt__(self, other: Any) -> bool:
        """Less than condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": "<", "value": other})

    def __le__(self, other: Any) -> bool:
        """Less than or equal condition.

        Args:
            other: Value to compare against

        Returns:
            Query condition
        """
        return bool({"field": self.name, "operator": "<=", "value": other})

    def in_(self, values: list[Any]) -> JsonDict:
        """In condition.

        Args:
            values: List of values to compare against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "in", "value": values}

    def not_in(self, values: list[Any]) -> JsonDict:
        """Not in condition.

        Args:
            values: List of values to compare against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "not in", "value": values}

    def like(self, pattern: str) -> JsonDict:
        """Like condition.

        Args:
            pattern: Pattern to match against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "like", "value": pattern}

    def ilike(self, pattern: str) -> JsonDict:
        """Case-insensitive like condition.

        Args:
            pattern: Pattern to match against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "ilike", "value": pattern}

    def not_like(self, pattern: str) -> JsonDict:
        """Not like condition.

        Args:
            pattern: Pattern to match against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "not like", "value": pattern}

    def not_ilike(self, pattern: str) -> JsonDict:
        """Case-insensitive not like condition.

        Args:
            pattern: Pattern to match against

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "not ilike", "value": pattern}

    def is_null(self) -> JsonDict:
        """Is null condition.

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "is null", "value": None}

    def is_not_null(self) -> JsonDict:
        """Is not null condition.

        Returns:
            Query condition
        """
        return {"field": self.name, "operator": "is not null", "value": None}

    def asc(self) -> str:
        """Ascending sort specification.

        Returns:
            Sort specification
        """
        return f"{self.name} ASC"

    def desc(self) -> str:
        """Descending sort specification.

        Returns:
            Sort specification
        """
        return f"{self.name} DESC"
