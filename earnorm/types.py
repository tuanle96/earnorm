"""Type definitions for EarnORM.

This module defines the core interfaces used throughout EarnORM:
- ModelInterface: Protocol for model classes
- FieldProtocol: Protocol for field classes
"""

from abc import abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class ModelInterface(Protocol):
    """Protocol for model classes.

    This protocol defines the interface that all model classes must implement.
    It includes methods for converting between Python objects and MongoDB documents.

    Attributes:
        data: Dictionary containing the model's data
        id: Model's unique identifier
    """

    data: Dict[str, Any]

    @property
    @abstractmethod
    def id(self) -> Optional[str]:
        """Get model ID.

        Returns:
            Model's unique identifier or None if not saved
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dict representation.

        Returns:
            Dict containing the model's data in Python format
        """
        pass

    @abstractmethod
    def to_mongo(self) -> Dict[str, Any]:
        """Convert model to MongoDB representation.

        Returns:
            Dict containing the model's data in MongoDB format
        """
        pass

    @abstractmethod
    def from_mongo(self, data: Dict[str, Any]) -> None:
        """Convert MongoDB data to model.

        Args:
            data: Dict containing the model's data in MongoDB format
        """
        pass

    @classmethod
    @abstractmethod
    async def find_by_id(cls, id: str) -> Optional["ModelInterface"]:
        """Find model by ID.

        Args:
            id: Model ID

        Returns:
            Model instance if found, None otherwise
        """
        pass


@runtime_checkable
class FieldProtocol(Protocol):
    """Protocol for field classes.

    This protocol defines the interface that all field classes must implement.
    It includes methods for validation, conversion, and serialization of field values.

    Attributes:
        name: Name of the field
    """

    name: str

    @property
    @abstractmethod
    def metadata(self) -> Any:
        """Get field metadata.

        Returns:
            Metadata object containing field configuration
        """
        pass

    @abstractmethod
    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    def convert(self, value: Any) -> Any:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value
        """
        pass

    @abstractmethod
    def to_dict(self, value: Any) -> Any:
        """Convert value to dict representation.

        Args:
            value: Value to convert

        Returns:
            Dict representation of value
        """
        pass

    @abstractmethod
    def to_mongo(self, value: Any) -> Any:
        """Convert value to MongoDB representation.

        Args:
            value: Value to convert

        Returns:
            MongoDB representation of value
        """
        pass

    @abstractmethod
    def from_mongo(self, value: Any) -> Any:
        """Convert MongoDB value to Python value.

        Args:
            value: Value to convert

        Returns:
            Python representation of value
        """
        pass
