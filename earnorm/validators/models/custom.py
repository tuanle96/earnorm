"""Custom model validators.

This module provides custom validators for model validation:
- Model validators
- Field validators
- Async validators
"""

from typing import Any, Coroutine, Optional, TypeVar

from earnorm.base.types import ModelProtocol
from earnorm.validators.base import BaseValidator

M = TypeVar("M", bound=ModelProtocol)


class ModelValidator(BaseValidator):
    """Base model validator.

    Examples:
        ```python
        class UserValidator(ModelValidator):
            def __call__(self, model: User) -> None:
                if model.age < 18:
                    raise ValidationError("User must be 18 or older")
        ```
    """

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize validator.

        Args:
            message: Custom error message
        """
        super().__init__(message)

    def __call__(self, model: ModelProtocol) -> None:
        """Validate model.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        pass


class FieldsValidator(ModelValidator):
    """Validator for multiple fields.

    Examples:
        ```python
        class UserFieldsValidator(FieldsValidator):
            def validate_fields(self, model: User) -> None:
                if model.age < 18 and model.role == "admin":
                    raise ValidationError("Admin must be 18 or older")
        ```
    """

    def __call__(self, model: ModelProtocol) -> None:
        """Validate model fields.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        self.validate_fields(model)

    def validate_fields(self, model: ModelProtocol) -> None:
        """Validate model fields.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        pass


class AsyncModelValidator(BaseValidator):
    """Base async model validator.

    Examples:
        ```python
        class UserValidator(AsyncModelValidator):
            async def __call__(self, model: User) -> None:
                if not await is_valid_email(model.email):
                    raise ValidationError("Invalid email")
        ```
    """

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize validator.

        Args:
            message: Custom error message
        """
        super().__init__(message)

    def __call__(self, model: ModelProtocol) -> Coroutine[Any, Any, None]:
        """Validate model.

        Args:
            model: Model to validate

        Returns:
            Coroutine that validates model

        Raises:
            ValidationError: If validation fails
        """
        return self._validate(model)

    async def _validate(self, model: ModelProtocol) -> None:
        """Internal validation method.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        pass


class AsyncFieldsValidator(AsyncModelValidator):
    """Async validator for multiple fields.

    Examples:
        ```python
        class UserFieldsValidator(AsyncFieldsValidator):
            async def validate_fields(self, model: User) -> None:
                if not await is_unique_email(model.email):
                    raise ValidationError("Email already exists")
        ```
    """

    def __call__(self, model: ModelProtocol) -> Coroutine[Any, Any, None]:
        """Validate model fields.

        Args:
            model: Model to validate

        Returns:
            Coroutine that validates model fields

        Raises:
            ValidationError: If validation fails
        """
        return self._validate(model)

    async def _validate(self, model: ModelProtocol) -> None:
        """Internal validation method.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        await self.validate_fields(model)

    async def validate_fields(self, model: ModelProtocol) -> None:
        """Validate model fields.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        pass
