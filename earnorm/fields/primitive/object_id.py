"""ObjectId field type."""

from typing import Any, Optional, Type

from bson import ObjectId

from earnorm.fields.base import Field


class ObjectIdField(Field[ObjectId]):
    """ObjectId field."""

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return ObjectId

    def convert(self, value: Any) -> ObjectId:
        """Convert value to ObjectId."""
        if value is None or value == "":
            return ObjectId()  # Generate new ObjectId instead of returning None
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    def to_dict(self, value: Optional[ObjectId]) -> Optional[str]:
        """Convert ObjectId to string."""
        if value is None:
            return None
        return str(value)

    def to_mongo(self, value: Optional[ObjectId]) -> Optional[ObjectId]:
        """Convert Python ObjectId to MongoDB ObjectId."""
        if value is None:
            return None
        if type(value) is ObjectId:  # type: ignore
            return value
        return ObjectId(str(value))

    def from_mongo(self, value: Any) -> ObjectId:
        """Convert MongoDB ObjectId to Python ObjectId."""
        if value is None:
            return ObjectId()  # Return new ObjectId instead of None
        if type(value) is ObjectId:  # type: ignore
            return value
        return ObjectId(str(value))
