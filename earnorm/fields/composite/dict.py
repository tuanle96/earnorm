"""Dict field type."""

from typing import Any, Dict, Optional, Type

from earnorm.fields.base import Field


class DictField(Field[Dict[str, Any]]):
    """Dict field."""

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return dict

    def convert(self, value: Any) -> Dict[str, Any]:
        """Convert value to dict."""
        if value is None:
            return {}
        return dict(value)

    def to_mongo(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Python dict to MongoDB document."""
        if value is None:
            return {}
        return dict(value)

    def from_mongo(self, value: Any) -> Dict[str, Any]:
        """Convert MongoDB document to Python dict."""
        if value is None:
            return {}
        return dict(value)
