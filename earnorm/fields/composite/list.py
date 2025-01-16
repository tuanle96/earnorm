"""List field type."""

from typing import Any, Generic, List, Optional, Type, TypeVar

from earnorm.fields.base import Field

T = TypeVar("T")


class ListField(Field[List[T]], Generic[T]):
    """List field."""

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        default: Any = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
        )
        self.field = field

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return list

    def convert(self, value: Any) -> List[T]:
        """Convert value to list."""
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.convert(item)
            result.append(converted)
        return result

    def to_dict(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert list to dict representation."""
        if value is None:
            return None
        return [self.field.to_dict(item) for item in value]

    def to_mongo(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert Python list to MongoDB array."""
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]

    def from_mongo(self, value: Any) -> List[T]:
        """Convert MongoDB array to Python list."""
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.from_mongo(item)
            result.append(converted)
        return result
