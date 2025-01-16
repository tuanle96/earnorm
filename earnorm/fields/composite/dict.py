"""Dict field type."""

from typing import Any, Dict, Optional, Type

from earnorm.fields.base import Field


class DictField(Field[Dict[str, Any]]):
    """Dict field for storing key-value pairs.

    This field type stores dictionaries with string keys and arbitrary values.
    It provides validation and conversion between Python dicts and MongoDB documents.

    Examples:
        >>> # Simple dict field
        >>> data = DictField()
        >>> data.convert({"name": "John", "age": 30})
        {'name': 'John', 'age': 30}
        >>>
        >>> # Dict with validation
        >>> data = DictField(required=True)
        >>> data.convert(None)  # Raises ValidationError
        >>>
        >>> # Dict with default value
        >>> data = DictField(default={"status": "active"})
        >>> data.convert(None)
        {'status': 'active'}
    """

    def _get_field_type(self) -> Type[Any]:
        """Get field type.

        Returns:
            The dict type

        Examples:
            >>> field = DictField()
            >>> field._get_field_type()
            <class 'dict'>
        """
        return dict

    def convert(self, value: Any) -> Dict[str, Any]:
        """Convert value to dict.

        Args:
            value: Value to convert

        Returns:
            Converted dictionary

        Raises:
            ValueError: If value cannot be converted to dict

        Examples:
            >>> field = DictField()
            >>> field.convert({"name": "John"})
            {'name': 'John'}
            >>> field.convert(None)
            {}
            >>> field.convert([("name", "John")])
            {'name': 'John'}
        """
        if value is None:
            return {}
        try:
            return dict(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot convert {type(value)} to dict: {e}")

    def to_mongo(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Python dict to MongoDB document.

        Args:
            value: Dict to convert

        Returns:
            MongoDB document

        Examples:
            >>> field = DictField()
            >>> field.to_mongo({"name": "John", "age": 30})
            {'name': 'John', 'age': 30}
            >>> field.to_mongo(None)
            {}
        """
        if value is None:
            return {}
        try:
            return dict(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot convert {type(value)} to dict: {e}")

    def from_mongo(self, value: Any) -> Dict[str, Any]:
        """Convert MongoDB document to Python dict.

        Args:
            value: MongoDB document to convert

        Returns:
            Python dictionary

        Raises:
            ValueError: If value cannot be converted to dict

        Examples:
            >>> field = DictField()
            >>> field.from_mongo({"name": "John", "age": 30})
            {'name': 'John', 'age': 30}
            >>> field.from_mongo(None)
            {}
        """
        if value is None:
            return {}
        try:
            return dict(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot convert {type(value)} to dict: {e}")

    def validate(self, value: Any) -> None:
        """Validate dict value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails

        Examples:
            >>> field = DictField(required=True)
            >>> field.validate({"name": "John"})  # OK
            >>> field.validate(None)  # Raises ValidationError
        """
        super().validate(value)
        if value is not None:
            try:
                dict(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid dictionary value: {e}")
