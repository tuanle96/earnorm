"""Unique field validator.

This module provides validators for ensuring field values are unique in the database.
"""

from typing import Any, Coroutine, Dict, Optional, Type

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.types import ModelProtocol
from earnorm.validators.base import BaseValidator, ValidationError


class UniqueValidator(BaseValidator):
    """Unique field validator.

    Examples:
        ```python
        # Create validator
        validate_unique = UniqueValidator(
            collection=db.users,
            field="email",
            model_class=User
        )

        # Use validator
        await validate_unique("user@example.com")  # OK if email is unique
        await validate_unique("existing@example.com")  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],
        field: str,
        model_class: Type[ModelProtocol],
        message: Optional[str] = None,
        case_sensitive: bool = True,
        exclude_id: Optional[ObjectId] = None,
    ) -> None:
        """Initialize validator.

        Args:
            collection: MongoDB collection to check uniqueness against
            field: Field name to check uniqueness for
            model_class: Model class for the collection
            message: Custom error message
            case_sensitive: Whether to perform case-sensitive comparison
            exclude_id: ObjectId to exclude from uniqueness check (for updates)
        """
        super().__init__(message)
        self.collection = collection
        self.field = field
        self.model_class = model_class
        self.case_sensitive = case_sensitive
        self.exclude_id = exclude_id

    def __call__(self, value: Any) -> Coroutine[Any, Any, None]:
        """Validate value is unique.

        Args:
            value: Value to validate

        Returns:
            Coroutine that validates uniqueness

        Raises:
            ValidationError: If value is not unique
        """
        return self._validate(value)

    async def _validate(self, value: Any) -> None:
        """Internal validation method.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is not unique
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        # Build query
        query: Dict[str, Any] = {}
        if self.case_sensitive:
            query[self.field] = value
        else:
            query[self.field] = {"$regex": f"^{value}$", "$options": "i"}

        # Exclude current document if updating
        if self.exclude_id is not None:
            query["_id"] = {"$ne": self.exclude_id}

        # Check if document exists
        document = await self.collection.find_one(query)
        if document is not None:
            raise ValidationError(
                self.message
                or f"Value '{value}' already exists for field '{self.field}'"
            )


def validate_unique(
    collection: AsyncIOMotorCollection[Dict[str, Any]],
    field: str,
    model_class: Type[ModelProtocol],
    message: Optional[str] = None,
    case_sensitive: bool = True,
    exclude_id: Optional[ObjectId] = None,
) -> UniqueValidator:
    """Create unique field validator.

    Args:
        collection: MongoDB collection to check uniqueness against
        field: Field name to check uniqueness for
        model_class: Model class for the collection
        message: Custom error message
        case_sensitive: Whether to perform case-sensitive comparison
        exclude_id: ObjectId to exclude from uniqueness check (for updates)

    Returns:
        Validator that checks field uniqueness

    Examples:
        ```python
        # Create validator
        validate_unique_email = validate_unique(
            collection=db.users,
            field="email",
            model_class=User
        )

        # Use validator
        await validate_unique_email("user@example.com")  # OK if email is unique
        await validate_unique_email("existing@example.com")  # Raises ValidationError
        ```
    """
    return UniqueValidator(
        collection=collection,
        field=field,
        model_class=model_class,
        message=message,
        case_sensitive=case_sensitive,
        exclude_id=exclude_id,
    )
