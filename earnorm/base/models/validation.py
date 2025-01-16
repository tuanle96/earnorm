"""Model validation implementation."""

from __future__ import annotations

from typing import Dict, List, cast

from earnorm.base.fields.metadata import FieldMetadata
from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.types import ContainerProtocol
from earnorm.di import container


class ValidationError(Exception):
    """Validation error.

    This exception is raised when model validation fails.
    It contains a dictionary of field errors.

    Attributes:
        errors: Dictionary mapping field names to error messages
    """

    def __init__(self, errors: Dict[str, List[str]]) -> None:
        """Initialize error.

        Args:
            errors: Dictionary mapping field names to error messages
        """
        self.errors = errors
        message = "\n".join(
            f"{field}: {', '.join(msgs)}" for field, msgs in errors.items()
        )
        super().__init__(message)


class Validator:
    """Model validator.

    This class handles model validation:
    - Field validation
    - Type checking
    - Required fields
    - Custom validators
    """

    async def validate(self, model: ModelInterface) -> None:
        """Validate model.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        errors: Dict[str, List[str]] = {}

        # Get model metadata
        metadata = self._get_model_metadata(model)

        # Validate fields
        for field_name, field_meta in metadata.items():
            try:
                value = getattr(model, field_name, None)
                field_meta.validate(value)
            except (ValueError, TypeError) as e:
                if field_name not in errors:
                    errors[field_name] = []
                errors[field_name].append(str(e))

        if errors:
            raise ValidationError(errors)

    def _get_model_metadata(self, model: ModelInterface) -> Dict[str, FieldMetadata]:
        """Get model metadata.

        Args:
            model: Model instance

        Returns:
            Dict mapping field names to metadata
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry  # type: ignore

        # Get model class name
        model_class = model.__class__
        model_name = getattr(model_class, "name", "")

        # Get metadata from registry
        try:
            metadata = registry.get_metadata(model_name)  # type: ignore
            if metadata:
                return cast(Dict[str, FieldMetadata], metadata)
        except AttributeError:
            pass

        return {}
