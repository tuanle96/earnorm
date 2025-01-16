"""Boolean field type."""

from typing import Any, Optional, Type

from earnorm.fields.base import Field


class BooleanField(Field[bool]):
    """Boolean field."""

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return bool

    def convert(self, value: Any) -> bool:
        """Convert value to boolean."""
        if value is None:
            return False
        return bool(value)

    def to_mongo(self, value: Optional[bool]) -> bool:
        """Convert Python boolean to MongoDB boolean."""
        if value is None:
            return False
        return bool(value)

    def from_mongo(self, value: Any) -> bool:
        """Convert MongoDB boolean to Python boolean."""
        if value is None:
            return False
        return bool(value)
