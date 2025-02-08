"""One-to-one relationship field implementation.

This module provides the OneToOneField class for defining one-to-one relationships
between models.

Examples:
    ```python
    class User(BaseModel):
        _name = "user"
        profile = fields.OneToOneField(
            "profile",
            field="user_id",
            required=True,
            ondelete="cascade"
        )

    class Profile(BaseModel):
        _name = "profile"
        user = fields.OneToOneField(
            "user",
            field="profile_id",
            required=True,
            ondelete="cascade"
        )
    ```
"""

from typing import Any, Dict, Optional, Type, TypeVar, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.relation.base import RelatedModelProtocol, RelationField

# Type variable for model type
M = TypeVar("M", bound=RelatedModelProtocol[Any])


class OneToOneField(RelationField[M]):
    """One-to-one relationship field.

    This field represents a one-to-one relationship between models.
    Only one record can be linked to another record through this field.

    Examples:
        >>> class User(Model):
        ...     profile = OneToOneField(
        ...         "profile",  # Use _name of model, not class name
        ...         field="user_id",
        ...         required=True,
        ...         ondelete="cascade"
        ...     )
    """

    def __init__(
        self,
        model_ref: str,
        field: str,
        *,
        ondelete: str = "set null",
        required: bool = False,
        index: bool = True,
        cascade_validation: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize one-to-one field.

        Args:
            model_ref: Referenced model name (_name attribute, not class name)
            field: Field name for the foreign key
            ondelete: Delete behavior ("cascade", "set null", "restrict")
            required: Whether the relationship is required
            index: Whether to create an index on the foreign key
            cascade_validation: Whether to cascade validation to related record
            **kwargs: Additional field options

        Raises:
            ValueError: If ondelete value is invalid
        """
        # Force unique=True for one-to-one relationships
        kwargs["unique"] = True

        super().__init__(
            model_ref,
            field=field,
            ondelete=ondelete,
            required=required,
            index=index,
            cascade_validation=cascade_validation,
            **kwargs,
        )

    async def _check_existing_relationship(
        self, value: M, context: Dict[str, Any]
    ) -> bool:
        """Check if a one-to-one relationship already exists.

        Args:
            value: Related record to check
            context: Validation context

        Returns:
            bool: True if relationship exists
        """
        # Get current model class
        model_class = context.get("model_class")
        if model_class is None:
            return False

        # Check if another record has this relationship
        existing = await model_class.search(
            [
                (self.field, "=", str(value.id)),
                ("id", "!=", context.get("record_id")),
            ]
        )

        return bool(existing)

    async def validate(
        self, value: Optional[M], context: Optional[Dict[str, Any]] = None
    ) -> Optional[M]:
        """Validate field value.

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            Optional[M]: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        # Run base validation first
        await super().validate(value, context)

        # Check unique constraint
        if value is not None and context is not None:
            if await self._check_existing_relationship(value, context):
                raise FieldValidationError(
                    f"Another record already has a one-to-one relationship with {value}",
                    field_name=self.name,
                    code="duplicate_relationship",
                )

        return value

    async def __get__(
        self, instance: Optional[Any] = None, owner: Optional[Type[Any]] = None
    ) -> Union[M, "OneToOneField[M]"]:
        """Get the related record.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Union[M, OneToOneField[M]]: Related record or field instance
        """
        if instance is None:
            return self

        value = instance.__dict__.get(self.name)

        # Return value if already loaded
        if (
            value is not None
            and self._model_class is not None
            and isinstance(value, self._model_class)
        ):
            return cast(M, value)

        return cast(M, None)

    def __set__(self, instance: Any, value: Optional[M]) -> None:
        """Set the related record.

        Args:
            instance: Model instance
            value: Related record or None

        Raises:
            FieldValidationError: If value is not a valid model instance
        """
        if value is not None:
            if self._model_class is None:
                raise FieldValidationError(
                    message=f"Model class not resolved for field {self.name}",
                    field_name=self.name,
                    code="model_not_resolved",
                )
            if not isinstance(value, self._model_class):
                raise FieldValidationError(
                    message=f"{self.name} must be instance of {self.model_ref}",
                    field_name=self.name,
                    code="invalid_type",
                )

        instance.__dict__[self.name] = value

    def _create_back_reference(self) -> RelationField[M]:
        """Create back reference field.

        Returns:
            RelationField: Back reference field instance
        """
        from earnorm.fields.relation.one_to_one import OneToOneField

        return OneToOneField(
            self.model_name,
            field=self.name,
            ondelete=self.ondelete,
            cascade=self.cascade,
            lazy_load=self.lazy_load,
            domain=self.domain,
            context=self.context,
        )
