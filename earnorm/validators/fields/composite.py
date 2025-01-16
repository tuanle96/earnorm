"""Composite field validators.

This module provides validators for composite fields, including:
- List length validation
- List item validation
- Dict key/value validation
- Dict schema validation
"""

from typing import Any, Dict, Optional, Sequence, TypeVar, Union

from earnorm.validators.base import BaseValidator, ValidationError
from earnorm.validators.types import ValidatorFunc

T = TypeVar("T")


class ListLengthValidator(BaseValidator):
    """List length validator.

    Examples:
        ```python
        # Create validator
        validate_length = ListLengthValidator(min_length=1, max_length=5)

        # Use validator
        validate_length([1, 2, 3])  # OK
        validate_length([])  # Raises ValidationError
        validate_length([1, 2, 3, 4, 5, 6])  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """Initialize validator.

        Args:
            min_length: Minimum length allowed
            max_length: Maximum length allowed
            message: Custom error message
        """
        super().__init__(message)
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value: Union[Sequence[T], Any]) -> None:
        """Validate list length.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If list length is invalid
        """
        if not isinstance(value, (list, tuple)):
            raise ValidationError("Value must be a list or tuple")

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                self.message or f"List length must be at least {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                self.message or f"List length must be at most {self.max_length}"
            )


class ListItemValidator(BaseValidator):
    """List item validator.

    Examples:
        ```python
        # Create validator
        validate_items = ListItemValidator(lambda x: x > 0)

        # Use validator
        validate_items([1, 2, 3])  # OK
        validate_items([1, -2, 3])  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        item_validator: ValidatorFunc,
        message: Optional[str] = None,
    ) -> None:
        """Initialize validator.

        Args:
            item_validator: Validator function for list items
            message: Custom error message
        """
        super().__init__(message)
        self.item_validator = item_validator

    def __call__(self, value: Union[Sequence[Any], Any]) -> None:
        """Validate list items.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If any list item is invalid
        """
        if not isinstance(value, (list, tuple)):
            raise ValidationError("Value must be a list or tuple")

        for i, item in enumerate(value):
            try:
                self.item_validator(item)
            except ValidationError as e:
                raise ValidationError(
                    self.message or f"Invalid item at index {i}: {e.message}"
                )


class DictSchemaValidator(BaseValidator):
    """Dict schema validator.

    Examples:
        ```python
        # Create validator
        validate_schema = DictSchemaValidator({
            "name": lambda x: isinstance(x, str),
            "age": lambda x: isinstance(x, int) and x >= 0
        })

        # Use validator
        validate_schema({"name": "John", "age": 30})  # OK
        validate_schema({"name": "John"})  # Raises ValidationError
        validate_schema({"name": "John", "age": -1})  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        schema: Dict[str, ValidatorFunc],
        message: Optional[str] = None,
    ) -> None:
        """Initialize validator.

        Args:
            schema: Dict of field names and validator functions
            message: Custom error message
        """
        super().__init__(message)
        self.schema = schema

    def __call__(self, value: Any) -> None:  # type: ignore
        """Validate dict against schema.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If dict does not match schema
        """
        if not isinstance(value, dict):
            raise ValidationError("Value must be a dict")

        for field, validator in self.schema.items():
            if field not in value:
                raise ValidationError(
                    self.message or f"Missing required field: {field}"
                )
            try:
                validator(value[field])  # type: ignore
            except ValidationError as e:
                raise ValidationError(
                    self.message or f"Invalid value for field {field}: {e.message}"
                )


def validate_list_length(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    message: Optional[str] = None,
) -> ValidatorFunc:
    """Create list length validator.

    Args:
        min_length: Minimum length allowed
        max_length: Maximum length allowed
        message: Custom error message

    Returns:
        Validator function that checks list length

    Examples:
        ```python
        # Create validator
        validate_length = validate_list_length(min_length=1, max_length=5)

        # Use validator
        validate_length([1, 2, 3])  # OK
        validate_length([])  # Raises ValidationError
        validate_length([1, 2, 3, 4, 5, 6])  # Raises ValidationError
        ```
    """
    return ListLengthValidator(min_length, max_length, message)


def validate_list_items(
    item_validator: ValidatorFunc,
    message: Optional[str] = None,
) -> ValidatorFunc:
    """Create list item validator.

    Args:
        item_validator: Validator function for list items
        message: Custom error message

    Returns:
        Validator function that checks list items

    Examples:
        ```python
        # Create validator
        validate_items = validate_list_items(lambda x: x > 0)

        # Use validator
        validate_items([1, 2, 3])  # OK
        validate_items([1, -2, 3])  # Raises ValidationError
        ```
    """
    return ListItemValidator(item_validator, message)


def validate_dict_schema(
    schema: Dict[str, ValidatorFunc],
    message: Optional[str] = None,
) -> ValidatorFunc:
    """Create dict schema validator.

    Args:
        schema: Dict of field names and validator functions
        message: Custom error message

    Returns:
        Validator function that checks dict schema

    Examples:
        ```python
        # Create validator
        validate_schema = validate_dict_schema({
            "name": lambda x: isinstance(x, str),
            "age": lambda x: isinstance(x, int) and x >= 0
        })

        # Use validator
        validate_schema({"name": "John", "age": 30})  # OK
        validate_schema({"name": "John"})  # Raises ValidationError
        validate_schema({"name": "John", "age": -1})  # Raises ValidationError
        ```
    """
    return DictSchemaValidator(schema, message)
