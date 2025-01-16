"""Model type definitions."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from bson import ObjectId

from earnorm.base.types import DocumentType


@runtime_checkable
class FieldProtocol(Protocol):
    """Field protocol.

    This protocol defines the interface for field types:
    - Validation
    - Type conversion
    - Serialization
    - MongoDB conversion

    Attributes:
        name: Field name
        _metadata: Field metadata
    """

    name: str
    _metadata: Any

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        ...

    def convert(self, value: Any) -> Any:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        ...

    def to_dict(self, value: Any) -> Any:
        """Convert value to dict representation.

        Args:
            value: Value to convert

        Returns:
            Dict representation
        """
        ...

    def to_mongo(self, value: Any) -> Any:
        """Convert Python value to MongoDB value.

        Args:
            value: Value to convert

        Returns:
            MongoDB value
        """
        ...

    def from_mongo(self, value: Any) -> Any:
        """Convert MongoDB value to Python value.

        Args:
            value: Value to convert

        Returns:
            Python value
        """
        ...


@runtime_checkable
class ModelProtocol(Protocol):
    """Model protocol.

    This protocol defines the interface for models:
    - Data access (id, data)
    - CRUD operations (find_by_id, save, delete)

    Attributes:
        id: Model ID
        data: Model data
    """

    id: Optional[ObjectId]
    data: DocumentType

    @classmethod
    async def find_by_id(cls, id: ObjectId) -> Optional[ModelProtocol]:
        """Find model by ID.

        Args:
            id: Model ID

        Returns:
            Optional[ModelProtocol]: Found model or None
        """
        ...

    async def save(self) -> None:
        """Save model.

        Raises:
            ValidationError: If validation fails
            PersistenceError: If save fails
        """
        ...

    async def delete(self) -> None:
        """Delete model.

        Raises:
            PersistenceError: If delete fails
        """
        ...
