"""Reference field validators.

This module provides validators for reference fields, including:
- Existence validation
- Reference integrity validation
"""

from typing import Any, Coroutine, Dict, Optional, Type

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.types import ModelInterface
from earnorm.validators.base import BaseValidator, ValidationError


class ExistsValidator(BaseValidator):
    """Reference existence validator.

    Examples:
        ```python
        # Create validator
        validate_exists = ExistsValidator(
            collection=db.users,
            model_class=User
        )

        # Use validator
        await validate_exists("507f1f77bcf86cd799439011")  # OK if ID exists
        await validate_exists("507f1f77bcf86cd799439012")  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],
        model_class: Type[ModelInterface],
        message: Optional[str] = None,
    ) -> None:
        """Initialize validator.

        Args:
            collection: MongoDB collection to check existence against
            model_class: Model class for the collection
            message: Custom error message
        """
        super().__init__(message)
        self.collection = collection
        self.model_class = model_class

    def __call__(self, value: Any) -> Coroutine[Any, Any, None]:
        """Validate reference exists.

        Args:
            value: Value to validate (ObjectId or string)

        Returns:
            Coroutine that validates existence

        Raises:
            ValidationError: If reference does not exist
        """
        return self._validate(value)

    async def _validate(self, value: Any) -> None:
        """Internal validation method.

        Args:
            value: Value to validate (ObjectId or string)

        Raises:
            ValidationError: If reference does not exist
        """
        # Convert string to ObjectId
        if isinstance(value, str):
            try:
                value = ObjectId(value)
            except InvalidId:
                raise ValidationError("Invalid ObjectId format")

        if not isinstance(value, ObjectId):
            raise ValidationError("Value must be an ObjectId or string")

        # Check if document exists
        document = await self.collection.find_one({"_id": value})
        if document is None:
            raise ValidationError(
                self.message or f"Document with ID '{value}' does not exist"
            )


def validate_exists(
    collection: AsyncIOMotorCollection[Dict[str, Any]],
    model_class: Type[ModelInterface],
    message: Optional[str] = None,
) -> ExistsValidator:
    """Create reference existence validator.

    Args:
        collection: MongoDB collection to check existence against
        model_class: Model class for the collection
        message: Custom error message

    Returns:
        Validator that checks reference existence

    Examples:
        ```python
        # Create validator
        validate_user_exists = validate_exists(
            collection=db.users,
            model_class=User
        )

        # Use validator
        await validate_user_exists("507f1f77bcf86cd799439011")  # OK if ID exists
        await validate_user_exists("507f1f77bcf86cd799439012")  # Raises ValidationError
        ```
    """
    return ExistsValidator(
        collection=collection,
        model_class=model_class,
        message=message,
    )
