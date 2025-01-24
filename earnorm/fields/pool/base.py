"""Field pool base implementation.

This module provides the base field pool system for managing field instances.
It supports:
- Field instance pooling
- Resource cleanup
- Reference counting
- Memory optimization
- Thread safety

Examples:
    >>> pool = FieldPool()
    >>> field = StringField()
    >>> pool.add(field)
    >>> field = pool.get(field.id)
    >>> pool.remove(field.id)
"""

from threading import Lock
from typing import Any, Dict, Optional, Set
from uuid import UUID, uuid4

from earnorm.fields.base import Field


class FieldPool:
    """Pool for managing field instances.

    Attributes:
        fields: Dictionary mapping field IDs to field instances
        references: Dictionary mapping field IDs to reference counts
        _lock: Thread lock for synchronization
    """

    def __init__(self) -> None:
        """Initialize field pool."""
        self.fields: Dict[UUID, Field[Any]] = {}
        self.references: Dict[UUID, int] = {}
        self._lock = Lock()

    def add(self, field: Field[Any]) -> None:
        """Add field to pool.

        Args:
            field: Field instance to add
        """
        with self._lock:
            # Generate UUID if field doesn't have one
            field_id = getattr(field, "id", None) or uuid4()
            setattr(field, "id", field_id)

            if field_id not in self.fields:
                self.fields[field_id] = field
                self.references[field_id] = 1
            else:
                self.references[field_id] += 1

    def get(self, field_id: UUID) -> Optional[Field[Any]]:
        """Get field from pool.

        Args:
            field_id: ID of field to get

        Returns:
            Field instance if found, None otherwise
        """
        with self._lock:
            field = self.fields.get(field_id)
            if field is not None:
                self.references[field_id] += 1
            return field

    def remove(self, field_id: UUID) -> None:
        """Remove field from pool.

        Args:
            field_id: ID of field to remove
        """
        with self._lock:
            if field_id in self.references:
                self.references[field_id] -= 1
                if self.references[field_id] <= 0:
                    del self.references[field_id]
                    del self.fields[field_id]

    def clear(self) -> None:
        """Clear all fields from pool."""
        with self._lock:
            self.fields.clear()
            self.references.clear()

    def cleanup(self) -> None:
        """Clean up unused fields."""
        with self._lock:
            unused: Set[UUID] = set()
            for field_id, count in self.references.items():
                if count <= 0:
                    unused.add(field_id)
            for field_id in unused:
                del self.references[field_id]
                del self.fields[field_id]

    def get_field_ids(self) -> Set[UUID]:
        """Get IDs of all fields in pool.

        Returns:
            Set of field IDs
        """
        with self._lock:
            return set(self.fields.keys())

    def get_reference_count(self, field_id: UUID) -> int:
        """Get reference count for field.

        Args:
            field_id: ID of field to get reference count for

        Returns:
            Reference count
        """
        with self._lock:
            return self.references.get(field_id, 0)

    def has_field(self, field_id: UUID) -> bool:
        """Check if field exists in pool.

        Args:
            field_id: ID of field to check

        Returns:
            True if field exists, False otherwise
        """
        with self._lock:
            return field_id in self.fields

    async def setup(self) -> None:
        """Set up field pool."""
        with self._lock:
            for field in self.fields.values():
                if hasattr(field, "setup"):
                    await field.setup()  # type: ignore

    async def cleanup_async(self) -> None:
        """Clean up field pool asynchronously."""
        with self._lock:
            for field in self.fields.values():
                if hasattr(field, "cleanup"):
                    await field.cleanup()  # type: ignore
            self.cleanup()
