"""Data store management for BaseModel.

This module provides classes for managing model data with proper type hints.
It includes:
1. Record data management
2. Changed fields tracking
3. Cache operations
4. Type safety
5. Serialization/deserialization
"""

from typing import Any, Dict, Generic, Protocol, Set, TypeVar

# Type variable for model class
ModelT = TypeVar("ModelT")


class ModelDataProtocol(Protocol):
    """Protocol for model data management."""

    def get_data(self) -> Dict[str, Any]:
        """Get record data."""
        ...

    def set_data(self, value: Dict[str, Any]) -> None:
        """Set record data."""
        ...

    def has_data(self) -> bool:
        """Check if data exists."""
        ...

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get field value."""
        ...

    def set_field(self, field_name: str, value: Any) -> None:
        """Set field value."""
        ...

    def has_field(self, field_name: str) -> bool:
        """Check if field exists."""
        ...

    def get_changed(self) -> Set[str]:
        """Get set of changed fields."""
        ...

    def clear_changed(self) -> None:
        """Clear set of changed fields."""
        ...

    def mark_changed(self, field_name: str) -> None:
        """Mark field as changed."""
        ...

    def is_changed(self, field_name: str) -> bool:
        """Check if field is changed."""
        ...

    def get_cache(self, key: str, default: Any = None) -> Any:
        """Get cached value."""
        ...

    def set_cache(self, key: str, value: Any) -> None:
        """Set cached value."""
        ...

    def clear_cache(self) -> None:
        """Clear all cached values."""
        ...


class ModelDataStore(Generic[ModelT]):
    """Data store for model instances.

    This class manages:
    1. Record data storage and access
    2. Changed fields tracking
    3. Field-level caching
    4. Type safety through generics

    Args:
        model: Model instance to store data for
    """

    __slots__ = ("_model", "_data", "_changed", "_cache")

    def __init__(self, model: ModelT) -> None:
        """Initialize data store.

        Args:
            model: Model instance to store data for
        """
        self._model = model
        self._data: Dict[str, Any] = {}
        self._changed: Set[str] = set()
        self._cache: Dict[str, Any] = {}

    def get_data(self) -> Dict[str, Any]:
        """Get record data.

        Returns:
            Dict[str, Any]: Current record data
        """
        return self._data

    def set_data(self, value: Dict[str, Any]) -> None:
        """Set record data.

        Args:
            value: New record data
        """
        self._data = value.copy()
        self.clear_changed()
        self.clear_cache()

    def has_data(self) -> bool:
        """Check if data exists.

        Returns:
            bool: True if data exists
        """
        return bool(self._data)

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get field value.

        Args:
            field_name: Name of field to get
            default: Default value if field not found

        Returns:
            Any: Field value or default
        """
        return self._data.get(field_name, default)

    def set_field(self, field_name: str, value: Any) -> None:
        """Set field value.

        Args:
            field_name: Name of field to set
            value: New field value
        """
        if field_name not in self._data or self._data[field_name] != value:
            self._data[field_name] = value
            self.mark_changed(field_name)
            if field_name in self._cache:
                del self._cache[field_name]

    def has_field(self, field_name: str) -> bool:
        """Check if field exists.

        Args:
            field_name: Name of field to check

        Returns:
            bool: True if field exists
        """
        return field_name in self._data

    def get_changed(self) -> Set[str]:
        """Get set of changed fields.

        Returns:
            Set[str]: Names of changed fields
        """
        return self._changed.copy()

    def clear_changed(self) -> None:
        """Clear set of changed fields."""
        self._changed.clear()

    def mark_changed(self, field_name: str) -> None:
        """Mark field as changed.

        Args:
            field_name: Name of field to mark
        """
        self._changed.add(field_name)

    def is_changed(self, field_name: str) -> bool:
        """Check if field is changed.

        Args:
            field_name: Name of field to check

        Returns:
            bool: True if field is changed
        """
        return field_name in self._changed

    def get_cache(self, key: str, default: Any = None) -> Any:
        """Get cached value.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Any: Cached value or default
        """
        return self._cache.get(key, default)

    def set_cache(self, key: str, value: Any) -> None:
        """Set cached value.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value

    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class ModelDataManager:
    """Default implementation of ModelDataProtocol."""

    def __init__(self) -> None:
        """Initialize data manager."""
        self._store = ModelDataStore(None)

    def get_data(self) -> Dict[str, Any]:
        """Get record data."""
        return self._store.get_data()

    def set_data(self, value: Dict[str, Any]) -> None:
        """Set record data."""
        self._store.set_data(value)

    def has_data(self) -> bool:
        """Check if data exists."""
        return self._store.has_data()

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get field value."""
        return self._store.get_field(field_name, default)

    def set_field(self, field_name: str, value: Any) -> None:
        """Set field value."""
        self._store.set_field(field_name, value)

    def has_field(self, field_name: str) -> bool:
        """Check if field exists."""
        return self._store.has_field(field_name)

    def get_changed(self) -> Set[str]:
        """Get set of changed fields."""
        return self._store.get_changed()

    def clear_changed(self) -> None:
        """Clear set of changed fields."""
        self._store.clear_changed()

    def mark_changed(self, field_name: str) -> None:
        """Mark field as changed."""
        self._store.mark_changed(field_name)

    def is_changed(self, field_name: str) -> bool:
        """Check if field is changed."""
        return self._store.is_changed(field_name)

    def get_cache(self, key: str, default: Any = None) -> Any:
        """Get cached value."""
        return self._store.get_cache(key, default)

    def set_cache(self, key: str, value: Any) -> None:
        """Set cached value."""
        self._store.set_cache(key, value)

    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._store.clear_cache()


# Type alias for data store
DataStore = ModelDataStore[ModelT]
