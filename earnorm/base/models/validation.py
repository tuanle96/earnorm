"""Model validation."""

from typing import Dict, List, Union

from earnorm.base.fields.metadata import FieldMetadata
from earnorm.base.types import ModelProtocol
from earnorm.validators.models.custom import AsyncModelValidator, ModelValidator


class Validator:
    """Model validator.

    This class handles model validation including:
    - Field validation
    - Model validation
    - Custom validation rules
    """

    def __init__(self) -> None:
        """Initialize validator."""
        self._validators: List[Union[ModelValidator, AsyncModelValidator]] = []

    def add_validator(
        self, validator: Union[ModelValidator, AsyncModelValidator]
    ) -> None:
        """Add model validator.

        Args:
            validator: Validator to add
        """
        self._validators.append(validator)

    async def validate(self, model: ModelProtocol) -> None:
        """Validate model.

        Args:
            model: Model to validate

        Raises:
            ValidationError: If validation fails
        """
        # Get model metadata
        metadata = self._get_model_metadata(model)

        # Validate fields
        for field_name, field_metadata in metadata.items():
            field = field_metadata.field
            value = getattr(model, field_name, None)

            # Skip if field is not required and value is None
            if not field.required and value is None:
                continue

            # Validate field value
            field.validate(value)

        # Run model validators
        for validator in self._validators:
            if isinstance(validator, AsyncModelValidator):
                await validator(model)
            else:
                validator(model)

    def _get_model_metadata(self, model: ModelProtocol) -> Dict[str, FieldMetadata]:
        """Get model field metadata.

        Args:
            model: Model instance

        Returns:
            Dict[str, FieldMetadata]: Dictionary mapping field names to their metadata objects
        """
        metadata: Dict[str, FieldMetadata] = {}

        # Get all field metadata
        for name, field in model.__class__.__dict__.items():
            if isinstance(field, FieldMetadata):
                metadata[name] = field

        return metadata
