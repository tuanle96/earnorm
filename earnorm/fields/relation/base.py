"""Base relation field type.

This module provides the base class for all relation fields.
It includes:
- Basic field functionality
- Database backend support
- Asynchronous operations
- Type validation

Examples:
    >>> from earnorm.fields.relation.base import BaseRelationField
    >>> from earnorm.base.model.base import BaseModel
    >>>
    >>> class CustomRelationField(BaseRelationField[BaseModel]):
    ...     def __init__(self, model: type[BaseModel], **kwargs):
    ...         super().__init__(model, **kwargs)
    ...
    ...     async def convert(self, value: Any) -> Optional[BaseModel]:
    ...         # Custom conversion logic
    ...         pass
"""

from abc import abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar, cast

from bson import ObjectId

from earnorm.base.model.base import BaseModel
from earnorm.fields.base import Field, ValidationError
from earnorm.fields.interface import DatabaseValue

M = TypeVar("M", bound=BaseModel)


class BaseRelationField(Field[M], Generic[M]):
    """Base class for all relation fields.

    This class provides:
    - Basic field functionality
    - Database backend support
    - Asynchronous operations
    - Type validation

    Attributes:
        model: Related model class
        required: Whether field is required
        unique: Whether field value must be unique
        index: Whether to create database index
        model_name: Name of model class
    """

    def __init__(
        self,
        model: Type[M],
        *,
        required: bool = False,
        unique: bool = False,
        index: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            model: Related model class
            required: Whether field is required
            unique: Whether field value must be unique
            index: Whether to create database index
            **kwargs: Additional field options
        """
        super().__init__(required=required, unique=unique, **kwargs)
        self.model = model
        self.unique = unique
        self.index = index
        self.model_name = model.__name__

        # Set backend options
        self.backend_options: dict[str, dict[str, Any]] = {
            "mongodb": {
                "type": "objectId",
                "required": self.required,
                "unique": self.unique,
                "index": self.index,
            },
            "postgres": {
                "type": "UUID",
                "null": not self.required,
                "unique": self.unique,
                "index": (
                    f"CREATE INDEX IF NOT EXISTS {self.name}_idx ON {self.model_name} ({self.name})"
                    if self.index
                    else None
                ),
            },
            "mysql": {
                "type": "CHAR(24)",
                "null": not self.required,
                "unique": self.unique,
                "index": (
                    f"CREATE INDEX {self.name}_idx ON {self.model_name} ({self.name})"
                    if self.index
                    else None
                ),
            },
        }

    async def validate(self, value: Any) -> None:
        """Validate relation value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)
        if value is None:
            return

        if not isinstance(value, (self.model, ObjectId, str)):
            raise ValidationError(
                f"Field {self.name} must be an instance of {self.model.__name__}, ObjectId, or str",
                self.name,
            )

    async def to_db(self, value: Any, backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        Args:
            value: Value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database value
        """
        if value is None:
            return None

        # Convert to ObjectId
        if isinstance(value, self.model):
            value = value.id  # type: ignore[attr-defined]
        elif isinstance(value, str):
            try:
                value = ObjectId(value)
            except Exception as e:
                raise ValidationError(f"Invalid ObjectId: {str(e)}", self.name)

        # MongoDB stores ObjectId as is
        if backend == "mongodb":
            return value

        # PostgreSQL and MySQL store ObjectId as string
        return str(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[M]:
        """Convert database value to Python format.

        Args:
            value: Database value
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Python value
        """
        if value is None:
            return None

        # Convert string to ObjectId for PostgreSQL and MySQL
        if backend in ("postgres", "mysql") and isinstance(value, str):
            try:
                value = ObjectId(value)
            except Exception as e:
                raise ValidationError(f"Invalid ObjectId: {str(e)}", self.name)

        return cast(M, value)

    @abstractmethod
    async def async_convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted model instance or None if value is None

        Raises:
            ValidationError: If conversion fails
        """
        pass

    @abstractmethod
    async def async_to_dict(self, value: Optional[M]) -> Optional[dict[str, Any]]:
        """Convert model instance to dict representation asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            Dict representation of model instance or None if value is None

        Raises:
            ValidationError: If conversion fails
        """
        pass
