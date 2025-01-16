"""Base relation field type."""

from abc import abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.types import ModelInterface

M = TypeVar("M", bound=ModelInterface)


class BaseRelationField(Field[M], Generic[M]):
    """Base relation field.

    This is the base class for all relation fields. It provides:
    - Basic field functionality (validation, conversion, etc.)
    - Asynchronous methods for converting values
    - Abstract methods that must be implemented by subclasses
    """

    def __init__(
        self,
        model: Type[M],
        *,
        required: bool = False,
        unique: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            model: Related model class
            required: Whether field is required
            unique: Whether field value must be unique
        """
        super().__init__(
            required=required,
            unique=unique,
            **kwargs,
        )
        self.model = model

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return self.model

    @abstractmethod
    async def async_convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance asynchronously.

        This method is called when a value needs to be converted to a model instance,
        but the conversion requires database access (e.g. looking up referenced models).

        Args:
            value: Value to convert

        Returns:
            Converted model instance or None if value is None

        Raises:
            ValueError: If value cannot be converted
        """
        pass

    @abstractmethod
    async def async_to_dict(self, value: Optional[M]) -> Any:
        """Convert model instance to dict representation asynchronously.

        This method is called when a model instance needs to be converted to a dict,
        but the conversion requires database access (e.g. looking up referenced models).

        Args:
            value: Model instance to convert

        Returns:
            Dict representation of model instance or None if value is None
        """
        pass

    @abstractmethod
    async def async_to_mongo(self, value: Optional[M]) -> Any:
        """Convert Python value to MongoDB value asynchronously.

        This method is called when a model instance needs to be converted to a MongoDB value,
        but the conversion requires database access (e.g. looking up referenced models).

        Args:
            value: Model instance to convert

        Returns:
            MongoDB representation of model instance or None if value is None
        """
        pass

    @abstractmethod
    async def async_from_mongo(self, value: Any) -> Optional[M]:
        """Convert MongoDB value to Python value asynchronously.

        This method is called when a MongoDB value needs to be converted to a model instance,
        but the conversion requires database access (e.g. looking up referenced models).

        Args:
            value: MongoDB value to convert

        Returns:
            Converted model instance or None if value is None

        Raises:
            ValueError: If value cannot be converted
        """
        pass
